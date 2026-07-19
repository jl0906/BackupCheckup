"""Coverage and regression tests for the 2.4 hardware-aware setup."""

from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import (
    config_flow,
    diagnostics,
    flow_schemas,
    hardware_profile,
    setup_recommendation,
)
from custom_components.backup_checkup import (
    coordinator as coordinator_module,
)
from custom_components.backup_checkup.configuration import (
    BackupCheckupSettings,
    normalize_configuration,
)
from custom_components.backup_checkup.const import (
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
    CONF_ADAPTIVE_POLLING,
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_ENTITY_MODE,
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_HARDWARE_DETECTION,
    CONF_MAX_AGE_DAYS,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MONITORING_POLICY,
    CONF_MONITORING_PROFILE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_RUNTIME_PROFILE,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_POLICY,
    CORE_AUTOMATIC_BACKUP_EVENT,
    CORE_BACKUP_MANAGER_STATE,
    ENTITY_MODE_STANDARD,
    MONITORING_POLICY_BALANCED,
    MONITORING_POLICY_CUSTOM,
    MONITORING_POLICY_STRICT,
    PROFILE_SECURE,
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_CUSTOM,
    RUNTIME_PROFILE_ENERGY_SAVING,
    RUNTIME_PROFILE_LEGACY,
    RUNTIME_PROFILE_PERFORMANCE,
    RUNTIME_PROFILE_SERVER,
    SIZE_CHECK_FIXED,
    VERIFICATION_POLICY_AUTOMATIC,
    VERIFICATION_POLICY_CUSTOM,
    VERIFICATION_POLICY_DEEP,
    VERIFICATION_POLICY_MANUAL,
)
from custom_components.backup_checkup.coordinator import BackupCheckupCoordinator
from custom_components.backup_checkup.hardware_profile import HardwareSnapshot
from custom_components.backup_checkup.native_backup import (
    native_backup_activity_entity_ids,
)
from custom_components.backup_checkup.presets import (
    monitoring_values,
    runtime_values,
    verification_values,
)


class _States:
    def get(self, _entity_id: str) -> None:
        return None


class _Hass:
    def __init__(self) -> None:
        self.states = _States()
        self.config = SimpleNamespace(language="en")
        self.services = SimpleNamespace(async_call=AsyncMock())
        self.tasks: list[asyncio.Task[Any]] = []

    def async_create_task(
        self, coroutine: Any, *, name: str | None = None
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


def _hardware(profile: str = RUNTIME_PROFILE_APPLIANCE) -> HardwareSnapshot:
    return HardwareSnapshot(
        installation_type="Home Assistant OS",
        architecture="aarch64",
        board="green",
        recommended_profile=profile,
        confidence="high",
        detection="automatic",
    )


def _presentation() -> dict[str, Any]:
    return {
        CONF_ENTITY_MODE: ENTITY_MODE_STANDARD,
        CONF_EXPOSE_BACKUP_METADATA: False,
        CONF_NOTIFICATIONS_ENABLED: False,
        CONF_NOTIFICATION_TARGETS: [],
        CONF_NOTIFY_ON_RECOVERY: True,
    }


@pytest.mark.parametrize(
    ("installation", "architecture", "board", "expected", "confidence"),
    [
        ("Home Assistant OS", "aarch64", "green", RUNTIME_PROFILE_APPLIANCE, "high"),
        (
            "Home Assistant OS",
            "aarch64",
            "rpi3-64",
            RUNTIME_PROFILE_ENERGY_SAVING,
            "high",
        ),
        ("Home Assistant OS", "aarch64", "rpi5-64", RUNTIME_PROFILE_APPLIANCE, "high"),
        ("Home Assistant OS", "x86_64", "ova", RUNTIME_PROFILE_PERFORMANCE, "medium"),
        (
            "Home Assistant Core",
            "amd64",
            "unknown",
            RUNTIME_PROFILE_PERFORMANCE,
            "medium",
        ),
        (
            "Home Assistant Core",
            "armv7",
            "unknown",
            RUNTIME_PROFILE_ENERGY_SAVING,
            "medium",
        ),
        ("Home Assistant OS", "arm64", "unknown", RUNTIME_PROFILE_APPLIANCE, "low"),
        ("Container", "mips", "unknown", RUNTIME_PROFILE_PERFORMANCE, "low"),
        ("Unknown", "mips", "unknown", RUNTIME_PROFILE_APPLIANCE, "low"),
    ],
)
def test_runtime_profile_recommendations(
    installation: str,
    architecture: str,
    board: str,
    expected: str,
    confidence: str,
) -> None:
    assert hardware_profile.recommend_runtime_profile(
        installation_type=installation,
        architecture=architecture,
        board=board,
    ) == (expected, confidence)


@pytest.mark.asyncio
async def test_hardware_detection_success_fallback_and_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        hardware_profile,
        "async_get_system_info",
        AsyncMock(
            return_value={
                "installation_type": "  Home   Assistant OS ",
                "container_arch": "aarch64",
                "board": "green" + "x" * 100,
            }
        ),
    )
    detected = await hardware_profile.async_detect_hardware(SimpleNamespace())
    assert detected.installation_type == "Home Assistant OS"
    assert detected.architecture == "aarch64"
    assert len(detected.board) == 80
    assert detected.as_dict()["detection"] == "automatic"
    assert detected.display_name == detected.board

    monkeypatch.setattr(
        hardware_profile,
        "async_get_system_info",
        AsyncMock(side_effect=RuntimeError("private detail")),
    )
    fallback = await hardware_profile.async_detect_hardware(SimpleNamespace())
    assert fallback.display_name == "unknown"
    assert fallback.detection == "fallback:RuntimeError"
    assert hardware_profile._clean(None) == "unknown"
    assert hardware_profile._clean("  ") == "unknown"


@pytest.mark.asyncio
async def test_inventory_size_recommendation_is_bounded_and_best_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup = SimpleNamespace(
        backup_id="largest",
        date=datetime.now(UTC),
        size=80_000_000_000,
        agents={},
    )
    manager = SimpleNamespace(
        async_get_backups=AsyncMock(return_value=({"largest": backup}, {}))
    )
    monkeypatch.setattr(
        setup_recommendation, "async_get_manager", lambda _hass: manager
    )
    assert (
        await setup_recommendation.async_recommended_verification_size_gb(
            SimpleNamespace()
        )
        == 100
    )

    manager.async_get_backups = AsyncMock(return_value=({}, {}))
    assert (
        await setup_recommendation.async_recommended_verification_size_gb(
            SimpleNamespace()
        )
        is None
    )
    manager.async_get_backups = AsyncMock(return_value=([], {}))
    assert (
        await setup_recommendation.async_recommended_verification_size_gb(
            SimpleNamespace()
        )
        is None
    )
    manager.async_get_backups = AsyncMock(side_effect=RuntimeError("unavailable"))
    assert (
        await setup_recommendation.async_recommended_verification_size_gb(
            SimpleNamespace()
        )
        is None
    )


def test_presets_and_legacy_normalization_preserve_existing_values() -> None:
    assert runtime_values(RUNTIME_PROFILE_SERVER)[CONF_UPDATE_INTERVAL_MINUTES] == 2
    assert runtime_values("missing") == {}
    assert monitoring_values(MONITORING_POLICY_STRICT)[CONF_MAX_AGE_DAYS] == 2
    assert monitoring_values("missing") == {}
    assert verification_values(VERIFICATION_POLICY_AUTOMATIC) == {
        CONF_AUTO_VERIFY_NEW_BACKUPS: True,
        CONF_DATABASE_INTEGRITY_CHECK: False,
    }
    assert verification_values("missing") == {}

    custom_verification = normalize_configuration(
        {
            CONF_AUTO_VERIFY_NEW_BACKUPS: False,
            CONF_DATABASE_INTEGRITY_CHECK: True,
        }
    )
    assert custom_verification[CONF_VERIFICATION_POLICY] == VERIFICATION_POLICY_CUSTOM
    custom_schema = flow_schemas.verification_policy_schema(custom_verification)
    selector = next(iter(custom_schema.schema.values()))
    assert VERIFICATION_POLICY_CUSTOM in selector.config.options

    migrated = normalize_configuration(
        {
            CONF_MONITORING_PROFILE: PROFILE_SECURE,
            CONF_UPDATE_INTERVAL_MINUTES: 7,
            CONF_MAX_AGE_DAYS: 9,
            CONF_AUTO_VERIFY_NEW_BACKUPS: True,
            CONF_DATABASE_INTEGRITY_CHECK: True,
            CONF_HARDWARE_DETECTION: {"board": "x" * 100, "ignored": "secret"},
        }
    )
    assert migrated[CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_LEGACY
    assert migrated[CONF_ADAPTIVE_POLLING] is False
    assert migrated[CONF_UPDATE_INTERVAL_MINUTES] == 7
    assert migrated[CONF_MAX_AGE_DAYS] == 9
    assert migrated[CONF_MONITORING_POLICY] == MONITORING_POLICY_STRICT
    assert migrated[CONF_VERIFICATION_POLICY] == VERIFICATION_POLICY_DEEP
    assert migrated[CONF_HARDWARE_DETECTION] == {"board": "x" * 80}

    settings = BackupCheckupSettings.from_sources(migrated)
    assert settings.as_dict() == migrated
    assert settings.runtime_profile == RUNTIME_PROFILE_LEGACY
    assert settings.monitoring_policy == MONITORING_POLICY_STRICT
    assert settings.verification_policy == VERIFICATION_POLICY_DEEP


@pytest.mark.asyncio
async def test_all_config_flow_validation_and_confirmation_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    monkeypatch.setattr(
        config_flow,
        "async_recommended_verification_size_gb",
        AsyncMock(return_value=80),
    )
    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_args: [])

    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()
    await flow.async_step_user()
    assert flow._draft[CONF_MAX_VERIFICATION_SIZE_GB] == 80
    assert flow._draft[CONF_MAX_EXPANDED_SIZE_GB] == 400
    await flow.async_step_user(
        {
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_ENERGY_SAVING,
            CONF_ADAPTIVE_POLLING: True,
        }
    )
    assert flow._draft[CONF_MAX_VERIFICATION_SIZE_GB] == 80
    assert flow._draft[CONF_MAX_EXPANDED_SIZE_GB] == 400
    flow._apply_runtime_profile(RUNTIME_PROFILE_CUSTOM, True)
    await flow.async_step_runtime_custom()
    invalid_runtime = dict(flow._draft)
    invalid_runtime[CONF_UPDATE_INTERVAL_MINUTES] = 10
    invalid_runtime[CONF_ACTIVE_UPDATE_INTERVAL_MINUTES] = 1
    invalid_runtime[CONF_ERROR_BACKOFF_INTERVAL_MINUTES] = 5
    assert (await flow.async_step_runtime_custom(invalid_runtime))["errors"] == {
        "base": "backoff_interval_too_fast"
    }
    valid_runtime = dict(flow._draft)
    assert (await flow.async_step_runtime_custom(valid_runtime))[
        "step_id"
    ] == "monitoring"
    await flow.async_step_monitoring({CONF_MONITORING_POLICY: MONITORING_POLICY_CUSTOM})
    custom_monitoring = dict(flow._draft)
    custom_monitoring[CONF_SIZE_CHECK_MODE] = "automatic"
    custom_monitoring[CONF_MINIMUM_BACKUP_SIZE_MB] = 0
    assert (await flow.async_step_monitoring_custom(custom_monitoring))[
        "step_id"
    ] == "verification"
    await flow.async_step_verification(
        {CONF_VERIFICATION_POLICY: VERIFICATION_POLICY_AUTOMATIC}
    )
    await flow.async_step_presentation(_presentation())
    created = await flow.async_step_summary({})
    assert created["type"] == "create_entry"


@pytest.mark.asyncio
async def test_every_options_flow_category_and_custom_assistant_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_args: [])

    entry = ConfigEntry(
        data={CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_LEGACY},
        options={CONF_UPDATE_INTERVAL_MINUTES: 7, CONF_ADAPTIVE_POLLING: False},
        version=10,
    )
    options = config_flow.BackupCheckupOptionsFlow()
    options.hass = SimpleNamespace()
    options.config_entry = entry
    assert (await options.async_step_runtime())["step_id"] == "runtime"
    assert (await options.async_step_monitoring())["step_id"] == "monitoring"
    assert (await options.async_step_verification())["step_id"] == "verification"
    assert (await options.async_step_presentation())["step_id"] == "presentation"

    saved_monitoring = await options.async_step_monitoring(
        {CONF_MONITORING_POLICY: MONITORING_POLICY_BALANCED}
    )
    assert (
        saved_monitoring["data"][CONF_MONITORING_POLICY] == MONITORING_POLICY_BALANCED
    )
    saved_verification = await options.async_step_verification(
        {CONF_VERIFICATION_POLICY: VERIFICATION_POLICY_MANUAL}
    )
    assert (
        saved_verification["data"][CONF_VERIFICATION_POLICY]
        == VERIFICATION_POLICY_MANUAL
    )

    invalid_presentation = _presentation()
    invalid_presentation[CONF_NOTIFICATIONS_ENABLED] = True
    invalid = await options.async_step_presentation(invalid_presentation)
    assert invalid["errors"] == {
        CONF_NOTIFICATION_TARGETS: "notification_target_required"
    }
    saved_presentation = await options.async_step_presentation(_presentation())
    assert saved_presentation["type"] == "create_entry"

    custom = config_flow.BackupCheckupOptionsFlow()
    custom.hass = SimpleNamespace()
    custom.config_entry = entry
    await custom.async_step_runtime(
        {CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_CUSTOM, CONF_ADAPTIVE_POLLING: True}
    )
    custom_form = await custom.async_step_runtime_custom()
    values = {
        marker.key: custom._draft[marker.key]
        for marker in custom_form["data_schema"].schema
    }
    saved_custom = await custom.async_step_runtime_custom(values)
    assert saved_custom["data"][CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_CUSTOM
    assert saved_custom["data"][CONF_ADAPTIVE_POLLING] is True

    monitor_custom = config_flow.BackupCheckupOptionsFlow()
    monitor_custom.hass = SimpleNamespace()
    monitor_custom.config_entry = entry
    await monitor_custom.async_step_monitoring(
        {CONF_MONITORING_POLICY: MONITORING_POLICY_CUSTOM}
    )
    monitoring_values_input = dict(monitor_custom._draft)
    monitoring_values_input[CONF_SIZE_CHECK_MODE] = SIZE_CHECK_FIXED
    monitoring_values_input[CONF_MINIMUM_BACKUP_SIZE_MB] = 5
    saved = await monitor_custom.async_step_monitoring_custom(monitoring_values_input)
    assert saved["data"][CONF_MONITORING_POLICY] == MONITORING_POLICY_CUSTOM

    assistant = config_flow.BackupCheckupOptionsFlow()
    assistant.hass = SimpleNamespace()
    assistant.config_entry = entry
    await assistant.async_step_setup_assistant()
    assert (
        await assistant.async_step_setup_assistant(
            {
                CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_CUSTOM,
                CONF_ADAPTIVE_POLLING: True,
            }
        )
    )["step_id"] == "runtime_custom"
    runtime_input = dict(assistant._draft)
    assert (await assistant.async_step_runtime_custom(runtime_input))[
        "step_id"
    ] == "setup_monitoring"
    await assistant.async_step_setup_monitoring(
        {CONF_MONITORING_POLICY: MONITORING_POLICY_CUSTOM}
    )
    monitoring_input = dict(assistant._draft)
    assert (await assistant.async_step_monitoring_custom(monitoring_input))[
        "step_id"
    ] == "setup_verification"
    await assistant.async_step_setup_verification(
        {CONF_VERIFICATION_POLICY: VERIFICATION_POLICY_MANUAL}
    )
    await assistant.async_step_setup_presentation(_presentation())
    saved_assistant = await assistant.async_step_setup_summary({})
    assert saved_assistant["type"] == "create_entry"


@pytest.mark.asyncio
async def test_adaptive_polling_events_backoff_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hass = _Hass()
    entry = ConfigEntry(
        data={
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_APPLIANCE,
            CONF_ADAPTIVE_POLLING: True,
            CONF_UPDATE_INTERVAL_MINUTES: 10,
            CONF_ACTIVE_UPDATE_INTERVAL_MINUTES: 1,
            CONF_ERROR_BACKOFF_INTERVAL_MINUTES: 30,
        },
        version=10,
    )
    coordinator = BackupCheckupCoordinator(hass, entry)
    callbacks: list[Any] = []
    unsubscribed: list[str] = []

    def _track(_hass: Any, entity_ids: list[str], callback: Any) -> Any:
        callbacks.append((entity_ids[0], callback))
        return lambda: unsubscribed.append(entity_ids[0])

    monkeypatch.setattr(coordinator_module, "async_track_state_change_event", _track)
    monkeypatch.setattr(
        coordinator_module,
        "native_backup_activity_entity_ids",
        lambda _hass: ("sensor.custom_manager", "event.custom_backup"),
    )
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_start_adaptive_polling()
    coordinator.async_start_adaptive_polling()
    assert [item[0] for item in callbacks] == [
        "sensor.custom_manager",
        "event.custom_backup",
    ]

    manager_callback = callbacks[0][1]
    manager_callback(
        SimpleNamespace(
            data={
                "entity_id": "sensor.custom_manager",
                "new_state": SimpleNamespace(state="creating"),
            }
        )
    )
    assert coordinator.update_interval == timedelta(minutes=1)
    coordinator._schedule_adaptive_refresh()
    await asyncio.gather(*hass.tasks)
    coordinator.async_request_refresh.assert_awaited_once()

    coordinator._inventory_error_count = coordinator.adaptive_error_threshold
    coordinator._set_adaptive_interval()
    assert coordinator.update_interval == timedelta(minutes=30)
    coordinator._record_inventory_success("idle")
    assert coordinator.update_interval == timedelta(minutes=10)

    await coordinator.async_shutdown()
    assert unsubscribed == ["sensor.custom_manager", "event.custom_backup"]
    assert coordinator._adaptive_manager_entity_id is None

    disabled = BackupCheckupCoordinator(
        _Hass(), ConfigEntry(data={CONF_ADAPTIVE_POLLING: False}, version=10)
    )
    disabled.async_start_adaptive_polling()
    assert disabled._adaptive_unsubscribers == []
    disabled._set_adaptive_interval()


def test_native_activity_entity_ids_follow_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = {
        "one": SimpleNamespace(
            platform="backup",
            unique_id="backup_manager_state",
            entity_id="sensor.renamed_manager",
        ),
        "two": SimpleNamespace(
            platform="backup",
            unique_id="automatic_backup_event",
            entity_id="event.renamed_backup",
        ),
    }
    registry = SimpleNamespace(entities=entries)
    from custom_components.backup_checkup import native_backup

    monkeypatch.setattr(native_backup.er, "async_get", lambda _hass: registry)
    assert native_backup_activity_entity_ids(SimpleNamespace()) == (
        "sensor.renamed_manager",
        "event.renamed_backup",
    )

    def _broken_registry(_hass: Any) -> Any:
        raise RuntimeError("bad registry")

    monkeypatch.setattr(native_backup.er, "async_get", _broken_registry)
    assert native_backup_activity_entity_ids(SimpleNamespace()) == (
        CORE_BACKUP_MANAGER_STATE,
        CORE_AUTOMATIC_BACKUP_EVENT,
    )


def test_adaptive_diagnostics_states() -> None:
    data = SimpleNamespace(
        checked_at=SimpleNamespace(isoformat=lambda: "checked"),
        last_inventory_success_at=None,
    )
    coordinator = SimpleNamespace(
        last_exception=None,
        last_update_success=True,
        update_interval=timedelta(minutes=10),
        runtime_profile=RUNTIME_PROFILE_APPLIANCE,
        adaptive_polling=True,
        adaptive_error_threshold=3,
        _inventory_error_count=0,
        _manager_backup_active=False,
    )
    assert (
        diagnostics._coordinator_diagnostics(coordinator, data)[
            "adaptive_polling_state"
        ]
        == "normal"
    )
    coordinator._manager_backup_active = True
    assert (
        diagnostics._coordinator_diagnostics(coordinator, data)[
            "adaptive_polling_state"
        ]
        == "backup_active"
    )
    coordinator._inventory_error_count = 3
    assert (
        diagnostics._coordinator_diagnostics(coordinator, data)[
            "adaptive_polling_state"
        ]
        == "error_backoff"
    )
    coordinator.adaptive_polling = False
    assert (
        diagnostics._coordinator_diagnostics(coordinator, data)[
            "adaptive_polling_state"
        ]
        == "disabled"
    )


@pytest.mark.asyncio
async def test_version_9_migration_preserves_resolved_values() -> None:
    integration = importlib.import_module("custom_components.backup_checkup.__init__")

    updates: list[dict[str, Any]] = []
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=lambda _entry, **kwargs: updates.append(kwargs)
        )
    )
    entry = ConfigEntry(
        data={
            CONF_MONITORING_PROFILE: PROFILE_SECURE,
            CONF_UPDATE_INTERVAL_MINUTES: 7,
            CONF_MAX_AGE_DAYS: 8,
            CONF_AUTO_VERIFY_NEW_BACKUPS: True,
            CONF_DATABASE_INTEGRITY_CHECK: False,
        },
        options={
            CONF_MINIMUM_BACKUP_SIZE_MB: 12,
            CONF_NOTIFICATIONS_ENABLED: False,
        },
        version=9,
    )

    assert await integration.async_migrate_entry(hass, entry) is True
    migrated = updates[0]
    assert migrated["version"] == 10
    assert migrated["data"][CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_LEGACY
    assert migrated["data"][CONF_ADAPTIVE_POLLING] is False
    assert migrated["data"][CONF_UPDATE_INTERVAL_MINUTES] == 7
    assert migrated["data"][CONF_MAX_AGE_DAYS] == 8
    assert migrated["data"][CONF_MINIMUM_BACKUP_SIZE_MB] == 12
    assert migrated["data"][CONF_MONITORING_POLICY] == MONITORING_POLICY_STRICT
    assert migrated["data"][CONF_VERIFICATION_POLICY] == VERIFICATION_POLICY_AUTOMATIC
    assert migrated["options"] == migrated["data"]
