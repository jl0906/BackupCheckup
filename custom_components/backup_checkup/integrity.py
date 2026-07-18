"""Full backup integrity verification for BackupCheckup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import tarfile
import time
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from homeassistant.components.backup import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from securetar import InvalidPasswordError, SecureTarArchive, SecureTarError

from .const import (
    DOMAIN,
    INTEGRITY_DATABASE_FAILED,
    INTEGRITY_DATABASE_NOT_APPLICABLE,
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_CORRUPT,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord
from .repairs import (
    async_set_storage_data_issue,
    async_set_temporary_cleanup_issue,
)
from .security import (
    VerificationBudget,
    VerificationLimitError,
    anonymous_agent_reference,
    cleanup_stale_temp_directories,
    cleanup_temp_directory,
    create_private_temp_directory,
    open_private_binary_writer,
    safe_error_type,
)

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1
_BUFFER_SIZE = 1024 * 1024
_FREE_SPACE_CHECK_INTERVAL = 64 * 1024 * 1024
_INNER_SUFFIXES = (".tar", ".tgz", ".tar.gz")
_KNOWN_OPTIONAL_INNER_ARCHIVES = frozenset({"supervisor"})
_DATABASE_FILENAME = "home-assistant_v2.db"
_DATABASE_PATH = PurePosixPath("data/home-assistant_v2.db")
_METADATA_PATH = PurePosixPath("backup.json")
_FAILURE_RANKS = {
    INTEGRITY_STATUS_ABORTED: 1,
    INTEGRITY_STATUS_UNREADABLE: 1,
    INTEGRITY_STATUS_PASSWORD_REQUIRED: 2,
    INTEGRITY_STATUS_INTERNAL_ERROR: 3,
    INTEGRITY_STATUS_CORRUPT: 4,
}
_GLOBAL_LIMIT_CODES = frozenset(
    {
        "verification_cancelled",
        "verification_timeout",
        "database_timeout",
        "insufficient_free_space",
    }
)


class _DuplicateJsonKeyError(ValueError):
    """Raised when backup metadata contains duplicate JSON keys."""


class _BackupPasswordRequiredError(Exception):
    """Raised when archive metadata requires a password that is unavailable."""


@dataclass(slots=True)
class _DatabaseCheckControl:
    """Track cooperative SQLite timeout and cancellation state."""

    budget: VerificationBudget
    deadline: float
    timed_out: bool = False
    cancelled: bool = False

    def progress_handler(self) -> int:
        """Return non-zero when SQLite should abort its current operation."""
        if self.budget.cancellation_event.is_set():
            self.cancelled = True
            return 1
        if time.monotonic() >= self.deadline:
            self.timed_out = True
            return 1
        return 0

    def raise_if_stopped(self) -> None:
        """Raise the stable resource-limit error matching the stop reason."""
        if self.cancelled or self.budget.cancellation_event.is_set():
            raise VerificationLimitError("verification_cancelled")
        if self.timed_out or time.monotonic() >= self.deadline:
            raise VerificationLimitError("database_timeout")


@dataclass(frozen=True, slots=True)
class IntegrityStoreState:
    """Persisted integrity result plus automatic retry and manual cooldown state."""

    result: BackupIntegrityResult
    retry_backup_id: str | None = None
    retry_error_key: str | None = None
    retry_attempts: int = 0
    retry_not_before: datetime | None = None
    password_marker: str | None = None
    last_manual_verification_at: datetime | None = None

    @property
    def retry_key(self) -> tuple[str, str] | None:
        """Return the runtime retry key when both persisted parts exist."""
        if self.retry_backup_id and self.retry_error_key:
            return (self.retry_backup_id, self.retry_error_key)
        return None


@dataclass(frozen=True, slots=True)
class _CandidateOutcome:
    """Result of one storage-copy attempt."""

    result: BackupIntegrityResult | None
    final: bool = False
    download_failed: bool = False


@dataclass(frozen=True, slots=True)
class _PreparedCandidate:
    """Validated per-copy resources before downloading a backup."""

    agent_id: str
    path: Path
    budget: VerificationBudget
    expected_size: int | None
    protected: bool


@dataclass(frozen=True, slots=True)
class _DownloadedCandidate:
    """Downloaded storage copy with integrity metadata."""

    prepared: _PreparedCandidate
    downloaded_size: int
    digest: str
    warnings: tuple[str, ...]
    checksum_changed: bool


@dataclass(slots=True)
class _ArchiveScan:
    """Counts and logical names collected from the streamed outer archive."""

    archive_count: int = 0
    file_count: int = 0
    inner_names: set[str] = field(default_factory=set)


@dataclass(slots=True)
class _VerificationFailures:
    """Aggregate failed-copy state while redundant locations are attempted."""

    best: BackupIntegrityResult | None = None
    copy_failures: int = 0
    download_failures: int = 0

    def record(self, outcome: _CandidateOutcome) -> None:
        """Remember one recoverable candidate failure."""
        self.copy_failures += 1
        if outcome.download_failed:
            self.download_failures += 1
        result = outcome.result
        if result is None:
            return
        if self.best is None or _FAILURE_RANKS.get(
            result.status, 0
        ) > _FAILURE_RANKS.get(self.best.status, 0):
            self.best = result


class BackupIntegrityStore:
    """Persist the last result and bounded retry metadata in one private Store."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store."""
        self._hass = hass
        self._entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.integrity",
            private=True,
            atomic_writes=True,
        )
        self._loaded = False
        self._load_lock = asyncio.Lock()
        self._state = IntegrityStoreState(BackupIntegrityResult.not_checked())
        self._result = self._state.result

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse one persisted timestamp and normalize it to aware UTC."""
        if not isinstance(value, str):
            return None
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return dt_util.as_utc(parsed)

    @staticmethod
    def _bounded_store_text(value: Any, maximum: int) -> str | None:
        """Return one non-empty bounded string from persisted private state."""
        return value[:maximum] if isinstance(value, str) and value else None

    @staticmethod
    def _retry_attempts(value: Any) -> int:
        """Return a bounded retry count from persisted private state."""
        if isinstance(value, bool) or not isinstance(value, int):
            return 0
        return value if 0 <= value <= 100 else 0

    @classmethod
    def _result_and_runtime_data(
        cls,
        stored: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], str | None, datetime | None]:
        """Split legacy result-only data from the current state envelope."""
        result_data = stored.get("result")
        if result_data is None:
            return stored, {}, None, None
        retry_data = stored.get("retry")
        return (
            result_data,
            retry_data if isinstance(retry_data, dict) else {},
            cls._bounded_store_text(stored.get("password_marker"), 128),
            cls._parse_datetime(stored.get("last_manual_verification_at")),
        )

    @classmethod
    def _state_from_stored(cls, stored: dict[str, Any]) -> IntegrityStoreState:
        """Read both the legacy result shape and the 2.2.4+ envelope."""
        result_data, retry_data, password_marker, last_manual = (
            cls._result_and_runtime_data(stored)
        )
        if not isinstance(
            result_data, dict
        ) or not BackupIntegrityResult.storage_dict_is_valid(result_data):
            raise ValueError("invalid_store_content")

        return IntegrityStoreState(
            result=BackupIntegrityResult.from_dict(result_data),
            retry_backup_id=cls._bounded_store_text(retry_data.get("backup_id"), 256),
            retry_error_key=cls._bounded_store_text(retry_data.get("error_key"), 128),
            retry_attempts=cls._retry_attempts(retry_data.get("attempts")),
            retry_not_before=cls._parse_datetime(retry_data.get("not_before")),
            password_marker=password_marker,
            last_manual_verification_at=last_manual,
        )

    @staticmethod
    def _state_as_dict(state: IntegrityStoreState) -> dict[str, Any]:
        """Serialize the current envelope without exposing the backup password."""
        return {
            "result": state.result.as_dict(),
            "retry": {
                "backup_id": state.retry_backup_id,
                "error_key": state.retry_error_key,
                "attempts": state.retry_attempts,
                "not_before": (
                    state.retry_not_before.isoformat()
                    if state.retry_not_before
                    else None
                ),
            },
            "password_marker": state.password_marker,
            "last_manual_verification_at": (
                state.last_manual_verification_at.isoformat()
                if state.last_manual_verification_at
                else None
            ),
        }

    async def async_load_state(self) -> IntegrityStoreState:
        """Load persistent state once and recover from invalid private data."""
        if self._loaded:
            return self._state
        async with self._load_lock:
            if self._loaded:
                return self._state
            try:
                stored = await self._store.async_load()
                if stored is None:
                    async_set_storage_data_issue(
                        self._hass, store_name="integrity", active=False
                    )
                elif not isinstance(stored, dict):
                    raise ValueError("invalid_store_root")
                else:
                    self._state = self._state_from_stored(stored)
                    self._result = self._state.result
            except Exception as err:  # noqa: BLE001 - private store boundary
                _LOGGER.warning(
                    "Invalid integrity store data was reset: error_type=%s",
                    safe_error_type(err),
                )
                self._state = IntegrityStoreState(BackupIntegrityResult.not_checked())
                self._result = self._state.result
                async_set_storage_data_issue(
                    self._hass, store_name="integrity", active=True
                )
                try:
                    await self._store.async_save(self._state_as_dict(self._state))
                except Exception as save_err:  # noqa: BLE001 - storage boundary
                    _LOGGER.warning(
                        "Unable to persist repaired integrity state: error_type=%s",
                        safe_error_type(save_err),
                    )
            else:
                async_set_storage_data_issue(
                    self._hass, store_name="integrity", active=False
                )
            self._loaded = True
            return self._state

    async def async_load(self) -> BackupIntegrityResult:
        """Load and return the last integrity result."""
        return (await self.async_load_state()).result

    async def async_save_state(self, state: IntegrityStoreState) -> None:
        """Persist a complete normalized state envelope."""
        self._loaded = True
        self._state = state
        self._result = state.result
        await self._store.async_save(self._state_as_dict(state))

    async def async_save(
        self,
        result: BackupIntegrityResult,
        *,
        retry_key: tuple[str, str] | None = None,
        retry_attempts: int = 0,
        retry_not_before: datetime | None = None,
        password_marker: str | None = None,
        last_manual_verification_at: datetime | None = None,
    ) -> None:
        """Persist one completed result with its runtime control metadata."""
        current = await self.async_load_state()
        state = IntegrityStoreState(
            result=result,
            retry_backup_id=retry_key[0] if retry_key else None,
            retry_error_key=retry_key[1] if retry_key else None,
            retry_attempts=max(0, retry_attempts),
            retry_not_before=retry_not_before,
            password_marker=(
                password_marker
                if password_marker is not None
                else current.password_marker
            ),
            last_manual_verification_at=(
                last_manual_verification_at
                if last_manual_verification_at is not None
                else current.last_manual_verification_at
            ),
        )
        await self.async_save_state(state)

    async def async_update_runtime(
        self,
        *,
        password_marker: str | None,
        retry_key: tuple[str, str] | None,
        retry_attempts: int,
        retry_not_before: datetime | None,
        last_manual_verification_at: datetime | None,
    ) -> None:
        """Persist control metadata without changing the last result."""
        current = await self.async_load_state()
        await self.async_save_state(
            IntegrityStoreState(
                result=current.result,
                retry_backup_id=retry_key[0] if retry_key else None,
                retry_error_key=retry_key[1] if retry_key else None,
                retry_attempts=max(0, retry_attempts),
                retry_not_before=retry_not_before,
                password_marker=password_marker,
                last_manual_verification_at=last_manual_verification_at,
            )
        )

    async def async_remove(self) -> None:
        """Remove the stored integrity state."""
        await self._store.async_remove()


class BackupIntegrityVerifier:
    """Download and fully read a Home Assistant backup."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the verifier."""
        self.hass = hass
        self._entry_id = entry_id
        self.store = BackupIntegrityStore(hass, entry_id)

    async def async_verify(
        self,
        record: BackupRecord,
        *,
        database_check: bool,
        max_download_gb: int,
        max_expanded_gb: int,
        timeout_minutes: int,
        database_timeout_minutes: int,
        repair_issues_enabled: bool,
    ) -> BackupIntegrityResult:
        """Verify an available backup copy and fall back to another agent if needed."""
        started = time.monotonic()
        budget_or_failure = self._verification_budget(
            record,
            started=started,
            max_download_gb=max_download_gb,
            max_expanded_gb=max_expanded_gb,
            timeout_minutes=timeout_minutes,
        )
        if isinstance(budget_or_failure, BackupIntegrityResult):
            return budget_or_failure

        manager = async_get_manager(self.hass)
        manager_agents = getattr(manager, "backup_agents", None)
        if not isinstance(manager_agents, Mapping):
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                error_code="storage_agent_registry_invalid",
            )
        candidate_agents = self._candidate_agents(record, manager_agents)
        if not candidate_agents:
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                error_code="no_available_storage_agent",
            )

        temp_dir = await self._async_create_temp_directory(record, started)
        if isinstance(temp_dir, BackupIntegrityResult):
            return temp_dir

        failures = _VerificationFailures()
        try:
            previous = await self.store.async_load()
            for index, candidate_id in enumerate(candidate_agents):
                outcome = await self._async_verify_candidate(
                    record=record,
                    started=started,
                    overall_budget=budget_or_failure,
                    manager_agents=manager_agents,
                    candidate_id=candidate_id,
                    candidate_path=temp_dir / f"backup-{index}.tar",
                    temp_dir=temp_dir,
                    password=self._backup_password(manager),
                    previous=previous,
                    database_check=database_check,
                    database_timeout_minutes=database_timeout_minutes,
                    prior_copy_failures=failures.copy_failures,
                )
                if outcome.final:
                    if outcome.result is None:
                        return self._failure(
                            INTEGRITY_STATUS_INTERNAL_ERROR,
                            record,
                            started,
                            error_code="candidate_result_missing",
                        )
                    return outcome.result
                failures.record(outcome)

            return self._aggregate_failure(record, started, failures)
        finally:
            await self._async_cleanup_verification_data(
                temp_dir, repair_issues_enabled=repair_issues_enabled
            )

    @staticmethod
    def _verification_budget(
        record: BackupRecord,
        *,
        started: float,
        max_download_gb: int,
        max_expanded_gb: int,
        timeout_minutes: int,
    ) -> VerificationBudget | BackupIntegrityResult:
        """Build the global resource budget or a stable aborted result."""
        try:
            return VerificationBudget.from_options(
                max_download_gb=max_download_gb,
                max_expanded_gb=max_expanded_gb,
                timeout_minutes=timeout_minutes,
            )
        except VerificationLimitError as err:
            return BackupIntegrityVerifier._failure(
                INTEGRITY_STATUS_ABORTED,
                record,
                started,
                error_code=err.code,
            )

    async def _async_create_temp_directory(
        self, record: BackupRecord, started: float
    ) -> Path | BackupIntegrityResult:
        """Create private verification storage or return a stable failure."""
        try:
            return await self.hass.async_add_executor_job(create_private_temp_directory)
        except OSError as err:
            _LOGGER.warning(
                "Unable to create private verification storage: error_type=%s",
                safe_error_type(err),
            )
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                error_code="temporary_storage_unavailable",
            )

    async def _async_verify_candidate(
        self,
        *,
        record: BackupRecord,
        started: float,
        overall_budget: VerificationBudget,
        manager_agents: Mapping[str, Any],
        candidate_id: str,
        candidate_path: Path,
        temp_dir: Path,
        password: str | None,
        previous: BackupIntegrityResult,
        database_check: bool,
        database_timeout_minutes: int,
        prior_copy_failures: int,
    ) -> _CandidateOutcome:
        """Verify one prepared copy and classify whether another should be tried."""
        prepared = await self._async_prepare_candidate(
            record=record,
            started=started,
            overall_budget=overall_budget,
            candidate_id=candidate_id,
            candidate_path=candidate_path,
            temp_dir=temp_dir,
        )
        if isinstance(prepared, _CandidateOutcome):
            return prepared

        downloaded = await self._async_download_candidate(
            record=record,
            started=started,
            prepared=prepared,
            agent=manager_agents[candidate_id],
            previous=previous,
        )
        if isinstance(downloaded, _CandidateOutcome):
            return downloaded

        return await self._async_verify_downloaded_candidate(
            record=record,
            started=started,
            downloaded=downloaded,
            temp_dir=temp_dir,
            password=password,
            database_check=database_check,
            database_timeout_minutes=database_timeout_minutes,
            prior_copy_failures=prior_copy_failures,
        )

    async def _async_prepare_candidate(
        self,
        *,
        record: BackupRecord,
        started: float,
        overall_budget: VerificationBudget,
        candidate_id: str,
        candidate_path: Path,
        temp_dir: Path,
    ) -> _PreparedCandidate | _CandidateOutcome:
        """Allocate and validate one independent per-copy resource budget."""
        try:
            copy_budget = overall_budget.for_copy()
        except VerificationLimitError as err:
            return _CandidateOutcome(
                self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=candidate_id,
                    error_code=err.code,
                ),
                final=True,
            )

        copy = next(
            (item for item in record.agent_copies if item.agent_id == candidate_id),
            None,
        )
        expected_size = copy.size if copy else None
        protected = bool(copy and copy.protected)
        try:
            copy_budget.validate_expected_download(expected_size)
            await self.hass.async_add_executor_job(
                copy_budget.check_free_space, temp_dir, expected_size or 0
            )
        except VerificationLimitError as err:
            failure = self._failure(
                INTEGRITY_STATUS_ABORTED,
                record,
                started,
                agent_id=candidate_id,
                error_code=err.code,
            )
            return _CandidateOutcome(failure, final=err.code in _GLOBAL_LIMIT_CODES)
        return _PreparedCandidate(
            agent_id=candidate_id,
            path=candidate_path,
            budget=copy_budget,
            expected_size=expected_size,
            protected=protected,
        )

    async def _async_download_candidate(
        self,
        *,
        record: BackupRecord,
        started: float,
        prepared: _PreparedCandidate,
        agent: Any,
        previous: BackupIntegrityResult,
    ) -> _DownloadedCandidate | _CandidateOutcome:
        """Download one copy and map controlled boundary failures."""
        try:
            downloaded_size, digest = await self._async_download(
                agent, record.backup_id, prepared.path, prepared.budget
            )
        except VerificationLimitError as err:
            _LOGGER.warning(
                "Backup verification download stopped by safety limit: "
                "agent=%s code=%s",
                anonymous_agent_reference(self._entry_id, prepared.agent_id),
                err.code,
            )
            self._remove_candidate_file(prepared.path)
            return _CandidateOutcome(
                self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=prepared.agent_id,
                    error_code=err.code,
                ),
                final=err.code in _GLOBAL_LIMIT_CODES,
            )
        except TimeoutError:
            self._remove_candidate_file(prepared.path)
            return _CandidateOutcome(
                self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=prepared.agent_id,
                    error_code="verification_timeout",
                ),
                final=True,
            )
        except Exception as err:  # noqa: BLE001 - backup-agent download boundary
            _LOGGER.warning(
                "Unable to download one backup copy; trying another: "
                "agent=%s error_type=%s",
                anonymous_agent_reference(self._entry_id, prepared.agent_id),
                safe_error_type(err),
            )
            self._remove_candidate_file(prepared.path)
            return _CandidateOutcome(None, download_failed=True)

        warnings = self._candidate_warnings(
            record,
            expected_size=prepared.expected_size,
            downloaded_size=downloaded_size,
        )
        checksum_changed = bool(
            previous.backup_id == record.backup_id
            and previous.agent_id == prepared.agent_id
            and previous.sha256
            and previous.sha256 != digest
        )
        if checksum_changed:
            warnings.append("checksum_changed")
        return _DownloadedCandidate(
            prepared=prepared,
            downloaded_size=downloaded_size,
            digest=digest,
            warnings=tuple(warnings),
            checksum_changed=checksum_changed,
        )

    @staticmethod
    def _candidate_warnings(
        record: BackupRecord, *, expected_size: int | None, downloaded_size: int
    ) -> list[str]:
        """Return warnings known before archive inspection."""
        warnings: list[str] = []
        if record.copy_size_mismatch:
            warnings.append("storage_copy_size_mismatch")
        if expected_size is not None and downloaded_size != expected_size:
            warnings.append("reported_size_mismatch")
        return warnings

    async def _async_verify_downloaded_candidate(
        self,
        *,
        record: BackupRecord,
        started: float,
        downloaded: _DownloadedCandidate,
        temp_dir: Path,
        password: str | None,
        database_check: bool,
        database_timeout_minutes: int,
        prior_copy_failures: int,
    ) -> _CandidateOutcome:
        """Inspect a downloaded archive and produce a final or retryable result."""
        prepared = downloaded.prepared
        if prepared.protected and password is None:
            self._remove_candidate_file(prepared.path)
            return _CandidateOutcome(
                self._downloaded_result(
                    INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    record,
                    started,
                    downloaded,
                    error_code="password_required",
                )
            )

        database_path = temp_dir / _DATABASE_FILENAME
        try:
            database_path.unlink(missing_ok=True)
        except OSError:
            return _CandidateOutcome(
                self._downloaded_result(
                    INTEGRITY_STATUS_UNREADABLE,
                    record,
                    started,
                    downloaded,
                    error_code="temporary_database_cleanup_failed",
                ),
                final=True,
            )

        archive_result = await self._async_archive_details(
            record=record,
            started=started,
            downloaded=downloaded,
            temp_dir=temp_dir,
            password=password,
            database_check=database_check,
            database_timeout_minutes=database_timeout_minutes,
        )
        if isinstance(archive_result, _CandidateOutcome):
            if not archive_result.final:
                self._remove_candidate_file(prepared.path)
            return archive_result

        return _CandidateOutcome(
            self._completed_result(
                record,
                started=started,
                downloaded=downloaded,
                details=archive_result,
                prior_copy_failures=prior_copy_failures,
            ),
            final=True,
        )

    async def _async_archive_details(
        self,
        *,
        record: BackupRecord,
        started: float,
        downloaded: _DownloadedCandidate,
        temp_dir: Path,
        password: str | None,
        database_check: bool,
        database_timeout_minutes: int,
    ) -> dict[str, Any] | _CandidateOutcome:
        """Run blocking archive verification and classify its failures."""
        prepared = downloaded.prepared
        archive_future = self.hass.async_add_executor_job(
            self._verify_archive,
            prepared.path,
            temp_dir,
            password,
            prepared.protected,
            database_check,
            database_timeout_minutes,
            prepared.budget,
        )
        try:
            return await asyncio.shield(archive_future)
        except asyncio.CancelledError:
            prepared.budget.cancel()
            try:
                await archive_future
            except Exception as worker_err:  # noqa: BLE001 - worker shutdown boundary
                _LOGGER.debug(
                    "Cancelled verification worker stopped: error_type=%s",
                    safe_error_type(worker_err),
                )
            raise
        except (_BackupPasswordRequiredError, InvalidPasswordError) as err:
            _LOGGER.debug(
                "Backup password validation failed: error_type=%s",
                safe_error_type(err),
            )
            return _CandidateOutcome(
                self._downloaded_result(
                    INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    record,
                    started,
                    downloaded,
                    error_code="password_required",
                )
            )
        except VerificationLimitError as err:
            _LOGGER.warning(
                "Backup verification stopped by safety limit: code=%s", err.code
            )
            return _CandidateOutcome(
                self._downloaded_result(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    downloaded,
                    error_code=err.code,
                ),
                final=err.code in _GLOBAL_LIMIT_CODES,
            )
        except (
            tarfile.TarError,
            SecureTarError,
            json.JSONDecodeError,
            KeyError,
            ValueError,
        ) as err:
            return self._archive_failure_outcome(
                INTEGRITY_STATUS_CORRUPT,
                "archive_invalid",
                "One backup copy is corrupt or invalid; trying another",
                err,
                record=record,
                started=started,
                downloaded=downloaded,
            )
        except OSError as err:
            return self._archive_failure_outcome(
                INTEGRITY_STATUS_UNREADABLE,
                "read_failed",
                "One backup copy could not be read; trying another",
                err,
                record=record,
                started=started,
                downloaded=downloaded,
            )
        except Exception as err:  # noqa: BLE001 - archive worker boundary
            return self._archive_failure_outcome(
                INTEGRITY_STATUS_INTERNAL_ERROR,
                "internal_error",
                "Unexpected verification failure for one backup copy",
                err,
                record=record,
                started=started,
                downloaded=downloaded,
                unexpected=True,
            )

    def _archive_failure_outcome(
        self,
        status: str,
        error_code: str,
        message: str,
        error: Exception,
        *,
        record: BackupRecord,
        started: float,
        downloaded: _DownloadedCandidate,
        unexpected: bool = False,
    ) -> _CandidateOutcome:
        """Log and return one retryable archive-copy failure."""
        logger = _LOGGER.error if unexpected else _LOGGER.warning
        logger(
            "%s: agent=%s error_type=%s",
            message,
            anonymous_agent_reference(self._entry_id, downloaded.prepared.agent_id),
            safe_error_type(error),
        )
        return _CandidateOutcome(
            self._downloaded_result(
                status, record, started, downloaded, error_code=error_code
            )
        )

    def _downloaded_result(
        self,
        status: str,
        record: BackupRecord,
        started: float,
        downloaded: _DownloadedCandidate,
        *,
        error_code: str | None,
    ) -> BackupIntegrityResult:
        """Build a result retaining checksum data from a downloaded copy."""
        prepared = downloaded.prepared
        return self._result(
            status,
            record,
            started,
            agent_id=prepared.agent_id,
            digest=downloaded.digest,
            downloaded_size=downloaded.downloaded_size,
            protected=prepared.protected,
            warnings=list(downloaded.warnings),
            error_code=error_code,
            checksum_changed=downloaded.checksum_changed,
        )

    @staticmethod
    def _completed_result(
        record: BackupRecord,
        *,
        started: float,
        downloaded: _DownloadedCandidate,
        details: dict[str, Any],
        prior_copy_failures: int,
    ) -> BackupIntegrityResult:
        """Build the final result for a fully inspected archive."""
        warnings = [*downloaded.warnings, *details["warnings"]]
        if prior_copy_failures:
            warnings.extend(
                ("alternate_storage_copy_used", "storage_copy_verification_failed")
            )
        database_status = details["database_status"]
        if database_status == INTEGRITY_DATABASE_FAILED:
            warnings.append("database_integrity_failed")
        status = (
            INTEGRITY_STATUS_CORRUPT
            if database_status == INTEGRITY_DATABASE_FAILED
            else (
                INTEGRITY_STATUS_VALID_WITH_WARNINGS
                if warnings
                else INTEGRITY_STATUS_VALID
            )
        )
        prepared = downloaded.prepared
        return BackupIntegrityResult(
            status=status,
            checked_at=dt_util.utcnow(),
            backup_id=record.backup_id,
            backup_reference=record.backup_reference,
            backup_date=record.date,
            agent_id=prepared.agent_id,
            sha256=downloaded.digest,
            verified_size=downloaded.downloaded_size,
            duration_seconds=round(time.monotonic() - started, 2),
            archive_count=details["archive_count"],
            file_count=details["file_count"],
            protected=details["protected"],
            database_status=database_status,
            warnings=tuple(dict.fromkeys(warnings)),
            error_code=(
                "database_integrity_failed"
                if database_status == INTEGRITY_DATABASE_FAILED
                else None
            ),
            checksum_changed=downloaded.checksum_changed,
        )

    def _aggregate_failure(
        self,
        record: BackupRecord,
        started: float,
        failures: _VerificationFailures,
    ) -> BackupIntegrityResult:
        """Return the most useful failure after all available copies were tried."""
        if failures.best is not None:
            return replace(
                failures.best,
                warnings=tuple(
                    dict.fromkeys(
                        (*failures.best.warnings, "all_storage_copies_failed")
                    )
                ),
            )
        return self._failure(
            INTEGRITY_STATUS_UNREADABLE,
            record,
            started,
            error_code=(
                "download_failed_all_copies"
                if failures.download_failures > 1
                else "download_failed"
            ),
        )

    async def _async_cleanup_verification_data(
        self, temp_dir: Path, *, repair_issues_enabled: bool
    ) -> None:
        """Remove private temporary data and update its optional Repair issue."""
        cleanup_ok = await self.hass.async_add_executor_job(
            cleanup_temp_directory, temp_dir
        )
        stale_cleanup = await self.hass.async_add_executor_job(
            cleanup_stale_temp_directories
        )
        issue_active = not cleanup_ok or stale_cleanup.issue_active
        if issue_active:
            _LOGGER.warning("Temporary verification data could not be removed")
        if repair_issues_enabled:
            async_set_temporary_cleanup_issue(self.hass, active=issue_active)

    @staticmethod
    def _remove_candidate_file(path: Path) -> None:
        """Best-effort removal of one failed candidate archive."""
        with suppress(OSError):
            path.unlink(missing_ok=True)

    async def _async_download(
        self,
        agent: Any,
        backup_id: str,
        path: Path,
        budget: VerificationBudget,
    ) -> tuple[int, str]:
        """Download one backup while enforcing safety limits and calculating SHA-256."""
        digest = hashlib.sha256()
        file_handle = await self.hass.async_add_executor_job(
            open_private_binary_writer, path
        )
        attempt_downloaded_bytes = 0
        bytes_since_space_check = 0
        stream: Any | None = None
        try:
            async with asyncio.timeout(budget.remaining_seconds()):
                stream = await agent.async_download_backup(backup_id)
                async for chunk in stream:
                    if not isinstance(chunk, bytes):
                        raise TypeError("Backup agent returned a non-bytes chunk")
                    budget.add_downloaded(len(chunk))
                    attempt_downloaded_bytes += len(chunk)
                    digest.update(chunk)
                    await self.hass.async_add_executor_job(file_handle.write, chunk)
                    bytes_since_space_check += len(chunk)
                    if bytes_since_space_check >= _FREE_SPACE_CHECK_INTERVAL:
                        await self.hass.async_add_executor_job(
                            budget.check_free_space, path.parent
                        )
                        bytes_since_space_check = 0
        finally:
            if stream is not None and callable(
                aclose := getattr(stream, "aclose", None)
            ):
                try:
                    await aclose()
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Backup download stream close failed: error_type=%s",
                        safe_error_type(err),
                    )
            await self.hass.async_add_executor_job(file_handle.close)
        return attempt_downloaded_bytes, digest.hexdigest()

    @staticmethod
    def _candidate_agents(
        record: BackupRecord, agents: Mapping[str, Any]
    ) -> tuple[str, ...]:
        """Return available copies with local storage preferred."""
        available = sorted(agent_id for agent_id in record.agents if agent_id in agents)
        local = [
            agent_id
            for agent_id in available
            if agent_id.endswith(".local") or agent_id == "backup.local"
        ]
        remote = [agent_id for agent_id in available if agent_id not in local]
        return tuple(local + remote)

    @staticmethod
    def _backup_password(manager: Any) -> str | None:
        """Read the native backup password without persisting or logging it."""
        try:
            password = manager.config.data.create_backup.password
        except AttributeError:
            return None
        return password if isinstance(password, str) and password else None

    @classmethod
    def _verify_archive(
        cls,
        backup_path: Path,
        working_dir: Path,
        password: str | None,
        protected: bool,
        database_check: bool,
        database_timeout_minutes: int,
        budget: VerificationBudget,
    ) -> dict[str, Any]:
        """Synchronously stream every outer and inner archive member."""
        metadata = cls._read_metadata(backup_path, password, budget)
        effective_protected = cls._effective_protection(metadata, protected)
        if effective_protected and password is None:
            raise _BackupPasswordRequiredError

        database_path = working_dir / _DATABASE_FILENAME
        scan = cls._scan_outer_archive(
            backup_path,
            password=password,
            protected=effective_protected,
            database_check=database_check,
            database_path=database_path,
            budget=budget,
        )
        warnings = cls._validate_archive_inventory(metadata, scan)
        database_status = cls._database_verification_status(
            metadata,
            database_path=database_path,
            database_check=database_check,
            database_timeout_minutes=database_timeout_minutes,
            budget=budget,
        )
        return {
            "archive_count": scan.archive_count,
            "file_count": scan.file_count,
            "database_status": database_status,
            "protected": effective_protected,
            "warnings": warnings,
        }

    @staticmethod
    def _effective_protection(metadata: dict[str, Any], fallback: bool) -> bool:
        """Prefer the validated metadata flag over external copy metadata."""
        metadata_protected = metadata.get("protected")
        return metadata_protected if isinstance(metadata_protected, bool) else fallback

    @classmethod
    def _scan_outer_archive(
        cls,
        backup_path: Path,
        *,
        password: str | None,
        protected: bool,
        database_check: bool,
        database_path: Path,
        budget: VerificationBudget,
    ) -> _ArchiveScan:
        """Stream the outer archive and all declared inner archives."""
        scan = _ArchiveScan()
        with SecureTarArchive(
            backup_path,
            "r",
            bufsize=_BUFFER_SIZE,
            password=password,
        ) as outer:
            for member in outer.tar:
                cls._scan_outer_member(
                    outer,
                    member,
                    scan=scan,
                    protected=protected,
                    database_check=database_check,
                    database_path=database_path,
                    budget=budget,
                )
        return scan

    @classmethod
    def _scan_outer_member(
        cls,
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        *,
        scan: _ArchiveScan,
        protected: bool,
        database_check: bool,
        database_path: Path,
        budget: VerificationBudget,
    ) -> None:
        """Validate and consume one outer TAR member."""
        budget.add_member()
        cls._validate_member_path(member.name)
        if member.isdir() or not member.isfile():
            return

        member_path = PurePosixPath(member.name)
        normalized_name = member_path.name
        if normalized_name == "backup.json" and member_path != _METADATA_PATH:
            raise KeyError("backup_metadata_path_invalid")
        if member_path == _METADATA_PATH:
            cls._consume_outer_member(
                outer, member, budget=budget, unreadable="backup_metadata_unreadable"
            )
            scan.file_count += 1
            return
        if normalized_name.endswith(_INNER_SUFFIXES):
            cls._scan_inner_member(
                outer,
                member,
                scan=scan,
                protected=protected,
                database_check=database_check,
                database_path=database_path,
                budget=budget,
            )
            return
        cls._consume_outer_member(
            outer, member, budget=budget, unreadable="archive_member_unreadable"
        )
        scan.file_count += 1

    @classmethod
    def _consume_outer_member(
        cls,
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        *,
        budget: VerificationBudget,
        unreadable: str,
    ) -> None:
        """Consume one regular outer member and close its reader deterministically."""
        budget.ensure_expanded_capacity(member.size)
        reader = outer.tar.extractfile(member)
        if reader is None:
            raise tarfile.ReadError(unreadable)
        with closing(reader):
            cls._consume_all(reader, budget=budget, count_expanded=True)

    @classmethod
    def _scan_inner_member(
        cls,
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        *,
        scan: _ArchiveScan,
        protected: bool,
        database_check: bool,
        database_path: Path,
        budget: VerificationBudget,
    ) -> None:
        """Validate and fully consume one root-level inner archive."""
        member_path = PurePosixPath(member.name)
        if len(member_path.parts) != 1:
            raise KeyError("inner_archive_path_invalid")
        archive_name = cls._archive_prefix(member_path.name)
        if archive_name in scan.inner_names:
            raise KeyError("inner_archive_duplicate")
        scan.inner_names.add(archive_name)
        scan.archive_count += 1
        inspect_database = database_check and archive_name == "homeassistant"
        with cls._inner_archive_stream(outer, member, protected) as inner_stream:
            scan.file_count += cls._read_inner_archive(
                inner_stream,
                database_check=inspect_database,
                database_path=database_path,
                budget=budget,
            )
            cls._consume_all(inner_stream, budget=budget, count_expanded=False)

    @staticmethod
    @contextmanager
    def _inner_archive_stream(
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        protected: bool,
    ) -> Iterator[Any]:
        """Yield an inner TAR stream and always close unprotected readers."""
        if protected:
            with outer.extract_tar(member) as stream:
                yield stream
            return
        reader = outer.tar.extractfile(member)
        if reader is None:
            raise tarfile.ReadError("archive_member_unreadable")
        with closing(reader):
            yield reader

    @classmethod
    def _validate_archive_inventory(
        cls, metadata: dict[str, Any], scan: _ArchiveScan
    ) -> list[str]:
        """Validate declared inner archives and return non-fatal warnings."""
        expected = cls._expected_archives(metadata)
        missing = expected - scan.inner_names
        if missing:
            raise KeyError(f"missing_expected_archives_count_{len(missing)}")
        if scan.archive_count == 0:
            raise tarfile.ReadError("no_inner_backup_archives")
        unexpected = scan.inner_names - expected - _KNOWN_OPTIONAL_INNER_ARCHIVES
        return [f"unexpected_inner_archives_{len(unexpected)}"] if unexpected else []

    @classmethod
    def _database_verification_status(
        cls,
        metadata: dict[str, Any],
        *,
        database_path: Path,
        database_check: bool,
        database_timeout_minutes: int,
        budget: VerificationBudget,
    ) -> str:
        """Return the database result or reject a declared missing database."""
        database_expected = cls._database_expected(metadata)
        if not database_check:
            return INTEGRITY_DATABASE_NOT_CHECKED
        if not database_expected:
            return INTEGRITY_DATABASE_NOT_APPLICABLE
        if not database_path.exists():
            raise KeyError("expected_database_missing")
        return cls._check_database(
            database_path,
            database_timeout_minutes=database_timeout_minutes,
            budget=budget,
        )

    @classmethod
    def _decode_metadata_member(
        cls,
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        budget: VerificationBudget,
    ) -> dict[str, Any]:
        """Read and validate one bounded root-level metadata member."""
        budget.check_metadata_size(member.size)
        reader = outer.tar.extractfile(member)
        if reader is None:
            raise KeyError("backup_metadata_unreadable")
        with closing(reader):
            raw = reader.read(budget.max_metadata_bytes + 1)
        if len(raw) > budget.max_metadata_bytes:
            raise VerificationLimitError("metadata_size_limit")
        parsed = json.loads(raw, object_pairs_hook=cls._unique_json_object)
        if not isinstance(parsed, dict):
            raise KeyError("backup_metadata_root_invalid")
        cls._validate_metadata_schema(parsed)
        return parsed

    @classmethod
    def _metadata_member(
        cls,
        outer: SecureTarArchive,
        member: tarfile.TarInfo,
        budget: VerificationBudget,
    ) -> dict[str, Any] | None:
        """Return decoded metadata for the canonical member or None otherwise."""
        budget.add_member()
        cls._validate_member_path(member.name)
        member_path = PurePosixPath(member.name)
        if member_path.name == "backup.json" and member_path != _METADATA_PATH:
            raise KeyError("backup_metadata_path_invalid")
        if not member.isfile() or member_path != _METADATA_PATH:
            return None
        return cls._decode_metadata_member(outer, member, budget)

    @classmethod
    def _read_metadata(
        cls,
        backup_path: Path,
        password: str | None,
        budget: VerificationBudget,
    ) -> dict[str, Any]:
        """Read exactly one bounded backup.json without retaining TAR members."""
        metadata: dict[str, Any] | None = None
        with SecureTarArchive(
            backup_path,
            "r",
            bufsize=_BUFFER_SIZE,
            password=password,
        ) as outer:
            for member in outer.tar:
                parsed = cls._metadata_member(outer, member, budget)
                if parsed is None:
                    continue
                if metadata is not None:
                    raise KeyError("backup_metadata_duplicate")
                metadata = parsed
        if metadata is None:
            raise KeyError("backup_metadata_missing")
        return metadata

    @staticmethod
    def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """Build one JSON object while rejecting duplicate keys."""
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKeyError("backup_metadata_duplicate_key")
            result[key] = value
        return result

    @staticmethod
    def _validated_homeassistant_metadata(metadata: dict[str, Any]) -> bool:
        """Validate Home Assistant metadata and return whether it is present."""
        homeassistant = metadata.get("homeassistant")
        if homeassistant is None:
            return False
        if not isinstance(homeassistant, dict):
            raise KeyError("backup_metadata_homeassistant_invalid")
        exclude_database = homeassistant.get("exclude_database")
        if exclude_database is not None and not isinstance(exclude_database, bool):
            raise KeyError("backup_metadata_database_flag_invalid")
        return True

    @classmethod
    def _validated_addon_slugs(cls, metadata: dict[str, Any]) -> list[str]:
        """Return unique, valid add-on archive identifiers."""
        addons = metadata.get("addons", [])
        if not isinstance(addons, list) or len(addons) > 10_000:
            raise KeyError("backup_metadata_addons_invalid")
        slugs: list[str] = []
        for item in addons:
            if not isinstance(item, dict):
                raise KeyError("backup_metadata_addons_invalid")
            slug = item.get("slug")
            if not cls._valid_archive_identifier(slug):
                raise KeyError("backup_metadata_addons_invalid")
            slugs.append(slug)
        if len(slugs) != len(set(slugs)):
            raise KeyError("backup_metadata_addons_duplicate")
        return slugs

    @classmethod
    def _validated_folders(cls, metadata: dict[str, Any]) -> list[str]:
        """Return unique, valid folder archive identifiers."""
        folders = metadata.get("folders", [])
        if not isinstance(folders, list) or len(folders) > 10_000:
            raise KeyError("backup_metadata_folders_invalid")
        if any(not cls._valid_archive_identifier(item) for item in folders):
            raise KeyError("backup_metadata_folders_invalid")
        if len(folders) != len(set(folders)):
            raise KeyError("backup_metadata_folders_duplicate")
        return folders

    @classmethod
    def _validate_metadata_schema(cls, metadata: dict[str, Any]) -> None:
        """Validate security-relevant backup metadata types conservatively."""
        protected = metadata.get("protected")
        if protected is not None and not isinstance(protected, bool):
            raise KeyError("backup_metadata_protected_invalid")
        homeassistant_present = cls._validated_homeassistant_metadata(metadata)
        addon_slugs = cls._validated_addon_slugs(metadata)
        folders = cls._validated_folders(metadata)
        logical_names = addon_slugs + [
            folder for folder in folders if folder != "homeassistant"
        ]
        if homeassistant_present:
            logical_names.append("homeassistant")
        if len(logical_names) != len(set(logical_names)):
            raise KeyError("backup_metadata_archive_name_collision")

    @staticmethod
    def _valid_archive_identifier(value: Any) -> bool:
        """Return whether metadata contains one safe root archive identifier."""
        return bool(
            isinstance(value, str)
            and 0 < len(value) <= 256
            and value not in {".", ".."}
            and "/" not in value
            and "\\" not in value
            and "\x00" not in value
            and all(
                unicodedata.category(character) not in {"Cc", "Cf", "Zl", "Zp"}
                for character in value
            )
            and not value.endswith(_INNER_SUFFIXES)
        )

    @classmethod
    def _read_inner_archive(
        cls,
        stream: Any,
        *,
        database_check: bool,
        database_path: Path,
        budget: VerificationBudget,
    ) -> int:
        """Read every member of one inner archive and return its file count."""
        file_count = 0
        database_candidates = 0
        with tarfile.open(fileobj=stream, mode="r|*", bufsize=_BUFFER_SIZE) as inner:
            for inner_member in inner:
                budget.add_member()
                cls._validate_member_path(inner_member.name)
                if not inner_member.isfile():
                    continue
                budget.ensure_expanded_capacity(inner_member.size)
                file_count += 1
                reader = inner.extractfile(inner_member)
                if reader is None:
                    raise tarfile.ReadError("inner_archive_member_unreadable")
                inner_path = PurePosixPath(inner_member.name)
                is_database_name = inner_path.name == _DATABASE_FILENAME
                with closing(reader):
                    if database_check and is_database_name:
                        database_candidates += 1
                        if inner_path != _DATABASE_PATH:
                            raise KeyError("database_path_invalid")
                        if database_candidates > 1 or database_path.exists():
                            raise KeyError("database_duplicate")
                        with open_private_binary_writer(database_path) as db_file:
                            cls._copy_all(
                                reader,
                                db_file,
                                budget=budget,
                                free_space_path=database_path.parent,
                            )
                    else:
                        cls._consume_all(reader, budget=budget, count_expanded=True)
        return file_count

    @staticmethod
    def _archive_prefix(name: str) -> str:
        """Return the logical name of an inner archive."""
        for suffix in (".tar.gz", ".tgz", ".tar"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name

    @classmethod
    def _expected_archives(cls, metadata: dict[str, Any]) -> set[str]:
        """Return archive names declared by backup.json."""
        expected: set[str] = set()
        homeassistant = metadata.get("homeassistant")
        if isinstance(homeassistant, dict):
            expected.add("homeassistant")
        addons = metadata.get("addons", [])
        if isinstance(addons, list):
            for addon in addons:
                if isinstance(addon, dict) and isinstance(addon.get("slug"), str):
                    expected.add(addon["slug"])
        folders = metadata.get("folders", [])
        if isinstance(folders, list):
            expected.update(
                str(folder) for folder in folders if folder != "homeassistant"
            )
        return expected

    @staticmethod
    def _database_expected(metadata: dict[str, Any]) -> bool:
        """Return whether backup metadata says the database should be included."""
        homeassistant = metadata.get("homeassistant")
        if not isinstance(homeassistant, dict):
            return False
        return homeassistant.get("exclude_database") is not True

    @staticmethod
    def _validate_member_path(name: str) -> None:
        """Reject unsafe paths even though verification never extracts them."""
        if (
            not isinstance(name, str)
            or not name
            or "\x00" in name
            or "\\" in name
            or any(
                unicodedata.category(character) in {"Cc", "Cf", "Zl", "Zp"}
                for character in name
            )
        ):
            raise tarfile.ReadError("unsafe_archive_member_path")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise tarfile.ReadError("unsafe_archive_member_path")

    @staticmethod
    def _consume_all(
        reader: Any,
        *,
        budget: VerificationBudget,
        count_expanded: bool,
    ) -> int:
        """Read a file-like object to EOF while checking the deadline."""
        total = 0
        while chunk := reader.read(_BUFFER_SIZE):
            budget.check_deadline()
            total += len(chunk)
            if count_expanded:
                budget.add_expanded(len(chunk))
        return total

    @staticmethod
    def _copy_all(
        reader: Any,
        writer: Any,
        *,
        budget: VerificationBudget,
        free_space_path: Path,
    ) -> int:
        """Copy a file-like object completely with resource checks."""
        total = 0
        bytes_since_space_check = 0
        while chunk := reader.read(_BUFFER_SIZE):
            budget.add_expanded(len(chunk))
            writer.write(chunk)
            total += len(chunk)
            bytes_since_space_check += len(chunk)
            if bytes_since_space_check >= _FREE_SPACE_CHECK_INTERVAL:
                budget.check_free_space(free_space_path)
                bytes_since_space_check = 0
        return total

    @staticmethod
    def _sqlite_quick_check_passed(connection: sqlite3.Connection) -> bool:
        """Return whether SQLite's bounded quick check reports only OK rows."""
        rows = list(connection.execute("PRAGMA quick_check(1)"))
        return bool(rows) and all(str(row[0]).lower() == "ok" for row in rows)

    @staticmethod
    def _sqlite_integrity_check_passed(connection: sqlite3.Connection) -> bool:
        """Return whether the full SQLite integrity check reports only OK rows."""
        rows_seen = False
        all_ok = True
        for row in connection.execute("PRAGMA integrity_check"):
            rows_seen = True
            if str(row[0]).lower() != "ok":
                all_ok = False
        return rows_seen and all_ok

    @staticmethod
    def _check_database(
        path: Path,
        *,
        database_timeout_minutes: int,
        budget: VerificationBudget,
    ) -> str:
        """Run SQLite's full integrity check with a cooperative deadline."""
        budget.check_deadline()
        control = _DatabaseCheckControl(
            budget=budget,
            deadline=min(
                budget.deadline,
                time.monotonic() + database_timeout_minutes * 60,
            ),
        )
        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro&immutable=1",
                uri=True,
                timeout=30,
            )
            try:
                connection.set_progress_handler(control.progress_handler, 10_000)
                connection.execute("PRAGMA trusted_schema=OFF")
                if not BackupIntegrityVerifier._sqlite_quick_check_passed(connection):
                    return INTEGRITY_DATABASE_FAILED
                passed = BackupIntegrityVerifier._sqlite_integrity_check_passed(
                    connection
                )
                control.raise_if_stopped()
            finally:
                connection.set_progress_handler(None, 0)
                connection.close()
        except VerificationLimitError:
            raise
        except sqlite3.DatabaseError:
            control.raise_if_stopped()
            return INTEGRITY_DATABASE_FAILED
        return INTEGRITY_DATABASE_PASSED if passed else INTEGRITY_DATABASE_FAILED

    @staticmethod
    def _result(
        status: str,
        record: BackupRecord,
        started: float,
        *,
        agent_id: str,
        digest: str,
        downloaded_size: int,
        protected: bool,
        warnings: list[str],
        error_code: str | None,
        checksum_changed: bool,
    ) -> BackupIntegrityResult:
        """Build a completed result after the checksum is available."""
        return BackupIntegrityResult(
            status=status,
            checked_at=dt_util.utcnow(),
            backup_id=record.backup_id,
            backup_reference=record.backup_reference,
            backup_date=record.date,
            agent_id=agent_id,
            sha256=digest,
            verified_size=downloaded_size,
            duration_seconds=round(time.monotonic() - started, 2),
            archive_count=0,
            file_count=0,
            protected=protected,
            database_status=INTEGRITY_DATABASE_NOT_CHECKED,
            warnings=tuple(warnings),
            error_code=error_code,
            checksum_changed=checksum_changed,
        )

    @staticmethod
    def _failure(
        status: str,
        record: BackupRecord,
        started: float,
        *,
        agent_id: str | None = None,
        error_code: str,
    ) -> BackupIntegrityResult:
        """Build a failed result before a checksum is available."""
        return BackupIntegrityResult(
            status=status,
            checked_at=dt_util.utcnow(),
            backup_id=record.backup_id,
            backup_reference=record.backup_reference,
            backup_date=record.date,
            agent_id=agent_id,
            sha256=None,
            verified_size=None,
            duration_seconds=round(time.monotonic() - started, 2),
            archive_count=0,
            file_count=0,
            protected=None,
            database_status=INTEGRITY_DATABASE_NOT_CHECKED,
            warnings=(),
            error_code=error_code,
            checksum_changed=False,
        )
