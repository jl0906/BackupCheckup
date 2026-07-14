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

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant state-attribute-safe representation."""
        return {
            "backup_id": self.backup_id,
            "name": self.name,
            "date": self.date.isoformat(),
            "automatic": self.automatic,
            "agents": list(self.agents),
            "agent_copies": [copy.as_dict() for copy in self.agent_copies],
            "failed_agents": list(self.failed_agents),
            "failed_addons": list(self.failed_addons),
            "failed_folders": list(self.failed_folders),
            "database_included": self.database_included,
            "homeassistant_included": self.homeassistant_included,
            "size": self.size,
            "incomplete": self.incomplete,
        }


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
