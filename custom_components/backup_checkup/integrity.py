"""Full backup integrity verification for BackupCheckup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import tarfile
import time
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
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_DATABASE_NOT_FOUND,
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_CORRUPT,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord
from .repairs import async_set_temporary_cleanup_issue
from .security import (
    VerificationBudget,
    VerificationLimitError,
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
_DATABASE_FILENAME = "home-assistant_v2.db"


class _BackupPasswordRequiredError(Exception):
    """Raised when archive metadata requires a password that is unavailable."""


class BackupIntegrityStore:
    """Persist the last completed integrity result."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store."""
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
        """Load the last result once."""
        if self._loaded:
            return self._result
        self._loaded = True
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self._result = BackupIntegrityResult.from_dict(stored)
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
        """Verify one backup copy and return a privacy-safe result."""
        started = time.monotonic()
        budget = VerificationBudget.from_options(
            max_download_gb=max_download_gb,
            max_expanded_gb=max_expanded_gb,
            timeout_minutes=timeout_minutes,
        )
        manager = async_get_manager(self.hass)
        agent_id = self._select_agent(record, manager.backup_agents)
        if agent_id is None:
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                error_code="no_available_storage_agent",
            )

        copy = next(
            (item for item in record.agent_copies if item.agent_id == agent_id),
            None,
        )
        expected_size = copy.size if copy else None
        protected = bool(copy and copy.protected)
        password = self._backup_password(manager)

        try:
            budget.validate_expected_download(expected_size)
        except VerificationLimitError as err:
            return self._failure(
                INTEGRITY_STATUS_ABORTED,
                record,
                started,
                agent_id=agent_id,
                error_code=err.code,
            )

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
                agent_id=agent_id,
                error_code="temporary_storage_unavailable",
            )

        try:
            try:
                await self.hass.async_add_executor_job(
                    budget.check_free_space,
                    temp_dir,
                    expected_size or 0,
                )
            except VerificationLimitError as err:
                return self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=agent_id,
                    error_code=err.code,
                )

            backup_path = temp_dir / "backup.tar"
            try:
                downloaded_size, digest = await self._async_download(
                    manager.backup_agents[agent_id],
                    record.backup_id,
                    backup_path,
                    budget,
                )
            except VerificationLimitError as err:
                _LOGGER.warning(
                    "Backup verification download stopped by safety limit: "
                    "agent=%s code=%s",
                    safe_log_value(agent_id),
                    err.code,
                )
                return self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=agent_id,
                    error_code=err.code,
                )
            except TimeoutError:
                return self._failure(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=agent_id,
                    error_code="verification_timeout",
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Unable to download backup for integrity check: "
                    "agent=%s error_type=%s",
                    safe_log_value(agent_id),
                    safe_error_type(err),
                )
                return self._failure(
                    INTEGRITY_STATUS_UNREADABLE,
                    record,
                    started,
                    agent_id=agent_id,
                    error_code="download_failed",
                )

            warnings: list[str] = []
            if expected_size is not None and downloaded_size != expected_size:
                warnings.append("reported_size_mismatch")

            previous = await self.store.async_load()
            checksum_changed = bool(
                previous.backup_id == record.backup_id
                and previous.agent_id == agent_id
                and previous.sha256
                and previous.sha256 != digest
            )
            if checksum_changed:
                warnings.append("checksum_changed")

            if protected and password is None:
                return self._result(
                    INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code="password_required",
                    checksum_changed=checksum_changed,
                )

            archive_future = self.hass.async_add_executor_job(
                self._verify_archive,
                backup_path,
                temp_dir,
                password,
                protected,
                database_check,
                database_timeout_minutes,
                budget,
            )
            try:
                details = await asyncio.shield(archive_future)
            except asyncio.CancelledError:
                budget.cancel()
                try:
                    await archive_future
                except Exception as worker_err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Cancelled verification worker stopped: error_type=%s",
                        safe_error_type(worker_err),
                    )
                raise
            except (
                _BackupPasswordRequiredError,
                InvalidPasswordError,
            ) as err:
                _LOGGER.debug(
                    "Backup password validation failed: error_type=%s",
                    safe_error_type(err),
                )
                return self._result(
                    INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code="password_required",
                    checksum_changed=checksum_changed,
                )
            except VerificationLimitError as err:
                _LOGGER.warning(
                    "Backup verification stopped by safety limit: code=%s", err.code
                )
                return self._result(
                    INTEGRITY_STATUS_ABORTED,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code=err.code,
                    checksum_changed=checksum_changed,
                )
            except (
                tarfile.TarError,
                SecureTarError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
            ) as err:
                _LOGGER.warning(
                    "Backup archive is corrupt or invalid: error_type=%s",
                    safe_error_type(err),
                )
                return self._result(
                    INTEGRITY_STATUS_CORRUPT,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code="archive_invalid",
                    checksum_changed=checksum_changed,
                )
            except OSError as err:
                _LOGGER.warning(
                    "Backup archive could not be read: error_type=%s",
                    safe_error_type(err),
                )
                return self._result(
                    INTEGRITY_STATUS_UNREADABLE,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code="read_failed",
                    checksum_changed=checksum_changed,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error(
                    "Unexpected backup integrity check failure: error_type=%s",
                    safe_error_type(err),
                )
                return self._result(
                    INTEGRITY_STATUS_UNREADABLE,
                    record,
                    started,
                    agent_id=agent_id,
                    digest=digest,
                    downloaded_size=downloaded_size,
                    protected=protected,
                    warnings=warnings,
                    error_code="unexpected_error",
                    checksum_changed=checksum_changed,
                )

            warnings.extend(details["warnings"])
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
                agent_id=agent_id,
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
        finally:
            cleanup_ok = await self.hass.async_add_executor_job(
                cleanup_temp_directory, temp_dir
            )
            if not cleanup_ok:
                _LOGGER.warning("Temporary verification data could not be removed")
            if repair_issues_enabled and not cleanup_ok:
                async_set_temporary_cleanup_issue(
                    self.hass,
                    active=True,
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
        bytes_since_space_check = 0
        try:
            async with asyncio.timeout(budget.remaining_seconds()):
                stream = await agent.async_download_backup(backup_id)
                async for chunk in stream:
                    if not isinstance(chunk, bytes):
                        raise TypeError("Backup agent returned a non-bytes chunk")
                    budget.add_downloaded(len(chunk))
                    digest.update(chunk)
                    await self.hass.async_add_executor_job(file_handle.write, chunk)
                    bytes_since_space_check += len(chunk)
                    if bytes_since_space_check >= _FREE_SPACE_CHECK_INTERVAL:
                        await self.hass.async_add_executor_job(
                            budget.check_free_space, path.parent
                        )
                        bytes_since_space_check = 0
        finally:
            await self.hass.async_add_executor_job(file_handle.close)
        return budget.downloaded_bytes, digest.hexdigest()

    @staticmethod
    def _select_agent(record: BackupRecord, agents: dict[str, Any]) -> str | None:
        """Prefer an available local copy, then any available copy."""
        available = [agent_id for agent_id in record.agents if agent_id in agents]
        if not available:
            return None
        local = [
            agent_id
            for agent_id in available
            if agent_id.endswith(".local") or agent_id == "backup.local"
        ]
        return sorted(local or available)[0]

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
        database_status = (
            INTEGRITY_DATABASE_NOT_FOUND
            if database_check
            else INTEGRITY_DATABASE_NOT_CHECKED
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

                normalized_name = PurePosixPath(member.name).name
                if normalized_name == "backup.json":
                    budget.ensure_expanded_capacity(member.size)
                    reader = outer.tar.extractfile(member)
                    if reader is None:
                        raise KeyError("backup_metadata_unreadable")
                    cls._consume_all(reader, budget=budget, count_expanded=True)
                    file_count += 1
                    continue

                if normalized_name.endswith(_INNER_SUFFIXES):
                    archive_count += 1
                    archive_name = cls._archive_prefix(normalized_name)
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

        database_expected = cls._database_expected(metadata)
        if database_check and database_path.exists():
            database_status = cls._check_database(
                database_path,
                database_timeout_minutes=database_timeout_minutes,
                budget=budget,
            )
        elif database_check and database_expected:
            warnings.append("database_not_found")

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
                if (
                    not member.isfile()
                    or PurePosixPath(member.name).name != "backup.json"
                ):
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
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise KeyError("backup_metadata_root_invalid")
                metadata = parsed

        if metadata_count != 1 or metadata is None:
            raise KeyError("backup_metadata_missing")
        return metadata

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
                if (
                    database_check
                    and PurePosixPath(inner_member.name).name == _DATABASE_FILENAME
                    and not database_path.exists()
                ):
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
        if isinstance(homeassistant, dict) and homeassistant.get("version"):
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
            return True
        return homeassistant.get("exclude_database") is not True

    @staticmethod
    def _validate_member_path(name: str) -> None:
        """Reject unsafe paths even though verification never extracts them."""
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
