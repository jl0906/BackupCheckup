"""Structured live activity logging for BackupCheckup."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from homeassistant.components.logbook import async_log_entry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, NAME
from .security import safe_log_value

_LOGGER = logging.getLogger(__name__)

ACTIVITY_OUTCOME_STARTED: Final = "started"
ACTIVITY_OUTCOME_COMPLETED: Final = "completed"
ACTIVITY_OUTCOME_CHANGED: Final = "changed"
ACTIVITY_OUTCOME_SKIPPED: Final = "skipped"
ACTIVITY_OUTCOME_FAILED: Final = "failed"
ACTIVITY_OUTCOME_CANCELLED: Final = "cancelled"

_ACTIVITY_BUFFER_SIZE = 250
_MAX_DETAIL_ITEMS = 12
_MAX_DETAIL_KEY_LENGTH = 48
_MAX_DETAIL_VALUE_LENGTH = 120


@dataclass(frozen=True, slots=True)
class BackupCheckupActivityRecord:
    """One privacy-safe integration activity record."""

    timestamp: datetime
    action: str
    outcome: str
    details: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation for diagnostics."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "outcome": self.outcome,
            "details": dict(self.details),
        }


class BackupCheckupActivityLog:
    """Publish bounded activity records to logs and Home Assistant Activity."""

    def __init__(self, hass: HomeAssistant, *, enabled: bool = True) -> None:
        """Initialize an optional in-memory activity journal."""
        self._hass = hass
        self._enabled = enabled
        self._records: deque[BackupCheckupActivityRecord] = deque(
            maxlen=_ACTIVITY_BUFFER_SIZE
        )
        self._sequence = 0

    @property
    def enabled(self) -> bool:
        """Return whether expert activity logging is enabled."""
        return self._enabled

    @property
    def count(self) -> int:
        """Return the number of records emitted during this runtime."""
        return self._sequence

    @property
    def latest(self) -> BackupCheckupActivityRecord | None:
        """Return the most recent activity record."""
        return self._records[-1] if self._records else None

    @callback
    def record(
        self,
        action: str,
        outcome: str,
        *,
        level: int = logging.INFO,
        activity_visible: bool = True,
        details: Mapping[str, object] | None = None,
    ) -> BackupCheckupActivityRecord | None:
        """Record one timestamped action when expert logging is enabled."""
        if not self._enabled:
            return None
        record = BackupCheckupActivityRecord(
            timestamp=datetime.now(UTC),
            action=safe_log_value(action, max_length=80),
            outcome=safe_log_value(outcome, max_length=32),
            details=self._safe_details(details),
        )
        self._sequence += 1
        self._records.append(record)
        fields = " ".join(f"{key}={value}" for key, value in record.details)
        suffix = f" {fields}" if fields else ""
        _LOGGER.log(
            level,
            "activity timestamp=%s action=%s outcome=%s%s",
            record.timestamp.isoformat(),
            record.action,
            record.outcome,
            suffix,
        )
        if activity_visible:
            try:
                async_log_entry(
                    self._hass,
                    NAME,
                    self._activity_message(record),
                    DOMAIN,
                )
            except Exception:  # noqa: BLE001 - optional UI publication boundary
                _LOGGER.debug(
                    "Unable to publish BackupCheckup Activity entry",
                    exc_info=True,
                )
        return record

    def diagnostics(self, *, limit: int = 100) -> dict[str, object]:
        """Return bounded recent activity for downloaded diagnostics."""
        bounded_limit = max(0, min(limit, _ACTIVITY_BUFFER_SIZE))
        records = list(self._records)[-bounded_limit:] if bounded_limit else []
        return {
            "enabled": self._enabled,
            "runtime_event_count": self._sequence,
            "buffered_event_count": len(self._records),
            "latest": self.latest.as_dict() if self.latest else None,
            "recent": [record.as_dict() for record in records],
        }

    @staticmethod
    def _safe_details(
        details: Mapping[str, object] | None,
    ) -> tuple[tuple[str, str], ...]:
        """Normalize detail fields to a deterministic bounded tuple."""
        if not details:
            return ()
        normalized: list[tuple[str, str]] = []
        used_keys: set[str] = set()
        for raw_key, raw_value in sorted(
            details.items(), key=lambda item: str(item[0])
        ):
            if len(normalized) >= _MAX_DETAIL_ITEMS:
                break
            base_key = BackupCheckupActivityLog._safe_detail_key(raw_key)
            key = base_key
            suffix_number = 2
            while key in used_keys:
                suffix = f"_{suffix_number}"
                key = f"{base_key[: _MAX_DETAIL_KEY_LENGTH - len(suffix)]}{suffix}"
                suffix_number += 1
            used_keys.add(key)
            value = safe_log_value(raw_value, max_length=_MAX_DETAIL_VALUE_LENGTH)
            normalized.append((key, value))
        return tuple(normalized)

    @staticmethod
    def _safe_detail_key(value: object) -> str:
        """Return one structured-log-safe detail key."""
        cleaned = safe_log_value(value, max_length=_MAX_DETAIL_KEY_LENGTH)
        normalized = "".join(
            character if character.isalnum() or character == "_" else "_"
            for character in cleaned
        ).strip("_")
        return normalized or "detail"

    @staticmethod
    def _activity_message(record: BackupCheckupActivityRecord) -> str:
        """Build the concise message displayed in Home Assistant Activity."""
        summary = f"{record.action}: {record.outcome}"
        if not record.details:
            return summary
        details = ", ".join(f"{key}={value}" for key, value in record.details)
        return f"{summary} ({details})"
