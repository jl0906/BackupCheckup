"""Regression tests for the audited 2.4 health score and adaptive polling."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup.analytics import calculate_health_score
from custom_components.backup_checkup.const import CONF_ADAPTIVE_POLLING
from custom_components.backup_checkup.coordinator import BackupCheckupCoordinator


def _score(flags: dict[str, bool], **kwargs: object):
    return calculate_health_score(
        flags,
        automatic_success_rate=kwargs.pop("automatic_success_rate", None),
        consecutive_automatic_failures=kwargs.pop("consecutive_automatic_failures", 0),
        resolved_attempts=kwargs.pop("resolved_attempts", 0),
        **kwargs,
    )


def test_health_score_does_not_double_count_correlated_storage_faults() -> None:
    result = _score(
        {
            "storage_error": True,
            "required_location_missing": True,
            "backup_not_redundant": True,
        },
        latest_backup_locations=1,
        minimum_redundant_locations=2,
    )

    assert result.score == 80
    assert result.deductions == {"storage_error": 20}
    assert result.component_deductions["storage"] == 20
    assert set(result.suppressed_deductions) == {
        "required_location_missing",
        "backup_not_redundant",
    }
    assert set(result.raw_deductions) == {
        "storage_error",
        "required_location_missing",
        "backup_not_redundant",
    }


def test_health_score_does_not_triple_count_one_automatic_failure_series() -> None:
    result = _score(
        {
            "automatic_backup_failed": True,
            "automatic_schedule_overdue": True,
        },
        automatic_success_rate=50.0,
        consecutive_automatic_failures=3,
        resolved_attempts=5,
    )

    assert result.score == 80
    assert result.deductions == {"automatic_backup_failed": 20}
    assert result.component_deductions["automation"] == 20
    assert set(result.suppressed_deductions) == {
        "automatic_schedule_overdue",
        "low_automatic_success_rate",
        "consecutive_automatic_failures",
    }


def test_health_score_integrity_and_no_backup_use_strongest_root_cause() -> None:
    integrity = _score(
        {
            "backup_integrity_failed": True,
            "backup_checksum_changed": True,
            "backup_integrity_warning": True,
        }
    )
    assert integrity.score == 40
    assert integrity.deductions == {"backup_integrity_failed": 60}

    empty = _score(
        {
            "no_backup": True,
            "automatic_schedule_missing": True,
            "backup_not_redundant": True,
        }
    )
    assert empty.score == 0
    assert empty.deductions == {"no_backup": 100}
    assert set(empty.suppressed_deductions) == {
        "automatic_schedule_missing",
        "backup_not_redundant",
    }


@pytest.mark.parametrize(
    ("age", "expected"),
    [(4.1, 20), (6.0, 25), (12.0, 35)],
)
def test_health_score_scales_stale_backup_severity(age: float, expected: int) -> None:
    result = _score(
        {"backup_stale": True},
        latest_backup_age_days=age,
        max_age_days=4,
    )
    assert result.deductions == {"backup_stale": expected}
    assert result.score == 100 - expected


def test_health_score_rejects_impossible_history_combinations() -> None:
    result = _score(
        {},
        automatic_success_rate=0.0,
        consecutive_automatic_failures=5,
        resolved_attempts=0,
    )
    assert result.score == 100
    assert result.raw_deductions == {}


@pytest.mark.asyncio
async def test_adaptive_refresh_replays_event_received_during_refresh() -> None:
    hass = SimpleNamespace()
    hass.async_create_task = lambda coroutine, *, name=None: asyncio.create_task(
        coroutine, name=name
    )
    coordinator = BackupCheckupCoordinator(
        hass,
        ConfigEntry(data={CONF_ADAPTIVE_POLLING: True}, version=10),
    )
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def _refresh() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await release.wait()

    coordinator.async_request_refresh = AsyncMock(side_effect=_refresh)
    coordinator._schedule_adaptive_refresh()
    await entered.wait()
    coordinator._schedule_adaptive_refresh()
    release.set()
    task = coordinator._adaptive_refresh_task
    assert task is not None
    await task

    assert calls == 2
    assert coordinator._adaptive_refresh_pending is False
