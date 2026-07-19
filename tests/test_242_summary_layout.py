"""Regression tests for the compact hassfest-valid confirmation summary."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.backup_checkup import flow_schemas
from custom_components.backup_checkup.configuration import normalize_configuration
from custom_components.backup_checkup.const import (
    CONF_ADAPTIVE_POLLING,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_RUNTIME_PROFILE,
    RUNTIME_PROFILE_PERFORMANCE,
)

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def test_summary_sections_are_compact_and_notifications_collapse_when_disabled() -> (
    None
):
    values = normalize_configuration(
        {
            CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_PERFORMANCE,
            CONF_ADAPTIVE_POLLING: False,
            CONF_NOTIFICATIONS_ENABLED: False,
            flow_schemas.SUMMARY_HARDWARE: "x86_64",
        }
    )
    values[flow_schemas.SUMMARY_HARDWARE] = "x86_64"
    translations = {
        (
            "component.backup_checkup.selector.runtime_profile.options.performance"
        ): "Leistungsstark",
        (
            "component.backup_checkup.selector.enabled_state.options.disabled"
        ): "Deaktiviert",
    }
    schema = flow_schemas.summary_schema(values, translations).schema

    system = next(
        value
        for marker, value in schema.items()
        if marker.key == flow_schemas.SUMMARY_SECTION_SYSTEM
    )
    profile = next(
        selector
        for marker, selector in system.schema.schema.items()
        if marker.key == flow_schemas.SUMMARY_RUNTIME_PROFILE
    )
    assert profile.config == {
        "value": RUNTIME_PROFILE_PERFORMANCE,
        "label": "Leistungsstark",
    }

    notifications = next(
        value
        for marker, value in schema.items()
        if marker.key == flow_schemas.SUMMARY_SECTION_NOTIFICATIONS
    )
    assert notifications.options["collapsed"] is True
    assert len(schema) == 5


def test_summary_sections_and_constant_values_exist_in_every_locale() -> None:
    source = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    expected_sections = {
        flow_schemas.SUMMARY_SECTION_SYSTEM,
        flow_schemas.SUMMARY_SECTION_POLLING,
        flow_schemas.SUMMARY_SECTION_MONITORING,
        flow_schemas.SUMMARY_SECTION_INTEGRITY,
        flow_schemas.SUMMARY_SECTION_NOTIFICATIONS,
    }

    for path in [
        INTEGRATION / "strings.json",
        *sorted((INTEGRATION / "translations").glob("*.json")),
    ]:
        data = json.loads(path.read_text(encoding="utf-8"))
        for branch, step in (("config", "summary"), ("options", "setup_summary")):
            assert set(data[branch]["step"][step]["sections"]) == expected_sections
            assert "data" not in data[branch]["step"][step]
        assert not any(key.startswith("summary_") for key in data["selector"])
        assert all(
            set(selector_translation) <= {"options", "unit_of_measurement"}
            for selector_translation in data["selector"].values()
        )
        assert "performance" in data["selector"]["runtime_profile"]["options"]
        assert "enabled" in data["selector"]["enabled_state"]["options"]

    assert source["config"]["step"]["summary"]["sections"]


def test_summary_section_icons_cover_config_and_options_flows() -> None:
    icons = json.loads((INTEGRATION / "icons.json").read_text(encoding="utf-8"))
    config_sections = icons["config"]["step"]["summary"]["sections"]
    options_sections = icons["options"]["step"]["setup_summary"]["sections"]
    assert config_sections == options_sections
    assert set(config_sections) == {
        flow_schemas.SUMMARY_SECTION_SYSTEM,
        flow_schemas.SUMMARY_SECTION_POLLING,
        flow_schemas.SUMMARY_SECTION_MONITORING,
        flow_schemas.SUMMARY_SECTION_INTEGRITY,
        flow_schemas.SUMMARY_SECTION_NOTIFICATIONS,
    }
