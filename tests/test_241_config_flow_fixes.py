"""Regression tests for the BackupCheckup 2.4.1 setup-flow fixes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import (
    config_flow,
    flow_schemas,
    hardware_profile,
    setup_recommendation,
)
from custom_components.backup_checkup.configuration import normalize_configuration
from custom_components.backup_checkup.const import (
    CONF_ADAPTIVE_POLLING,
    CONF_HARDWARE_DETECTION,
    CONF_RUNTIME_PROFILE,
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_CUSTOM,
)
from custom_components.backup_checkup.hardware_profile import HardwareSnapshot

ROOT = Path(__file__).resolve().parents[1]


def _hardware() -> HardwareSnapshot:
    return HardwareSnapshot(
        installation_type="Home Assistant OS",
        architecture="aarch64",
        board="green",
        recommended_profile=RUNTIME_PROFILE_APPLIANCE,
        confidence="high",
        detection="automatic",
    )


def _schema_payload(form: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """Return exactly the fields a real frontend form can submit."""
    return {
        marker.key: values[marker.key]
        for marker in form["data_schema"].schema
        if marker.key in values
    }


def _options_flow(*, adaptive: bool) -> config_flow.BackupCheckupOptionsFlow:
    flow = config_flow.BackupCheckupOptionsFlow()
    flow.hass = SimpleNamespace()
    flow.config_entry = ConfigEntry(
        data={
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_APPLIANCE,
            CONF_ADAPTIVE_POLLING: adaptive,
        },
        version=10,
    )
    return flow


@pytest.mark.asyncio
async def test_summary_uses_compact_grouped_constant_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    monkeypatch.setattr(
        config_flow,
        "async_recommended_verification_size_gb",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        config_flow,
        "async_get_translations",
        AsyncMock(
            return_value={
                (
                    "component.backup_checkup.selector.runtime_profile.options."
                    "home_assistant_appliance"
                ): "Home Assistant Appliance",
                (
                    "component.backup_checkup.selector.enabled_state.options.enabled"
                ): "Aktiviert",
            }
        ),
    )
    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()
    await flow._async_prepare()

    form = await flow.async_step_summary()
    sections = form["data_schema"].schema
    section_keys = [marker.key for marker in sections]
    assert section_keys == [
        flow_schemas.SUMMARY_SECTION_SYSTEM,
        flow_schemas.SUMMARY_SECTION_POLLING,
        flow_schemas.SUMMARY_SECTION_MONITORING,
        flow_schemas.SUMMARY_SECTION_INTEGRITY,
        flow_schemas.SUMMARY_SECTION_NOTIFICATIONS,
    ]
    assert form["last_step"] is True

    system = next(
        value
        for marker, value in sections.items()
        if marker.key == flow_schemas.SUMMARY_SECTION_SYSTEM
    )
    system_fields = system.schema.schema
    profile_selector = next(
        selector
        for marker, selector in system_fields.items()
        if marker.key == flow_schemas.SUMMARY_RUNTIME_PROFILE
    )
    assert profile_selector.config["value"] == RUNTIME_PROFILE_APPLIANCE
    assert profile_selector.config["label"] == "Home Assistant Appliance"
    assert "translation_key" not in profile_selector.config

    polling = next(
        value
        for marker, value in sections.items()
        if marker.key == flow_schemas.SUMMARY_SECTION_POLLING
    )
    adaptive_selector = next(
        selector
        for marker, selector in polling.schema.schema.items()
        if marker.key == flow_schemas.SUMMARY_ADAPTIVE_POLLING
    )
    assert adaptive_selector.config["label"] == "Aktiviert"
    assert "translation_key" not in adaptive_selector.config
    assert all(
        selector.__class__.__name__ == "ConstantSelector"
        for summary_section in sections.values()
        for selector in summary_section.schema.schema.values()
    )

    created = await flow.async_step_summary({})
    assert created["type"] == "create_entry"


@pytest.mark.asyncio
@pytest.mark.parametrize(("before", "selected"), [(False, True), (True, False)])
async def test_custom_runtime_keeps_adaptive_polling_from_previous_form(
    before: bool,
    selected: bool,
) -> None:
    flow = _options_flow(adaptive=before)
    custom_form = await flow.async_step_runtime(
        {
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_CUSTOM,
            CONF_ADAPTIVE_POLLING: selected,
        }
    )
    assert custom_form["step_id"] == "runtime_custom"

    payload = _schema_payload(custom_form, flow._draft)
    assert CONF_ADAPTIVE_POLLING not in payload
    saved = await flow.async_step_runtime_custom(payload)

    assert saved["type"] == "create_entry"
    assert saved["data"][CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_CUSTOM
    assert saved["data"][CONF_ADAPTIVE_POLLING] is selected


@pytest.mark.asyncio
async def test_hardware_recommendation_is_preselected_without_raw_internal_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_flow, "async_detect_hardware", AsyncMock(return_value=_hardware())
    )
    monkeypatch.setattr(
        config_flow,
        "async_recommended_verification_size_gb",
        AsyncMock(return_value=None),
    )
    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()

    form = await flow.async_step_user()
    assert form["description_placeholders"] == {
        "installation_type": "Home Assistant OS",
        "architecture": "aarch64",
        "board": "green",
    }
    assert "recommended_profile" not in form["description_placeholders"]
    assert "confidence" not in form["description_placeholders"]

    profile_marker = next(
        marker
        for marker in form["data_schema"].schema
        if marker.key == CONF_RUNTIME_PROFILE
    )
    assert profile_marker.default == RUNTIME_PROFILE_APPLIANCE


@pytest.mark.asyncio
async def test_setup_recommendations_have_bounded_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    never = asyncio.Event()

    async def _hung_system_info(_hass: Any) -> dict[str, str]:
        await never.wait()
        return {}

    monkeypatch.setattr(hardware_profile, "async_get_system_info", _hung_system_info)
    monkeypatch.setattr(hardware_profile, "_HARDWARE_DETECTION_TIMEOUT_SECONDS", 0.001)
    detected = await hardware_profile.async_detect_hardware(SimpleNamespace())
    assert detected.detection == "fallback:TimeoutError"

    manager = SimpleNamespace(
        async_get_backups=AsyncMock(side_effect=_hung_system_info)
    )
    monkeypatch.setattr(
        setup_recommendation, "async_get_manager", lambda _hass: manager
    )
    monkeypatch.setattr(
        setup_recommendation, "_SETUP_RECOMMENDATION_TIMEOUT_SECONDS", 0.001
    )
    assert (
        await setup_recommendation.async_recommended_verification_size_gb(
            SimpleNamespace()
        )
        is None
    )


@pytest.mark.asyncio
async def test_hardware_and_inventory_recommendations_are_prepared_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hardware_started = asyncio.Event()
    inventory_started = asyncio.Event()
    release = asyncio.Event()

    async def _detect(_hass: Any) -> HardwareSnapshot:
        hardware_started.set()
        await release.wait()
        return _hardware()

    async def _inventory(_hass: Any) -> None:
        inventory_started.set()
        await release.wait()
        return None

    monkeypatch.setattr(config_flow, "async_detect_hardware", _detect)
    monkeypatch.setattr(
        config_flow, "async_recommended_verification_size_gb", _inventory
    )
    flow = config_flow.BackupCheckupConfigFlow()
    flow.hass = SimpleNamespace()

    task = asyncio.create_task(flow._async_prepare())
    await asyncio.wait_for(hardware_started.wait(), timeout=1)
    await asyncio.wait_for(inventory_started.wait(), timeout=1)
    release.set()
    await task
    assert flow._hardware == _hardware()


@pytest.mark.asyncio
async def test_options_menu_resets_stale_setup_assistant_state() -> None:
    flow = _options_flow(adaptive=True)
    flow._assistant_mode = True
    flow._draft = {"stale": True}

    menu = await flow.async_step_init()
    assert menu["type"] == "menu"
    assert flow._assistant_mode is False
    assert flow._draft == {}
    assert flow._hardware is None
    assert flow._recommended_verification_size_gb is None


@pytest.mark.asyncio
async def test_options_setup_summary_saves_with_normal_submit() -> None:
    flow = _options_flow(adaptive=True)
    flow._assistant_mode = True
    flow._draft = normalize_configuration(
        {
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_APPLIANCE,
            CONF_ADAPTIVE_POLLING: True,
            CONF_HARDWARE_DETECTION: _hardware().as_dict(),
        }
    )

    form = await flow.async_step_setup_summary()
    assert "confirm" not in {marker.key for marker in form["data_schema"].schema}
    saved = await flow.async_step_setup_summary({})
    assert saved["type"] == "create_entry"


def test_summary_translation_values_and_badges_are_release_safe() -> None:
    de = json.loads(
        (ROOT / "custom_components/backup_checkup/translations/de.json").read_text(
            encoding="utf-8"
        )
    )
    summary = de["config"]["step"]["summary"]
    assert "{runtime_profile}" not in summary["description"]
    assert (
        summary["sections"][flow_schemas.SUMMARY_SECTION_SYSTEM]["data"][
            flow_schemas.SUMMARY_RUNTIME_PROFILE
        ]
        == "Leistungsprofil"
    )
    assert (
        de["selector"]["runtime_profile"]["options"][RUNTIME_PROFILE_APPLIANCE]
        == "Home Assistant Appliance"
    )
    assert not any(key.startswith("summary_") for key in de["selector"])
    assert de["selector"]["enabled_state"]["options"]["enabled"] == "Aktiviert"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/badges/" not in readme
    assert "https://img.shields.io/badge/HACS-Custom-orange.svg" in readme
    assert "https://img.shields.io/badge/AI-Coded_and_Maintained-8A2BE2.svg" in readme
    assert (
        "https://img.shields.io/badge/Home_Assistant-2026.3_or_newer-41BDF5.svg"
        in readme
    )
