"""BackupCheckup 2.2.1 regression tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from custom_components.backup_checkup.analytics import (
    SIZE_TREND_INSUFFICIENT_DATA,
    calculate_inventory_analytics,
)
from custom_components.backup_checkup.configuration import normalize_configuration
from custom_components.backup_checkup.const import (
    CONF_ENTITY_MODE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_UPDATE_INTERVAL_MINUTES,
)
from custom_components.backup_checkup.history import BackupCheckupHistory
from custom_components.backup_checkup.models import BackupRecord
from custom_components.backup_checkup.security import VerificationBudget


class _FakeStore:
    def __init__(self, data):
        self.data = data

    async def async_load(self):
        return self.data

    def async_delay_save(self, _callback, *, delay):
        assert delay == 1


class _Hass:
    pass


def _record(*, date: datetime, automatic: bool, scope: str, size: int) -> BackupRecord:
    return BackupRecord(
        backup_id=f"{date.isoformat()}-{automatic}-{scope}",
        backup_reference="reference",
        name="backup",
        date=date,
        automatic=automatic,
        purpose="automatic" if automatic else "manual",
        included_addons=(),
        included_folders=(),
        scope_fingerprint=scope,
        agents=(),
        agent_copies=(),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=size,
        incomplete=False,
    )


def test_legacy_data_and_options_are_canonicalized() -> None:
    normalized = normalize_configuration(
        {
            CONF_UPDATE_INTERVAL_MINUTES: "15",
            CONF_NOTIFICATIONS_ENABLED: "false",
            CONF_NOTIFICATION_TARGETS: "notify.mobile_app_phone",
        },
        {
            CONF_UPDATE_INTERVAL_MINUTES: 20,
            CONF_ENTITY_MODE: "expert",
        },
    )

    assert normalized[CONF_UPDATE_INTERVAL_MINUTES] == 20
    assert normalized[CONF_NOTIFICATIONS_ENABLED] is False
    assert normalized[CONF_NOTIFICATION_TARGETS] == ["notify.mobile_app_phone"]
    assert normalized[CONF_ENTITY_MODE] == "expert"


def test_analytics_do_not_fall_back_outside_window() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    records = (
        _record(date=now - timedelta(days=60), automatic=True, scope="a", size=1),
    )

    result = calculate_inventory_analytics(records, now=now, window_days=30)

    assert result.analyzed_backup_count == 0
    assert result.average_backup_size is None
    assert result.size_trend == SIZE_TREND_INSUFFICIENT_DATA


def test_analytics_separate_manual_and_automatic_origins() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    records = (
        _record(date=now, automatic=False, scope="same", size=200),
        _record(date=now - timedelta(days=1), automatic=True, scope="same", size=100),
    )

    result = calculate_inventory_analytics(records, now=now, window_days=30)

    assert result.analyzed_backup_count == 1
    assert result.average_backup_size == 200
    assert result.analyzed_backup_origin == "manual"


def test_late_success_repairs_previous_failed_attempt() -> None:
    attempt = datetime(2026, 7, 17, 2, 0, tzinfo=UTC)
    history = BackupCheckupHistory(_Hass(), "entry")
    history._store = _FakeStore(
        {
            "tracking_started_at": attempt.isoformat(),
            "attempts": [
                {
                    "attempt_at": attempt.isoformat(),
                    "status": "failed",
                    "resolved_at": (attempt + timedelta(hours=7)).isoformat(),
                }
            ],
        }
    )

    metrics = asyncio.run(
        history.async_observe(
            last_attempt=attempt,
            last_success=attempt + timedelta(seconds=30),
            now=attempt + timedelta(hours=8),
            window_days=30,
        )
    )

    assert metrics.successful_attempts == 1
    assert metrics.failed_attempts == 0


def test_copy_budget_resets_counters_but_keeps_deadline() -> None:
    overall = VerificationBudget.from_options(
        max_download_gb=1,
        max_expanded_gb=2,
        timeout_minutes=30,
    )
    overall.downloaded_bytes = 900
    overall.expanded_bytes = 800
    overall.members = 7

    copy = overall.for_copy()

    assert copy.deadline == overall.deadline
    assert copy.cancellation_event is overall.cancellation_event
    assert copy.downloaded_bytes == 0
    assert copy.expanded_bytes == 0
    assert copy.members == 0
