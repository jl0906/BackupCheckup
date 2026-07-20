"""Regression coverage for BackupCheckup 2.2.3 fixes."""

from __future__ import annotations

import asyncio
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from custom_components.backup_checkup import diagnostics, notifications, repairs
from custom_components.backup_checkup.const import (
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    RECOMMENDATION_NONE,
    STATUS_OK,
)
from custom_components.backup_checkup.coordinator import BackupCheckupCoordinator
from custom_components.backup_checkup.models import (
    BackupAgentRecord,
    BackupAgentSummary,
    BackupCheckupData,
    BackupIntegrityResult,
    BackupRecord,
)
from custom_components.backup_checkup.native_backup import _as_datetime, _enum_value
from custom_components.backup_checkup.notifications import (
    BackupCheckupNotificationManager,
)
from custom_components.backup_checkup.security import safe_log_value


def _record(*, date: datetime | None = None) -> BackupRecord:
    return BackupRecord(
        backup_id="backup-id",
        backup_reference="backup-ref",
        name="Backup",
        date=date or datetime.now(UTC),
        automatic=True,
        purpose="automatic",
        included_addons=(),
        included_folders=(),
        scope_fingerprint="scope",
        agents=("backup.local",),
        agent_copies=(
            BackupAgentRecord("backup.local", "storage-ref", 10_000_000, False),
        ),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=10_000_000,
        incomplete=False,
    )


def _result(
    status: str,
    *,
    checked_at: datetime,
    error_code: str | None = None,
) -> BackupIntegrityResult:
    return BackupIntegrityResult(
        status=status,
        checked_at=checked_at,
        backup_id="backup-id",
        backup_reference="backup-ref",
        backup_date=checked_at,
        agent_id="backup.local",
        sha256=None,
        verified_size=None,
        duration_seconds=1.0,
        archive_count=0,
        file_count=0,
        protected=False,
        database_status=INTEGRITY_DATABASE_NOT_CHECKED,
        warnings=(),
        error_code=error_code,
        checksum_changed=False,
    )


def _data(
    *,
    now: datetime | None = None,
    record: BackupRecord | None = None,
    summary: BackupAgentSummary | None = None,
) -> BackupCheckupData:
    now = now or datetime.now(UTC)
    record = record or _record(date=now)
    values: dict[str, Any] = {field.name: None for field in fields(BackupCheckupData)}
    values.update(
        checked_at=now,
        max_age_days=2,
        minimum_backup_size_bytes=1_000_000,
        maximum_size_drop_percent=35,
        minimum_redundant_locations=1,
        total_backups=1,
        inventory_backup_count=1,
        ignored_update_backup_count=0,
        automatic_backups=1,
        manual_backups=0,
        latest_backup=record.date,
        latest_automatic_backup=record.date,
        latest_manual_backup=None,
        latest_backup_age_days=0,
        latest_backup_age_days_precise=0.0,
        automatic_backup_age_days=0,
        automatic_backup_age_days_precise=0.0,
        manual_backup_age_days=None,
        manual_backup_age_days_precise=None,
        latest_backup_size=record.size,
        latest_automatic_backup_size=record.size,
        latest_backup_size_change_percent=None,
        comparable_backup_count=0,
        latest_backup_result="complete",
        latest_backup_locations=1,
        latest_backup_location_ids=("storage-ref",),
        last_automatic_attempt=record.date,
        last_successful_automatic_event=record.date,
        next_automatic_backup=now + timedelta(days=1),
        manager_state="idle",
        agent_errors={},
        agent_summaries=(summary,) if summary else (),
        backups=(record,),
        monitored_backups=(record,),
        no_backup=False,
        backup_stale=False,
        automatic_backup_overdue=False,
        automatic_backup_failed=False,
        automatic_schedule_missing=False,
        automatic_schedule_overdue=False,
        manager_unavailable=False,
        storage_error=False,
        backup_size_suspicious=False,
        latest_backup_incomplete=False,
        backup_not_redundant=False,
        required_location_missing=False,
        backup_checksum_changed=False,
        backup_integrity_warning=False,
        problem=False,
        status=STATUS_OK,
        recommendation=RECOMMENDATION_NONE,
        problem_count=0,
        active_problems=(),
        size_check_mode="automatic",
        analytics_window_days=30,
        health_score=100,
        health_rating="excellent",
        health_score_deductions={},
        average_backup_size=record.size,
        longest_backup_gap_days=None,
        size_trend="insufficient_data",
        size_trend_percent=None,
        analyzed_backup_count=1,
        analyzed_backup_scope=record.scope_fingerprint,
        analyzed_backup_origin="automatic",
        automatic_success_rate=100.0,
        automatic_attempts_observed=1,
        automatic_successes_observed=1,
        automatic_failures_observed=0,
        consecutive_automatic_failures=0,
        history_tracking_started_at=now,
        integrity=BackupIntegrityResult.not_checked(),
        integrity_check_running=False,
        expose_backup_metadata=False,
        invalid_backup_count=0,
        invalid_agent_copy_count=0,
        copy_size_mismatch_count=0,
        last_inventory_success_at=now,
    )
    return BackupCheckupData(**values)


def _bare_coordinator(result: BackupIntegrityResult) -> BackupCheckupCoordinator:
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.integrity_result = result
    coordinator._integrity_retry_not_before = None
    coordinator._integrity_retry_key = None
    coordinator._integrity_retry_attempts = 0
    coordinator._backup_password_marker = None
    coordinator._backup_password_marker_initialized = False
    return coordinator


def test_retry_policy_blocks_immediate_and_limits_attempts() -> None:
    now = datetime.now(UTC)
    coordinator = _bare_coordinator(
        _result(
            INTEGRITY_STATUS_UNREADABLE,
            checked_at=now,
            error_code="read_failed",
        )
    )
    record = _record(date=now)

    coordinator._update_integrity_retry_state(coordinator.integrity_result)
    assert coordinator._integrity_retry_attempts == 1
    assert not coordinator._automatic_verification_due(record, now=now)
    assert coordinator._automatic_verification_due(
        record,
        now=now + timedelta(minutes=31),
    )

    coordinator._integrity_retry_attempts = 3
    assert not coordinator._automatic_verification_due(
        record,
        now=now + timedelta(days=1),
    )


def test_resource_limit_and_password_retry_policy() -> None:
    now = datetime.now(UTC)
    record = _record(date=now)
    coordinator = _bare_coordinator(
        _result(
            INTEGRITY_STATUS_ABORTED,
            checked_at=now - timedelta(days=1),
            error_code="download_size_limit",
        )
    )
    assert not coordinator._automatic_verification_due(record, now=now)

    coordinator.integrity_result = _result(
        INTEGRITY_STATUS_PASSWORD_REQUIRED,
        checked_at=now,
        error_code="password_required",
    )
    assert not coordinator._automatic_verification_due(record, now=now)
    coordinator._backup_password_marker = "new-password-marker"
    assert coordinator._automatic_verification_due(
        record,
        now=now,
        password_changed=True,
    )


def test_password_marker_only_changes_for_new_password() -> None:
    coordinator = _bare_coordinator(BackupIntegrityResult.not_checked())

    def manager(password: str | None) -> SimpleNamespace:
        return SimpleNamespace(
            config=SimpleNamespace(
                data=SimpleNamespace(create_backup=SimpleNamespace(password=password))
            )
        )

    assert not coordinator._update_backup_password_marker(manager("secret"))
    assert not coordinator._update_backup_password_marker(manager("secret"))
    assert coordinator._update_backup_password_marker(manager("different"))


def test_faulty_foreign_objects_are_isolated_and_counted() -> None:
    class BadText:
        def __str__(self) -> str:
            raise RuntimeError("broken string")

    class BadBackup:
        @property
        def backup_id(self) -> str:
            raise RuntimeError("broken property")

    valid = SimpleNamespace(
        backup_id="valid-id",
        name=BadText(),
        date=datetime.now(UTC),
        agents={
            "backup.local": SimpleNamespace(size=100_000_000, protected=False),
            "backup.remote": SimpleNamespace(size=102_000_001, protected=False),
            BadText(): SimpleNamespace(size=1, protected=False),
        },
        failed_agent_ids=(),
        failed_addons=(),
        failed_folders=(),
        with_automatic_settings=True,
        extra_metadata={},
        addons=(),
        folders=(),
        database_included=True,
        homeassistant_included=True,
    )
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.config_entry = SimpleNamespace(entry_id="entry")

    records = coordinator._normalize_backups({"good": valid, "bad": BadBackup()})

    assert len(records) == 1
    assert records[0].name == ""
    assert records[0].copy_size_mismatch
    assert records[0].copy_size_spread_bytes == 2_000_001
    assert coordinator._invalid_backup_count == 1
    assert coordinator._invalid_agent_copy_count == 1
    assert safe_log_value(BadText()).startswith("<unprintable:")


def test_manager_error_snapshot_advances_storage_ages() -> None:
    now = datetime.now(UTC)
    old_record = _record(date=now - timedelta(days=3))
    summary = BackupAgentSummary(
        agent_id="backup.local",
        agent_reference="storage-ref",
        storage_name="Local",
        backup_count=1,
        inventory_backup_count=1,
        ignored_update_backup_count=0,
        latest_backup=old_record.date,
        latest_backup_age_days=0.0,
        latest_backup_size=old_record.size,
        stored_bytes=old_record.size,
        error=None,
        stale=False,
        problem=False,
    )
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.data = _data(
        now=now - timedelta(days=3), record=old_record, summary=summary
    )
    coordinator.max_age_days = 2

    snapshot = coordinator._manager_error_snapshot("manager_error")

    assert snapshot.backup_stale
    assert snapshot.automatic_backup_overdue
    assert not snapshot.required_location_missing
    assert snapshot.agent_summaries[0].stale
    assert snapshot.agent_summaries[0].problem
    assert (
        snapshot.last_inventory_success_at == coordinator.data.last_inventory_success_at
    )


class _Services:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def async_call(
        self, _domain: str, _service: str, _data: Any, **kwargs: Any
    ) -> None:
        self.calls.append(kwargs["target"])


class _Hass:
    def __init__(self) -> None:
        self.config = SimpleNamespace(language="en")
        self.services = _Services()


async def _empty_translations(*_args: Any, **_kwargs: Any) -> dict[str, str]:
    return {}


def test_notification_target_changes_only_notify_added_devices(monkeypatch) -> None:
    hass = _Hass()
    manager = BackupCheckupNotificationManager(hass, "entry")
    data = SimpleNamespace(
        active_problems=("backup_stale",),
        status="backup_stale",
        recommendation="create_backup",
        problem_count=1,
    )
    monkeypatch.setattr(notifications, "async_get_translations", _empty_translations)

    asyncio.run(
        manager.async_process(
            data,
            enabled=True,
            targets=("notify.phone",),
            notify_on_recovery=True,
        )
    )
    asyncio.run(
        manager.async_process(
            data,
            enabled=True,
            targets=("notify.phone", "notify.tablet"),
            notify_on_recovery=True,
        )
    )
    asyncio.run(
        manager.async_process(
            data,
            enabled=True,
            targets=("notify.tablet",),
            notify_on_recovery=True,
        )
    )

    assert hass.services.calls == [
        {"entity_id": ["notify.phone"]},
        {"entity_id": ["notify.tablet"]},
    ]


def test_invalid_notification_store_is_repaired_immediately(monkeypatch) -> None:
    hass = _Hass()
    manager = BackupCheckupNotificationManager(hass, "entry")
    manager._store.data = {
        "last_signature": 123,
        "was_enabled": "yes",
        "last_targets": ["notify.phone", "bad", "notify.phone"],
    }
    issues: list[bool] = []
    monkeypatch.setattr(
        notifications,
        "async_set_storage_data_issue",
        lambda _hass, *, store_name, active: issues.append(active),
    )

    asyncio.run(manager._async_load())

    assert manager._store.data == {
        "last_signature": "",
        "was_enabled": False,
        "last_targets": ["notify.phone"],
    }
    assert issues[-1] is False


def test_required_location_missing_has_repair_issue(monkeypatch) -> None:
    now = datetime.now(UTC)
    record = _record(date=now)
    summary = BackupAgentSummary(
        agent_id="backup.local",
        agent_reference="storage-ref",
        storage_name="Local",
        backup_count=1,
        inventory_backup_count=1,
        ignored_update_backup_count=0,
        latest_backup=record.date,
        latest_backup_age_days=0.0,
        latest_backup_size=record.size,
        stored_bytes=record.size,
        error="io_error",
        stale=False,
        problem=True,
    )
    data = _data(now=now, record=record, summary=summary)
    data = data.__class__(
        **{
            **{field.name: getattr(data, field.name) for field in fields(data)},
            "required_location_missing": True,
        }
    )
    created: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(
        repairs.ir,
        "async_create_issue",
        lambda _hass, _domain, issue_id, **kwargs: created.append(
            (issue_id, kwargs.get("translation_placeholders", {}))
        ),
    )
    monkeypatch.setattr(
        repairs.ir, "async_delete_issue", lambda *_args, **_kwargs: None
    )

    repairs.async_update_issues(SimpleNamespace(), data)

    assert ("required_location_missing", {"count": "1"}) in created


def test_diagnostics_normalizes_legacy_single_notification_target(monkeypatch) -> None:
    data = _data()
    coordinator = SimpleNamespace(
        data=data,
        notifications_enabled=True,
        notification_targets=("notify.phone",),
        notify_on_recovery=True,
        notification_manager=SimpleNamespace(last_error=None),
        last_update_success=True,
        last_exception=None,
        update_interval=timedelta(minutes=5),
    )
    entry = SimpleNamespace(
        runtime_data=coordinator,
        data={"notification_targets": "notify.phone"},
        options={},
        entry_id="entry",
        version=9,
        title="BackupCheckup",
    )
    registry = SimpleNamespace(entities={})
    monkeypatch.setattr(diagnostics.er, "async_get", lambda _hass: registry)

    result = asyncio.run(
        diagnostics.async_get_config_entry_diagnostics(SimpleNamespace(), entry)
    )

    assert result["configuration"]["notification_target_count"] == 1
    assert result["coordinator"]["last_inventory_success_at"] is not None


def test_native_datetime_and_enum_helpers_are_defensive() -> None:
    naive = datetime(2026, 1, 2, 3, 4, 5)
    assert _as_datetime(naive) == naive.replace(tzinfo=UTC)

    class BadEnum:
        @property
        def value(self) -> str:
            raise RuntimeError("broken enum")

    assert _enum_value(BadEnum()) == ""
