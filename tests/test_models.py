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
    assert "backup_id" not in public
    assert "name" not in public
    assert "failed_addons" not in public

    private = record.as_dict(expose_metadata=True)
    assert private["backup_id"] == "raw-secret-id"
    assert private["name"] == "My private backup name"
    assert private["failed_addons"] == ["private-addon"]
