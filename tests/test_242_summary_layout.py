"""Regression tests for the value-free final confirmation page."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.backup_checkup.flow_schemas import confirmation_schema

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def test_confirmation_schema_contains_no_resolved_values() -> None:
    """The final page must not render raw or read-only setting values."""
    assert confirmation_schema().schema == {}


def test_confirmation_pages_are_value_free_in_every_locale() -> None:
    """Translations describe submission without declaring data rows or sections."""
    for path in [
        INTEGRATION / "strings.json",
        *sorted((INTEGRATION / "translations").glob("*.json")),
    ]:
        data = json.loads(path.read_text(encoding="utf-8"))
        for branch, step in (("config", "summary"), ("options", "setup_summary")):
            summary = data[branch]["step"][step]
            assert set(summary) == {"title", "description"}
            assert "summary_" not in json.dumps(summary)


def test_obsolete_summary_section_icons_are_removed() -> None:
    """No section icons remain after removing the summary value rows."""
    icons = json.loads((INTEGRATION / "icons.json").read_text(encoding="utf-8"))
    assert icons == {}
