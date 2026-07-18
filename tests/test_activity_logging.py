"""Tests for structured live BackupCheckup activity logging."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from custom_components.backup_checkup import activity as activity_module
from custom_components.backup_checkup.activity import (
    ACTIVITY_OUTCOME_CHANGED,
    ACTIVITY_OUTCOME_COMPLETED,
    ACTIVITY_OUTCOME_FAILED,
    ACTIVITY_OUTCOME_STARTED,
    BackupCheckupActivityLog,
)
from custom_components.backup_checkup.const import DOMAIN, NAME
from custom_components.backup_checkup.notifications import (
    BackupCheckupNotificationManager,
)


def test_record_publishes_bounded_structured_activity(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Records are timestamped, sanitized, logged, and published to Activity."""
    published: list[tuple[object, str, str, str]] = []
    hass = SimpleNamespace()
    monkeypatch.setattr(
        activity_module,
        "async_log_entry",
        lambda *args: published.append(args),
    )
    journal = BackupCheckupActivityLog(hass)
    details = {f"field {index}": f"value-{index}\nsecret" for index in range(15)}

    with caplog.at_level(logging.INFO, logger=activity_module.__name__):
        record = journal.record(
            "inventory_refresh",
            ACTIVITY_OUTCOME_COMPLETED,
            details=details,
        )

    assert record.timestamp.tzinfo is not None
    assert record.action == "inventory_refresh"
    assert record.outcome == ACTIVITY_OUTCOME_COMPLETED
    assert len(record.details) == 12
    assert all(" " not in key and "\n" not in value for key, value in record.details)
    assert journal.count == 1
    assert journal.latest is record
    assert published == [
        (
            hass,
            NAME,
            activity_module.BackupCheckupActivityLog._activity_message(record),
            DOMAIN,
        )
    ]
    assert "activity timestamp=" in caplog.text
    assert "action=inventory_refresh" in caplog.text
    assert "outcome=completed" in caplog.text


def test_activity_visibility_can_be_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detailed records can stay in Core logs without flooding Activity."""
    published: list[object] = []
    monkeypatch.setattr(
        activity_module,
        "async_log_entry",
        lambda *args: published.append(args),
    )
    journal = BackupCheckupActivityLog(SimpleNamespace())

    journal.record(
        "inventory_refresh",
        "started",
        activity_visible=False,
    )

    assert journal.count == 1
    assert published == []


def test_activity_publication_failure_never_breaks_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An optional Activity UI failure cannot destabilize BackupCheckup."""
    monkeypatch.setattr(
        activity_module,
        "async_log_entry",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("activity unavailable")),
    )
    journal = BackupCheckupActivityLog(SimpleNamespace())

    record = journal.record("setup", ACTIVITY_OUTCOME_FAILED)

    assert record.outcome == ACTIVITY_OUTCOME_FAILED
    assert journal.count == 1


def test_activity_ring_buffer_and_diagnostics_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The journal keeps only the newest 250 records and exports a limited slice."""
    monkeypatch.setattr(activity_module, "async_log_entry", lambda *_args: None)
    journal = BackupCheckupActivityLog(SimpleNamespace())

    for index in range(260):
        journal.record(
            "refresh",
            ACTIVITY_OUTCOME_COMPLETED,
            activity_visible=False,
            details={"sequence": index},
        )

    diagnostics = journal.diagnostics(limit=3)
    assert journal.count == 260
    assert diagnostics["runtime_event_count"] == 260
    assert diagnostics["buffered_event_count"] == 250
    assert [item["details"]["sequence"] for item in diagnostics["recent"]] == [
        "257",
        "258",
        "259",
    ]
    assert diagnostics["latest"]["details"]["sequence"] == "259"
    assert journal.diagnostics(limit=-1)["recent"] == []
    assert len(journal.diagnostics(limit=999)["recent"]) == 250


class _NotificationServices:
    """Capture notify calls and optionally raise one boundary error."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def async_call(
        self,
        domain: str,
        service: str,
        data: dict[str, object],
        **kwargs: object,
    ) -> None:
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "data": data,
                "target": kwargs.get("target"),
            }
        )
        if self.error is not None:
            raise self.error


def _notification_manager(
    journal: BackupCheckupActivityLog,
    services: _NotificationServices,
) -> BackupCheckupNotificationManager:
    """Return a notification manager with a minimal Home Assistant runtime."""
    hass = SimpleNamespace(
        config=SimpleNamespace(language="en"),
        services=services,
    )
    return BackupCheckupNotificationManager(hass, "entry", activity=journal)


def test_notification_success_is_logged_without_target_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Notification activity exposes counts but never entity identifiers."""
    monkeypatch.setattr(activity_module, "async_log_entry", lambda *_args: None)
    journal = BackupCheckupActivityLog(SimpleNamespace())
    services = _NotificationServices()
    manager = _notification_manager(journal, services)

    sent = asyncio.run(
        manager.async_send_test(("notify.mobile_app_phone", "notify.mobile_app_tablet"))
    )

    assert sent is True
    assert len(services.calls) == 1
    recent = journal.diagnostics(limit=2)["recent"]
    assert [item["outcome"] for item in recent] == [
        ACTIVITY_OUTCOME_STARTED,
        ACTIVITY_OUTCOME_COMPLETED,
    ]
    assert all(item["action"] == "notification_send" for item in recent)
    assert all(item["details"]["target_count"] == "2" for item in recent)
    assert all(item["details"]["notification_type"] == "test" for item in recent)
    assert "notify.mobile_app" not in repr(recent)


def test_notification_failure_is_logged_and_remains_nonfatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Controlled notify failures create a failed action result."""
    monkeypatch.setattr(activity_module, "async_log_entry", lambda *_args: None)
    journal = BackupCheckupActivityLog(SimpleNamespace())
    manager = _notification_manager(
        journal,
        _NotificationServices(ValueError("invalid target notify.private_phone")),
    )

    sent = asyncio.run(manager.async_send_test(("notify.private_phone",)))

    assert sent is False
    assert manager.last_error is not None
    latest = journal.latest
    assert latest is not None
    assert latest.action == "notification_send"
    assert latest.outcome == ACTIVITY_OUTCOME_FAILED
    assert dict(latest.details)["target_count"] == "1"
    assert "private_phone" not in repr(latest.as_dict())


def test_notification_disable_transition_is_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Turning notification processing off creates one state-change record."""
    monkeypatch.setattr(activity_module, "async_log_entry", lambda *_args: None)
    journal = BackupCheckupActivityLog(SimpleNamespace())
    manager = _notification_manager(journal, _NotificationServices())
    manager._loaded = True
    manager._was_enabled = True
    data = SimpleNamespace(active_problems=())

    asyncio.run(
        manager.async_process(
            data,
            enabled=False,
            targets=(),
            notify_on_recovery=True,
        )
    )

    latest = journal.latest
    assert latest is not None
    assert latest.action == "notification_processing"
    assert latest.outcome == ACTIVITY_OUTCOME_CHANGED
    assert dict(latest.details) == {"enabled": "False"}
