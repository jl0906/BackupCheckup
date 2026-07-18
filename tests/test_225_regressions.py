"""Regression tests for BackupCheckup 2.2.5 maintainability fixes."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.backup_checkup.backup_normalizer import BackupRecordNormalizer
from custom_components.backup_checkup.integrity import BackupIntegrityStore
from custom_components.backup_checkup.models import BackupIntegrityResult


def test_addon_slugs_accept_string_mapping_and_object() -> None:
    value = {
        "one": "string_slug",
        "two": {"slug": "mapping_slug"},
        "three": SimpleNamespace(slug="object_slug"),
    }
    assert BackupRecordNormalizer.addon_slugs(value) == (
        "mapping_slug",
        "object_slug",
        "string_slug",
    )


def test_addon_slugs_ignore_missing_slug_instead_of_stringifying_none() -> None:
    assert BackupRecordNormalizer.addon_slugs([{}, SimpleNamespace()]) == ()


def test_agent_copy_mapping_and_legacy_iterable_remain_compatible() -> None:
    normalizer = BackupRecordNormalizer("entry")
    mapped, mapped_invalid = normalizer._agent_copies(
        {"backup.local": {"size": 123, "is_protected": True}}
    )
    legacy, legacy_invalid = normalizer._agent_copies(
        ["backup.local", "backup.local", "backup.remote"]
    )
    assert mapped_invalid == 0
    assert mapped[0].size == 123
    assert mapped[0].protected is True
    assert legacy_invalid == 0
    assert tuple(copy.agent_id for copy in legacy) == (
        "backup.local",
        "backup.remote",
    )


def test_integrity_store_runtime_fields_are_bounded() -> None:
    result = BackupIntegrityResult.not_checked().as_dict()
    state = BackupIntegrityStore._state_from_stored(
        {
            "result": result,
            "retry": {
                "backup_id": "b" * 300,
                "error_key": "e" * 200,
                "attempts": 101,
                "not_before": "2026-07-17T12:00:00",
            },
            "password_marker": "p" * 200,
            "last_manual_verification_at": "2026-07-17T12:00:00",
        }
    )
    assert len(state.retry_backup_id or "") == 256
    assert len(state.retry_error_key or "") == 128
    assert state.retry_attempts == 0
    assert len(state.password_marker or "") == 128
    assert state.retry_not_before == datetime(2026, 7, 17, 12, tzinfo=UTC)
    assert state.last_manual_verification_at == datetime(2026, 7, 17, 12, tzinfo=UTC)
