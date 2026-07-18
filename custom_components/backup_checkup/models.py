"""Data models for BackupCheckup."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .age import completed_age_days
from .const import (
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_DATABASE_OPTIONS,
    INTEGRITY_STATUS_NOT_CHECKED,
    INTEGRITY_STATUS_OPTIONS,
)

_MAX_RESULT_COUNTER = 10_000_000
_MAX_VERIFIED_SIZE = 10**15
_MAX_DURATION_SECONDS = 365 * 86400
_MAX_STORED_WARNINGS = 1000
_MAX_LOADED_WARNINGS = 50


def _parse_stored_datetime(value: Any) -> datetime | None:
    """Parse a stored timestamp and normalize it to aware UTC."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return dt_util.as_utc(parsed)


def _valid_optional_datetime(value: Any) -> bool:
    """Return whether a persisted optional timestamp is valid."""
    return value is None or _parse_stored_datetime(value) is not None


def _valid_optional_text(value: Any) -> bool:
    """Return whether a persisted optional text field has the expected type."""
    return value is None or isinstance(value, str)


def _valid_optional_integral(value: Any) -> bool:
    """Return whether a persisted optional number is finite and integral."""
    if value is None:
        return True
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    numeric = float(value)
    return math.isfinite(numeric) and numeric >= 0 and numeric.is_integer()


def _valid_optional_duration(value: Any) -> bool:
    """Return whether a persisted optional duration is finite and non-negative."""
    if value is None:
        return True
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(float(value))
        and value >= 0
    )


def _valid_optional_bool(value: Any) -> bool:
    """Return whether a persisted optional value is a strict boolean."""
    return value is None or isinstance(value, bool)


def _valid_warnings(value: Any) -> bool:
    """Return whether persisted warning data is bounded text."""
    return value is None or (
        isinstance(value, list)
        and len(value) <= _MAX_STORED_WARNINGS
        and all(isinstance(item, str) for item in value)
    )


def _bounded_text(value: Any, *, maximum: int = 256) -> str | None:
    """Return one bounded non-empty stored string."""
    return value[:maximum] if isinstance(value, str) and value else None


def _bounded_integer(value: Any, *, maximum: int) -> int | None:
    """Return a bounded non-negative integer without accepting truncation."""
    if not _valid_optional_integral(value) or value is None:
        return None
    parsed = int(value)
    return parsed if parsed <= maximum else None


def _integer_or_zero(value: Any, *, maximum: int = _MAX_RESULT_COUNTER) -> int:
    """Return a bounded stored integer or zero."""
    return _bounded_integer(value, maximum=maximum) or 0


def _bounded_duration(value: Any) -> float | None:
    """Return a bounded finite duration."""
    if not _valid_optional_duration(value) or value is None:
        return None
    parsed = float(value)
    return parsed if parsed <= _MAX_DURATION_SECONDS else None


def _enum_or_default(value: Any, allowed: tuple[str, ...], default: str) -> str:
    """Return a supported stored enum value or its safe default."""
    return value if isinstance(value, str) and value in allowed else default


def _loaded_warnings(value: Any) -> tuple[str, ...]:
    """Return bounded warnings from private stored data."""
    if not isinstance(value, list):
        return ()
    return tuple(item[:128] for item in value if isinstance(item, str))[
        :_MAX_LOADED_WARNINGS
    ]


@dataclass(frozen=True, slots=True)
class BackupAgentRecord:
    """One stored copy of a backup on a backup agent."""

    agent_id: str
    agent_reference: str
    size: int | None
    protected: bool | None

    def as_dict(self, *, expose_metadata: bool = False) -> dict[str, Any]:
        """Return a privacy-safe storage-copy representation."""
        result: dict[str, Any] = {
            "storage_reference": self.agent_reference,
            "size": self.size,
            "protected": self.protected,
        }
        if expose_metadata:
            result["agent_id"] = self.agent_id
        return result


@dataclass(frozen=True, slots=True)
class BackupRecord:
    """Serializable summary of one stored backup."""

    backup_id: str
    backup_reference: str
    name: str
    date: datetime
    automatic: bool
    purpose: str
    included_addons: tuple[str, ...]
    included_folders: tuple[str, ...]
    scope_fingerprint: str
    agents: tuple[str, ...]
    agent_copies: tuple[BackupAgentRecord, ...]
    failed_agents: tuple[str, ...]
    failed_addons: tuple[str, ...]
    failed_folders: tuple[str, ...]
    database_included: bool | None
    homeassistant_included: bool | None
    size: int | None
    incomplete: bool
    copy_size_mismatch: bool = False
    copy_size_spread_bytes: int | None = None

    def as_public_dict(self) -> dict[str, Any]:
        """Return a privacy-safe state-attribute representation."""
        return {
            "backup_reference": self.backup_reference,
            "date": self.date.isoformat(),
            "automatic": self.automatic,
            "purpose": self.purpose,
            "included_addon_count": len(self.included_addons),
            "included_folder_count": len(self.included_folders),
            "scope_fingerprint": self.scope_fingerprint,
            "storage_references": [copy.agent_reference for copy in self.agent_copies],
            "agent_copies": [copy.as_dict() for copy in self.agent_copies],
            "failed_agent_count": len(self.failed_agents),
            "failed_addon_count": len(self.failed_addons),
            "failed_folder_count": len(self.failed_folders),
            "database_included": self.database_included,
            "homeassistant_included": self.homeassistant_included,
            "size": self.size,
            "incomplete": self.incomplete,
            "storage_copy_size_mismatch": self.copy_size_mismatch,
        }

    def as_private_dict(self) -> dict[str, Any]:
        """Return full metadata after the user explicitly opts in."""
        return {
            **self.as_public_dict(),
            "backup_id": self.backup_id,
            "name": self.name,
            "agents": list(self.agents),
            "agent_copies": [
                copy.as_dict(expose_metadata=True) for copy in self.agent_copies
            ],
            "included_addons": list(self.included_addons),
            "included_folders": list(self.included_folders),
            "failed_agents": list(self.failed_agents),
            "failed_addons": list(self.failed_addons),
            "failed_folders": list(self.failed_folders),
            "storage_copy_size_spread_bytes": self.copy_size_spread_bytes,
        }

    def as_dict(self, *, expose_metadata: bool = False) -> dict[str, Any]:
        """Return public metadata unless full details were explicitly enabled."""
        return self.as_private_dict() if expose_metadata else self.as_public_dict()


@dataclass(frozen=True, slots=True)
class BackupAgentSummary:
    """Current summary for one backup storage agent."""

    agent_id: str
    agent_reference: str
    storage_name: str
    backup_count: int
    inventory_backup_count: int
    ignored_update_backup_count: int
    latest_backup: datetime | None
    latest_backup_age_days: float | None
    latest_backup_size: int | None
    stored_bytes: int | None
    error: str | None
    stale: bool
    problem: bool

    def as_dict(self, *, expose_metadata: bool = False) -> dict[str, Any]:
        """Return a privacy-safe storage summary."""
        result: dict[str, Any] = {
            "storage_reference": self.agent_reference,
            "storage_name": self.storage_name,
            "backup_count": self.backup_count,
            "inventory_backup_count": self.inventory_backup_count,
            "ignored_update_backup_count": self.ignored_update_backup_count,
            "latest_backup": (
                self.latest_backup.isoformat() if self.latest_backup else None
            ),
            "latest_backup_age_days": completed_age_days(self.latest_backup_age_days),
            "latest_backup_age_days_precise": self.latest_backup_age_days,
            "latest_backup_size": self.latest_backup_size,
            "stored_bytes": self.stored_bytes,
            "error": self.error,
            "stale": self.stale,
            "problem": self.problem,
        }
        if expose_metadata:
            result["agent_id"] = self.agent_id
        return result


@dataclass(frozen=True, slots=True)
class BackupIntegrityResult:
    """Persisted result of a full backup integrity check."""

    status: str
    checked_at: datetime | None
    backup_id: str | None
    backup_reference: str | None
    backup_date: datetime | None
    agent_id: str | None
    sha256: str | None
    verified_size: int | None
    duration_seconds: float | None
    archive_count: int
    file_count: int
    protected: bool | None
    database_status: str
    warnings: tuple[str, ...]
    error_code: str | None
    checksum_changed: bool

    @classmethod
    def not_checked(cls) -> BackupIntegrityResult:
        """Return the initial state."""
        from .const import (
            INTEGRITY_DATABASE_NOT_CHECKED,
            INTEGRITY_STATUS_NOT_CHECKED,
        )

        return cls(
            status=INTEGRITY_STATUS_NOT_CHECKED,
            checked_at=None,
            backup_id=None,
            backup_reference=None,
            backup_date=None,
            agent_id=None,
            sha256=None,
            verified_size=None,
            duration_seconds=None,
            archive_count=0,
            file_count=0,
            protected=None,
            database_status=INTEGRITY_DATABASE_NOT_CHECKED,
            warnings=(),
            error_code=None,
            checksum_changed=False,
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize the integrity result."""
        return {
            "status": self.status,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "backup_id": self.backup_id,
            "backup_reference": self.backup_reference,
            "backup_date": self.backup_date.isoformat() if self.backup_date else None,
            "agent_id": self.agent_id,
            "sha256": self.sha256,
            "verified_size": self.verified_size,
            "duration_seconds": self.duration_seconds,
            "archive_count": self.archive_count,
            "file_count": self.file_count,
            "protected": self.protected,
            "database_status": self.database_status,
            "warnings": list(self.warnings),
            "error_code": self.error_code,
            "checksum_changed": self.checksum_changed,
        }

    @classmethod
    def storage_dict_is_valid(cls, data: dict[str, Any]) -> bool:
        """Return whether persisted integrity data has safe expected field types."""
        if not isinstance(data, dict):
            return False
        enum_fields_valid = (
            data.get("status") is None or data.get("status") in INTEGRITY_STATUS_OPTIONS
        ) and (
            data.get("database_status") is None
            or data.get("database_status") in INTEGRITY_DATABASE_OPTIONS
        )
        datetime_fields_valid = all(
            _valid_optional_datetime(data.get(key))
            for key in ("checked_at", "backup_date")
        )
        text_fields_valid = all(
            _valid_optional_text(data.get(key))
            for key in (
                "backup_id",
                "backup_reference",
                "agent_id",
                "sha256",
                "error_code",
            )
        )
        integer_fields_valid = all(
            _valid_optional_integral(data.get(key))
            for key in ("archive_count", "file_count", "verified_size")
        )
        return all(
            (
                enum_fields_valid,
                datetime_fields_valid,
                text_fields_valid,
                integer_fields_valid,
                _valid_optional_duration(data.get("duration_seconds")),
                _valid_optional_bool(data.get("protected")),
                _valid_optional_bool(data.get("checksum_changed")),
                _valid_warnings(data.get("warnings")),
            )
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupIntegrityResult:
        """Deserialize a stored integrity result defensively."""
        protected = data.get("protected")
        return cls(
            status=_enum_or_default(
                data.get("status"),
                tuple(INTEGRITY_STATUS_OPTIONS),
                INTEGRITY_STATUS_NOT_CHECKED,
            ),
            checked_at=_parse_stored_datetime(data.get("checked_at")),
            backup_id=_bounded_text(data.get("backup_id")),
            backup_reference=_bounded_text(
                data.get("backup_reference"),
                maximum=64,
            ),
            backup_date=_parse_stored_datetime(data.get("backup_date")),
            agent_id=_bounded_text(data.get("agent_id")),
            sha256=_bounded_text(data.get("sha256"), maximum=128),
            verified_size=_bounded_integer(
                data.get("verified_size"),
                maximum=_MAX_VERIFIED_SIZE,
            ),
            duration_seconds=_bounded_duration(data.get("duration_seconds")),
            archive_count=_integer_or_zero(data.get("archive_count", 0)),
            file_count=_integer_or_zero(data.get("file_count", 0)),
            protected=protected if isinstance(protected, bool) else None,
            database_status=_enum_or_default(
                data.get("database_status"),
                tuple(INTEGRITY_DATABASE_OPTIONS),
                INTEGRITY_DATABASE_NOT_CHECKED,
            ),
            warnings=_loaded_warnings(data.get("warnings", [])),
            error_code=_bounded_text(data.get("error_code"), maximum=128),
            checksum_changed=data.get("checksum_changed") is True,
        )


@dataclass(frozen=True, slots=True)
class BackupCheckupData:
    """Current BackupCheckup snapshot."""

    checked_at: datetime
    max_age_days: int
    minimum_backup_size_bytes: int
    maximum_size_drop_percent: int
    minimum_redundant_locations: int
    total_backups: int
    inventory_backup_count: int
    ignored_update_backup_count: int
    automatic_backups: int
    manual_backups: int
    latest_backup: datetime | None
    latest_automatic_backup: datetime | None
    latest_manual_backup: datetime | None
    latest_backup_age_days: int | None
    latest_backup_age_days_precise: float | None
    automatic_backup_age_days: int | None
    automatic_backup_age_days_precise: float | None
    manual_backup_age_days: int | None
    manual_backup_age_days_precise: float | None
    latest_backup_size: int | None
    latest_automatic_backup_size: int | None
    latest_backup_size_change_percent: float | None
    comparable_backup_count: int
    latest_backup_result: str
    latest_backup_locations: int
    latest_backup_location_ids: tuple[str, ...]
    last_automatic_attempt: datetime | None
    last_successful_automatic_event: datetime | None
    next_automatic_backup: datetime | None
    manager_state: str
    agent_errors: dict[str, str]
    agent_summaries: tuple[BackupAgentSummary, ...]
    backups: tuple[BackupRecord, ...]
    monitored_backups: tuple[BackupRecord, ...]
    no_backup: bool
    backup_stale: bool
    automatic_backup_overdue: bool
    automatic_backup_failed: bool
    automatic_schedule_missing: bool
    automatic_schedule_overdue: bool
    manager_unavailable: bool
    storage_error: bool
    backup_size_suspicious: bool
    latest_backup_incomplete: bool
    backup_not_redundant: bool
    required_location_missing: bool
    backup_checksum_changed: bool
    backup_integrity_warning: bool
    problem: bool
    status: str
    recommendation: str
    problem_count: int
    active_problems: tuple[str, ...]
    size_check_mode: str
    analytics_window_days: int
    health_score: int
    health_rating: str
    health_score_deductions: dict[str, int]
    average_backup_size: int | None
    longest_backup_gap_days: float | None
    size_trend: str
    size_trend_percent: float | None
    analyzed_backup_count: int
    analyzed_backup_scope: str | None
    analyzed_backup_origin: str | None
    automatic_success_rate: float | None
    automatic_attempts_observed: int
    automatic_successes_observed: int
    automatic_failures_observed: int
    consecutive_automatic_failures: int
    history_tracking_started_at: datetime | None
    integrity: BackupIntegrityResult
    integrity_check_running: bool
    expose_backup_metadata: bool
    invalid_backup_count: int
    invalid_agent_copy_count: int = 0
    copy_size_mismatch_count: int = 0
    last_inventory_success_at: datetime | None = None

    @property
    def latest_monitored_backup_record(self) -> BackupRecord | None:
        """Return the newest regular backup used for health monitoring."""
        return self.monitored_backups[0] if self.monitored_backups else None
