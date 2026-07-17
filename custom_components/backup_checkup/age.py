"""Backup age helpers shared by coordinator and entity tests."""

from __future__ import annotations

from datetime import datetime
from math import floor


def precise_age_days(now: datetime, value: datetime | None) -> float | None:
    """Return the non-negative precise age in days."""
    if value is None:
        return None
    return max(0.0, (now - value).total_seconds() / 86400)


def completed_age_days(value: float | None) -> int | None:
    """Return only fully completed 24-hour periods."""
    if value is None:
        return None
    return max(0, floor(value))
