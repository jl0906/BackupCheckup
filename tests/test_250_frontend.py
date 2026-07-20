"""Regression tests for the optional BackupCheckup 2.5.0 frontend panel."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import flow_schemas
from custom_components.backup_checkup import frontend as panel_frontend
from custom_components.backup_checkup.configuration import normalize_configuration
from custom_components.backup_checkup.const import (
    CONF_SHOW_SIDEBAR_PANEL,
    DEFAULT_SHOW_SIDEBAR_PANEL,
)

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_declares_every_direct_frontend_dependency() -> None:
    """Hassfest requires direct component imports to be declared explicitly."""
    manifest = json.loads(
        (
            ROOT
            / "custom_components"
            / "backup_checkup"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["dependencies"] == ["backup", "http", "panel_custom"]


def test_sidebar_panel_setting_is_normalized_and_exposed_in_flow_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """New and malformed settings use the safe opt-in default."""
    assert DEFAULT_SHOW_SIDEBAR_PANEL is False
    assert normalize_configuration({})[CONF_SHOW_SIDEBAR_PANEL] is False
    assert (
        normalize_configuration({CONF_SHOW_SIDEBAR_PANEL: True})[
            CONF_SHOW_SIDEBAR_PANEL
        ]
        is True
    )
    assert (
        normalize_configuration({CONF_SHOW_SIDEBAR_PANEL: "invalid"})[
            CONF_SHOW_SIDEBAR_PANEL
        ]
        is False
    )

    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_: [])
    values = normalize_configuration({})
    schema = flow_schemas.presentation_schema(SimpleNamespace(), values).schema
    marker = next(
        marker for marker in schema if marker.key == CONF_SHOW_SIDEBAR_PANEL
    )
    assert marker.default is False


@pytest.mark.asyncio
async def test_version_10_migration_adds_disabled_sidebar_default() -> None:
    """Existing installations do not gain a sidebar item without consent."""
    integration = importlib.import_module("custom_components.backup_checkup.__init__")
    updates: list[dict[str, Any]] = []
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=lambda _entry, **kwargs: updates.append(kwargs)
        )
    )
    entry = ConfigEntry(
        data={"max_age_days": 7},
        options={"notifications_enabled": True},
        version=10,
    )

    assert await integration.async_migrate_entry(hass, entry) is True
    assert updates[0]["version"] == 12
    assert updates[0]["data"]["max_age_days"] == 7
    assert updates[0]["data"]["notifications_enabled"] is True
    assert updates[0]["data"][CONF_SHOW_SIDEBAR_PANEL] is False
    assert updates[0]["options"] == updates[0]["data"]


@pytest.mark.asyncio
async def test_static_module_and_enabled_panel_are_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The integration serves its bundled module and resolves renamed entities."""
    static_register = AsyncMock()
    hass = SimpleNamespace(
        http=SimpleNamespace(async_register_static_paths=static_register)
    )
    await panel_frontend.async_register_frontend(hass)
    static_register.assert_awaited_once()
    static_path = static_register.await_args.args[0][0]
    assert static_path.url_path == panel_frontend.PANEL_MODULE_PATH
    assert static_path.path == str(panel_frontend.PANEL_MODULE_FILE)
    assert static_path.cache_headers is True

    registry = SimpleNamespace(
        async_get_entity_id=lambda platform, _domain, unique_id: (
            f"{platform}.renamed_{unique_id.rsplit('_', 1)[-1]}"
        )
    )
    monkeypatch.setattr(panel_frontend.er, "async_get", lambda _hass: registry)
    register_panel = AsyncMock()
    remove_panel = Mock()
    monkeypatch.setattr(
        panel_frontend.panel_custom, "async_register_panel", register_panel
    )
    monkeypatch.setattr(panel_frontend.frontend, "async_remove_panel", remove_panel)

    entry = ConfigEntry(
        entry_id="entry",
        data={CONF_SHOW_SIDEBAR_PANEL: True},
        version=11,
    )
    await panel_frontend.async_setup_panel(hass, entry)

    register_panel.assert_awaited_once()
    kwargs: dict[str, Any] = register_panel.await_args.kwargs
    assert kwargs["frontend_url_path"] == "backup-checkup"
    assert kwargs["webcomponent_name"] == "backup-checkup-panel"
    assert kwargs["module_url"].endswith("?v=2.6.0")
    assert kwargs["sidebar_icon"] == "mdi:backup-restore"
    assert kwargs["config"]["entry_id"] == "entry"
    assert kwargs["config"]["entities"]["status"].startswith("sensor.renamed_")
    assert len(entry._unloads) == 1

    entry._unloads[0]()
    remove_panel.assert_called_once_with(
        hass,
        "backup-checkup",
        warn_if_unknown=False,
    )


@pytest.mark.asyncio
async def test_disabled_or_conflicting_panel_does_not_break_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Panel registration remains optional and collision-safe."""
    hass = SimpleNamespace()
    register_panel = AsyncMock()
    monkeypatch.setattr(
        panel_frontend.panel_custom, "async_register_panel", register_panel
    )

    disabled = ConfigEntry(data={}, version=11)
    await panel_frontend.async_setup_panel(hass, disabled)
    register_panel.assert_not_awaited()
    assert disabled._unloads == []

    register_panel.side_effect = ValueError("Overwriting panel backup-checkup")
    enabled = ConfigEntry(data={CONF_SHOW_SIDEBAR_PANEL: True}, version=11)
    await panel_frontend.async_setup_panel(hass, enabled)
    assert enabled._unloads == []


def test_frontend_bundle_is_local_responsive_and_escapes_dynamic_content() -> None:
    """The panel is self-contained and protects innerHTML rendering boundaries."""
    source = (
        ROOT
        / "custom_components"
        / "backup_checkup"
        / "frontend"
        / "backup-checkup-panel.js"
    ).read_text(encoding="utf-8")

    assert 'customElements.define("backup-checkup-panel"' in source
    assert "https://" not in source
    assert "replaceAll(\"&\", \"&amp;\")" in source
    assert 'if (agent.error) return "danger"' in source
    assert 'data-tab="logs"' in source
    assert 'data-log-search' in source
    assert "@media (max-width:620px)" in source
    assert 'callService("button", "press"' in source
