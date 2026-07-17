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
from collections.abc import Mapping
from dataclasses import replace
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
    INTEGRITY_DATABASE_NOT_FOUND,
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
    cleanup_stale_temp_directories,
    cleanup_temp_directory,
    create_private_temp_directory,
    open_private_binary_writer,
    safe_error_type,
    safe_log_value,
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


class BackupIntegrityStore:
    """Persist the last completed integrity result."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.integrity",
            private=True,
            atomic_writes=True,
        )
        self._loaded = False
        self._result = BackupIntegrityResult.not_checked()

    async def async_load(self) -> BackupIntegrityResult:
        """Load the last result once and recover from invalid private data."""
        if self._loaded:
            return self._result
        self._loaded = True
        try:
            stored = await self._store.async_load()
            if stored is None:
                async_set_storage_data_issue(
                    self._hass, store_name="integrity", active=False
                )
                return self._result
            if not isinstance(stored, dict):
                raise ValueError("invalid_store_root")
            if not BackupIntegrityResult.storage_dict_is_valid(stored):
                raise ValueError("invalid_store_content")
            self._result = BackupIntegrityResult.from_dict(stored)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Invalid integrity store data was reset: error_type=%s",
                safe_error_type(err),
            )
            self._result = BackupIntegrityResult.not_checked()
            async_set_storage_data_issue(
                self._hass, store_name="integrity", active=True
            )
        else:
            async_set_storage_data_issue(
                self._hass, store_name="integrity", active=False
            )
        return self._result

    async def async_save(self, result: BackupIntegrityResult) -> None:
        """Persist one completed result."""
        self._loaded = True
        self._result = result
        await self._store.async_save(result.as_dict())

    async def async_remove(self) -> None:
        """Remove the stored integrity result."""
        await self._store.async_remove()


class BackupIntegrityVerifier:
    """Download and fully read a Home Assistant backup."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the verifier."""
        self.hass = hass
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
        overall_budget = VerificationBudget.from_options(
            max_download_gb=max_download_gb,
            max_expanded_gb=max_expanded_gb,
            timeout_minutes=timeout_minutes,
        )
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
        password = self._backup_password(manager)

        try:
            temp_dir = await self.hass.async_add_executor_job(
                create_private_temp_directory
            )
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

        failure_ranks = {
            INTEGRITY_STATUS_ABORTED: 1,
            INTEGRITY_STATUS_UNREADABLE: 1,
            INTEGRITY_STATUS_PASSWORD_REQUIRED: 2,
            INTEGRITY_STATUS_INTERNAL_ERROR: 3,
            INTEGRITY_STATUS_CORRUPT: 4,
        }
        best_failure: BackupIntegrityResult | None = None
        copy_failures = 0
        download_failures = 0

        def remember_failure(result: BackupIntegrityResult) -> None:
            nonlocal best_failure
            if best_failure is None or failure_ranks.get(
                result.status, 0
            ) > failure_ranks.get(best_failure.status, 0):
                best_failure = result

        try:
            previous = await self.store.async_load()
            for index, candidate_id in enumerate(candidate_agents):
                try:
                    copy_budget = overall_budget.for_copy()
                except VerificationLimitError as err:
                    return self._failure(
                        INTEGRITY_STATUS_ABORTED,
                        record,
                        started,
                        agent_id=candidate_id,
                        error_code=err.code,
                    )
                copy = next(
                    (
                        item
                        for item in record.agent_copies
                        if item.agent_id == candidate_id
                    ),
                    None,
                )
                candidate_expected = copy.size if copy else None
                candidate_protected = bool(copy and copy.protected)
                try:
                    copy_budget.validate_expected_download(candidate_expected)
                    await self.hass.async_add_executor_job(
                        copy_budget.check_free_space,
                        temp_dir,
                        candidate_expected or 0,
                    )
                except VerificationLimitError as err:
                    failure = self._failure(
                        INTEGRITY_STATUS_ABORTED,
                        record,
                        started,
                        agent_id=candidate_id,
                        error_code=err.code,
                    )
                    if err.code in _GLOBAL_LIMIT_CODES:
                        return failure
                    remember_failure(failure)
                    copy_failures += 1
                    continue

                candidate_path = temp_dir / f"backup-{index}.tar"
                try:
                    downloaded_size, digest = await self._async_download(
                        manager_agents[candidate_id],
                        record.backup_id,
                        candidate_path,
                        copy_budget,
                    )
                except VerificationLimitError as err:
                    _LOGGER.warning(
                        "Backup verification download stopped by safety limit: "
                        "agent=%s code=%s",
                        safe_log_value(candidate_id),
                        err.code,
                    )
                    failure = self._failure(
                        INTEGRITY_STATUS_ABORTED,
                        record,
                        started,
                        agent_id=candidate_id,
                        error_code=err.code,
                    )
                    try:
                        candidate_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    if err.code in _GLOBAL_LIMIT_CODES:
                        return failure
                    remember_failure(failure)
                    copy_failures += 1
                    continue
                except TimeoutError:
                    return self._failure(
                        INTEGRITY_STATUS_ABORTED,
                        record,
                        started,
                        agent_id=candidate_id,
                        error_code="verification_timeout",
                    )
                except Exception as err:  # noqa: BLE001
                    download_failures += 1
                    copy_failures += 1
                    _LOGGER.warning(
                        "Unable to download one backup copy; trying another: "
                        "agent=%s error_type=%s",
                        safe_log_value(candidate_id),
                        safe_error_type(err),
                    )
                    try:
                        candidate_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    continue

                warnings: list[str] = []
                if record.copy_size_mismatch:
                    warnings.append("storage_copy_size_mismatch")
                if (
                    candidate_expected is not None
                    and downloaded_size != candidate_expected
                ):
                    warnings.append("reported_size_mismatch")
                checksum_changed = bool(
                    previous.backup_id == record.backup_id
                    and previous.agent_id == candidate_id
                    and previous.sha256
                    and previous.sha256 != digest
                )
                if checksum_changed:
                    warnings.append("checksum_changed")

                if candidate_protected and password is None:
                    remember_failure(
                        self._result(
                            INTEGRITY_STATUS_PASSWORD_REQUIRED,
                            record,
                            started,
                            agent_id=candidate_id,
                            digest=digest,
                            downloaded_size=downloaded_size,
                            protected=candidate_protected,
                            warnings=warnings,
                            error_code="password_required",
                            checksum_changed=checksum_changed,
                        )
                    )
                    copy_failures += 1
                    try:
                        candidate_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    continue

                database_path = temp_dir / _DATABASE_FILENAME
                try:
                    database_path.unlink(missing_ok=True)
                except OSError:
                    return self._result(
                        INTEGRITY_STATUS_UNREADABLE,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code="temporary_database_cleanup_failed",
                        checksum_changed=checksum_changed,
                    )

                archive_future = self.hass.async_add_executor_job(
                    self._verify_archive,
                    candidate_path,
                    temp_dir,
                    password,
                    candidate_protected,
                    database_check,
                    database_timeout_minutes,
                    copy_budget,
                )
                candidate_failure: BackupIntegrityResult | None = None
                try:
                    details = await asyncio.shield(archive_future)
                except asyncio.CancelledError:
                    copy_budget.cancel()
                    try:
                        await archive_future
                    except Exception as worker_err:  # noqa: BLE001
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
                    candidate_failure = self._result(
                        INTEGRITY_STATUS_PASSWORD_REQUIRED,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code="password_required",
                        checksum_changed=checksum_changed,
                    )
                except VerificationLimitError as err:
                    _LOGGER.warning(
                        "Backup verification stopped by safety limit: code=%s", err.code
                    )
                    candidate_failure = self._result(
                        INTEGRITY_STATUS_ABORTED,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code=err.code,
                        checksum_changed=checksum_changed,
                    )
                    if err.code in _GLOBAL_LIMIT_CODES:
                        return candidate_failure
                except (
                    tarfile.TarError,
                    SecureTarError,
                    json.JSONDecodeError,
                    KeyError,
                    ValueError,
                ) as err:
                    _LOGGER.warning(
                        "One backup copy is corrupt or invalid; trying another: "
                        "agent=%s error_type=%s",
                        safe_log_value(candidate_id),
                        safe_error_type(err),
                    )
                    candidate_failure = self._result(
                        INTEGRITY_STATUS_CORRUPT,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code="archive_invalid",
                        checksum_changed=checksum_changed,
                    )
                except OSError as err:
                    _LOGGER.warning(
                        "One backup copy could not be read; trying another: "
                        "agent=%s error_type=%s",
                        safe_log_value(candidate_id),
                        safe_error_type(err),
                    )
                    candidate_failure = self._result(
                        INTEGRITY_STATUS_UNREADABLE,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code="read_failed",
                        checksum_changed=checksum_changed,
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.error(
                        "Unexpected verification failure for one backup copy: "
                        "agent=%s error_type=%s",
                        safe_log_value(candidate_id),
                        safe_error_type(err),
                    )
                    candidate_failure = self._result(
                        INTEGRITY_STATUS_INTERNAL_ERROR,
                        record,
                        started,
                        agent_id=candidate_id,
                        digest=digest,
                        downloaded_size=downloaded_size,
                        protected=candidate_protected,
                        warnings=warnings,
                        error_code="internal_error",
                        checksum_changed=checksum_changed,
                    )

                if candidate_failure is not None:
                    remember_failure(candidate_failure)
                    copy_failures += 1
                    try:
                        candidate_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    continue

                warnings.extend(details["warnings"])
                if copy_failures:
                    warnings.extend(
                        (
                            "alternate_storage_copy_used",
                            "storage_copy_verification_failed",
                        )
                    )
                database_status = details["database_status"]
                if database_status == INTEGRITY_DATABASE_FAILED:
                    warnings.append("database_integrity_failed")

                status = (
                    INTEGRITY_STATUS_VALID_WITH_WARNINGS
                    if warnings
                    else INTEGRITY_STATUS_VALID
                )
                if database_status == INTEGRITY_DATABASE_FAILED:
                    status = INTEGRITY_STATUS_CORRUPT

                return BackupIntegrityResult(
                    status=status,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
                    backup_reference=record.backup_reference,
                    backup_date=record.date,
                    agent_id=candidate_id,
                    sha256=digest,
                    verified_size=downloaded_size,
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
                    checksum_changed=checksum_changed,
                )

            if best_failure is not None:
                return replace(
                    best_failure,
                    warnings=tuple(
                        dict.fromkeys(
                            (*best_failure.warnings, "all_storage_copies_failed")
                        )
                    ),
                )
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                error_code=(
                    "download_failed_all_copies"
                    if download_failures > 1
                    else "download_failed"
                ),
            )
        finally:
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
                async_set_temporary_cleanup_issue(
                    self.hass,
                    active=issue_active,
                )

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
        metadata_protected = metadata.get("protected")
        effective_protected = (
            metadata_protected if isinstance(metadata_protected, bool) else protected
        )
        if effective_protected and password is None:
            raise _BackupPasswordRequiredError

        archive_count = 0
        file_count = 0
        warnings: list[str] = []
        inner_names: set[str] = set()
        database_expected = cls._database_expected(metadata)
        database_status = (
            INTEGRITY_DATABASE_NOT_APPLICABLE
            if database_check and not database_expected
            else (
                INTEGRITY_DATABASE_NOT_FOUND
                if database_check
                else INTEGRITY_DATABASE_NOT_CHECKED
            )
        )
        database_path = working_dir / _DATABASE_FILENAME

        with SecureTarArchive(
            backup_path,
            "r",
            bufsize=_BUFFER_SIZE,
            password=password,
        ) as outer:
            for member in outer.tar:
                budget.add_member()
                cls._validate_member_path(member.name)
                if member.isdir() or not member.isfile():
                    continue

                member_path = PurePosixPath(member.name)
                normalized_name = member_path.name
                if normalized_name == "backup.json" and member_path != _METADATA_PATH:
                    raise KeyError("backup_metadata_path_invalid")
                if member_path == _METADATA_PATH:
                    budget.ensure_expanded_capacity(member.size)
                    reader = outer.tar.extractfile(member)
                    if reader is None:
                        raise KeyError("backup_metadata_unreadable")
                    cls._consume_all(reader, budget=budget, count_expanded=True)
                    file_count += 1
                    continue

                if normalized_name.endswith(_INNER_SUFFIXES):
                    if len(member_path.parts) != 1:
                        raise KeyError("inner_archive_path_invalid")
                    archive_count += 1
                    archive_name = cls._archive_prefix(normalized_name)
                    if archive_name in inner_names:
                        raise KeyError("inner_archive_duplicate")
                    inner_names.add(archive_name)
                    inspect_database = (
                        database_check and archive_name == "homeassistant"
                    )
                    if effective_protected:
                        with outer.extract_tar(member) as inner_stream:
                            file_count += cls._read_inner_archive(
                                inner_stream,
                                database_check=inspect_database,
                                database_path=database_path,
                                budget=budget,
                            )
                            cls._consume_all(
                                inner_stream,
                                budget=budget,
                                count_expanded=False,
                            )
                    else:
                        inner_stream = outer.tar.extractfile(member)
                        if inner_stream is None:
                            raise tarfile.ReadError("archive_member_unreadable")
                        file_count += cls._read_inner_archive(
                            inner_stream,
                            database_check=inspect_database,
                            database_path=database_path,
                            budget=budget,
                        )
                        cls._consume_all(
                            inner_stream,
                            budget=budget,
                            count_expanded=False,
                        )
                    continue

                budget.ensure_expanded_capacity(member.size)
                reader = outer.tar.extractfile(member)
                if reader is None:
                    raise tarfile.ReadError("archive_member_unreadable")
                cls._consume_all(reader, budget=budget, count_expanded=True)
                file_count += 1

        expected = cls._expected_archives(metadata)
        missing = expected - inner_names
        if missing:
            raise KeyError(f"missing_expected_archives_count_{len(missing)}")
        if archive_count == 0:
            raise tarfile.ReadError("no_inner_backup_archives")
        unexpected = inner_names - expected - _KNOWN_OPTIONAL_INNER_ARCHIVES
        if unexpected:
            warnings.append(f"unexpected_inner_archives_{len(unexpected)}")

        if database_check and database_path.exists():
            database_status = cls._check_database(
                database_path,
                database_timeout_minutes=database_timeout_minutes,
                budget=budget,
            )
        elif database_check and database_expected:
            raise KeyError("expected_database_missing")

        return {
            "archive_count": archive_count,
            "file_count": file_count,
            "database_status": database_status,
            "protected": effective_protected,
            "warnings": warnings,
        }

    @classmethod
    def _read_metadata(
        cls,
        backup_path: Path,
        password: str | None,
        budget: VerificationBudget,
    ) -> dict[str, Any]:
        """Read exactly one bounded backup.json without retaining TAR member objects."""
        metadata: dict[str, Any] | None = None
        metadata_count = 0
        scanned_members = 0

        with SecureTarArchive(
            backup_path,
            "r",
            bufsize=_BUFFER_SIZE,
            password=password,
        ) as outer:
            for member in outer.tar:
                budget.check_deadline()
                scanned_members += 1
                if scanned_members > budget.max_members:
                    raise VerificationLimitError("archive_member_limit")
                cls._validate_member_path(member.name)
                member_path = PurePosixPath(member.name)
                if member_path.name == "backup.json" and member_path != _METADATA_PATH:
                    raise KeyError("backup_metadata_path_invalid")
                if not member.isfile() or member_path != _METADATA_PATH:
                    continue
                metadata_count += 1
                if metadata_count > 1:
                    raise KeyError("backup_metadata_duplicate")
                budget.check_metadata_size(member.size)
                reader = outer.tar.extractfile(member)
                if reader is None:
                    raise KeyError("backup_metadata_unreadable")
                raw = reader.read(budget.max_metadata_bytes + 1)
                if len(raw) > budget.max_metadata_bytes:
                    raise VerificationLimitError("metadata_size_limit")
                parsed = json.loads(raw, object_pairs_hook=cls._unique_json_object)
                if not isinstance(parsed, dict):
                    raise KeyError("backup_metadata_root_invalid")
                cls._validate_metadata_schema(parsed)
                metadata = parsed

        if metadata_count != 1 or metadata is None:
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
    def _validate_metadata_schema(metadata: dict[str, Any]) -> None:
        """Validate security-relevant backup metadata types conservatively."""
        protected = metadata.get("protected")
        if protected is not None and not isinstance(protected, bool):
            raise KeyError("backup_metadata_protected_invalid")
        homeassistant = metadata.get("homeassistant")
        if homeassistant is not None and not isinstance(homeassistant, dict):
            raise KeyError("backup_metadata_homeassistant_invalid")
        if isinstance(homeassistant, dict):
            exclude_database = homeassistant.get("exclude_database")
            if exclude_database is not None and not isinstance(exclude_database, bool):
                raise KeyError("backup_metadata_database_flag_invalid")
        addons = metadata.get("addons", [])
        if not isinstance(addons, list) or len(addons) > 10_000:
            raise KeyError("backup_metadata_addons_invalid")
        addon_slugs: list[str] = []
        for item in addons:
            if not isinstance(item, dict):
                raise KeyError("backup_metadata_addons_invalid")
            slug = item.get("slug")
            if not BackupIntegrityVerifier._valid_archive_identifier(slug):
                raise KeyError("backup_metadata_addons_invalid")
            addon_slugs.append(slug)
        if len(addon_slugs) != len(set(addon_slugs)):
            raise KeyError("backup_metadata_addons_duplicate")

        folders = metadata.get("folders", [])
        if not isinstance(folders, list) or len(folders) > 10_000:
            raise KeyError("backup_metadata_folders_invalid")
        if any(
            not BackupIntegrityVerifier._valid_archive_identifier(item)
            for item in folders
        ):
            raise KeyError("backup_metadata_folders_invalid")
        if len(folders) != len(set(folders)):
            raise KeyError("backup_metadata_folders_duplicate")

        logical_names = addon_slugs + [
            folder for folder in folders if folder != "homeassistant"
        ]
        if isinstance(homeassistant, dict):
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
    def _check_database(
        path: Path,
        *,
        database_timeout_minutes: int,
        budget: VerificationBudget,
    ) -> str:
        """Run SQLite's full integrity check with a cooperative deadline."""
        budget.check_deadline()
        database_deadline = min(
            budget.deadline,
            time.monotonic() + database_timeout_minutes * 60,
        )
        timed_out = False
        cancelled = False

        def _abort_if_timed_out() -> int:
            nonlocal cancelled, timed_out
            if budget.cancellation_event.is_set():
                cancelled = True
                return 1
            if time.monotonic() >= database_deadline:
                timed_out = True
                return 1
            return 0

        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro&immutable=1",
                uri=True,
                timeout=30,
            )
            try:
                connection.set_progress_handler(_abort_if_timed_out, 10_000)
                connection.execute("PRAGMA trusted_schema=OFF")
                quick_rows = list(connection.execute("PRAGMA quick_check(1)"))
                if not quick_rows or any(
                    str(row[0]).lower() != "ok" for row in quick_rows
                ):
                    return INTEGRITY_DATABASE_FAILED
                rows_seen = False
                all_ok = True
                for row in connection.execute("PRAGMA integrity_check"):
                    rows_seen = True
                    if str(row[0]).lower() != "ok":
                        all_ok = False
                if cancelled:
                    raise VerificationLimitError("verification_cancelled")
                if timed_out:
                    raise VerificationLimitError("database_timeout")
            finally:
                connection.set_progress_handler(None, 0)
                connection.close()
        except VerificationLimitError:
            raise
        except sqlite3.DatabaseError:
            if cancelled or budget.cancellation_event.is_set():
                raise VerificationLimitError("verification_cancelled") from None
            if timed_out or time.monotonic() >= database_deadline:
                raise VerificationLimitError("database_timeout") from None
            return INTEGRITY_DATABASE_FAILED
        return (
            INTEGRITY_DATABASE_PASSED
            if rows_seen and all_ok
            else INTEGRITY_DATABASE_FAILED
        )

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
