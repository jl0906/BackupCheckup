"""Functional tests for config flows and all entity platforms."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import binary_sensor, button, config_flow, sensor
from custom_components.backup_checkup.const import (
    CONF_ENTITY_MODE,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MONITORING_PROFILE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_SIZE_CHECK_MODE,
    ENTITY_MODE_EXPERT,
    PROFILE_CUSTOM,
    PROFILE_STANDARD,
    SIZE_CHECK_FIXED,
)
from custom_components.backup_checkup.models import BackupAgentSummary


def _profile_input(profile: str = PROFILE_STANDARD) -> dict[str, Any]:
    return {
        CONF_MONITORING_PROFILE: profile,
        CONF_ENTITY_MODE: ENTITY_MODE_EXPERT,
        CONF_NOTIFICATIONS_ENABLED: False,
        CONF_NOTIFICATION_TARGETS: [],
        CONF_NOTIFY_ON_RECOVERY: True,
    }


def _advanced_input() -> dict[str, Any]:
    return config_flow._monitoring_defaults()


def _summary(agent_id: str = "backup.local") -> BackupAgentSummary:
    now = datetime.now(UTC)
    return BackupAgentSummary(
        agent_id=agent_id,
        agent_reference=f"ref-{agent_id}",
        storage_name=f"Storage {agent_id}",
        backup_count=2,
        inventory_backup_count=3,
        ignored_update_backup_count=1,
        latest_backup=now,
        latest_backup_age_days=0.5,
        latest_backup_size=2_500_000,
        stored_bytes=7_500_000,
        error=None,
        stale=False,
        problem=False,
    )


class _Services:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def async_call(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((*args, kwargs))


class _Coordinator:
    def __init__(self, summaries: tuple[BackupAgentSummary, ...] = ()) -> None:
        self.hass = SimpleNamespace(services=_Services())
        self.last_update_success = True
        self.entity_mode = ENTITY_MODE_EXPERT
        self.expose_backup_metadata = False
        self.integrity_check_pending_or_running = False
        self.manual_verification_cooldown_active = False
        self.notifications_enabled = True
        self.notification_targets = ("notify.mobile_app_phone",)
        self.data = SimpleNamespace(
            agent_summaries=summaries,
            status="ok",
            manager_state="idle",
            storage_error=False,
            monitored_backups=(object(),),
        )
        self.listener: Any = None

    def async_add_listener(self, listener: Any) -> Any:
        self.listener = listener
        return listener


class _Hass:
    def __init__(self) -> None:
        self.tasks: list[asyncio.Task[Any]] = []

    def async_create_task(self, coroutine: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


@pytest.mark.asyncio
async def test_config_flow_profile_validation_and_custom_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_flow, "mobile_notification_options", lambda *_args: [])
    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()

    form = await flow.async_step_user()
    assert form["type"] == "form"
    assert form["step_id"] == "user"

    invalid = _profile_input()
    invalid[CONF_NOTIFICATIONS_ENABLED] = True
    invalid_result = await flow.async_step_user(invalid)
    assert invalid_result["errors"] == {
        CONF_NOTIFICATION_TARGETS: "notification_target_required"
    }

    created = await flow.async_step_user(_profile_input())
    assert created["type"] == "create_entry"
    assert created["data"][CONF_MONITORING_PROFILE] == PROFILE_STANDARD

    custom = config_flow.BackupCheckupConfigFlow()
    custom.hass = SimpleNamespace()
    custom_form = await custom.async_step_user(_profile_input(PROFILE_CUSTOM))
    assert custom_form["step_id"] == "advanced"

    bad_advanced = _advanced_input()
    bad_advanced[CONF_SIZE_CHECK_MODE] = SIZE_CHECK_FIXED
    bad_advanced[CONF_MINIMUM_BACKUP_SIZE_MB] = 0
    bad_result = await custom.async_step_advanced(bad_advanced)
    assert bad_result["errors"] == {"base": "fixed_size_required"}

    good_result = await custom.async_step_advanced(_advanced_input())
    assert good_result["type"] == "create_entry"
    assert good_result["data"][CONF_MONITORING_PROFILE] == PROFILE_CUSTOM

    duplicate = config_flow.BackupCheckupConfigFlow()
    duplicate._async_current_entries = lambda: [object()]
    assert (await duplicate.async_step_user())["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_options_flow_applies_changed_entity_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[str] = []
    monkeypatch.setattr(config_flow, "mobile_notification_options", lambda *_args: [])
    monkeypatch.setattr(
        config_flow,
        "async_apply_entity_mode",
        lambda _hass, _entry, mode: applied.append(mode),
    )
    options = config_flow.BackupCheckupOptionsFlow()
    options.hass = SimpleNamespace()
    options.config_entry = ConfigEntry(data={}, options={})

    shown = await options.async_step_init()
    assert shown["step_id"] == "init"

    created = await options.async_step_init(_profile_input())
    assert created["type"] == "create_entry"
    assert applied == [ENTITY_MODE_EXPERT]

    custom = config_flow.BackupCheckupOptionsFlow()
    custom.hass = SimpleNamespace()
    custom.config_entry = ConfigEntry(data={}, options={})
    advanced_form = await custom.async_step_init(_profile_input(PROFILE_CUSTOM))
    assert advanced_form["step_id"] == "advanced"
    advanced_created = await custom.async_step_advanced(_advanced_input())
    assert advanced_created["type"] == "create_entry"

    assert isinstance(
        config_flow.BackupCheckupConfigFlow.async_get_options_flow(ConfigEntry()),
        config_flow.BackupCheckupOptionsFlow,
    )


def test_entity_values_attributes_and_availability() -> None:
    summary = _summary()
    coordinator = _Coordinator((summary,))
    entry = ConfigEntry(entry_id="entry")

    status_description = next(
        item for item in sensor.SENSORS if item.key == "backup_manager_state"
    )
    status_sensor = sensor.BackupCheckupSensor(coordinator, entry, status_description)
    assert status_sensor.native_value == "idle"
    assert status_sensor.extra_state_attributes is None
    assert status_sensor.unique_id == "entry_backup_manager_state"

    agent = sensor.BackupCheckupAgentSensor(
        coordinator, entry, summary.agent_id, "latest_backup_age"
    )
    assert agent.available is True
    assert agent.native_value == 0
    assert agent.extra_state_attributes["precise_age_hours"] == 12.0

    size = sensor.BackupCheckupAgentSensor(
        coordinator, entry, summary.agent_id, "latest_backup_size"
    )
    assert size.native_value == 2.5
    assert size.extra_state_attributes["size_bytes"] == 2_500_000

    problem_description = next(
        item for item in binary_sensor.BINARY_SENSORS if item.key == "storage_error"
    )
    problem = binary_sensor.BackupCheckupBinarySensor(
        coordinator, entry, problem_description
    )
    assert problem.is_on is False

    agent_problem = binary_sensor.BackupCheckupAgentProblemBinarySensor(
        coordinator, entry, summary.agent_id
    )
    assert agent_problem.is_on is False
    assert agent_problem.extra_state_attributes["storage_name"] == summary.storage_name

    coordinator.data.agent_summaries = ()
    assert agent.available is False
    assert agent.native_value is None
    assert agent.extra_state_attributes == {"storage_reference": agent.agent_reference}
    assert agent_problem.is_on is False


@pytest.mark.asyncio
async def test_buttons_setup_availability_and_actions() -> None:
    coordinator = _Coordinator()
    entry = ConfigEntry(entry_id="entry")
    entry.runtime_data = coordinator
    added: list[Any] = []
    await button.async_setup_entry(
        coordinator.hass,
        entry,
        lambda entities: added.extend(entities),
    )
    assert len(added) == 3

    verify = next(
        item for item in added if isinstance(item, button.BackupCheckupVerifyButton)
    )
    refresh = next(
        item for item in added if isinstance(item, button.BackupCheckupRefreshButton)
    )
    test = next(
        item
        for item in added
        if isinstance(item, button.BackupCheckupTestNotificationButton)
    )
    assert verify.available is True
    assert test.available is True
    await verify.async_press()
    await refresh.async_press()
    await test.async_press()
    assert len(coordinator.hass.services.calls) == 3

    coordinator.integrity_check_pending_or_running = True
    coordinator.notifications_enabled = False
    assert verify.available is False
    assert test.available is False


@pytest.mark.asyncio
async def test_sensor_platform_tracks_added_and_removed_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _summary("first")
    second = _summary("second")
    coordinator = _Coordinator((first,))
    entry = ConfigEntry(entry_id="entry")
    entry.runtime_data = coordinator
    hass = _Hass()
    batches: list[list[Any]] = []
    removed = AsyncMock()
    monkeypatch.setattr(sensor, "_migrate_enum_translation_keys", lambda *_args: None)
    monkeypatch.setattr(sensor, "_migrate_size_sensor_units", lambda *_args: None)
    monkeypatch.setattr(sensor, "async_remove_agent_entities", removed)

    await sensor.async_setup_entry(
        hass, entry, lambda entities: batches.append(list(entities))
    )
    assert len(batches[0]) == len(sensor.SENSORS) + len(sensor.AGENT_METRICS)

    coordinator.data.agent_summaries = (first, second)
    coordinator.listener()
    assert len(batches[-1]) == len(sensor.AGENT_METRICS)

    coordinator.data.agent_summaries = (second,)
    coordinator.listener()
    coordinator.listener()
    coordinator.listener()
    await asyncio.gather(*hass.tasks)
    removed.assert_awaited_once()


@pytest.mark.asyncio
async def test_binary_sensor_platform_tracks_added_and_removed_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _summary("first")
    second = _summary("second")
    coordinator = _Coordinator((first,))
    entry = ConfigEntry(entry_id="entry")
    entry.runtime_data = coordinator
    hass = _Hass()
    batches: list[list[Any]] = []
    removed = AsyncMock()
    monkeypatch.setattr(binary_sensor, "async_remove_agent_entities", removed)

    await binary_sensor.async_setup_entry(
        hass, entry, lambda entities: batches.append(list(entities))
    )
    assert len(batches[0]) == len(binary_sensor.BINARY_SENSORS) + 1

    coordinator.data.agent_summaries = (first, second)
    coordinator.listener()
    assert len(batches[-1]) == 1

    coordinator.data.agent_summaries = (second,)
    coordinator.listener()
    coordinator.listener()
    coordinator.listener()
    await asyncio.gather(*hass.tasks)
    removed.assert_awaited_once()
