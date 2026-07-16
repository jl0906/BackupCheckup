"""Repository metadata, translation, and release-layout tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def _leaf_values(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    leaves: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        leaves.update(_leaf_values(child, path))
    return leaves


def _placeholders(value: str) -> set[str]:
    return set(re.findall(r"\{([^{}]+)\}", value))


def test_release_versions_are_consistent() -> None:
    """Manifest, constants, README, and changelog advertise beta4 consistently."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    constants = (INTEGRATION / "const.py").read_text()
    readme = (ROOT / "README.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    assert manifest["version"] == "2.2.0-beta4"
    assert 'VERSION = "2.2.0-beta4"' in constants
    assert "2.2.0-beta4" in readme
    assert "## 2.2.0-beta4" in changelog


def test_hacs_uses_repository_source_without_zip_release() -> None:
    """HACS remains configured for direct tagged-repository installation."""
    hacs = json.loads((ROOT / "hacs.json").read_text())

    assert hacs.get("zip_release") is not True
    assert "filename" not in hacs
    assert (ROOT / "custom_components" / "backup_checkup").is_dir()


def test_brand_assets_exist() -> None:
    """The README's local brand image is present in standard and 2x sizes."""
    assert (INTEGRATION / "brand" / "icon.png").is_file()
    assert (INTEGRATION / "brand" / "icon@2x.png").is_file()


def test_all_json_and_yaml_files_parse() -> None:
    """Repository metadata files are syntactically valid."""
    for path in ROOT.rglob("*.json"):
        json.loads(path.read_text())
    for path in [
        INTEGRATION / "services.yaml",
        ROOT / ".github/workflows/validate.yml",
    ]:
        assert yaml.safe_load(path.read_text()) is not None


def test_translation_structures_and_placeholders_match() -> None:
    """Every locale stays structurally aligned with the English source."""
    source = _leaf_values(json.loads((INTEGRATION / "strings.json").read_text()))

    for path in sorted((INTEGRATION / "translations").glob("*.json")):
        translated = _leaf_values(json.loads(path.read_text()))
        assert translated.keys() == source.keys(), path.name
        for key, source_value in source.items():
            translated_value = translated[key]
            if isinstance(source_value, str) and isinstance(translated_value, str):
                assert _placeholders(translated_value) == _placeholders(source_value), (
                    path.name,
                    key,
                )
