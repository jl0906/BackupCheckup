"""Privacy tests for BackupCheckup data models."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.backup_checkup.models import BackupRecord


def test_backup_record_is_private_by_default() -> None:
    """Normal entity attributes omit raw backup names, IDs, and component names."""
    record = BackupRecord(
        backup_id="raw-secret-id",
        backup_reference="aabbccddeeff",
        name="My private backup name",
        date=datetime(2026, 7, 15, tzinfo=UTC),
        automatic=True,
        purpose="automatic",
        included_addons=("private-addon",),
        included_folders=("share",),
        scope_fingerprint="scope1234",
        agents=("backup.local",),
        agent_copies=(),
        failed_agents=("private-agent",),
        failed_addons=("private-addon",),
        failed_folders=("private-folder",),
        database_included=True,
        homeassistant_included=True,
        size=123,
        incomplete=True,
    )

    public = record.as_dict()
    assert public["backup_reference"] == "aabbccddeeff"
    assert public["failed_addon_count"] == 1
    assert public["included_addon_count"] == 1
    assert public["purpose"] == "automatic"
    assert "included_addons" not in public
    assert "backup_id" not in public
    assert "name" not in public
    assert "failed_addons" not in public

    private = record.as_dict(expose_metadata=True)
    assert private["backup_id"] == "raw-secret-id"
    assert private["name"] == "My private backup name"
    assert private["failed_addons"] == ["private-addon"]
    assert private["included_addons"] == ["private-addon"]


def test_corrupt_integrity_store_values_are_rejected() -> None:
    """Malformed private-store values are detected before deserialization."""
    from custom_components.backup_checkup.models import BackupIntegrityResult

    assert not BackupIntegrityResult.storage_dict_is_valid(
        {"status": "valid", "archive_count": "not-an-int"}
    )
    assert not BackupIntegrityResult.storage_dict_is_valid(
        {"status": "unknown-future-status"}
    )
    assert not BackupIntegrityResult.storage_dict_is_valid(
        {"status": "valid", "checked_at": "not-a-date"}
    )


def test_missing_new_integrity_fields_remain_backward_compatible() -> None:
    """Older beta store records can load without every newer optional field."""
    from custom_components.backup_checkup.models import BackupIntegrityResult

    stored = {
        "status": "valid",
        "archive_count": 1,
        "file_count": 2,
        "database_status": "not_checked",
    }

    assert BackupIntegrityResult.storage_dict_is_valid(stored)
    parsed = BackupIntegrityResult.from_dict(stored)
    assert parsed.status == "valid"
    assert parsed.archive_count == 1
    assert parsed.checksum_changed is False


def test_integrity_warning_reduces_health_rating() -> None:
    """A valid backup with actionable warnings cannot remain excellent."""
    from custom_components.backup_checkup.analytics import calculate_health_score

    result = calculate_health_score(
        {"backup_integrity_warning": True},
        automatic_success_rate=None,
        consecutive_automatic_failures=0,
        resolved_attempts=0,
    )

    assert result.score == 89
    assert result.rating == "good"
    assert result.deductions == {"backup_integrity_warning": 11}
