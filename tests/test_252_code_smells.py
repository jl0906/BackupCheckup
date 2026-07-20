"""Regression tests for the code-quality-only BackupCheckup 2.5.2 release."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from custom_components.backup_checkup.backup_normalizer import BackupRecordNormalizer

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def _function_node(path: Path, function_name: str) -> ast.AsyncFunctionDef:
    """Return one top-level async function from a Python module."""
    module = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    (
        ("__init__.py", "async_migrate_entry"),
        ("__init__.py", "async_remove_config_entry_device"),
        ("binary_sensor.py", "async_setup_entry"),
        ("button.py", "async_setup_entry"),
        ("sensor.py", "async_setup_entry"),
    ),
)
def test_home_assistant_coroutine_hooks_contain_an_await(
    module_name: str, function_name: str
) -> None:
    """Required coroutine hooks must perform an asynchronous operation."""
    function = _function_node(INTEGRATION / module_name, function_name)
    assert any(isinstance(node, ast.Await) for node in ast.walk(function))


def test_addon_metadata_normalizer_always_returns_a_tuple() -> None:
    """Every supported metadata shape has one stable return type."""
    values = (None, {"one": "slug"}, "slug", (item for item in ("a", "b")))
    for value in values:
        assert isinstance(BackupRecordNormalizer._addon_iterable(value), tuple)


def test_notification_fallback_retains_exception_context() -> None:
    """Unexpected notification failures must log their traceback."""
    source = (INTEGRATION / "notifications.py").read_text(encoding="utf-8")
    marker = "Unexpected BackupCheckup notification error"
    block = source[source.index(marker) - 120 : source.index(marker)]
    assert "_LOGGER.exception(" in block


def test_backup_metadata_filename_has_one_code_literal() -> None:
    """Archive path validation uses one shared metadata filename constant."""
    source = (INTEGRATION / "integrity.py").read_text(encoding="utf-8")
    assert source.count('"backup.json"') == 1
    assert "normalized_name == _METADATA_FILENAME" in source
    assert "member_path.name == _METADATA_FILENAME" in source


def test_complex_render_and_archive_work_is_decomposed() -> None:
    """Keep both formerly complex functions split into focused helpers."""
    frontend = (
        INTEGRATION / "frontend" / "backup-checkup-panel.js"
    ).read_text(encoding="utf-8")
    render = frontend.split("  _render() {", 1)[1].split(
        "  _buttonDisabled", 1
    )[0]
    assert "this._renderModel()" in render
    assert "const status =" not in render

    integrity = (INTEGRATION / "integrity.py").read_text(encoding="utf-8")
    reader = integrity.split("    def _read_inner_archive(", 1)[1].split(
        "    def _consume_inner_file(", 1
    )[0]
    assert "cls._consume_inner_file(" in reader

