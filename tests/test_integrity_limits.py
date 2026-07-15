"""Archive-limit tests for BackupCheckup integrity verification."""

from __future__ import annotations

import io
import json
import tarfile
import time
from pathlib import Path

import pytest

from custom_components.backup_checkup.integrity import BackupIntegrityVerifier
from custom_components.backup_checkup.security import (
    VerificationBudget,
    VerificationLimitError,
)


def _write_inner(path: Path, *, member_name: str = "data/file.bin") -> None:
    payload = b"x" * 1024
    with tarfile.open(path, "w") as archive:
        member = tarfile.TarInfo(member_name)
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))


def _write_outer(path: Path, inner_path: Path) -> None:
    metadata = json.dumps(
        {
            "protected": False,
            "homeassistant": {"version": "2026.7", "exclude_database": True},
            "addons": [],
            "folders": [],
        }
    ).encode()
    inner = inner_path.read_bytes()
    with tarfile.open(path, "w") as archive:
        metadata_member = tarfile.TarInfo("backup.json")
        metadata_member.size = len(metadata)
        archive.addfile(metadata_member, io.BytesIO(metadata))
        inner_member = tarfile.TarInfo("homeassistant.tar")
        inner_member.size = len(inner)
        archive.addfile(inner_member, io.BytesIO(inner))


def test_expanded_archive_limit(tmp_path: Path) -> None:
    """A declared expanded member beyond the budget aborts verification."""
    inner = tmp_path / "inner.tar"
    outer = tmp_path / "backup.tar"
    _write_inner(inner)
    _write_outer(outer, inner)
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=1_000_000,
        max_expanded_bytes=100,
        max_members=100,
    )

    with pytest.raises(VerificationLimitError, match="expanded_size_limit"):
        BackupIntegrityVerifier._verify_archive(
            outer,
            tmp_path,
            None,
            False,
            False,
            1,
            budget,
        )


def test_unsafe_inner_member_path_is_rejected(tmp_path: Path) -> None:
    """Traversal paths are rejected even though no archive is extracted directly."""
    inner = tmp_path / "inner.tar"
    outer = tmp_path / "backup.tar"
    _write_inner(inner, member_name="../outside")
    _write_outer(outer, inner)
    budget = VerificationBudget.from_options(
        max_download_gb=1,
        max_expanded_gb=1,
        timeout_minutes=1,
    )

    with pytest.raises(tarfile.ReadError, match="unsafe_archive_member_path"):
        BackupIntegrityVerifier._verify_archive(
            outer,
            tmp_path,
            None,
            False,
            False,
            1,
            budget,
        )


def test_metadata_size_limit(tmp_path: Path) -> None:
    """Oversized backup.json is rejected before JSON parsing."""
    inner = tmp_path / "inner.tar"
    outer = tmp_path / "backup.tar"
    _write_inner(inner)
    _write_outer(outer, inner)
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=1_000_000,
        max_expanded_bytes=1_000_000,
        max_members=100,
        max_metadata_bytes=10,
    )

    with pytest.raises(VerificationLimitError, match="metadata_size_limit"):
        BackupIntegrityVerifier._verify_archive(
            outer,
            tmp_path,
            None,
            False,
            False,
            1,
            budget,
        )


def test_archive_member_limit(tmp_path: Path) -> None:
    """The streamed second pass enforces the combined archive-member budget."""
    inner = tmp_path / "inner.tar"
    outer = tmp_path / "backup.tar"
    _write_inner(inner)
    _write_outer(outer, inner)
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=1_000_000,
        max_expanded_bytes=1_000_000,
        max_members=1,
    )

    with pytest.raises(VerificationLimitError, match="archive_member_limit"):
        BackupIntegrityVerifier._verify_archive(
            outer,
            tmp_path,
            None,
            False,
            False,
            1,
            budget,
        )
