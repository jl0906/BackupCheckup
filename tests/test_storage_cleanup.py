"""Private storage cleanup tests."""

from custom_components.backup_checkup.storage_cleanup import (
    STORE_KINDS,
    cleanup_entry_store_files,
    cleanup_orphaned_store_files,
)


def test_orphan_cleanup_removes_only_stores_without_config_entry(tmp_path) -> None:
    """Active and unrelated Home Assistant storage files are preserved."""
    active_id = "ACTIVE123"
    orphan_id = "ORPHAN456"
    for kind in STORE_KINDS:
        (tmp_path / f"backup_checkup.{active_id}.{kind}").write_text("active")
        (tmp_path / f"backup_checkup.{orphan_id}.{kind}").write_text("orphan")
    foreign = tmp_path / "another_integration.ORPHAN456.history"
    foreign.write_text("foreign")
    malformed = tmp_path / "backup_checkup.bad.extra.history"
    malformed.write_text("malformed")

    result = cleanup_orphaned_store_files(tmp_path, {active_id})

    assert result.removed == 3
    assert result.failed == 0
    for kind in STORE_KINDS:
        assert (tmp_path / f"backup_checkup.{active_id}.{kind}").exists()
        assert not (tmp_path / f"backup_checkup.{orphan_id}.{kind}").exists()
    assert foreign.exists()
    assert malformed.exists()


def test_exact_entry_cleanup_removes_all_three_stores(tmp_path) -> None:
    """Deleting a config entry removes every BackupCheckup private store."""
    entry_id = "ENTRY123"
    for kind in STORE_KINDS:
        (tmp_path / f"backup_checkup.{entry_id}.{kind}").write_text(kind)

    result = cleanup_entry_store_files(tmp_path, entry_id)

    assert result.removed == 3
    assert result.failed == 0
    assert not any(tmp_path.iterdir())


def test_exact_entry_cleanup_rejects_unsafe_entry_id(tmp_path) -> None:
    """An entry ID cannot escape the Home Assistant storage directory."""
    outside = tmp_path.parent / "backup_checkup.escape.history"
    outside.write_text("keep")

    result = cleanup_entry_store_files(tmp_path, "../escape")

    assert result.removed == 0
    assert result.failed == 1
    assert outside.exists()
