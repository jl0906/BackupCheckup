"""Diagnostics support for BackupCheckup."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BackupCheckupCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a BackupCheckup config entry."""
    coordinator: BackupCheckupCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    return {
        "config": {**entry.data, **entry.options},
        "status": data.status,
        "checked_at": data.checked_at.isoformat(),
        "total_backups": data.total_backups,
        "automatic_backups": data.automatic_backups,
        "manual_or_other_backups": data.manual_backups,
        "latest_backup": data.latest_backup.isoformat() if data.latest_backup else None,
        "latest_automatic_backup": (
            data.latest_automatic_backup.isoformat()
            if data.latest_automatic_backup
            else None
        ),
        "latest_manual_backup": (
            data.latest_manual_backup.isoformat()
            if data.latest_manual_backup
            else None
        ),
        "manager_state": data.manager_state,
        "agent_errors": data.agent_errors,
        "flags": {
            "no_backup": data.no_backup,
            "backup_stale": data.backup_stale,
            "automatic_backup_overdue": data.automatic_backup_overdue,
            "automatic_backup_failed": data.automatic_backup_failed,
            "automatic_schedule_missing": data.automatic_schedule_missing,
            "automatic_schedule_overdue": data.automatic_schedule_overdue,
            "manager_unavailable": data.manager_unavailable,
            "storage_error": data.storage_error,
            "problem": data.problem,
        },
        "backups": [item.as_dict() for item in data.backups],
    }
