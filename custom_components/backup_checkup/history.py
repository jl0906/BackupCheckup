"""Persistent automatic-backup observation history for BackupCheckup."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .repairs import async_set_storage_data_issue
from .security import safe_error_type

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_HISTORY_RETENTION_DAYS = 400
_FAILURE_GRACE_PERIOD = timedelta(hours=6)
_SUCCESS_MATCH_TOLERANCE = timedelta(seconds=60)

_STATUS_PENDING = "pending"
_STATUS_SUCCESS = "success"
_STATUS_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AutomaticHistoryMetrics:
    """Calculated metrics from observed automatic-backup attempts."""

    success_rate: float | None
    resolved_attempts: int
    successful_attempts: int
    failed_attempts: int
    consecutive_failures: int
    tracking_started_at: datetime | None


class BackupCheckupHistory:
    """Store a small privacy-safe history of automatic backup outcomes."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the history store."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.history",
            private=True,
            atomic_writes=True,
        )
        self._loaded = False
        self._tracking_started_at: datetime | None = None
        self._attempts: list[dict[str, str]] = []

    async def async_load(self) -> None:
        """Load persisted history once."""
        if self._loaded:
            return
        try:
            stored = await self._store.async_load()
            if stored is None:
                stored = {}
            if not isinstance(stored, dict):
                raise ValueError("invalid_store_root")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Invalid history store data was reset: error_type=%s",
                safe_error_type(err),
            )
            stored = {}
            async_set_storage_data_issue(self._hass, store_name="history", active=True)
        else:
            async_set_storage_data_issue(self._hass, store_name="history", active=False)
        invalid_content = False
        tracking_raw = stored.get("tracking_started_at")
        self._tracking_started_at = self._parse_datetime(tracking_raw)
        if tracking_raw is not None and self._tracking_started_at is None:
            invalid_content = True

        attempts = stored.get("attempts", [])
        if not isinstance(attempts, list):
            attempts = []
            invalid_content = True
        sanitized_attempts: list[dict[str, str]] = []
        for item in attempts[:5000]:
            if not isinstance(item, dict):
                invalid_content = True
                continue
            attempt_at = item.get("attempt_at")
            status = item.get("status")
            if (
                not isinstance(attempt_at, str)
                or self._parse_datetime(attempt_at) is None
                or status not in {_STATUS_PENDING, _STATUS_SUCCESS, _STATUS_FAILED}
            ):
                invalid_content = True
                continue
            sanitized: dict[str, str] = {
                "attempt_at": attempt_at,
                "status": status,
            }
            resolved_at = item.get("resolved_at")
            if isinstance(resolved_at, str) and self._parse_datetime(resolved_at):
                sanitized["resolved_at"] = resolved_at
            elif resolved_at is not None:
                invalid_content = True
            sanitized_attempts.append(sanitized)
        if len(attempts) > 5000:
            invalid_content = True
        self._attempts = sanitized_attempts
        if invalid_content:
            async_set_storage_data_issue(self._hass, store_name="history", active=True)
        self._loaded = True

    async def async_observe(
        self,
        *,
        last_attempt: datetime | None,
        last_success: datetime | None,
        now: datetime,
        window_days: int,
        in_progress: bool = False,
    ) -> AutomaticHistoryMetrics:
        """Observe the native automatic-backup timestamps and update history."""
        await self.async_load()
        changed = False

        if self._tracking_started_at is None:
            self._tracking_started_at = now
            changed = True

        if last_attempt is not None:
            attempt_iso = dt_util.as_utc(last_attempt).isoformat()
            if not any(item["attempt_at"] == attempt_iso for item in self._attempts):
                self._attempts.append(
                    {"attempt_at": attempt_iso, "status": _STATUS_PENDING}
                )
                changed = True

        self._attempts.sort(key=lambda item: item["attempt_at"])

        if last_success is not None:
            success = dt_util.as_utc(last_success)
            candidates = [
                item
                for item in self._attempts
                if item["status"] in {_STATUS_PENDING, _STATUS_FAILED}
                and (attempt := self._parse_datetime(item["attempt_at"])) is not None
                and attempt <= success + _SUCCESS_MATCH_TOLERANCE
            ]
            if candidates:
                matched = candidates[-1]
                matched["status"] = _STATUS_SUCCESS
                matched["resolved_at"] = success.isoformat()
                changed = True

        attempt_datetimes = [
            (item, self._parse_datetime(item["attempt_at"])) for item in self._attempts
        ]
        for index, (item, attempt) in enumerate(attempt_datetimes):
            if item["status"] != _STATUS_PENDING or attempt is None:
                continue
            has_newer_attempt = any(
                later_attempt is not None and later_attempt > attempt
                for _, later_attempt in attempt_datetimes[index + 1 :]
            )
            if not in_progress and (
                has_newer_attempt or now - attempt > _FAILURE_GRACE_PERIOD
            ):
                item["status"] = _STATUS_FAILED
                item["resolved_at"] = now.isoformat()
                changed = True

        retention_start = now - timedelta(days=_HISTORY_RETENTION_DAYS)
        retained = [
            item
            for item in self._attempts
            if (attempt := self._parse_datetime(item["attempt_at"])) is not None
            and attempt >= retention_start
        ]
        if len(retained) != len(self._attempts):
            self._attempts = retained
            changed = True

        if changed:
            self._store.async_delay_save(self._serialize, delay=1)

        return self.metrics(now=now, window_days=window_days)

    def metrics(self, *, now: datetime, window_days: int) -> AutomaticHistoryMetrics:
        """Return metrics for the selected analysis window."""
        window_start = now - timedelta(days=window_days)
        resolved = [
            item
            for item in self._attempts
            if item["status"] in {_STATUS_SUCCESS, _STATUS_FAILED}
            and (attempt := self._parse_datetime(item["attempt_at"])) is not None
            and attempt >= window_start
        ]
        successes = sum(item["status"] == _STATUS_SUCCESS for item in resolved)
        failures = sum(item["status"] == _STATUS_FAILED for item in resolved)
        success_rate = round((successes / len(resolved)) * 100, 1) if resolved else None

        consecutive_failures = 0
        for item in reversed(self._attempts):
            if item["status"] == _STATUS_PENDING:
                continue
            if item["status"] == _STATUS_FAILED:
                consecutive_failures += 1
                continue
            break

        return AutomaticHistoryMetrics(
            success_rate=success_rate,
            resolved_attempts=len(resolved),
            successful_attempts=successes,
            failed_attempts=failures,
            consecutive_failures=consecutive_failures,
            tracking_started_at=self._tracking_started_at,
        )

    async def async_remove(self) -> None:
        """Remove persisted history."""
        await self._store.async_remove()

    def _serialize(self) -> dict[str, Any]:
        """Serialize the current history."""
        return {
            "tracking_started_at": (
                self._tracking_started_at.isoformat()
                if self._tracking_started_at is not None
                else None
            ),
            "attempts": list(self._attempts),
        }

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse a stored datetime and normalize it to UTC."""
        if not isinstance(value, str):
            return None
        parsed = dt_util.parse_datetime(value)
        return dt_util.as_utc(parsed) if parsed is not None else None
