"""Regression tests for the 2.4.3 hassfest fixes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.backup_checkup import config_flow

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def test_selector_translations_use_only_hassfest_supported_nodes() -> None:
    """Selector translations must use options, never constant value nodes."""
    for path in [
        INTEGRATION / "strings.json",
        *sorted((INTEGRATION / "translations").glob("*.json")),
    ]:
        selectors = json.loads(path.read_text(encoding="utf-8"))["selector"]
        assert not any(key.startswith("summary_") for key in selectors)
        for payload in selectors.values():
            assert set(payload) <= {"options", "unit_of_measurement"}


def test_config_entry_only_schema_is_declared() -> None:
    """The integration must explicitly reject YAML configuration."""
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    assert "from homeassistant.helpers import config_validation as cv" in source
    assert "CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)" in source


@pytest.mark.asyncio
async def test_summary_translation_loader_uses_flow_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Summary labels are loaded from the valid selector option category."""
    loader = AsyncMock(return_value={"translated": "value"})
    monkeypatch.setattr(config_flow, "async_get_translations", loader)
    flow = SimpleNamespace(
        hass=SimpleNamespace(config=SimpleNamespace(language="en")),
        context={"language": "de"},
    )

    assert await config_flow._async_summary_translations(flow) == {
        "translated": "value"
    }
    loader.assert_awaited_once_with(flow.hass, "de", "selector", {"backup_checkup"})


def test_flow_language_falls_back_to_home_assistant_and_english() -> None:
    """Options flows and isolated tests get stable language fallbacks."""
    assert (
        config_flow._flow_language(
            SimpleNamespace(hass=SimpleNamespace(config=SimpleNamespace(language="nl")))
        )
        == "nl"
    )
    assert config_flow._flow_language(SimpleNamespace(hass=SimpleNamespace())) == "en"
