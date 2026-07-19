"""Functional tests for config flows and all entity platforms."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import (
    binary_sensor,
    button,
    config_flow,
    flow_schemas,
    sensor,
)
from custom_components.backup_checkup.const import (
    CONF_ADAPTIVE_POLLING,
    CONF_ENTITY_MODE,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MONITORING_POLICY,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_RUNTIME_PROFILE,
    CONF_SIZE_CHECK_MODE,
    CONF_VERIFICATION_POLICY,
    ENTITY_MODE_EXPERT,
    MONITORING_POLICY_BALANCED,
    MONITORING_POLICY_CUSTOM,
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_CUSTOM,
    RUNTIME_PROFILE_PERFORMANCE,
    SIZE_CHECK_FIXED,
    VERIFICATION_POLICY_MANUAL,
)
from custom_components.backup_checkup.hardware_profile import HardwareSnapshot
from custom_components.backup_checkup.models import BackupAgentSummary


def _hardware() -> HardwareSnapshot:
    return HardwareSnapshot(
        installation_type="Home Assistant OS",
        architecture="aarch64",
        board="green",
        recommended_profile=RUNTIME_PROFILE_APPLIANCE,
        confidence="high",
        detection="automatic",
    )


def _runtime_input(profile: str = RUNTIME_PROFILE_APPLIANCE) -> dict[str, Any]:
    return {
        CONF_RUNTIME_PROFILE: profile,
        CONF_ADAPTIVE_POLLING: True,
    }


def _presentation_input() -> dict[str, Any]:
    return {
        CONF_ENTITY_MODE: ENTITY_MODE_EXPERT,
        CONF_EXPOSE_BACKUP_METADATA: False,
        CONF_NOTIFICATIONS_ENABLED: False,
        CONF_NOTIFICATION_TARGETS: [],
        CONF_NOTIFY_ON_RECOVERY: True,
    }


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
async def test_guided_config_flow_and_custom_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_args: [])
    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()

    form = await flow.async_step_user()
    assert form["step_id"] == "user"
    assert form["description_placeholders"]["board"] == "green"

    assert (await flow.async_step_user(_runtime_input()))["step_id"] == "monitoring"
    assert (
        await flow.async_step_monitoring(
            {CONF_MONITORING_POLICY: MONITORING_POLICY_BALANCED}
        )
    )["step_id"] == "verification"
    assert (
        await flow.async_step_verification(
            {CONF_VERIFICATION_POLICY: VERIFICATION_POLICY_MANUAL}
        )
    )["step_id"] == "presentation"

    invalid = _presentation_input()
    invalid[CONF_NOTIFICATIONS_ENABLED] = True
    invalid_result = await flow.async_step_presentation(invalid)
    assert invalid_result["errors"] == {
        CONF_NOTIFICATION_TARGETS: "notification_target_required"
    }

    assert (await flow.async_step_presentation(_presentation_input()))[
        "step_id"
    ] == "summary"
    created = await flow.async_step_summary({})
    assert created["type"] == "create_entry"
    assert created["data"][CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_APPLIANCE
    assert created["data"][CONF_MONITORING_POLICY] == MONITORING_POLICY_BALANCED
    assert created["data"][CONF_VERIFICATION_POLICY] == VERIFICATION_POLICY_MANUAL

    custom = config_flow.BackupCheckupConfigFlow()
    custom.hass = SimpleNamespace()
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    assert (await custom.async_step_user(_runtime_input(RUNTIME_PROFILE_CUSTOM)))[
        "step_id"
    ] == "runtime_custom"
    bad_runtime = dict(custom._draft)
    bad_runtime["active_update_interval_minutes"] = 10
    bad_runtime["update_interval_minutes"] = 5
    assert (await custom.async_step_runtime_custom(bad_runtime))["errors"] == {
        "base": "active_interval_too_slow"
    }

    good_runtime = dict(custom._draft)
    assert (await custom.async_step_runtime_custom(good_runtime))[
        "step_id"
    ] == "monitoring"
    assert (
        await custom.async_step_monitoring(
            {CONF_MONITORING_POLICY: MONITORING_POLICY_CUSTOM}
        )
    )["step_id"] == "monitoring_custom"
    bad_monitoring = dict(custom._draft)
    bad_monitoring[CONF_SIZE_CHECK_MODE] = SIZE_CHECK_FIXED
    bad_monitoring[CONF_MINIMUM_BACKUP_SIZE_MB] = 0
    assert (await custom.async_step_monitoring_custom(bad_monitoring))["errors"] == {
        "base": "fixed_size_required"
    }

    duplicate = config_flow.BackupCheckupConfigFlow()
    duplicate._async_current_entries = lambda: [object()]
    assert (await duplicate.async_step_user())["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_options_flow_menu_categories_and_setup_assistant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_args: [])
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    options = config_flow.BackupCheckupOptionsFlow()
    options.hass = SimpleNamespace()
    options.config_entry = ConfigEntry(data={}, options={})

    menu = await options.async_step_init()
    assert menu["type"] == "menu"
    assert "setup_assistant" in menu["menu_options"]

    runtime = await options.async_step_runtime(
        {CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_PERFORMANCE, CONF_ADAPTIVE_POLLING: True}
    )
    assert runtime["type"] == "create_entry"
    assert runtime["data"][CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_PERFORMANCE

    assistant = config_flow.BackupCheckupOptionsFlow()
    assistant.hass = SimpleNamespace()
    assistant.config_entry = ConfigEntry(data={}, options={})
    assert (await assistant.async_step_setup_assistant())[
        "step_id"
    ] == "setup_assistant"
    assert (await assistant.async_step_setup_assistant(_runtime_input()))[
        "step_id"
    ] == "setup_monitoring"
    assert (
        await assistant.async_step_setup_monitoring(
            {CONF_MONITORING_POLICY: MONITORING_POLICY_BALANCED}
        )
    )["step_id"] == "setup_verification"
    assert (
        await assistant.async_step_setup_verification(
            {CONF_VERIFICATION_POLICY: VERIFICATION_POLICY_MANUAL}
        )
    )["step_id"] == "setup_presentation"
    assert (await assistant.async_step_setup_presentation(_presentation_input()))[
        "step_id"
    ] == "setup_summary"
    saved = await assistant.async_step_setup_summary({})
    assert saved["type"] == "create_entry"

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
