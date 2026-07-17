"""Additional automatic-history branch tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from custom_components.backup_checkup.history import BackupCheckupHistory


class FakeStore:
    def __init__(self, data: Any) -> None:
        self.data = data
        self.delayed_saves = 0
        self.removed = False

    async def async_load(self) -> Any:
        if isinstance(self.data, BaseException):
            raise self.data
        return self.data

    def async_delay_save(self, _callback: Any, *, delay: int) -> None:
        assert delay == 1
        self.delayed_saves += 1

    async def async_remove(self) -> None:
        self.removed = True


class Hass:
    pass


def test_load_is_idempotent_and_accepts_empty_store() -> None:
    history = BackupCheckupHistory(Hass(), "entry")
    store = FakeStore(None)
    history._store = store

    asyncio.run(history.async_load())
    asyncio.run(history.async_load())

    assert history._loaded is True
    assert history._attempts == []


def test_invalid_store_root_and_attempt_collection_are_reset() -> None:
    for data in (ValueError("load failed"), [], {"attempts": "not-a-list"}):
        history = BackupCheckupHistory(Hass(), "entry")
        history._store = FakeStore(data)
        asyncio.run(history.async_load())
        assert history._attempts == []
        assert history._loaded is True


def test_valid_resolved_timestamp_and_oversized_history_are_sanitized() -> None:
    attempt = "2026-07-17T02:00:00+00:00"
    history = BackupCheckupHistory(Hass(), "entry")
    history._store = FakeStore(
        {
            "tracking_started_at": attempt,
            "attempts": [
                {
                    "attempt_at": attempt,
                    "status": "success",
                    "resolved_at": "2026-07-17T02:00:30+00:00",
                }
            ]
            * 5001,
        }
    )

    asyncio.run(history.async_load())

    assert len(history._attempts) == 5000
    assert history._attempts[0]["resolved_at"].endswith("+00:00")


def test_existing_attempt_and_unmatched_success_do_not_schedule_save() -> None:
    attempt = datetime(2026, 7, 17, 2, 0, tzinfo=UTC)
    history = BackupCheckupHistory(Hass(), "entry")
    store = FakeStore(
        {
            "tracking_started_at": attempt.isoformat(),
            "attempts": [
                {"attempt_at": attempt.isoformat(), "status": "success"},
            ],
        }
    )
    history._store = store

    metrics = asyncio.run(
        history.async_observe(
            last_attempt=attempt,
            last_success=attempt - timedelta(days=1),
            now=attempt + timedelta(hours=1),
            window_days=30,
        )
    )

    assert store.delayed_saves == 0
    assert metrics.successful_attempts == 1


def test_newer_attempt_resolves_older_pending_attempt_as_failed() -> None:
    first = datetime(2026, 7, 17, 2, 0, tzinfo=UTC)
    second = first + timedelta(hours=1)
    history = BackupCheckupHistory(Hass(), "entry")
    history._store = FakeStore(
        {
            "tracking_started_at": first.isoformat(),
            "attempts": [
                {"attempt_at": first.isoformat(), "status": "pending"},
                {"attempt_at": second.isoformat(), "status": "pending"},
            ],
        }
    )

    asyncio.run(
        history.async_observe(
            last_attempt=second,
            last_success=None,
            now=second + timedelta(minutes=1),
            window_days=30,
            in_progress=False,
        )
    )

    assert history._attempts[0]["status"] == "failed"
    assert history._attempts[1]["status"] == "pending"


def test_retention_metrics_serialization_and_remove() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    old = now - timedelta(days=401)
    recent_failed = now - timedelta(days=2)
    recent_pending = now - timedelta(days=1)
    recent_success = now
    history = BackupCheckupHistory(Hass(), "entry")
    store = FakeStore(
        {
            "tracking_started_at": now.isoformat(),
            "attempts": [
                {"attempt_at": old.isoformat(), "status": "failed"},
                {"attempt_at": recent_success.isoformat(), "status": "success"},
                {"attempt_at": recent_pending.isoformat(), "status": "pending"},
                {"attempt_at": recent_failed.isoformat(), "status": "failed"},
            ],
        }
    )
    history._store = store

    metrics = asyncio.run(
        history.async_observe(
            last_attempt=None,
            last_success=None,
            now=now,
            window_days=30,
            in_progress=True,
        )
    )

    assert all(item["attempt_at"] != old.isoformat() for item in history._attempts)
    assert metrics.resolved_attempts == 2
    assert metrics.successful_attempts == 1
    assert metrics.failed_attempts == 1
    assert metrics.consecutive_failures == 0
    assert store.delayed_saves == 1
    assert history._serialize()["tracking_started_at"] == now.isoformat()

    asyncio.run(history.async_remove())
    assert store.removed is True

    history._tracking_started_at = None
    assert history._serialize()["tracking_started_at"] is None


def test_consecutive_failures_skip_pending_and_count_from_newest() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    history = BackupCheckupHistory(Hass(), "entry")
    history._loaded = True
    history._attempts = [
        {"attempt_at": (now - timedelta(days=3)).isoformat(), "status": "success"},
        {"attempt_at": (now - timedelta(days=2)).isoformat(), "status": "failed"},
        {"attempt_at": (now - timedelta(days=1)).isoformat(), "status": "failed"},
        {"attempt_at": now.isoformat(), "status": "pending"},
    ]

    metrics = history.metrics(now=now, window_days=30)
    assert metrics.consecutive_failures == 2
    assert metrics.success_rate == 33.3
