"""Exercise the folder identifiers of a backup without Home Assistant.

Home Assistant stores the "Local add-ons" folder as ``addons/local`` in
``backup.json`` while the Supervisor names the inner archive
``addons_local.tar.gz``. The structural verification used to reject every
folder name with a slash and reported an intact backup as corrupt.

This check builds real, unencrypted archives and verifies that such a backup
passes, that a missing folder archive, a real archive name collision and unsafe
folder names are still rejected, and that the log and the journal only ever name
a fixed internal rule code as the reason of a failure.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import io
import json
import logging
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
PACKAGE = "backup_checkup_folder_check"
FOLDERS = ("share", "addons/local", "ssl", "media")
ADDON_SLUG = "core_example"
INVALID_FOLDERS = (
    "../x",
    "a/../b",
    "/abs",
    "a/",
    "a//b",
    "a\\b",
    "",
    "x.tar.gz",
    "a/b.tar",
)


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


def _inner_archive(files: dict[str, bytes]) -> bytes:
    """Return one gzip-compressed inner archive, as the Supervisor writes it."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _metadata(folders: object, addon_slug: str = ADDON_SLUG) -> dict[str, object]:
    return {
        "protected": False,
        "homeassistant": {"exclude_database": False},
        "addons": [{"slug": addon_slug}],
        "folders": folders,
    }


def _backup(
    directory: Path,
    name: str,
    metadata: dict[str, object],
    archives: tuple[str, ...],
) -> Path:
    """Write a backup with ``backup.json`` and the named inner archives."""
    members: list[tuple[str, bytes]] = [("backup.json", json.dumps(metadata).encode())]
    for archive in archives:
        if archive == "homeassistant":
            files = {
                "data/configuration.yaml": b"default_config:\n",
                "data/home-assistant_v2.db": b"fixture database\n",
            }
        else:
            files = {f"{archive}/file.txt": b"content\n"}
        members.append((f"{archive}.tar.gz", _inner_archive(files)))
    path = directory / name
    with tarfile.open(path, "w") as outer:
        for member, content in members:
            info = tarfile.TarInfo(member)
            info.size = len(content)
            outer.addfile(info, io.BytesIO(content))
    return path


def _verify(integrity: ModuleType, security: ModuleType, backup: Path, root: Path):
    """Run the complete structural verification of one fixture."""
    working_dir = root / f"{backup.stem}-work"
    working_dir.mkdir()
    return integrity.BackupIntegrityVerifier._verify_archive(
        backup,
        working_dir,
        None,
        False,
        False,
        1,
        security.VerificationBudget(
            deadline=time.monotonic() + 60,
            max_download_bytes=10**9,
            max_expanded_bytes=10**9,
        ),
        integrity._ScanProgress(reporter=None, total=backup.stat().st_size),
    )


def _rejected_with(
    integrity: ModuleType,
    security: ModuleType,
    backup: Path,
    root: Path,
    code: str,
    label: str,
) -> None:
    """Require the verification to stop with exactly one internal rule code."""
    try:
        _verify(integrity, security, backup, root)
    except KeyError as err:
        _require(
            err.args == (code,),
            f"{label}: expected {code}, got {security.safe_reason_code(err)}",
        )
        _require(
            security.safe_reason_code(err) == code,
            f"{label}: the rule code {code} is not reported as the reason",
        )
        return
    raise SystemExit(f"{label}: the backup was accepted, expected {code}")


# --- checks -----------------------------------------------------------------


def _check_supported_folders(
    integrity: ModuleType, security: ModuleType, root: Path
) -> None:
    """(a) A backup with ``addons/local`` passes without a warning."""
    archives = ("homeassistant", ADDON_SLUG, "share", "addons_local", "ssl", "media")
    backup = _backup(root, "supported.tar", _metadata(list(FOLDERS)), archives)
    try:
        details = _verify(integrity, security, backup, root)
    except Exception as err:  # noqa: BLE001 - every failure fails the check
        raise SystemExit(
            "A backup with the folder addons/local was rejected: "
            f"{type(err).__name__}{err.args}"
        ) from None
    _require(
        details["warnings"] == [],
        f"A backup with the folder addons/local reports warnings: {details['warnings']}",
    )
    _require(
        details["archive_count"] == len(archives),
        f"Expected {len(archives)} inner archives, got {details['archive_count']}",
    )


def _check_missing_folder_archive(
    integrity: ModuleType, security: ModuleType, root: Path
) -> None:
    """(b) A declared folder without its archive is still rejected."""
    archives = ("homeassistant", ADDON_SLUG, "share", "ssl", "media")
    backup = _backup(root, "missing.tar", _metadata(list(FOLDERS)), archives)
    _rejected_with(
        integrity,
        security,
        backup,
        root,
        "missing_expected_archives_count_1",
        "Missing addons_local archive",
    )


def _check_invalid_folders(
    integrity: ModuleType, security: ModuleType, root: Path
) -> None:
    """(c) Unsafe folder names are still rejected."""
    archives = ("homeassistant", ADDON_SLUG)
    for index, folder in enumerate(INVALID_FOLDERS):
        backup = _backup(root, f"invalid-{index}.tar", _metadata([folder]), archives)
        _rejected_with(
            integrity,
            security,
            backup,
            root,
            "backup_metadata_folders_invalid",
            f"Folder {folder!r}",
        )


def _check_archive_name_collision(
    integrity: ModuleType, security: ModuleType, root: Path
) -> None:
    """(d) An add-on and a folder that share one archive name collide."""
    backup = _backup(
        root,
        "collision.tar",
        _metadata(["addons/local"], addon_slug="addons_local"),
        ("homeassistant", "addons_local"),
    )
    _rejected_with(
        integrity,
        security,
        backup,
        root,
        "backup_metadata_archive_name_collision",
        "Add-on addons_local with folder addons/local",
    )


def _check_addon_identifier(integrity: ModuleType) -> None:
    """Add-on slugs keep the strict single-segment rule."""
    valid = integrity.BackupIntegrityVerifier._valid_archive_identifier
    _require(valid("core_example"), "A plain add-on slug must stay valid")
    _require(
        not valid("addons/local"), "An add-on slug with a slash must stay invalid"
    )


def _check_reason_codes(security: ModuleType) -> None:
    """(e) Only fixed internal rule codes are reported as a reason."""
    reason = security.safe_reason_code
    _require(
        reason(KeyError("backup_metadata_missing")) == "backup_metadata_missing",
        "An internal rule code must be reported",
    )
    foreign: tuple[BaseException, ...] = (
        KeyError("filename 'x/y' not found"),
        ValueError("Bad Path: /etc"),
        KeyError(),
        KeyError(5),
    )
    for error in foreign:
        _require(
            reason(error) is None,
            f"A foreign {type(error).__name__} message must never be reported",
        )


class _LogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _report_failure(
    integrity: ModuleType, error: Exception
) -> tuple[dict[str, object], str]:
    """Return the journal details and the log line of one rejected copy."""
    recorded: list[dict[str, object]] = []
    verifier = SimpleNamespace(
        _entry_id="entry",
        _record_archive_end=lambda *_args, details, **_kwargs: recorded.append(
            dict(details)
        ),
        _downloaded_result=lambda *_args, **_kwargs: None,
    )
    downloaded = SimpleNamespace(
        prepared=SimpleNamespace(protected=False, agent_id="agent")
    )
    capture = _LogCapture()
    logger = integrity._LOGGER
    logger.addHandler(capture)
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    try:
        integrity.BackupIntegrityVerifier._archive_failure_outcome(
            verifier,
            "corrupt",
            "archive_invalid",
            "One backup copy is corrupt or invalid; trying another",
            error,
            record=None,
            started=0.0,
            downloaded=downloaded,
            database_check=False,
        )
    finally:
        logger.removeHandler(capture)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
    _require(len(recorded) == 1, "A rejected copy must write one journal entry")
    _require(len(capture.messages) == 1, "A rejected copy must log one line")
    return recorded[0], capture.messages[0]


def _check_failure_report(integrity: ModuleType) -> None:
    """(f) Log and journal name the rule code and never a foreign message."""
    details, line = _report_failure(integrity, KeyError("backup_metadata_missing"))
    _require(
        details == {"error_code": "archive_invalid", "reason": "backup_metadata_missing"},
        f"The journal entry must carry the rule code: {details}",
    )
    _require(
        line.endswith("error_type=KeyError reason=backup_metadata_missing"),
        f"The log line must name the rule code: {line}",
    )
    secret = "filename 'private/name' not found"
    details, line = _report_failure(integrity, KeyError(secret))
    _require(
        details == {"error_code": "archive_invalid"},
        f"A foreign exception must not add a reason: {details}",
    )
    _require(
        line.endswith("error_type=KeyError") and "private" not in line,
        f"A foreign exception message must never be logged: {line}",
    )


def main() -> None:
    _install_stubs()
    security = _load_integration("security")
    integrity = _load_integration("integrity")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _check_supported_folders(integrity, security, root)
        _check_reason_codes(security)
        _check_failure_report(integrity)
        _check_addon_identifier(integrity)
        _check_missing_folder_archive(integrity, security, root)
        _check_invalid_folders(integrity, security, root)
        _check_archive_name_collision(integrity, security, root)
    print(
        "Backup folder identifiers verified: addons/local accepted, "
        f"{len(INVALID_FOLDERS)} unsafe names rejected"
    )


if __name__ == "__main__":
    main()
