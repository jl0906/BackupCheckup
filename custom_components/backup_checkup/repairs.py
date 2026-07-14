"""Home Assistant Repairs support for BackupCheckup."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, REPAIR_ISSUE_IDS, TROUBLESHOOTING_URL
from .models import BackupCheckupData


@callback
def async_update_issues(hass: HomeAssistant, data: BackupCheckupData) -> None:
    """Create active repair issues and remove resolved issues."""
    latest = data.backups[0] if data.backups else None
    issue_definitions: dict[
        str,
        tuple[bool, ir.IssueSeverity, dict[str, str]],
    ] = {
        "no_backup": (
            data.no_backup,
            ir.IssueSeverity.ERROR,
            {},
        ),
        "backup_stale": (
            data.backup_stale,
            ir.IssueSeverity.WARNING,
            {
                "age": _format_days(data.latest_backup_age_days),
                "maximum": str(data.max_age_days),
            },
        ),
        "automatic_backup_overdue": (
            data.automatic_backup_overdue and not data.no_backup,
            ir.IssueSeverity.WARNING,
            {
                "age": _format_days(data.automatic_backup_age_days_precise),
                "maximum": str(data.max_age_days),
            },
        ),
        "automatic_backup_failed": (
            data.automatic_backup_failed,
            ir.IssueSeverity.ERROR,
            {
                "attempt": _format_datetime(data.last_automatic_attempt),
                "success": _format_datetime(data.last_successful_automatic_event),
            },
        ),
        "automatic_schedule_missing": (
            data.automatic_schedule_missing,
            ir.IssueSeverity.WARNING,
            {},
        ),
        "automatic_schedule_overdue": (
            data.automatic_schedule_overdue,
            ir.IssueSeverity.WARNING,
            {
                "scheduled": _format_datetime(data.next_automatic_backup),
            },
        ),
        "manager_unavailable": (
            data.manager_unavailable,
            ir.IssueSeverity.ERROR,
            {"state": data.manager_state},
        ),
        "storage_error": (
            data.storage_error,
            ir.IssueSeverity.ERROR,
            {
                "locations": ", ".join(sorted(data.agent_errors)) or "unknown",
            },
        ),
        "backup_size_suspicious": (
            data.backup_size_suspicious,
            ir.IssueSeverity.WARNING,
            {
                "size": _format_bytes(data.latest_backup_size),
                "change": _format_percent(data.latest_backup_size_change_percent),
                "threshold": str(data.maximum_size_drop_percent),
            },
        ),
        "latest_backup_incomplete": (
            data.latest_backup_incomplete,
            ir.IssueSeverity.ERROR,
            {
                "addons": _join_or_none(latest.failed_addons if latest else ()),
                "folders": _join_or_none(latest.failed_folders if latest else ()),
                "locations": _join_or_none(latest.failed_agents if latest else ()),
            },
        ),
        "backup_not_redundant": (
            data.backup_not_redundant,
            ir.IssueSeverity.WARNING,
            {
                "current": str(data.latest_backup_locations),
                "required": str(data.minimum_redundant_locations),
            },
        ),
    }

    for issue_id, (active, severity, placeholders) in issue_definitions.items():
        if active:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                is_persistent=False,
                learn_more_url=TROUBLESHOOTING_URL,
                severity=severity,
                translation_key=issue_id,
                translation_placeholders=placeholders,
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


@callback
def async_remove_issues(hass: HomeAssistant) -> None:
    """Remove all BackupCheckup repair issues."""
    for issue_id in REPAIR_ISSUE_IDS:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


def _format_datetime(value: datetime | None) -> str:
    """Format a datetime for use in a repair translation."""
    return value.isoformat() if value else "unknown"


def _format_days(value: float | None) -> str:
    """Format a day value without unnecessary precision."""
    return f"{value:.1f}" if value is not None else "unknown"


def _format_percent(value: float | None) -> str:
    """Format a percentage value."""
    return f"{value:.1f}%" if value is not None else "unknown"


def _format_bytes(value: int | None) -> str:
    """Format a byte value for a repair message."""
    if value is None:
        return "unknown"
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(value)
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}"


def _join_or_none(values: tuple[str, ...]) -> str:
    """Join a tuple for display in a repair message."""
    return ", ".join(values) if values else "none"
