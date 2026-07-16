"""Automatic-backup history regression tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from custom_components.backup_checkup.history import BackupCheckupHistory


class _FakeStore:
    """Minimal in-memory Home Assistant Store replacement."""

    def __init__(self, data: Any) -> None:
        self.data = data
        self.delayed_saves = 0

    async def async_load(self) -> Any:
        return self.data

    def async_delay_save(self, _callback: Any, *, delay: int) -> None:
        assert delay == 1
        self.delayed_saves += 1

    async def async_remove(self) -> None:
        self.data = None


class _Hass:
    """Type-only test object."""


def test_running_automatic_backup_is_not_marked_failed() -> None:
    """A native in-progress signal suppresses timestamp-based false failures."""
    history = BackupCheckupHistory(_Hass(), "entry")
    history._store = _FakeStore({})
    attempt = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    now = attempt + timedelta(hours=7)

    metrics = asyncio.run(
        history.async_observe(
            last_attempt=attempt,
            last_success=None,
            now=now,
            window_days=30,
            in_progress=True,
        )
    )

    assert metrics.failed_attempts == 0
    assert history._attempts[0]["status"] == "pending"


def test_finished_stale_attempt_is_marked_failed() -> None:
    """The same stale attempt resolves to failed once no backup is running."""
    history = BackupCheckupHistory(_Hass(), "entry")
    history._store = _FakeStore({})
    attempt = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    now = attempt + timedelta(hours=7)

    metrics = asyncio.run(
        history.async_observe(
            last_attempt=attempt,
            last_success=None,
            now=now,
            window_days=30,
            in_progress=False,
        )
    )

    assert metrics.failed_attempts == 1
    assert history._attempts[0]["status"] == "failed"


def test_corrupt_history_entries_are_sanitized() -> None:
    """Malformed private history entries cannot poison later calculations."""
    history = BackupCheckupHistory(_Hass(), "entry")
    history._store = _FakeStore(
        {
            "tracking_started_at": "not-a-date",
            "attempts": [
                {"attempt_at": "bad", "status": "success"},
                {"attempt_at": "2026-07-16T12:00:00+00:00", "status": "future"},
                42,
                {
                    "attempt_at": "2026-07-16T13:00:00+00:00",
                    "status": "pending",
                    "resolved_at": "bad",
                },
            ],
        }
    )

    asyncio.run(history.async_load())

    assert history._tracking_started_at is None
    assert history._attempts == [
        {"attempt_at": "2026-07-16T13:00:00+00:00", "status": "pending"}
    ]
