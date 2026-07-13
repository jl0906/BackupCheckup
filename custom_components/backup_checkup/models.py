"""Data models for BackupCheckup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BackupRecord:
    """Serializable summary of one stored backup."""

    backup_id: str
    name: str
    date: datetime
    automatic: bool
    agents: tuple[str, ...]
    failed_agents: tuple[str, ...]
    size: int | None

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant state-attribute-safe representation."""
        return {
            "backup_id": self.backup_id,
            "name": self.name,
            "date": self.date.isoformat(),
            "automatic": self.automatic,
            "agents": list(self.agents),
            "failed_agents": list(self.failed_agents),
            "size": self.size,
        }


@dataclass(frozen=True, slots=True)
class BackupCheckupData:
    """Current BackupCheckup snapshot."""

    checked_at: datetime
    max_age_days: int
    total_backups: int
    automatic_backups: int
    manual_backups: int
    latest_backup: datetime | None
    latest_automatic_backup: datetime | None
    latest_manual_backup: datetime | None
    latest_backup_age_days: float | None
    automatic_backup_age_days: float | None
    manual_backup_age_days: float | None
    last_automatic_attempt: datetime | None
    last_successful_automatic_event: datetime | None
    next_automatic_backup: datetime | None
    manager_state: str
    agent_errors: dict[str, str]
    backups: tuple[BackupRecord, ...]
    no_backup: bool
    backup_stale: bool
    automatic_backup_overdue: bool
    automatic_backup_failed: bool
    automatic_schedule_missing: bool
    automatic_schedule_overdue: bool
    manager_unavailable: bool
    storage_error: bool
    problem: bool
    status: str
