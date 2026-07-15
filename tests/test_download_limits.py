"""Download-limit tests for BackupCheckup integrity verification."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

import pytest

from custom_components.backup_checkup.integrity import BackupIntegrityVerifier
from custom_components.backup_checkup.security import (
    VerificationBudget,
    VerificationLimitError,
)


class _TestHass:
    """Run executor jobs inline for isolated async unit tests."""

    async def async_add_executor_job(self, target: Any, *args: Any) -> Any:
        return target(*args)


class _ChunkAgent:
    """Return a fixed sequence of backup chunks."""

    async def async_download_backup(self, _backup_id: str):
        async def _stream():
            for chunk in (b"1234", b"5678"):
                yield chunk

        return _stream()


def test_download_limit_closes_private_partial_file(tmp_path: Path) -> None:
    """An oversized stream stops promptly and leaves a closable private partial file."""
    verifier = BackupIntegrityVerifier(_TestHass(), "entry")
    target = tmp_path / "backup.tar"
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=6,
        max_expanded_bytes=100,
    )

    with pytest.raises(VerificationLimitError, match="download_size_limit"):
        asyncio.run(
            verifier._async_download(
                _ChunkAgent(),
                "backup-id",
                target,
                budget,
            )
        )

    assert target.read_bytes() == b"1234"
    if os.name == "posix":
        assert target.stat().st_mode & 0o777 == 0o600
    target.unlink()
