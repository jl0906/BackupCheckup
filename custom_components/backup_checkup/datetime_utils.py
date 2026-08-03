"""Shared helpers for persisted BackupCheckup timestamps."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.util import dt as dt_util


def parse_stored_utc_datetime(value: Any) -> datetime | None:
    """Parse one persisted timestamp and normalize it to aware UTC."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return dt_util.as_utc(parsed)
