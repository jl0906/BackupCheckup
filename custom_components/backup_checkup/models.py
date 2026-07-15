"""Data models for BackupCheckup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BackupAgentRecord:
    """One stored copy of a backup on a backup agent."""

    agent_id: str
    size: int | None
    protected: bool | None

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant state-attribute-safe representation."""
        return {
            "agent_id": self.agent_id,
            "size": self.size,
            "protected": self.protected,
        }


@dataclass(frozen=True, slots=True)
class BackupRecord:
    """Serializable summary of one stored backup."""

    backup_id: str
    backup_reference: str
    name: str
    date: datetime
    automatic: bool
    agents: tuple[str, ...]
    agent_copies: tuple[BackupAgentRecord, ...]
    failed_agents: tuple[str, ...]
    failed_addons: tuple[str, ...]
    failed_folders: tuple[str, ...]
    database_included: bool | None
    homeassistant_included: bool | None
    size: int | None
    incomplete: bool

    def as_public_dict(self) -> dict[str, Any]:
        """Return a privacy-safe state-attribute representation."""
        return {
            "backup_reference": self.backup_reference,
            "date": self.date.isoformat(),
            "automatic": self.automatic,
            "agents": list(self.agents),
            "agent_copies": [copy.as_dict() for copy in self.agent_copies],
            "failed_agent_count": len(self.failed_agents),
            "failed_addon_count": len(self.failed_addons),
            "failed_folder_count": len(self.failed_folders),
            "database_included": self.database_included,
            "homeassistant_included": self.homeassistant_included,
            "size": self.size,
            "incomplete": self.incomplete,
        }

    def as_private_dict(self) -> dict[str, Any]:
        """Return full metadata after the user explicitly opts in."""
        return {
            **self.as_public_dict(),
            "backup_id": self.backup_id,
            "name": self.name,
            "failed_agents": list(self.failed_agents),
            "failed_addons": list(self.failed_addons),
            "failed_folders": list(self.failed_folders),
        }

    def as_dict(self, *, expose_metadata: bool = False) -> dict[str, Any]:
        """Return public metadata unless full details were explicitly enabled."""
        return self.as_private_dict() if expose_metadata else self.as_public_dict()


@dataclass(frozen=True, slots=True)
class BackupAgentSummary:
    """Current summary for one backup storage agent."""

    agent_id: str
    backup_count: int
    latest_backup: datetime | None
    latest_backup_age_days: float | None
    latest_backup_size: int | None
    stored_bytes: int | None
    error: str | None
    stale: bool
    problem: bool

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant state-attribute-safe representation."""
        return {
            "agent_id": self.agent_id,
            "backup_count": self.backup_count,
            "latest_backup": (
                self.latest_backup.isoformat() if self.latest_backup else None
            ),
            "latest_backup_age_days": self.latest_backup_age_days,
            "latest_backup_size": self.latest_backup_size,
            "stored_bytes": self.stored_bytes,
            "error": self.error,
            "stale": self.stale,
            "problem": self.problem,
        }


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
    def from_dict(cls, data: dict[str, Any]) -> BackupIntegrityResult:
        """Deserialize a stored integrity result."""
        from homeassistant.util import dt as dt_util

        from .const import (
            INTEGRITY_DATABASE_NOT_CHECKED,
            INTEGRITY_STATUS_NOT_CHECKED,
        )

        def parse(value: Any) -> datetime | None:
            if not isinstance(value, str):
                return None
            return dt_util.parse_datetime(value)

        backup_id = data.get("backup_id")
        backup_reference = data.get("backup_reference")
        agent_id = data.get("agent_id")
        sha256 = data.get("sha256")
        verified_size = data.get("verified_size")
        duration_seconds = data.get("duration_seconds")
        protected = data.get("protected")
        error_code = data.get("error_code")
        warnings = data.get("warnings", [])
        return cls(
            status=str(data.get("status", INTEGRITY_STATUS_NOT_CHECKED)),
            checked_at=parse(data.get("checked_at")),
            backup_id=backup_id if isinstance(backup_id, str) else None,
            backup_reference=(
                backup_reference if isinstance(backup_reference, str) else None
            ),
            backup_date=parse(data.get("backup_date")),
            agent_id=agent_id if isinstance(agent_id, str) else None,
            sha256=sha256 if isinstance(sha256, str) else None,
            verified_size=(
                int(verified_size) if isinstance(verified_size, (int, float)) else None
            ),
            duration_seconds=(
                float(duration_seconds)
                if isinstance(duration_seconds, (int, float))
                else None
            ),
            archive_count=int(data.get("archive_count", 0)),
            file_count=int(data.get("file_count", 0)),
            protected=protected if isinstance(protected, bool) else None,
            database_status=str(
                data.get("database_status", INTEGRITY_DATABASE_NOT_CHECKED)
            ),
            warnings=tuple(str(item) for item in warnings if isinstance(item, str)),
            error_code=error_code if isinstance(error_code, str) else None,
            checksum_changed=bool(data.get("checksum_changed", False)),
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
    automatic_backups: int
    manual_backups: int
    latest_backup: datetime | None
    latest_automatic_backup: datetime | None
    latest_manual_backup: datetime | None
    latest_backup_age_days: float | None
    automatic_backup_age_days: int | None
    automatic_backup_age_days_precise: float | None
    manual_backup_age_days: float | None
    latest_backup_size: int | None
    latest_automatic_backup_size: int | None
    latest_backup_size_change_percent: float | None
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
    automatic_success_rate: float | None
    automatic_attempts_observed: int
    automatic_successes_observed: int
    automatic_failures_observed: int
    consecutive_automatic_failures: int
    history_tracking_started_at: datetime | None
    integrity: BackupIntegrityResult
    integrity_check_running: bool
    expose_backup_metadata: bool
