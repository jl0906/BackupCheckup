"""Functional entry coverage and beta1 regressions."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, UnitOfInformation

from custom_components.backup_checkup import diagnostics, models, repairs, sensor
from custom_components.backup_checkup.configuration import BackupCheckupSettings
from custom_components.backup_checkup.coordinator import BackupCheckupCoordinator
from custom_components.backup_checkup.integrity import (
    BackupIntegrityStore,
    IntegrityStoreState,
    _DatabaseCheckControl,
)
from custom_components.backup_checkup.models import BackupIntegrityResult
from custom_components.backup_checkup.notifications import (
    BackupCheckupNotificationManager,
)
from custom_components.backup_checkup.security import VerificationBudget


class _Services:
    def __init__(self) -> None:
        self.async_call = AsyncMock()


class _Hass:
    def __init__(self) -> None:
        self.config = SimpleNamespace(language="en")
        self.services = _Services()


class _BlockingStore:
    def __init__(self, data: Any) -> None:
        self.data = data
        self.loads = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_load(self) -> Any:
        self.loads += 1
        self.started.set()
        await self.release.wait()
        return self.data

    async def async_save(self, data: Any) -> None:
        self.data = data


class _Registry:
    def __init__(self) -> None:
        self.entries: dict[str, Any] = {}
        self.unique_ids: dict[str, str] = {}
        self.translation_updates: list[tuple[str, str]] = []
        self.option_updates: list[tuple[str, str, dict[str, Any]]] = []

    def async_get_entity_id(
        self, platform: str, domain: str, unique_id: str
    ) -> str | None:
        del platform, domain
        return self.unique_ids.get(unique_id)

    def async_get(self, entity_id: str) -> Any:
        return self.entries.get(entity_id)

    def async_update_entity(self, entity_id: str, *, translation_key: str) -> None:
        self.translation_updates.append((entity_id, translation_key))

    def async_update_entity_options(
        self, entity_id: str, domain: str, options: dict[str, Any]
    ) -> None:
        self.option_updates.append((entity_id, domain, options))


def _notification_data(*problems: str) -> SimpleNamespace:
    return SimpleNamespace(
        active_problems=problems,
        status="problem" if problems else "ok",
        recommendation="check_backups" if problems else "none",
        problem_count=len(problems),
    )


def test_settings_as_dict_round_trip_is_canonical() -> None:
    settings = BackupCheckupSettings.from_sources(
        {"notification_targets": "notify.mobile_app_phone"}
    )

    serialized = settings.as_dict()

    assert serialized["notification_targets"] == ["notify.mobile_app_phone"]
    assert BackupCheckupSettings.from_sources(serialized) == settings


@pytest.mark.asyncio
async def test_integrity_store_runtime_update_and_single_concurrent_load() -> None:
    expected = BackupIntegrityResult.not_checked()
    backing = _BlockingStore(
        {
            "result": expected.as_dict(),
            "retry": {
                "backup_id": None,
                "error_key": None,
                "attempts": 0,
                "not_before": None,
            },
            "password_marker": None,
            "last_manual_verification_at": None,
        }
    )
    store = BackupIntegrityStore(object(), "entry")
    store._store = backing

    first = asyncio.create_task(store.async_load_state())
    await backing.started.wait()
    second = asyncio.create_task(store.async_load_state())
    await asyncio.sleep(0)
    backing.release.set()

    first_state, second_state = await asyncio.gather(first, second)
    assert first_state is second_state
    assert backing.loads == 1

    retry_at = datetime.now(UTC) + timedelta(minutes=5)
    manual_at = datetime.now(UTC)
    await store.async_update_runtime(
        password_marker="marker",
        retry_key=("backup", "read_failed"),
        retry_attempts=-2,
        retry_not_before=retry_at,
        last_manual_verification_at=manual_at,
    )

    assert store._state == IntegrityStoreState(
        result=expected,
        retry_backup_id="backup",
        retry_error_key="read_failed",
        retry_attempts=0,
        retry_not_before=retry_at,
        password_marker="marker",
        last_manual_verification_at=manual_at,
    )


def test_database_progress_handler_covers_running_cancelled_and_timeout() -> None:
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=1,
        max_expanded_bytes=1,
    )
    running = _DatabaseCheckControl(budget, time.monotonic() + 60)
    assert running.progress_handler() == 0

    budget.cancel()
    assert running.progress_handler() == 1
    assert running.cancelled

    timeout_budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=1,
        max_expanded_bytes=1,
    )
    timed_out = _DatabaseCheckControl(timeout_budget, time.monotonic() - 1)
    assert timed_out.progress_handler() == 1
    assert timed_out.timed_out


@pytest.mark.asyncio
async def test_coordinator_persists_complete_integrity_runtime_state() -> None:
    coordinator = object.__new__(BackupCheckupCoordinator)
    save = AsyncMock()
    coordinator.integrity_verifier = SimpleNamespace(
        store=SimpleNamespace(async_save=save)
    )
    coordinator._integrity_retry_key = ("backup", "error")
    coordinator._integrity_retry_attempts = 2
    coordinator._integrity_retry_not_before = datetime.now(UTC)
    coordinator._backup_password_marker = "marker"
    coordinator._last_manual_verification_at = datetime.now(UTC)
    result = BackupIntegrityResult.not_checked()

    await coordinator._async_save_integrity_result(result)

    save.assert_awaited_once_with(
        result,
        retry_key=coordinator._integrity_retry_key,
        retry_attempts=2,
        retry_not_before=coordinator._integrity_retry_not_before,
        password_marker="marker",
        last_manual_verification_at=coordinator._last_manual_verification_at,
    )


@pytest.mark.asyncio
async def test_healthy_notification_enable_and_target_change_never_send_problem() -> (
    None
):
    hass = _Hass()
    manager = BackupCheckupNotificationManager(hass, "entry")

    await manager.async_process(
        _notification_data(),
        enabled=True,
        targets=("notify.phone",),
        notify_on_recovery=True,
    )
    await manager.async_process(
        _notification_data(),
        enabled=True,
        targets=("notify.phone", "notify.tablet"),
        notify_on_recovery=True,
    )

    hass.services.async_call.assert_not_awaited()
    assert manager._last_signature == ""
    assert manager._last_targets == ("notify.phone", "notify.tablet")


@pytest.mark.asyncio
async def test_notification_recovery_and_remove_paths(monkeypatch) -> None:
    async def _empty_translations(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        return {}

    from custom_components.backup_checkup import notifications

    monkeypatch.setattr(notifications, "async_get_translations", _empty_translations)
    hass = _Hass()
    manager = BackupCheckupNotificationManager(hass, "entry")

    await manager.async_process(
        _notification_data("backup_stale"),
        enabled=True,
        targets=("notify.phone",),
        notify_on_recovery=True,
    )
    await manager.async_process(
        _notification_data(),
        enabled=True,
        targets=("notify.phone",),
        notify_on_recovery=True,
    )
    await manager.async_remove()

    calls = hass.services.async_call.await_args_list
    assert len(calls) == 2
    assert "Problem detected" in calls[0].args[2]["title"]
    assert "Backups healthy" in calls[1].args[2]["title"]
    assert manager._store.data is None


def test_repair_cleanup_helpers_create_and_remove_every_issue(monkeypatch) -> None:
    created: list[str] = []
    removed: list[str] = []
    monkeypatch.setattr(
        repairs.ir,
        "async_create_issue",
        lambda _hass, _domain, issue_id, **_kwargs: created.append(issue_id),
    )
    monkeypatch.setattr(
        repairs.ir,
        "async_delete_issue",
        lambda _hass, _domain, issue_id: removed.append(issue_id),
    )

    repairs.async_set_temporary_cleanup_issue(object(), active=True)
    repairs.async_set_temporary_cleanup_issue(object(), active=False)
    repairs.async_remove_issues(object())

    assert created == ["temporary_cleanup_failed"]
    assert "temporary_cleanup_failed" in removed
    assert set(repairs.REPAIR_ISSUE_IDS).issubset(removed)


def test_storage_name_helpers_return_deduplicated_friendly_names() -> None:
    summaries = (
        SimpleNamespace(agent_id="agent-b", storage_name="Remote"),
        SimpleNamespace(agent_id="agent-a", storage_name="Local"),
        SimpleNamespace(agent_id="agent-c", storage_name="Local"),
    )
    record = SimpleNamespace(agents=("agent-b", "agent-a", "agent-c", "missing"))
    data = SimpleNamespace(
        agent_summaries=summaries,
        latest_monitored_backup_record=record,
    )

    assert sensor._storage_name(data, None) is None
    assert sensor._storage_name(data, "agent-a") == "Local"
    assert sensor._storage_name(data, "missing") is None
    assert sensor._latest_storage_names(data) == ["Local", "Remote"]
    assert (
        sensor._latest_storage_names(
            SimpleNamespace(latest_monitored_backup_record=None)
        )
        == []
    )


@pytest.mark.asyncio
async def test_unexpected_notification_service_failure_remains_nonfatal() -> None:
    hass = _Hass()
    hass.services.async_call.side_effect = RuntimeError("unexpected")
    manager = BackupCheckupNotificationManager(hass, "entry")

    sent = await manager.async_send_test(("notify.phone",))

    assert sent is False
    assert manager.last_error == "unknown_error"


def test_diagnostics_activity_and_integrity_privacy_paths() -> None:
    activity = SimpleNamespace(diagnostics=lambda *, limit: {"limit": limit})
    assert diagnostics._activity_diagnostics(SimpleNamespace(activity=activity)) == {
        "limit": 100
    }

    integrity = SimpleNamespace(
        agent_id="backup.remote",
        sha256="a" * 64,
        status="valid",
        checked_at=None,
        backup_date=None,
        backup_reference="reference",
        verified_size=1,
        duration_seconds=1.0,
        archive_count=1,
        file_count=1,
        protected=False,
        database_status="not_checked",
        warnings=(),
        error_code=None,
        checksum_changed=False,
    )
    result = diagnostics._integrity_diagnostics(
        ConfigEntry(entry_id="entry"),
        SimpleNamespace(
            integrity=integrity,
            expose_backup_metadata=False,
            integrity_check_running=False,
        ),
    )
    assert result["storage_location"] != "backup.remote"
    assert result["sha256"] == "a" * 16


def test_naive_stored_datetime_is_normalized_to_utc() -> None:
    parsed = models._parse_stored_datetime("2026-07-18T12:00:00")
    assert parsed is not None
    assert parsed.tzinfo is UTC


def test_entity_registry_diagnostics_counts_enabled_and_disabled(monkeypatch) -> None:
    registry = SimpleNamespace(
        entities={
            "sensor.enabled": SimpleNamespace(
                config_entry_id="entry",
                platform="backup_checkup",
                disabled_by=None,
                entity_id="sensor.enabled",
            ),
            "sensor.disabled": SimpleNamespace(
                config_entry_id="entry",
                platform="backup_checkup",
                disabled_by=SimpleNamespace(value="integration"),
                entity_id="sensor.disabled",
            ),
            "sensor.other": SimpleNamespace(
                config_entry_id="other",
                platform="backup_checkup",
                disabled_by=None,
                entity_id="sensor.other",
            ),
        }
    )
    monkeypatch.setattr(diagnostics.er, "async_get", lambda _hass: registry)

    result = diagnostics._entity_registry_diagnostics(
        object(), ConfigEntry(entry_id="entry"), expose_metadata=True
    )

    assert result == {
        "total": 2,
        "enabled": 1,
        "disabled_by": {"integration": 1},
        "disabled_entities": [
            {"entity_id": "sensor.disabled", "disabled_by": "integration"}
        ],
    }


def test_sensor_registry_migrations_repair_metadata(monkeypatch) -> None:
    registry = _Registry()
    entry = ConfigEntry(entry_id="entry")
    enum_entity_id = "sensor.backup_checkup_status"
    registry.unique_ids["entry_status"] = enum_entity_id
    registry.entries[enum_entity_id] = SimpleNamespace(translation_key=None)

    size_entry = SimpleNamespace(
        entity_id="sensor.backup_size",
        unique_id="entry_latest_backup_size",
        options={"sensor": {CONF_UNIT_OF_MEASUREMENT: UnitOfInformation.BYTES}},
    )
    already_mb = SimpleNamespace(
        entity_id="sensor.stored_bytes",
        unique_id="entry_stored_bytes",
        options={"sensor": {CONF_UNIT_OF_MEASUREMENT: UnitOfInformation.MEGABYTES}},
    )
    unrelated = SimpleNamespace(
        entity_id="sensor.status",
        unique_id="entry_status",
        options={},
    )

    monkeypatch.setattr(sensor.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        sensor.er,
        "async_entries_for_config_entry",
        lambda _registry, _entry_id: [size_entry, already_mb, unrelated],
        raising=False,
    )

    sensor._migrate_enum_translation_keys(object(), entry)
    sensor._migrate_size_sensor_units(object(), entry)

    assert registry.translation_updates == [(enum_entity_id, "status")]
    assert registry.option_updates == [
        (
            "sensor.backup_size",
            "sensor",
            {CONF_UNIT_OF_MEASUREMENT: UnitOfInformation.MEGABYTES},
        )
    ]
