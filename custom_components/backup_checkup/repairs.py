"""Home Assistant Repairs support for BackupCheckup."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, REPAIR_ISSUE_IDS, TROUBLESHOOTING_URL
from .models import BackupCheckupData


def _integrity_is_current(data: BackupCheckupData) -> bool:
    """Return whether the stored integrity result belongs to the latest backup."""
    latest = data.latest_monitored_backup_record
    return bool(latest and data.integrity.backup_id == latest.backup_id)


def _required_location_problem_count(data: BackupCheckupData) -> int:
    """Count unavailable storage locations used by the latest backup."""
    latest = data.latest_monitored_backup_record
    if latest is None:
        return 0
    return sum(
        bool(summary.error) and summary.agent_id in latest.agents
        for summary in data.agent_summaries
    )


def _issue_definitions(
    data: BackupCheckupData,
) -> dict[str, tuple[bool, ir.IssueSeverity, dict[str, str]]]:
    """Build the complete active Repair issue definition table."""
    latest = data.latest_monitored_backup_record
    integrity_current = _integrity_is_current(data)
    return {
        "no_backup": (data.no_backup, ir.IssueSeverity.ERROR, {}),
        "backup_integrity_failed": (
            integrity_current
            and data.integrity.status in {"corrupt", "unreadable", "internal_error"},
            ir.IssueSeverity.ERROR,
            {
                "checked": _format_datetime(data.integrity.checked_at),
                "location": (
                    data.integrity.agent_id
                    if data.expose_backup_metadata and data.integrity.agent_id
                    else "storage copy"
                ),
            },
        ),
        "backup_integrity_warning": (
            integrity_current
            and data.integrity.status
            in {"valid_with_warnings", "aborted", "password_required"},
            ir.IssueSeverity.WARNING,
            {"checked": _format_datetime(data.integrity.checked_at)},
        ),
        "backup_checksum_changed": (
            integrity_current and data.integrity.checksum_changed,
            ir.IssueSeverity.ERROR,
            {"checked": _format_datetime(data.integrity.checked_at)},
        ),
        "backup_stale": (
            data.backup_stale,
            ir.IssueSeverity.WARNING,
            {
                "age": _format_days(data.latest_backup_age_days_precise),
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
            {"scheduled": _format_datetime(data.next_automatic_backup)},
        ),
        "manager_unavailable": (
            data.manager_unavailable,
            ir.IssueSeverity.ERROR,
            {"state": data.manager_state},
        ),
        "storage_error": (
            data.storage_error,
            ir.IssueSeverity.ERROR,
            {"locations": ", ".join(sorted(data.agent_errors)) or "unknown"},
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
                "addons": str(len(latest.failed_addons) if latest else 0),
                "folders": str(len(latest.failed_folders) if latest else 0),
                "locations": str(len(latest.failed_agents) if latest else 0),
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
        "required_location_missing": (
            data.required_location_missing,
            ir.IssueSeverity.WARNING,
            {"count": str(_required_location_problem_count(data))},
        ),
    }


@callback
def async_update_issues(hass: HomeAssistant, data: BackupCheckupData) -> None:
    """Create active repair issues and remove resolved issues."""
    for issue_id, (active, severity, placeholders) in _issue_definitions(data).items():
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


@callback
def async_set_temporary_cleanup_issue(
    hass: HomeAssistant,
    *,
    active: bool,
) -> None:
    """Create or remove the temporary-data cleanup repair issue."""
    if active:
        ir.async_create_issue(
            hass,
            DOMAIN,
            "temporary_cleanup_failed",
            is_fixable=False,
            is_persistent=True,
            learn_more_url=TROUBLESHOOTING_URL,
            severity=ir.IssueSeverity.WARNING,
            translation_key="temporary_cleanup_failed",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, "temporary_cleanup_failed")


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
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}"


@callback
def async_set_storage_data_issue(
    hass: HomeAssistant,
    *,
    store_name: str,
    active: bool,
) -> None:
    """Create or remove a repair issue for invalid private store data."""
    issue_id = f"storage_data_invalid_{store_name}"
    if active:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            is_persistent=True,
            learn_more_url=TROUBLESHOOTING_URL,
            severity=ir.IssueSeverity.WARNING,
            translation_key="storage_data_invalid",
            translation_placeholders={"store": store_name},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
