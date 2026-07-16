"""Adversarial archive tests for BackupCheckup integrity verification."""

from __future__ import annotations

import io
import json
import sqlite3
import tarfile
import time
from pathlib import Path
from typing import Any

import pytest

from custom_components.backup_checkup.const import (
    INTEGRITY_DATABASE_NOT_APPLICABLE,
    INTEGRITY_DATABASE_PASSED,
)
from custom_components.backup_checkup.integrity import BackupIntegrityVerifier
from custom_components.backup_checkup.security import VerificationBudget


def _tar_bytes(members: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, payload in members:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def _metadata_bytes(
    *,
    homeassistant: dict[str, Any] | None = None,
    addons: list[dict[str, Any]] | None = None,
    folders: list[str] | None = None,
) -> bytes:
    payload: dict[str, Any] = {
        "protected": False,
        "addons": addons or [],
        "folders": folders or [],
    }
    if homeassistant is not None:
        payload["homeassistant"] = homeassistant
    return json.dumps(payload).encode()


def _write_outer(path: Path, members: list[tuple[str, bytes]]) -> None:
    path.write_bytes(_tar_bytes(members))


def _budget() -> VerificationBudget:
    return VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=100_000_000,
        max_expanded_bytes=100_000_000,
        max_members=10_000,
    )


def _verify(
    backup: Path,
    work: Path,
    *,
    database_check: bool = False,
) -> dict[str, Any]:
    work.mkdir(exist_ok=True)
    return BackupIntegrityVerifier._verify_archive(
        backup,
        work,
        None,
        False,
        database_check,
        1,
        _budget(),
    )


def test_duplicate_backup_metadata_is_rejected(tmp_path: Path) -> None:
    """A TAR cannot select a more favorable duplicate backup.json."""
    inner = _tar_bytes([("data/file", b"ok")])
    metadata = _metadata_bytes(homeassistant={"version": "2026.7"})
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            ("backup.json", metadata),
            ("backup.json", metadata),
            ("homeassistant.tar", inner),
        ],
    )

    with pytest.raises(KeyError, match="backup_metadata_duplicate"):
        _verify(backup, tmp_path / "work")


def test_nested_backup_metadata_is_rejected(tmp_path: Path) -> None:
    """Only the canonical root backup.json is accepted."""
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "nested/backup.json",
                _metadata_bytes(homeassistant={"version": "2026.7"}),
            )
        ],
    )

    with pytest.raises(KeyError, match="backup_metadata_path_invalid"):
        _verify(backup, tmp_path / "work")


def test_duplicate_json_key_is_rejected(tmp_path: Path) -> None:
    """Duplicate security-relevant metadata keys are never accepted."""
    backup = tmp_path / "backup.tar"
    metadata = b'{"protected":false,"protected":true,"addons":[],"folders":[]}'
    _write_outer(backup, [("backup.json", metadata)])

    with pytest.raises(ValueError, match="backup_metadata_duplicate_key"):
        _verify(backup, tmp_path / "work")


def test_duplicate_logical_inner_archive_is_rejected(tmp_path: Path) -> None:
    """Different suffixes cannot hide duplicate logical archives."""
    inner = _tar_bytes([("data/file", b"ok")])
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(homeassistant={"version": "2026.7"}),
            ),
            ("homeassistant.tar", inner),
            ("homeassistant.tgz", inner),
        ],
    )

    with pytest.raises(KeyError, match="inner_archive_duplicate"):
        _verify(backup, tmp_path / "work")


def test_decoy_database_path_is_rejected(tmp_path: Path) -> None:
    """A valid-looking decoy cannot mask the canonical database."""
    database = tmp_path / "valid.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE test (value TEXT)")
    connection.commit()
    connection.close()
    inner = _tar_bytes(
        [
            ("decoy/home-assistant_v2.db", database.read_bytes()),
            ("data/home-assistant_v2.db", b"not a database"),
        ]
    )
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(
                    homeassistant={
                        "version": "2026.7",
                        "exclude_database": False,
                    }
                ),
            ),
            ("homeassistant.tar", inner),
        ],
    )

    with pytest.raises(KeyError, match="database_path_invalid"):
        _verify(backup, tmp_path / "work", database_check=True)


def test_app_only_backup_database_is_not_applicable(tmp_path: Path) -> None:
    """An app-only backup does not receive a false missing-database warning."""
    inner = _tar_bytes([("data/options.json", b"{}")])
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(addons=[{"slug": "example_addon"}]),
            ),
            ("example_addon.tar", inner),
        ],
    )

    result = _verify(backup, tmp_path / "work", database_check=True)

    assert result["database_status"] == INTEGRITY_DATABASE_NOT_APPLICABLE
    assert "database_not_found" not in result["warnings"]


def test_canonical_database_is_checked(tmp_path: Path) -> None:
    """The one canonical database is copied and checked successfully."""
    database = tmp_path / "valid.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE test (value TEXT)")
    connection.commit()
    connection.close()
    inner = _tar_bytes([("data/home-assistant_v2.db", database.read_bytes())])
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(
                    homeassistant={
                        "version": "2026.7",
                        "exclude_database": False,
                    }
                ),
            ),
            ("homeassistant.tar", inner),
        ],
    )

    result = _verify(backup, tmp_path / "work", database_check=True)

    assert result["database_status"] == INTEGRITY_DATABASE_PASSED
    assert result["warnings"] == []


def test_unexpected_inner_archive_is_reported(tmp_path: Path) -> None:
    """Undeclared archives are read but surfaced as a bounded warning."""
    declared = _tar_bytes([("data/file", b"ok")])
    unexpected = _tar_bytes([("data/other", b"ok")])
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(homeassistant={"exclude_database": True}),
            ),
            ("homeassistant.tar", declared),
            ("unexpected.tar", unexpected),
        ],
    )

    result = _verify(backup, tmp_path / "work")

    assert result["warnings"] == ["unexpected_inner_archives_1"]


def test_archive_identifier_collision_is_rejected(tmp_path: Path) -> None:
    """An add-on and folder cannot claim the same logical inner archive."""
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(
                    addons=[{"slug": "shared"}],
                    folders=["shared"],
                ),
            )
        ],
    )

    with pytest.raises(KeyError, match="backup_metadata_archive_name_collision"):
        _verify(backup, tmp_path / "work")


def test_invalid_database_exclusion_flag_is_rejected(tmp_path: Path) -> None:
    """Database-presence metadata must use a real boolean value."""
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(homeassistant={"exclude_database": "false"}),
            )
        ],
    )

    with pytest.raises(KeyError, match="backup_metadata_database_flag_invalid"):
        _verify(backup, tmp_path / "work")


def test_control_characters_in_archive_identifier_are_rejected(tmp_path: Path) -> None:
    """Metadata cannot introduce control characters into logical archive names."""
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(addons=[{"slug": "unsafe\nname"}]),
            )
        ],
    )

    with pytest.raises(KeyError, match="backup_metadata_addons_invalid"):
        _verify(backup, tmp_path / "work")


def test_corrupt_canonical_database_fails_integrity_check(tmp_path: Path) -> None:
    """A corrupt canonical database is never reported as passing."""
    inner = _tar_bytes([("data/home-assistant_v2.db", b"not a sqlite database")])
    backup = tmp_path / "backup.tar"
    _write_outer(
        backup,
        [
            (
                "backup.json",
                _metadata_bytes(homeassistant={"exclude_database": False}),
            ),
            ("homeassistant.tar", inner),
        ],
    )

    result = _verify(backup, tmp_path / "work", database_check=True)

    assert result["database_status"] == "failed"
