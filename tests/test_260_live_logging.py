"""Regression tests for BackupCheckup 2.6.0 detailed live logging."""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup import activity as activity_module
from custom_components.backup_checkup import flow_schemas
from custom_components.backup_checkup.activity import (
    ACTIVITY_OUTCOME_COMPLETED,
    BackupCheckupActivityLog,
)
from custom_components.backup_checkup.configuration import (
    BackupCheckupSettings,
    normalize_configuration,
)
from custom_components.backup_checkup.const import (
    CONF_ACTIVITY_LOGGING_ENABLED,
    CONF_ENTITY_MODE,
    ENTITY_MODE_EXPERT,
    ENTITY_MODE_STANDARD,
)
from custom_components.backup_checkup.integrity import BackupIntegrityVerifier
from custom_components.backup_checkup.security import VerificationBudget

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


class _InlineHass:
    """Execute Home Assistant executor jobs inline for isolated verification."""

    async def async_add_executor_job(self, target: Any, *args: Any) -> Any:
        return target(*args)


class _ChunkAgent:
    """Return two deterministic download chunks."""

    async def async_download_backup(self, _backup_id: str):
        async def _stream():
            for chunk in (b"1234", b"5678"):
                yield chunk

        return _stream()


def test_activity_logging_is_independent_from_entity_mode() -> None:
    """New installs default off while legacy Expert behavior is preserved."""
    assert normalize_configuration({})[CONF_ACTIVITY_LOGGING_ENABLED] is False
    assert (
        normalize_configuration({CONF_ENTITY_MODE: ENTITY_MODE_EXPERT})[
            CONF_ACTIVITY_LOGGING_ENABLED
        ]
        is True
    )
    explicit = normalize_configuration(
        {
            CONF_ENTITY_MODE: ENTITY_MODE_EXPERT,
            CONF_ACTIVITY_LOGGING_ENABLED: False,
        }
    )
    assert explicit[CONF_ACTIVITY_LOGGING_ENABLED] is False
    assert (
        BackupCheckupSettings.from_sources(explicit).activity_logging_enabled is False
    )

    standard_with_logging = normalize_configuration(
        {
            CONF_ENTITY_MODE: ENTITY_MODE_STANDARD,
            CONF_ACTIVITY_LOGGING_ENABLED: True,
        }
    )
    assert BackupCheckupSettings.from_sources(
        standard_with_logging
    ).activity_logging_enabled is True


def test_presentation_schema_exposes_separate_logging_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The logging toggle is present without changing the entity-mode selector."""
    monkeypatch.setattr(flow_schemas, "mobile_notification_options", lambda *_args: [])
    values = normalize_configuration({})
    schema = flow_schemas.presentation_schema(SimpleNamespace(), values)
    keys = {marker.key for marker in schema.schema}
    assert CONF_ACTIVITY_LOGGING_ENABLED in keys
    assert CONF_ENTITY_MODE in keys


@pytest.mark.asyncio
async def test_version_11_expert_entry_migrates_with_logging_enabled() -> None:
    """Existing Expert users retain their previously enabled activity journal."""
    integration = importlib.import_module("custom_components.backup_checkup.__init__")
    updates: list[dict[str, Any]] = []
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=lambda _entry, **kwargs: updates.append(kwargs)
        )
    )
    entry = ConfigEntry(
        data={CONF_ENTITY_MODE: ENTITY_MODE_EXPERT},
        options={},
        version=11,
    )

    assert await integration.async_migrate_entry(hass, entry) is True
    assert updates[0]["version"] == 12
    assert updates[0]["data"][CONF_ACTIVITY_LOGGING_ENABLED] is True


def test_live_journal_notifies_listeners_and_drops_private_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Frontend updates remain live and centrally protected from identifiers."""
    monkeypatch.setattr(activity_module, "async_log_entry", lambda *_args: None)
    journal = BackupCheckupActivityLog(SimpleNamespace())
    notifications: list[int] = []
    remove = journal.async_add_listener(lambda: notifications.append(journal.count))

    record = journal.record(
        "encrypted_backup_extract",
        ACTIVITY_OUTCOME_COMPLETED,
        level=logging.WARNING,
        activity_visible=False,
        details={
            "progress_percent": 100,
            "backup_name": "Private backup",
            "backup_id": "secret-id",
            "path": "/private/path",
            "password": "secret",
        },
    )
    remove()
    journal.record("after_unsubscribe", ACTIVITY_OUTCOME_COMPLETED)

    assert record is not None
    assert record.level == "warning"
    assert dict(record.details) == {"progress_percent": "100"}
    assert notifications == [1]
    assert "secret" not in repr(journal.recent())


def test_download_progress_is_logged_without_backup_identity(tmp_path: Path) -> None:
    """Known-size downloads publish bounded progress without identifiers."""
    journal = BackupCheckupActivityLog(SimpleNamespace())
    verifier = BackupIntegrityVerifier(_InlineHass(), "entry", activity=journal)
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=100,
        max_expanded_bytes=100,
    )

    size, _digest = asyncio.run(
        verifier._async_download(
            _ChunkAgent(),
            "private-backup-id",
            tmp_path / "backup.tar",
            budget,
            expected_size=8,
        )
    )

    assert size == 8
    progress = [
        item["details"]["progress_percent"]
        for item in journal.recent()
        if item["action"] == "backup_download"
    ]
    assert progress == ["50", "95"]
    assert "private-backup-id" not in repr(journal.recent())


def test_sidebar_bundle_contains_dedicated_searchable_live_log() -> None:
    """The sidebar exposes two tabs and privacy-safe generic operation labels."""
    source = (
        INTEGRATION / "frontend" / "backup-checkup-panel.js"
    ).read_text(encoding="utf-8")
    assert 'data-tab="overview"' in source
    assert 'data-tab="logs"' in source
    assert "data-log-search" in source
    assert "Verschlüsseltes Backup wird extrahiert" in source
    assert "Datenbank wird gelesen und geprüft" in source
    assert "progress_percent" in source


def test_reported_code_smell_patterns_are_removed() -> None:
    """Keep the screenshot-reported Python smells from returning."""
    integrity = (INTEGRATION / "integrity.py").read_text(encoding="utf-8")
    coordinator = (INTEGRATION / "coordinator.py").read_text(encoding="utf-8")
    repairs = (INTEGRATION / "repairs.py").read_text(encoding="utf-8")
    assert "json.JSONDecodeError," not in integrity
    assert "age :=" not in coordinator
    assert (
        "Unexpected error while processing BackupCheckup notifications" in coordinator
    )
    assert "_LOGGER.exception(" in coordinator
    assert "unit = units[0]" not in repairs
