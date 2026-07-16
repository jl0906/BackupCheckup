"""Diagnostics support for BackupCheckup."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as home_assistant_version
from homeassistant.core import HomeAssistant

from .const import CONF_NOTIFICATION_TARGETS, VERSION
from .coordinator import BackupCheckupCoordinator
from .models import BackupRecord
from .security import (
    anonymous_agent_reference,
    classify_exception,
    safe_error_type,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a BackupCheckup config entry."""
    coordinator: BackupCheckupCoordinator = entry.runtime_data
    data = coordinator.data

    configuration = {**entry.data, **entry.options}
    notification_targets = configuration.pop(CONF_NOTIFICATION_TARGETS, [])

    return {
        "integration": {
            "version": VERSION,
            "home_assistant_version": home_assistant_version,
            "config_entry_version": entry.version,
            "title": entry.title,
        },
        "configuration": {
            **configuration,
            "notification_target_count": len(notification_targets or []),
        },
        "notifications": {
            "enabled": coordinator.notifications_enabled,
            "target_count": len(coordinator.notification_targets),
            "notify_on_recovery": coordinator.notify_on_recovery,
            "last_error": coordinator.notification_manager.last_error,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                {
                    "error_code": classify_exception(coordinator.last_exception),
                    "error_type": safe_error_type(coordinator.last_exception),
                }
                if coordinator.last_exception is not None
                else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval is not None
                else None
            ),
            "checked_at": data.checked_at.isoformat(),
        },
        "health": {
            "score": data.health_score,
            "rating": data.health_rating,
            "score_deductions": data.health_score_deductions,
            "status": data.status,
            "recommendation": data.recommendation,
            "problem": data.problem,
            "problem_count": data.problem_count,
            "active_problems": list(data.active_problems),
            "flags": {
                "no_backup": data.no_backup,
                "backup_stale": data.backup_stale,
                "automatic_backup_overdue": data.automatic_backup_overdue,
                "automatic_backup_failed": data.automatic_backup_failed,
                "automatic_schedule_missing": data.automatic_schedule_missing,
                "automatic_schedule_overdue": data.automatic_schedule_overdue,
                "manager_unavailable": data.manager_unavailable,
                "storage_error": data.storage_error,
                "backup_size_suspicious": data.backup_size_suspicious,
                "latest_backup_incomplete": data.latest_backup_incomplete,
                "backup_not_redundant": data.backup_not_redundant,
                "required_location_missing": data.required_location_missing,
                "backup_checksum_changed": data.backup_checksum_changed,
            },
        },
        "inventory": {
            "monitored_backup_count": data.total_backups,
            "inventory_backup_count": data.inventory_backup_count,
            "ignored_update_backup_count": data.ignored_update_backup_count,
            "automatic_backups": data.automatic_backups,
            "manual_or_other_backups": data.manual_backups,
            "latest_backup": (
                data.latest_backup.isoformat() if data.latest_backup else None
            ),
            "latest_backup_age_days": data.latest_backup_age_days,
            "latest_backup_size": data.latest_backup_size,
            "latest_backup_size_change_percent": (
                data.latest_backup_size_change_percent
            ),
            "latest_backup_result": data.latest_backup_result,
            "latest_backup_purpose": (
                data.latest_monitored_backup_record.purpose
                if data.latest_monitored_backup_record
                else None
            ),
            "latest_inventory_backup_purpose": (
                data.backups[0].purpose if data.backups else None
            ),
            "latest_backup_locations": list(data.latest_backup_location_ids),
            "comparable_backup_count": data.comparable_backup_count,
            "latest_automatic_backup": (
                data.latest_automatic_backup.isoformat()
                if data.latest_automatic_backup
                else None
            ),
            "automatic_backup_age_days": data.automatic_backup_age_days,
            "automatic_backup_age_days_precise": (
                data.automatic_backup_age_days_precise
            ),
            "latest_manual_backup": (
                data.latest_manual_backup.isoformat()
                if data.latest_manual_backup
                else None
            ),
            "manager_state": data.manager_state,
            "invalid_backup_count": data.invalid_backup_count,
        },
        "integrity": {
            "status": data.integrity.status,
            "check_running": data.integrity_check_running,
            "checked_at": (
                data.integrity.checked_at.isoformat()
                if data.integrity.checked_at
                else None
            ),
            "backup_date": (
                data.integrity.backup_date.isoformat()
                if data.integrity.backup_date
                else None
            ),
            "backup_reference": data.integrity.backup_reference,
            "storage_location": (
                data.integrity.agent_id
                if data.expose_backup_metadata
                else (
                    anonymous_agent_reference(entry.entry_id, data.integrity.agent_id)
                    if data.integrity.agent_id
                    else None
                )
            ),
            "sha256": (
                data.integrity.sha256
                if data.expose_backup_metadata
                else (data.integrity.sha256[:16] if data.integrity.sha256 else None)
            ),
            "verified_size": data.integrity.verified_size,
            "duration_seconds": data.integrity.duration_seconds,
            "archive_count": data.integrity.archive_count,
            "file_count": data.integrity.file_count,
            "protected": data.integrity.protected,
            "database_status": data.integrity.database_status,
            "warnings": list(data.integrity.warnings),
            "error_code": data.integrity.error_code,
            "checksum_changed": data.integrity.checksum_changed,
        },
        "analytics": {
            "window_days": data.analytics_window_days,
            "analyzed_backup_count": data.analyzed_backup_count,
            "analyzed_backup_scope": data.analyzed_backup_scope,
            "ignored_update_backup_count": data.ignored_update_backup_count,
            "average_backup_size": data.average_backup_size,
            "longest_backup_gap_days": data.longest_backup_gap_days,
            "size_trend": data.size_trend,
            "size_trend_percent": data.size_trend_percent,
            "automatic_success_rate": data.automatic_success_rate,
            "automatic_attempts_observed": data.automatic_attempts_observed,
            "automatic_successes_observed": data.automatic_successes_observed,
            "automatic_failures_observed": data.automatic_failures_observed,
            "consecutive_automatic_failures": (data.consecutive_automatic_failures),
            "history_tracking_started_at": (
                data.history_tracking_started_at.isoformat()
                if data.history_tracking_started_at
                else None
            ),
        },
        "automatic_backup_system": {
            "last_attempt": (
                data.last_automatic_attempt.isoformat()
                if data.last_automatic_attempt
                else None
            ),
            "last_success": (
                data.last_successful_automatic_event.isoformat()
                if data.last_successful_automatic_event
                else None
            ),
            "next_scheduled": (
                data.next_automatic_backup.isoformat()
                if data.next_automatic_backup
                else None
            ),
        },
        "storage": {
            "minimum_required_locations": data.minimum_redundant_locations,
            "agent_errors": data.agent_errors,
            "agents": [
                item.as_dict(expose_metadata=data.expose_backup_metadata)
                for item in data.agent_summaries
            ],
        },
        "recent_inventory_backups": [
            _serialize_backup(record) for record in data.backups[:20]
        ],
        "recent_monitored_backups": [
            _serialize_backup(record) for record in data.monitored_backups[:20]
        ],
    }


def _serialize_backup(record: BackupRecord) -> dict[str, Any]:
    """Serialize a backup without exposing its user-defined name or ID."""
    return record.as_public_dict()
