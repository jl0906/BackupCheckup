"""Full backup integrity verification for BackupCheckup."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

from homeassistant.components.backup import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from securetar import (
    InvalidPasswordError,
    SecureTarArchive,
    SecureTarError,
)

from .const import (
    DOMAIN,
    INTEGRITY_DATABASE_FAILED,
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_DATABASE_NOT_FOUND,
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_CORRUPT,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1
_BUFFER_SIZE = 1024 * 1024
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
    ) -> BackupIntegrityResult:
        """Verify one backup copy and return a privacy-safe result."""
        started = time.monotonic()
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
            temp_context = tempfile.TemporaryDirectory(
                prefix="backup_checkup_",
                ignore_cleanup_errors=True,
            )
        except OSError as err:
            _LOGGER.warning(
                "Unable to create temporary verification directory: %s", err
            )
            return self._failure(
                INTEGRITY_STATUS_UNREADABLE,
                record,
                started,
                agent_id=agent_id,
                error_code="temporary_storage_unavailable",
            )

        with temp_context as temp_dir:
            backup_path = Path(temp_dir) / "backup.tar"
            try:
                downloaded_size, digest = await self._async_download(
                    manager.backup_agents[agent_id],
                    record.backup_id,
                    backup_path,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Unable to download backup %s from %s for integrity check: %s",
                    record.backup_id,
                    agent_id,
                    err,
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
                return BackupIntegrityResult(
                    status=INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
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
                    error_code="password_required",
                    checksum_changed=checksum_changed,
                )

            try:
                details = await self.hass.async_add_executor_job(
                    self._verify_archive,
                    backup_path,
                    password,
                    protected,
                    database_check,
                )
            except (_BackupPasswordRequiredError, InvalidPasswordError) as err:
                _LOGGER.debug("Backup password validation failed: %s", err)
                return BackupIntegrityResult(
                    status=INTEGRITY_STATUS_PASSWORD_REQUIRED,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
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
                    error_code="password_required",
                    checksum_changed=checksum_changed,
                )
            except (
                tarfile.TarError,
                SecureTarError,
                json.JSONDecodeError,
                KeyError,
            ) as err:
                _LOGGER.warning("Backup archive is corrupt or invalid: %s", err)
                return BackupIntegrityResult(
                    status=INTEGRITY_STATUS_CORRUPT,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
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
                    error_code="archive_invalid",
                    checksum_changed=checksum_changed,
                )
            except OSError as err:
                _LOGGER.warning("Backup archive could not be read: %s", err)
                return BackupIntegrityResult(
                    status=INTEGRITY_STATUS_UNREADABLE,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
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
                    error_code="read_failed",
                    checksum_changed=checksum_changed,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected backup integrity check failure: %s", err)
                return BackupIntegrityResult(
                    status=INTEGRITY_STATUS_UNREADABLE,
                    checked_at=dt_util.utcnow(),
                    backup_id=record.backup_id,
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
                    error_code="unexpected_error",
                    checksum_changed=checksum_changed,
                )

        warnings.extend(details["warnings"])
        database_status = details["database_status"]
        if database_status == INTEGRITY_DATABASE_FAILED:
            warnings.append("database_integrity_failed")

        status = (
            INTEGRITY_STATUS_VALID_WITH_WARNINGS if warnings else INTEGRITY_STATUS_VALID
        )
        if database_status == INTEGRITY_DATABASE_FAILED:
            status = INTEGRITY_STATUS_CORRUPT

        return BackupIntegrityResult(
            status=status,
            checked_at=dt_util.utcnow(),
            backup_id=record.backup_id,
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

    async def _async_download(
        self,
        agent: Any,
        backup_id: str,
        path: Path,
    ) -> tuple[int, str]:
        """Download one backup while calculating its SHA-256 checksum."""
        stream = await agent.async_download_backup(backup_id)
        digest = hashlib.sha256()
        size = 0
        with path.open("wb") as file_handle:
            async for chunk in stream:
                if not isinstance(chunk, bytes):
                    raise TypeError("Backup agent returned a non-bytes chunk")
                digest.update(chunk)
                size += len(chunk)
                await self.hass.async_add_executor_job(file_handle.write, chunk)
        return size, digest.hexdigest()

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
        password: str | None,
        protected: bool,
        database_check: bool,
    ) -> dict[str, Any]:
        """Synchronously read every outer and inner archive member."""
        archive_count = 0
        file_count = 0
        warnings: list[str] = []
        metadata: dict[str, Any] | None = None
        inner_names: set[str] = set()
        database_status = (
            INTEGRITY_DATABASE_NOT_FOUND
            if database_check
            else INTEGRITY_DATABASE_NOT_CHECKED
        )
        effective_protected = protected

        with tempfile.TemporaryDirectory(prefix="backup_checkup_verify_") as temp_dir:
            database_path = Path(temp_dir) / _DATABASE_FILENAME
            with SecureTarArchive(
                backup_path,
                "r",
                bufsize=_BUFFER_SIZE,
                password=password,
            ) as outer:
                members = outer.tar.getmembers()
                for member in members:
                    cls._validate_member_path(member.name)

                metadata_members = [
                    member
                    for member in members
                    if member.isfile()
                    and PurePosixPath(member.name).name == "backup.json"
                ]
                if len(metadata_members) != 1:
                    raise KeyError("backup.json must exist exactly once")
                metadata_member = metadata_members[0]
                metadata_reader = outer.tar.extractfile(metadata_member)
                if metadata_reader is None:
                    raise KeyError("backup.json is unreadable")
                parsed_metadata = json.loads(metadata_reader.read())
                if not isinstance(parsed_metadata, dict):
                    raise KeyError("backup.json root is not an object")
                metadata = parsed_metadata
                metadata_protected = metadata.get("protected")
                if isinstance(metadata_protected, bool):
                    effective_protected = metadata_protected
                file_count += 1

                for member in members:
                    if member is metadata_member or member.isdir():
                        continue
                    normalized_name = PurePosixPath(member.name).name
                    if not member.isfile():
                        continue
                    if normalized_name.endswith(_INNER_SUFFIXES):
                        archive_count += 1
                        archive_name = cls._archive_prefix(normalized_name)
                        inner_names.add(archive_name)
                        inspect_database = (
                            database_check and archive_name == "homeassistant"
                        )
                        if effective_protected:
                            if password is None:
                                raise _BackupPasswordRequiredError
                            with outer.extract_tar(member) as inner_stream:
                                file_count += cls._read_inner_archive(
                                    inner_stream,
                                    database_check=inspect_database,
                                    database_path=database_path,
                                )
                                cls._consume_all(inner_stream)
                        else:
                            inner_stream = outer.tar.extractfile(member)
                            if inner_stream is None:
                                raise tarfile.ReadError(f"Unable to read {member.name}")
                            file_count += cls._read_inner_archive(
                                inner_stream,
                                database_check=inspect_database,
                                database_path=database_path,
                            )
                            cls._consume_all(inner_stream)
                        continue
                    reader = outer.tar.extractfile(member)
                    if reader is None:
                        raise tarfile.ReadError(f"Unable to read {member.name}")
                    cls._consume_all(reader)
                    file_count += 1

            if metadata is None:
                raise KeyError("backup.json not found")
            expected = cls._expected_archives(metadata)
            missing = expected - inner_names
            if missing:
                raise KeyError(f"Missing expected inner archives: {sorted(missing)}")
            if archive_count == 0:
                raise tarfile.ReadError("No inner backup archives found")

            database_expected = cls._database_expected(metadata)
            if database_check and database_path.exists():
                database_status = cls._check_database(database_path)
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
    def _read_inner_archive(
        cls,
        stream: Any,
        *,
        database_check: bool,
        database_path: Path,
    ) -> int:
        """Read every member of one inner archive and return its file count."""
        file_count = 0
        with tarfile.open(
            fileobj=stream,
            mode="r|*",
            bufsize=_BUFFER_SIZE,
        ) as inner:
            for inner_member in inner:
                cls._validate_member_path(inner_member.name)
                if not inner_member.isfile():
                    continue
                file_count += 1
                reader = inner.extractfile(inner_member)
                if reader is None:
                    raise tarfile.ReadError(f"Unable to read {inner_member.name}")
                if (
                    database_check
                    and PurePosixPath(inner_member.name).name == _DATABASE_FILENAME
                ):
                    with database_path.open("wb") as db_file:
                        cls._copy_all(reader, db_file)
                else:
                    cls._consume_all(reader)
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
            raise tarfile.ReadError(f"Unsafe archive member path: {name}")

    @staticmethod
    def _consume_all(reader: Any) -> int:
        """Read a file-like object to EOF."""
        total = 0
        while chunk := reader.read(_BUFFER_SIZE):
            total += len(chunk)
        return total

    @staticmethod
    def _copy_all(reader: Any, writer: Any) -> int:
        """Copy a file-like object completely."""
        total = 0
        while chunk := reader.read(_BUFFER_SIZE):
            writer.write(chunk)
            total += len(chunk)
        return total

    @staticmethod
    def _check_database(path: Path) -> str:
        """Run SQLite's full integrity check on the backed-up database."""
        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro&immutable=1",
                uri=True,
                timeout=30,
            )
            try:
                rows = connection.execute("PRAGMA integrity_check").fetchall()
            finally:
                connection.close()
        except sqlite3.DatabaseError:
            return INTEGRITY_DATABASE_FAILED
        return (
            INTEGRITY_DATABASE_PASSED
            if rows and all(str(row[0]).lower() == "ok" for row in rows)
            else INTEGRITY_DATABASE_FAILED
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
