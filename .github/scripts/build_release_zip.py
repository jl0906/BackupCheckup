"""Build the ZIP asset that the Marketplace (HACS) installs.

``hacs.json`` enables ``zip_release``: instead of the tagged repository source,
the asset named by ``filename`` is downloaded from the GitHub release and
unpacked into ``custom_components/backup_checkup``. The archive therefore holds
the integration files at its top level, without a wrapping folder.

``--check`` builds the archive in memory and validates it together with
``hacs.json``; ``--tag`` additionally requires the release tag to match the
manifest version.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
_EXCLUDED_DIRECTORIES = frozenset({"__pycache__", ".ruff_cache", ".pytest_cache"})
_EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})
_REQUIRED = ("manifest.json", "__init__.py", "strings.json", "translations/en.json")
# A fixed timestamp keeps two builds of the same source byte-identical.
_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def _files() -> list[Path]:
    """Return every file that belongs into the asset, in a stable order."""
    return sorted(
        path
        for path in INTEGRATION.rglob("*")
        if path.is_file()
        and not _EXCLUDED_DIRECTORIES.intersection(path.relative_to(INTEGRATION).parts)
        and path.suffix not in _EXCLUDED_SUFFIXES
    )


def build() -> bytes:
    """Return the archive with the integration files at its top level."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in _files():
            info = zipfile.ZipInfo(
                path.relative_to(INTEGRATION).as_posix(), date_time=_TIMESTAMP
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def _problems(data: bytes, tag: str | None) -> list[str]:
    """Validate the archive, hacs.json and the optional release tag."""
    problems: list[str] = []
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    if hacs.get("zip_release") is not True:
        problems.append("hacs.json must enable zip_release")
    if hacs.get("filename") != "backup_checkup.zip":
        problems.append("hacs.json filename must be backup_checkup.zip")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        if archive.testzip() is not None:
            problems.append("The archive is damaged")
        manifest = json.loads(archive.read("manifest.json")) if "manifest.json" in names else {}
    for required in _REQUIRED:
        if required not in names:
            problems.append(f"The archive lacks {required} at its top level")
    for name in sorted(names):
        if name.startswith(("custom_components/", "/")) or "__pycache__" in name:
            problems.append(f"Unexpected archive entry {name}")
    version = manifest.get("version")
    if tag is not None and tag.removeprefix("v") != version:
        problems.append(f"Release tag {tag} does not match manifest version {version}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the archive to this file")
    parser.add_argument("--tag", help="release tag that must match the manifest version")
    parser.add_argument("--check", action="store_true", help="only validate")
    arguments = parser.parse_args()
    data = build()
    problems = _problems(data, arguments.tag)
    if problems:
        print("\n".join(problems))
        return 1
    if arguments.output is not None and not arguments.check:
        arguments.output.write_bytes(data)
        print(f"Wrote {arguments.output} ({len(data)} bytes, {len(_files())} files)")
    else:
        print(f"Release ZIP asset is valid: {len(_files())} files, {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
