"""Exercise the shared archive member policy without Home Assistant.

The structural verification of the integration and the extraction of the
Runtime Runner must reach the same verdict on one archive. A backup with link
entries used to be reported as valid by the integration and then aborted the
runtime test with ``unsupported_archive_member``.

Both sides now apply one policy: safe relative links are accepted, unsafe links
and special files are skipped and reported. This check builds real archives and
runs both implementations against them.
"""

from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from types import ModuleType, SimpleNamespace

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
SERVER_PATH = (
    ROOT / "runtime_runner" / "rootfs" / "opt" / "backup-checkup-runner" / "server.py"
)
PACKAGE = "backup_checkup_link_policy_check"
CONFIGURATION = b"default_config:\n"
DEPENDENCY = b"VALUE = 1\n"


class _Anything:
    """Stand in for every Home Assistant name the modules only reference."""

    def __call__(self, *args: object, **kwargs: object) -> object:
        # Used as a decorator it must hand the decorated function back.
        if len(args) == 1 and not kwargs and callable(args[0]):
            return args[0]
        return _Anything()

    def __getattr__(self, name: str) -> object:
        if name.startswith("__"):
            raise AttributeError(name)
        return _Anything()

    def __getitem__(self, item: object) -> object:
        return self

    def __mro_entries__(self, bases: tuple[object, ...]) -> tuple[type, ...]:
        return (object,)

    def __or__(self, other: object) -> object:
        return self

    __ror__ = __or__


class _StubModule(ModuleType):
    def __getattr__(self, name: str) -> object:
        if name.startswith("__"):
            raise AttributeError(name)
        return _Anything()


class _HomeAssistantStubs(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve Home Assistant and its HTTP client with empty stand-in modules."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] not in {"homeassistant", "aiohttp"}:
            return None
        return importlib.machinery.ModuleSpec(fullname, self, is_package=True)

    def create_module(self, spec):
        module = _StubModule(spec.name)
        module.__path__ = []
        return module

    def exec_module(self, module) -> None:
        return None


class _PlainArchive:
    """Unencrypted stand-in for ``securetar.SecureTarArchive``."""

    def __init__(self, path, mode="r", *, bufsize=0, password=None) -> None:
        self._path = path
        self.tar: tarfile.TarFile | None = None

    def __enter__(self):
        self.tar = tarfile.open(self._path, "r")
        return self

    def __exit__(self, *_exc: object) -> None:
        if self.tar is not None:
            self.tar.close()


def _install_stubs() -> None:
    securetar = ModuleType("securetar")
    securetar.SecureTarArchive = _PlainArchive
    securetar.SecureTarError = type("SecureTarError", (Exception,), {})
    securetar.InvalidPasswordError = type(
        "InvalidPasswordError", (securetar.SecureTarError,), {}
    )
    sys.modules["securetar"] = securetar
    sys.meta_path.insert(0, _HomeAssistantStubs())


def _load_server() -> ModuleType:
    spec = importlib.util.spec_from_file_location("runner_server_link_policy", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load the runner server module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_integration(name: str) -> ModuleType:
    """Import one integration module as part of a private package."""
    if PACKAGE not in sys.modules:
        package = ModuleType(PACKAGE)
        package.__path__ = [str(INTEGRATION)]
        sys.modules[PACKAGE] = package
    return importlib.import_module(f"{PACKAGE}.{name}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


# --- fixtures ---------------------------------------------------------------


def _directory(name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    return info


def _link(name: str, target: str, kind: bytes = tarfile.SYMTYPE) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = target
    return info


def _inner_archive(entries: list[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for info, content in entries:
            if content is None:
                archive.addfile(info)
            else:
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _file(name: str, content: bytes) -> tuple[tarfile.TarInfo, bytes]:
    return tarfile.TarInfo(name), content


def _base_entries() -> list[tuple[tarfile.TarInfo, bytes | None]]:
    return [
        (_directory("data"), None),
        _file("data/configuration.yaml", CONFIGURATION),
        (_directory("data/custom_components"), None),
        _file("deps/x/__init__.py", DEPENDENCY),
        (_link("data/custom_components/x", "../../deps/x"), None),
    ]


def _mixed_fixture() -> bytes:
    """A regular file, a directory, safe and unsafe links and a FIFO."""
    fifo = tarfile.TarInfo("data/pipe")
    fifo.type = tarfile.FIFOTYPE
    return _inner_archive(
        [
            *_base_entries(),
            (_link("data/escape_relative", "../../../etc/passwd"), None),
            (_link("data/escape_absolute", "/etc/passwd"), None),
            (
                _link("data/configuration.copy", "data/configuration.yaml", tarfile.LNKTYPE),
                None,
            ),
            (fifo, None),
        ]
    )


def _safe_fixture() -> bytes:
    return _inner_archive(_base_entries())


def _backup(directory: Path, name: str, inner: bytes) -> Path:
    """Wrap one inner archive into a minimal Home Assistant backup."""
    metadata = json.dumps(
        {"protected": False, "homeassistant": {"exclude_database": True}}
    ).encode()
    path = directory / name
    with tarfile.open(path, "w") as outer:
        for member, content in (
            ("backup.json", metadata),
            ("homeassistant.tar", inner),
        ):
            info = tarfile.TarInfo(member)
            info.size = len(content)
            outer.addfile(info, io.BytesIO(content))
    return path


# --- (a) the shared function --------------------------------------------------


def _function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise SystemExit(f"{path.name} does not define {name}")


def _check_safe_link_target(server: ModuleType, security: ModuleType) -> None:
    _require(
        _function_source(SERVER_PATH, "_safe_link_target")
        == _function_source(INTEGRATION / "security.py", "_safe_link_target"),
        "_safe_link_target differs between the runner and the integration",
    )
    for constant in ("MAX_ARCHIVE_PATH_LENGTH", "MAX_ARCHIVE_PATH_DEPTH"):
        _require(
            getattr(server, constant) == getattr(security, constant),
            f"{constant} differs between the runner and the integration",
        )
    safe = {
        ("data/custom_components/x", "../../deps/x"): "deps/x",
        ("data/a", "b"): "data/b",
        ("data/a", "./b/c"): "data/b/c",
        ("data/a", ".."): ".",
        ("data/sub/a", "../other"): "data/other",
    }
    unsafe = [
        ("data/escape", "../../../etc/passwd"),
        ("data/escape", "/etc/passwd"),
        ("top", ".."),
        ("data/a", ""),
        ("data/a", "b\x00c"),
        ("data/a", "x" * 4097),
        # A ".." behind a name could cross another link on the file system.
        ("data/a", "b/../.."),
        ("data/a", "b/../c"),
        ("data/a", "/".join(["d"] * 64)),
    ]
    for module in (server, security):
        for (member, linkname), expected in safe.items():
            result = module._safe_link_target(member, linkname)
            _require(
                result == PurePosixPath(expected),
                f"{module.__name__}: {member} -> {linkname} returned {result}",
            )
        for member, linkname in unsafe:
            result = module._safe_link_target(member, linkname)
            _require(
                result is None,
                f"{module.__name__}: unsafe link {member} -> {linkname[:40]!r} "
                f"was accepted as {result}",
            )


# --- (b) runner ---------------------------------------------------------------


class _Symlinks:
    """Create real symlinks where possible and record them otherwise.

    Windows refuses ``os.symlink`` without a special privilege. The policy
    decisions are identical either way; only the final system call is replaced.
    """

    def __init__(self, server: ModuleType, probe: Path) -> None:
        self.recorded: dict[str, str] = {}
        try:
            os.symlink("target", probe / "probe")
        except OSError:
            self.real = False
            server.os = SimpleNamespace(
                **{name: getattr(os, name) for name in dir(os) if not name.startswith("__")}
            )
            server.os.symlink = self._record
        else:
            self.real = True
            (probe / "probe").unlink()

    def _record(self, source: str, destination: object) -> None:
        key = str(destination)
        if key in self.recorded or Path(key).exists():
            raise FileExistsError(key)
        self.recorded[key] = source

    def target(self, path: Path) -> str | None:
        if self.real:
            return os.readlink(path) if path.is_symlink() else None
        return self.recorded.get(str(path))


def _extract(server: ModuleType, backup: Path, target: Path, limit: int = 10**9):
    counts = server.ExtractionCounts()
    config_dir = server._extract_homeassistant(backup, target, None, limit, counts=counts)
    return config_dir, counts


def _check_runner(server: ModuleType, root: Path, symlinks: _Symlinks) -> None:
    backup = _backup(root, "mixed.tar", _mixed_fixture())
    target = root / "mixed"
    config_dir, counts = _extract(server, backup, target)
    _require(config_dir == target / "data", "The runner returned a wrong config path")
    _require(
        (target / "data" / "configuration.yaml").read_bytes() == CONFIGURATION,
        "The regular file was not extracted",
    )
    _require(
        symlinks.target(target / "data" / "custom_components" / "x") == "../../deps/x",
        "The safe symlink was not recreated with its raw relative target",
    )
    for name in ("escape_relative", "escape_absolute", "pipe"):
        path = target / "data" / name
        _require(
            symlinks.target(path) is None and not os.path.lexists(path),
            f"{name} must be skipped by the runner",
        )
    copy = target / "data" / "configuration.copy"
    _require(
        copy.is_file() and not copy.is_symlink() and copy.read_bytes() == CONFIGURATION,
        "The hard link was not materialized as a private copy",
    )
    _require(
        (counts.link_count, counts.unsafe_link_count, counts.skipped_member_count)
        == (2, 2, 1),
        f"Unexpected runner counters: {counts}",
    )

    # A hard-link copy counts towards the expanded size budget.
    exact = len(CONFIGURATION) * 2 + len(DEPENDENCY)
    _extract(server, backup, root / "exact", exact)
    try:
        _extract(server, backup, root / "tight", exact - 1)
    except server.RunnerFailure as error:
        _require(error.code == "expanded_size_limit", f"Unexpected code {error.code}")
    else:
        raise SystemExit("A hard-link copy escaped the expanded size limit")

    safe_backup = _backup(root, "safe.tar", _safe_fixture())
    _, safe_counts = _extract(server, safe_backup, root / "safe")
    _require(
        (safe_counts.link_count, safe_counts.unsafe_link_count, safe_counts.skipped_member_count)
        == (1, 0, 0),
        f"Unexpected runner counters for safe links: {safe_counts}",
    )
    _require(
        (root / "safe" / "deps" / "x" / "__init__.py").read_bytes() == DEPENDENCY,
        "The archive with safe links was not extracted completely",
    )

    source = SERVER_PATH.read_text(encoding="utf-8")
    _require(
        "unsupported_archive_member" not in source,
        "server.py still mentions unsupported_archive_member",
    )


# --- (c) and (d) integration --------------------------------------------------


def _budget(security: ModuleType):
    return security.VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=10**9,
        max_expanded_bytes=10**9,
    )


def _scan_inner(integrity: ModuleType, security: ModuleType, inner: bytes, root: Path):
    scan = integrity._ArchiveScan()
    files = integrity.BackupIntegrityVerifier._read_inner_archive(
        io.BytesIO(inner),
        scan=scan,
        database_check=False,
        database_path=root / "unused.db",
        budget=_budget(security),
        progress=integrity._ScanProgress(reporter=None, total=len(inner)),
    )
    return files, scan


def _verify(integrity: ModuleType, security: ModuleType, backup: Path, root: Path):
    """Run the complete structural verification and return its final result."""
    verifier = integrity.BackupIntegrityVerifier
    details = verifier._verify_archive(
        backup,
        root,
        None,
        False,
        False,
        1,
        _budget(security),
        integrity._ScanProgress(reporter=None, total=backup.stat().st_size),
    )
    record = SimpleNamespace(backup_id="id", backup_reference="ref", date=None)
    downloaded = SimpleNamespace(
        warnings=(),
        prepared=SimpleNamespace(agent_id="agent"),
        digest="0" * 64,
        downloaded_size=backup.stat().st_size,
        checksum_changed=False,
    )
    return details, verifier._completed_result(
        record,
        started=time.monotonic(),
        downloaded=downloaded,
        details=details,
        prior_copy_failures=0,
    )


def _check_integration(
    integrity: ModuleType, security: ModuleType, const: ModuleType, root: Path
) -> None:
    files, scan = _scan_inner(integrity, security, _mixed_fixture(), root)
    _require(files == 2, f"files_checked must only count regular files, got {files}")
    _require(
        (scan.link_count, scan.unsafe_link_count, scan.skipped_member_count) == (2, 2, 1),
        f"Unexpected integration counters: {scan}",
    )
    details, result = _verify(integrity, security, root / "mixed.tar", root)
    _require(
        list(details["warnings"]) == ["archive_links_unsafe", "archive_members_skipped"],
        f"Unexpected warnings: {details['warnings']}",
    )
    _require(
        result.status == const.INTEGRITY_STATUS_VALID_WITH_WARNINGS,
        f"Unsafe links must yield valid_with_warnings, got {result.status}",
    )
    # backup.json plus the two regular files of the inner archive.
    _require(result.file_count == 3, f"Unexpected file count {result.file_count}")

    files, scan = _scan_inner(integrity, security, _safe_fixture(), root)
    _require(
        (files, scan.link_count, scan.unsafe_link_count, scan.skipped_member_count)
        == (2, 1, 0, 0),
        f"Unexpected integration counters for safe links: {scan}",
    )
    details, result = _verify(integrity, security, root / "safe.tar", root)
    _require(
        not details["warnings"] and result.status == const.INTEGRITY_STATUS_VALID,
        f"Safe links must stay valid without warnings, got {result.status} "
        f"{details['warnings']}",
    )


def _check_agreement(
    server: ModuleType, integrity: ModuleType, security: ModuleType, root: Path
) -> None:
    """A member behind a link is rejected by both sides, never by only one."""
    inner = _inner_archive(
        [
            (_directory("data"), None),
            _file("deps/keep", DEPENDENCY),
            (_link("data/link", "../deps"), None),
            _file("data/link/written-through-link", DEPENDENCY),
        ]
    )
    backup = _backup(root, "through-link.tar", inner)
    try:
        _extract(server, backup, root / "through-link")
    except server.RunnerFailure as error:
        _require(error.code == "unsafe_archive_path", f"Unexpected code {error.code}")
    else:
        raise SystemExit("The runner wrote a member through a link")
    try:
        _scan_inner(integrity, security, inner, root)
    except tarfile.ReadError as error:
        _require(
            str(error) == "unsafe_archive_member_path", f"Unexpected error {error}"
        )
    else:
        raise SystemExit("The integration accepted a member behind a link")


def main() -> None:
    _install_stubs()
    server = _load_server()
    security = _load_integration("security")
    integrity = _load_integration("integrity")
    const = _load_integration("const")
    _check_safe_link_target(server, security)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        symlinks = _Symlinks(server, root)
        _check_runner(server, root, symlinks)
        _check_integration(integrity, security, const, root)
        _check_agreement(server, integrity, security, root)
    mode = "real symlinks" if symlinks.real else "recorded symlinks (no OS privilege)"
    print(f"Archive member policy passed with {mode}")


if __name__ == "__main__":
    main()
