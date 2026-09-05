"""Security helpers for BackupCheckup."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import threading
import time
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from .const import (
    MAX_ARCHIVE_MEMBERS,
    MAX_BACKUP_METADATA_BYTES,
    MAX_FREE_SPACE_RESERVE_BYTES,
    MAX_VERIFICATION_STAGING_DIRECTORY_LENGTH,
    MIN_FREE_SPACE_RESERVE_BYTES,
    STAGING_DIRECTORY_RELATIVE_PARTS,
    STAGING_DIRECTORY_RESERVED_RELATIVE_PARTS,
    STALE_TEMP_DIRECTORY_AGE_HOURS,
)

_TEMP_PREFIX = "backup_checkup_"
_GB = 1_000_000_000
_MAX_LOG_VALUE_LENGTH = 160
_MAX_ERROR_TYPE_LENGTH = 80
_MAX_DISPLAY_NAME_LENGTH = 128


@dataclass(frozen=True, slots=True)
class TempCleanupResult:
    """Summarize startup cleanup without exposing temporary paths."""

    failures: int = 0
    remaining: int = 0

    @property
    def issue_active(self) -> bool:
        """Return whether sensitive temporary data may still remain."""
        return self.failures > 0 or self.remaining > 0


class VerificationLimitError(Exception):
    """Raised when a verification safety limit is reached."""

    def __init__(self, code: str) -> None:
        """Initialize the error with a stable privacy-safe code."""
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class VerificationBudget:
    """Track resource use and deadlines during one integrity check."""

    deadline: float
    max_download_bytes: int
    max_expanded_bytes: int
    max_members: int = MAX_ARCHIVE_MEMBERS
    max_metadata_bytes: int = MAX_BACKUP_METADATA_BYTES
    free_space_reserve_bytes: int = MIN_FREE_SPACE_RESERVE_BYTES
    downloaded_bytes: int = 0
    expanded_bytes: int = 0
    members: int = 0
    cancellation_event: threading.Event = field(
        default_factory=threading.Event,
        repr=False,
    )

    @classmethod
    def from_options(
        cls,
        *,
        max_download_gb: int,
        max_expanded_gb: int,
        timeout_minutes: int,
    ) -> VerificationBudget:
        """Create a budget from validated integration options."""
        values = (max_download_gb, max_expanded_gb, timeout_minutes)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in values
        ):
            raise VerificationLimitError("invalid_verification_budget")
        return cls(
            deadline=time.monotonic() + timeout_minutes * 60,
            max_download_bytes=max_download_gb * _GB,
            max_expanded_bytes=max_expanded_gb * _GB,
        )

    def for_copy(self) -> VerificationBudget:
        """Return fresh per-copy counters sharing the deadline and cancel flag."""
        self.check_deadline()
        return VerificationBudget(
            deadline=self.deadline,
            max_download_bytes=self.max_download_bytes,
            max_expanded_bytes=self.max_expanded_bytes,
            max_members=self.max_members,
            max_metadata_bytes=self.max_metadata_bytes,
            free_space_reserve_bytes=self.free_space_reserve_bytes,
            cancellation_event=self.cancellation_event,
        )

    def cancel(self) -> None:
        """Ask cooperative worker code to stop at its next safety check."""
        self.cancellation_event.set()

    def remaining_seconds(self) -> float:
        """Return the remaining overall verification time."""
        if self.cancellation_event.is_set():
            raise VerificationLimitError("verification_cancelled")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise VerificationLimitError("verification_timeout")
        return remaining

    def check_deadline(self) -> None:
        """Raise when the overall verification deadline has expired."""
        self.remaining_seconds()

    @staticmethod
    def _require_nonnegative(size: int, *, code: str) -> None:
        """Reject invalid negative accounting values."""
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise VerificationLimitError(code)

    def validate_expected_download(self, expected_size: int | None) -> None:
        """Reject a known backup size above the configured download limit."""
        if expected_size is None:
            return
        self._require_nonnegative(expected_size, code="download_size_limit")
        if expected_size > self.max_download_bytes:
            raise VerificationLimitError("download_size_limit")

    def add_downloaded(self, size: int) -> None:
        """Account for downloaded bytes and enforce the limit."""
        self._require_nonnegative(size, code="download_size_limit")
        self.check_deadline()
        self.downloaded_bytes += size
        if self.downloaded_bytes > self.max_download_bytes:
            raise VerificationLimitError("download_size_limit")

    def add_expanded(self, size: int) -> None:
        """Account for bytes read from expanded archive members."""
        self._require_nonnegative(size, code="expanded_size_limit")
        self.check_deadline()
        self.expanded_bytes += size
        if self.expanded_bytes > self.max_expanded_bytes:
            raise VerificationLimitError("expanded_size_limit")

    def ensure_expanded_capacity(self, size: int) -> None:
        """Reject a declared member size that cannot fit in the remaining budget."""
        self._require_nonnegative(size, code="expanded_size_limit")
        self.check_deadline()
        if self.expanded_bytes + size > self.max_expanded_bytes:
            raise VerificationLimitError("expanded_size_limit")

    def add_member(self) -> None:
        """Account for an archive member and enforce the member-count limit."""
        self.check_deadline()
        self.members += 1
        if self.members > self.max_members:
            raise VerificationLimitError("archive_member_limit")

    def check_metadata_size(self, size: int) -> None:
        """Reject oversized backup metadata."""
        self._require_nonnegative(size, code="metadata_size_limit")
        self.check_deadline()
        if size > self.max_metadata_bytes:
            raise VerificationLimitError("metadata_size_limit")

    def check_free_space(self, path: Path, required_bytes: int = 0) -> None:
        """Ensure the temporary filesystem keeps a safety reserve."""
        self._require_nonnegative(required_bytes, code="insufficient_free_space")
        self.check_deadline()
        usage = shutil.disk_usage(path)
        dynamic_reserve = max(
            self.free_space_reserve_bytes,
            min(usage.total // 10, MAX_FREE_SPACE_RESERVE_BYTES),
        )
        if usage.free - required_bytes < dynamic_reserve:
            raise VerificationLimitError("insufficient_free_space")


def classify_exception(error: BaseException) -> str:
    """Map an arbitrary exception to a stable privacy-safe error code."""
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, PermissionError):
        return "permission_denied"
    if isinstance(error, ConnectionError):
        return "connection_error"
    if isinstance(error, FileNotFoundError):
        return "not_found"
    if isinstance(error, OSError):
        return "io_error"

    name = type(error).__name__.lower()
    if "auth" in name or "credential" in name or "login" in name:
        return "authentication_error"
    if "timeout" in name:
        return "timeout"
    if "connect" in name or "network" in name:
        return "connection_error"
    return "unknown_error"


def safe_log_value(value: object, *, max_length: int = _MAX_LOG_VALUE_LENGTH) -> str:
    """Return a single-line bounded representation for untrusted log values."""
    try:
        text = str(value)
    except Exception:  # noqa: BLE001 - third-party boundary by design
        text = f"<unprintable:{type(value).__name__}>"
    cleaned = "".join(
        character
        if character == " "
        or unicodedata.category(character) not in {"Cc", "Cf", "Zl", "Zp"}
        else "?"
        for character in text
    )
    return cleaned[: max(0, max_length)]


def safe_error_type(error: BaseException) -> str:
    """Return a bounded log-safe exception class name."""
    return safe_log_value(type(error).__name__, max_length=_MAX_ERROR_TYPE_LENGTH)


def safe_display_name(value: object, *, fallback: str) -> str:
    """Return a bounded single-line user-facing name."""
    if isinstance(value, str):
        cleaned = safe_log_value(value, max_length=_MAX_DISPLAY_NAME_LENGTH).strip()
        if cleaned:
            return cleaned
    cleaned_fallback = safe_log_value(
        fallback,
        max_length=_MAX_DISPLAY_NAME_LENGTH,
    ).strip()
    return cleaned_fallback or "Backup storage"


def anonymous_backup_reference(entry_id: str, backup_id: str) -> str:
    """Return a stable installation-local reference without exposing the backup ID."""
    digest = hashlib.sha256(f"{entry_id}:{backup_id}".encode()).hexdigest()
    return digest[:12]


def anonymous_agent_reference(entry_id: str, agent_id: str) -> str:
    """Return a stable installation-local storage reference."""
    digest = hashlib.sha256(f"{entry_id}:agent:{agent_id}".encode()).hexdigest()
    return digest[:10]


def backup_scope_fingerprint(
    *,
    entry_id: str,
    homeassistant_included: bool | None,
    database_included: bool | None,
    addons: tuple[str, ...],
    folders: tuple[str, ...],
) -> str:
    """Return a stable content-scope fingerprint for size comparisons."""
    payload = json.dumps(
        {
            "homeassistant": homeassistant_included,
            "database": database_included,
            "addons": addons,
            "folders": folders,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(f"{entry_id}:{payload}".encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class StagingCapacity:
    """Privacy-safe capacity summary of the verification staging filesystem."""

    available: bool
    total_bytes: int | None = None
    free_bytes: int | None = None


def default_staging_root(config_dir: str | Path) -> Path:
    """Return the automatic staging location below the configuration directory.

    Home Assistant excludes ``.cache/*`` from its own backups, so verification
    copies staged here are never captured by a backup that starts meanwhile.
    """
    return Path(config_dir).joinpath(*STAGING_DIRECTORY_RELATIVE_PARTS)


def resolve_staging_root(config_dir: str | Path, custom_directory: str) -> Path:
    """Return the configured staging root or the automatic default."""
    candidate = custom_directory.strip() if isinstance(custom_directory, str) else ""
    if candidate:
        return Path(os.path.normpath(candidate))
    return default_staging_root(config_dir)


def _is_within(path: Path, parent: Path) -> bool:
    """Return whether ``path`` equals or lies below ``parent``."""
    try:
        return os.path.commonpath([path, parent]) == str(parent)
    except ValueError:
        return False


def validate_staging_directory(candidate: str, *, config_dir: str | Path) -> str | None:
    """Validate a user-supplied staging directory and return an error code.

    This performs blocking filesystem checks and must run in an executor. The
    returned codes are stable and never contain the checked path.
    """
    if not isinstance(candidate, str):
        return "staging_directory_invalid"
    text = candidate.strip()
    if not text:
        return None
    if (
        len(text) > MAX_VERIFICATION_STAGING_DIRECTORY_LENGTH
        or "\x00" in text
        or not os.path.isabs(text)
    ):
        return "staging_directory_not_absolute"
    path = Path(os.path.normpath(text))
    try:
        stat_result = path.lstat()
    except FileNotFoundError:
        return "staging_directory_missing"
    except OSError:
        return "staging_directory_invalid"
    if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISDIR(stat_result.st_mode):
        return "staging_directory_invalid"

    config_root = Path(config_dir).resolve()
    resolved = path.resolve()
    if resolved == default_staging_root(config_root).resolve():
        # The automatic location is always acceptable; BackupCheckup owns it.
        return None
    if resolved == config_root or resolved.parent == resolved:
        return "staging_directory_reserved"
    for relative_parts in STAGING_DIRECTORY_RESERVED_RELATIVE_PARTS:
        if _is_within(resolved, config_root.joinpath(*relative_parts)):
            return "staging_directory_reserved"

    if not os.access(path, os.W_OK | os.X_OK):
        return "staging_directory_not_writable"
    try:
        probe = Path(tempfile.mkdtemp(prefix=f"{_TEMP_PREFIX}probe_", dir=path))
    except OSError:
        return "staging_directory_not_writable"
    with suppress(OSError):
        probe.rmdir()
    return None


def _prepare_staging_root(root: Path) -> None:
    """Create the staging root and keep the directories BackupCheckup owns private."""
    if root.exists():
        if root.is_symlink() or not root.is_dir():
            raise NotADirectoryError(str(root))
        return
    root.mkdir(parents=True, exist_ok=True)
    with suppress(OSError):
        root.chmod(0o700)


def staging_capacity(root: Path) -> StagingCapacity:
    """Return the capacity of the filesystem that will hold verification data."""
    probe = root
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            return StagingCapacity(available=False)
        probe = parent
    try:
        usage = shutil.disk_usage(probe)
    except OSError:
        return StagingCapacity(available=False)
    return StagingCapacity(
        available=True, total_bytes=usage.total, free_bytes=usage.free
    )


def remove_default_staging_root(root: Path) -> bool:
    """Delete the automatic staging root and everything BackupCheckup staged there."""
    try:
        if root.is_symlink() or not root.exists():
            return True
        shutil.rmtree(root)
    except OSError:
        return False
    return True


def create_private_temp_directory(root: Path) -> Path:
    """Create a private per-verification directory below the staging root."""
    _prepare_staging_root(root)
    path = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX, dir=root))
    try:
        path.chmod(0o700)
    except OSError:
        shutil.rmtree(path, ignore_errors=True)
        raise
    return path


def open_private_binary_writer(path: Path) -> BinaryIO:
    """Create a new private binary file and return an open writer."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        return os.fdopen(descriptor, "wb")
    except Exception:
        # Cleanup errors must never hide the original fdopen failure.
        with suppress(OSError):
            os.close(descriptor)
        with suppress(OSError):
            path.unlink(missing_ok=True)
        raise


def cleanup_temp_directory(path: Path) -> bool:
    """Remove one verification directory without following a symlink."""
    try:
        if path.is_symlink():
            return False
        shutil.rmtree(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _stale_temp_candidate_action(
    candidate: Path,
    *,
    root: Path,
    cutoff: float,
    current_uid: int | None,
) -> str:
    """Classify one temporary path as ignored, recent, removable, or failed."""
    if not candidate.name.startswith(_TEMP_PREFIX):
        return "ignore"
    try:
        stat_result = candidate.lstat()
        unsafe_type = stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISDIR(
            stat_result.st_mode
        )
        wrong_owner = current_uid is not None and stat_result.st_uid != current_uid
        wrong_parent = candidate.parent.resolve() != root
    except OSError:
        return "failed"
    if unsafe_type or wrong_owner or wrong_parent:
        return "ignore"
    return "recent" if stat_result.st_mtime > cutoff else "remove"


def legacy_temp_root() -> Path:
    """Return the process temporary directory used by releases before 3.1.0."""
    return Path(tempfile.gettempdir())


def cleanup_stale_temp_directories(root: Path) -> TempCleanupResult:
    """Remove stale BackupCheckup directories and report any data left behind."""
    try:
        root = root.resolve()
    except OSError:
        return TempCleanupResult(failures=1)
    if not root.is_dir():
        return TempCleanupResult()
    cutoff = time.time() - STALE_TEMP_DIRECTORY_AGE_HOURS * 3600
    current_uid = os.getuid() if hasattr(os, "getuid") else None
    try:
        candidates = list(root.iterdir())
    except OSError:
        return TempCleanupResult(failures=1)

    failures = 0
    remaining = 0
    for candidate in candidates:
        action = _stale_temp_candidate_action(
            candidate,
            root=root,
            cutoff=cutoff,
            current_uid=current_uid,
        )
        if action == "failed":
            failures += 1
        elif action == "recent":
            remaining += 1
        elif action == "remove" and not cleanup_temp_directory(candidate):
            failures += 1
            remaining += 1
    return TempCleanupResult(failures=failures, remaining=remaining)
