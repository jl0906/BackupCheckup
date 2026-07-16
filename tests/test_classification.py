"""Tests for technical backup filtering and comparable-size selection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.backup_checkup.classification import (
    automatic_size_drop_is_suspicious,
    classify_backup_purpose,
    comparable_size_backups,
    monitoring_backups,
)
from custom_components.backup_checkup.const import (
    BACKUP_PURPOSE_APP_UPDATE,
    BACKUP_PURPOSE_AUTOMATIC,
    BACKUP_PURPOSE_MANUAL,
)
from custom_components.backup_checkup.models import BackupRecord


def _record(
    backup_id: str,
    *,
    days_ago: int,
    automatic: bool,
    purpose: str,
    scope: str,
    size: int,
) -> BackupRecord:
    return BackupRecord(
        backup_id=backup_id,
        backup_reference=f"ref-{backup_id}",
        name=backup_id,
        date=datetime(2026, 7, 16, tzinfo=UTC) - timedelta(days=days_ago),
        automatic=automatic,
        purpose=purpose,
        included_addons=("addon-a",),
        included_folders=("share",),
        scope_fingerprint=scope,
        agents=("backup.local",),
        agent_copies=(),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=size,
        incomplete=False,
    )


def test_app_update_marker_takes_precedence() -> None:
    assert (
        classify_backup_purpose(
            automatic=False,
            extra_metadata={"supervisor.addon_update": "core_mosquitto"},
        )
        == BACKUP_PURPOSE_APP_UPDATE
    )
    assert (
        classify_backup_purpose(automatic=True, extra_metadata={})
        == BACKUP_PURPOSE_AUTOMATIC
    )
    assert (
        classify_backup_purpose(automatic=False, extra_metadata={})
        == BACKUP_PURPOSE_MANUAL
    )


def test_app_update_backup_is_not_monitored() -> None:
    update = _record(
        "update",
        days_ago=0,
        automatic=False,
        purpose=BACKUP_PURPOSE_APP_UPDATE,
        scope="addon-only",
        size=50_000,
    )
    regular = _record(
        "regular",
        days_ago=1,
        automatic=True,
        purpose=BACKUP_PURPOSE_AUTOMATIC,
        scope="full",
        size=2_000_000_000,
    )
    assert monitoring_backups((update, regular)) == (regular,)


def test_size_comparison_requires_same_scope_and_origin() -> None:
    latest = _record(
        "latest",
        days_ago=0,
        automatic=True,
        purpose=BACKUP_PURPOSE_AUTOMATIC,
        scope="full",
        size=1_500_000_000,
    )
    same_scope = _record(
        "same",
        days_ago=1,
        automatic=True,
        purpose=BACKUP_PURPOSE_AUTOMATIC,
        scope="full",
        size=2_000_000_000,
    )
    manual = _record(
        "manual",
        days_ago=2,
        automatic=False,
        purpose=BACKUP_PURPOSE_MANUAL,
        scope="full",
        size=2_100_000_000,
    )
    partial = _record(
        "partial",
        days_ago=3,
        automatic=True,
        purpose=BACKUP_PURPOSE_AUTOMATIC,
        scope="partial",
        size=100_000_000,
    )
    assert comparable_size_backups(latest, (latest, same_scope, manual, partial)) == (
        same_scope,
    )


def test_automatic_size_drop_needs_two_comparable_backups() -> None:
    assert not automatic_size_drop_is_suspicious(
        maximum_drop_percent=50,
        previous_change_percent=-80.0,
        baseline_change_percent=-80.0,
        comparable_backup_count=1,
    )
    assert automatic_size_drop_is_suspicious(
        maximum_drop_percent=50,
        previous_change_percent=-80.0,
        baseline_change_percent=-80.0,
        comparable_backup_count=2,
    )


def test_native_automatic_event_is_authoritative() -> None:
    """Native events suppress timestamp lag and report explicit failures."""
    from datetime import UTC, datetime, timedelta

    from custom_components.backup_checkup.classification import automatic_backup_failed

    attempt = datetime(2026, 7, 16, 12, tzinfo=UTC)
    old_success = attempt - timedelta(hours=1)
    assert not automatic_backup_failed(
        event_type="completed",
        in_progress=False,
        last_attempt=attempt,
        last_success=old_success,
    )
    assert automatic_backup_failed(
        event_type="failed",
        in_progress=False,
        last_attempt=None,
        last_success=None,
    )
    assert not automatic_backup_failed(
        event_type="in_progress",
        in_progress=True,
        last_attempt=attempt,
        last_success=old_success,
    )


def test_automatic_failure_timestamp_fallback() -> None:
    """Older Home Assistant versions still use the guarded timestamp fallback."""
    from datetime import UTC, datetime, timedelta

    from custom_components.backup_checkup.classification import automatic_backup_failed

    attempt = datetime(2026, 7, 16, 12, tzinfo=UTC)
    success = attempt - timedelta(minutes=10)
    assert automatic_backup_failed(
        event_type="",
        in_progress=False,
        last_attempt=attempt,
        last_success=success,
    )
    assert not automatic_backup_failed(
        event_type="",
        in_progress=True,
        last_attempt=attempt,
        last_success=success,
    )
