"""Tests for user-facing completed-day backup ages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.backup_checkup.age import completed_age_days, precise_age_days


def test_completed_age_boundaries() -> None:
    """Visible ages advance only after a complete 24-hour period."""
    assert completed_age_days(0.0) == 0
    assert completed_age_days(23.999 / 24) == 0
    assert completed_age_days(0.999999) == 0
    assert completed_age_days(1.0) == 1
    assert completed_age_days(1.999999) == 1
    assert completed_age_days(2.0) == 2
    assert completed_age_days(None) is None


def test_precise_age_is_kept_for_diagnostics() -> None:
    """Precise age remains available without leaking into the visible state."""
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    backup = now - timedelta(hours=26, minutes=30)

    precise = precise_age_days(now, backup)

    assert precise is not None
    assert round(precise, 6) == round(26.5 / 24, 6)
    assert completed_age_days(precise) == 1


def test_future_timestamp_is_clamped_to_zero() -> None:
    """Minor clock skew never creates a negative backup age."""
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    future = now + timedelta(minutes=5)

    assert precise_age_days(now, future) == 0.0
    assert completed_age_days(precise_age_days(now, future)) == 0
