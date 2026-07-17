"""Safe cleanup of BackupCheckup private storage files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .const import DOMAIN

STORE_KINDS = ("history", "integrity", "notifications")
_STORE_PATTERN = re.compile(
    rf"^{re.escape(DOMAIN)}\.(?P<entry_id>[A-Za-z0-9_-]+)\."
    rf"(?P<kind>{'|'.join(STORE_KINDS)})$"
)


@dataclass(frozen=True, slots=True)
class StoreCleanupResult:
    """Outcome of a private-store cleanup pass."""

    removed: int = 0
    failed: int = 0


def cleanup_orphaned_store_files(
    storage_dir: Path,
    active_entry_ids: set[str],
) -> StoreCleanupResult:
    """Remove only BackupCheckup stores whose config entry no longer exists."""
    if not storage_dir.is_dir():
        return StoreCleanupResult()

    removed = 0
    failed = 0
    try:
        candidates = tuple(storage_dir.iterdir())
    except OSError:
        return StoreCleanupResult(failed=1)

    for path in candidates:
        match = _STORE_PATTERN.fullmatch(path.name)
        if match is None or match.group("entry_id") in active_entry_ids:
            continue
        try:
            if path.is_symlink() or not path.is_file():
                continue
        except OSError:
            failed += 1
            continue
        try:
            path.unlink()
        except OSError:
            failed += 1
        else:
            removed += 1
    return StoreCleanupResult(removed=removed, failed=failed)


def cleanup_entry_store_files(
    storage_dir: Path,
    entry_id: str,
) -> StoreCleanupResult:
    """Remove the three exact private stores belonging to one config entry."""
    if not isinstance(entry_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", entry_id):
        return StoreCleanupResult(failed=1)

    removed = 0
    failed = 0
    for kind in STORE_KINDS:
        path = storage_dir / f"{DOMAIN}.{entry_id}.{kind}"
        existed = path.exists() or path.is_symlink()
        try:
            path.unlink(missing_ok=True)
        except OSError:
            failed += 1
        else:
            if existed and not path.exists() and not path.is_symlink():
                removed += 1
    return StoreCleanupResult(removed=removed, failed=failed)
