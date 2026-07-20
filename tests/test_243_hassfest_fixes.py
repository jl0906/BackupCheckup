"""Regression tests for the 2.4.3 hassfest fixes."""

from __future__ import annotations

import json
from pathlib import Path

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
