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


class _ClosableStream:
    """Async iterator that records explicit closure."""

    def __init__(self) -> None:
        self._chunks = iter((b"abc", b"def"))
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._chunks)
        except StopIteration as err:
            raise StopAsyncIteration from err

    async def aclose(self) -> None:
        self.closed = True


class _ClosableAgent:
    """Return a stream whose lifecycle can be asserted."""

    def __init__(self, stream: _ClosableStream) -> None:
        self.stream = stream

    async def async_download_backup(self, _backup_id: str) -> _ClosableStream:
        return self.stream


def test_download_stream_is_explicitly_closed(tmp_path: Path) -> None:
    """Foreign agent streams are closed after a successful download."""
    verifier = BackupIntegrityVerifier(_TestHass(), "entry")
    stream = _ClosableStream()
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=100,
        max_expanded_bytes=100,
    )

    size, _digest = asyncio.run(
        verifier._async_download(
            _ClosableAgent(stream),
            "backup-id",
            tmp_path / "backup.tar",
            budget,
        )
    )

    assert size == 6
    assert stream.closed is True


def test_download_size_is_per_copy_even_after_previous_attempt(tmp_path: Path) -> None:
    """Fallback-copy size reporting excludes bytes from failed earlier attempts."""
    verifier = BackupIntegrityVerifier(_TestHass(), "entry")
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=100,
        max_expanded_bytes=100,
        downloaded_bytes=11,
    )

    size, _digest = asyncio.run(
        verifier._async_download(
            _ChunkAgent(),
            "backup-id",
            tmp_path / "backup.tar",
            budget,
        )
    )

    assert size == 8
    assert budget.downloaded_bytes == 19
