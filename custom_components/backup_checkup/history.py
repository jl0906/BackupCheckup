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

    async def _async_load_root(self) -> tuple[dict[str, Any], bool]:
        """Load the private store root and report whether it needed resetting."""
        try:
            stored = await self._store.async_load()
            if stored is None:
                return {}, False
            if not isinstance(stored, dict):
                raise ValueError("invalid_store_root")
        except Exception as err:  # noqa: BLE001 - private store boundary
            _LOGGER.warning(
                "Invalid history store data was reset: error_type=%s",
                safe_error_type(err),
            )
            return {}, True
        return stored, False

    @classmethod
    def _sanitize_attempt(cls, item: Any) -> tuple[dict[str, str] | None, bool]:
        """Return one normalized history attempt and whether data was discarded."""
        if not isinstance(item, dict):
            return None, True
        attempt_at = item.get("attempt_at")
        status = item.get("status")
        if (
            not isinstance(attempt_at, str)
            or cls._parse_datetime(attempt_at) is None
            or status not in {_STATUS_PENDING, _STATUS_SUCCESS, _STATUS_FAILED}
        ):
            return None, True

        sanitized = {"attempt_at": attempt_at, "status": status}
        resolved_at = item.get("resolved_at")
        if resolved_at is None:
            return sanitized, False
        if isinstance(resolved_at, str) and cls._parse_datetime(resolved_at):
            sanitized["resolved_at"] = resolved_at
            return sanitized, False
        return sanitized, True

    @classmethod
    def _sanitize_attempts(cls, value: Any) -> tuple[list[dict[str, str]], bool]:
        """Normalize bounded persisted attempt history."""
        if not isinstance(value, list):
            return [], True
        sanitized: list[dict[str, str]] = []
        invalid = len(value) > 5000
        for item in value[:5000]:
            attempt, item_invalid = cls._sanitize_attempt(item)
            invalid = invalid or item_invalid
            if attempt is not None:
                sanitized.append(attempt)
        return sanitized, invalid

    async def async_load(self) -> None:
        """Load persisted history once."""
        if self._loaded:
            return
        stored, invalid_content = await self._async_load_root()
        tracking_raw = stored.get("tracking_started_at")
        self._tracking_started_at = self._parse_datetime(tracking_raw)
        invalid_content = invalid_content or (
            tracking_raw is not None and self._tracking_started_at is None
        )
        self._attempts, attempts_invalid = self._sanitize_attempts(
            stored.get("attempts", [])
        )
        invalid_content = invalid_content or attempts_invalid
        async_set_storage_data_issue(
            self._hass,
            store_name="history",
            active=invalid_content,
        )
        self._loaded = True

    def _ensure_tracking_started(self, now: datetime) -> bool:
        """Initialize the observation start time once."""
        if self._tracking_started_at is not None:
            return False
        self._tracking_started_at = now
        return True

    def _record_attempt(self, last_attempt: datetime | None) -> bool:
        """Append one newly observed automatic-backup attempt."""
        if last_attempt is None:
            return False
        attempt_iso = dt_util.as_utc(last_attempt).isoformat()
        if any(item["attempt_at"] == attempt_iso for item in self._attempts):
            return False
        self._attempts.append({"attempt_at": attempt_iso, "status": _STATUS_PENDING})
        return True

    def _match_success(self, last_success: datetime | None) -> bool:
        """Resolve the newest compatible pending or failed attempt as successful."""
        if last_success is None:
            return False
        success = dt_util.as_utc(last_success)
        candidates = [
            item
            for item in self._attempts
            if item["status"] in {_STATUS_PENDING, _STATUS_FAILED}
            and (attempt := self._parse_datetime(item["attempt_at"])) is not None
            and attempt <= success + _SUCCESS_MATCH_TOLERANCE
        ]
        if not candidates:
            return False
        matched = candidates[-1]
        matched["status"] = _STATUS_SUCCESS
        matched["resolved_at"] = success.isoformat()
        return True

    def _resolve_pending(self, *, now: datetime, in_progress: bool) -> bool:
        """Mark expired pending attempts as failed."""
        changed = False
        dated_attempts = [
            (item, self._parse_datetime(item["attempt_at"])) for item in self._attempts
        ]
        for index, (item, attempt) in enumerate(dated_attempts):
            if item["status"] != _STATUS_PENDING or attempt is None:
                continue
            has_newer_attempt = any(
                later is not None and later > attempt
                for _later_item, later in dated_attempts[index + 1 :]
            )
            expired = has_newer_attempt or now - attempt > _FAILURE_GRACE_PERIOD
            if in_progress or not expired:
                continue
            item["status"] = _STATUS_FAILED
            item["resolved_at"] = now.isoformat()
            changed = True
        return changed

    def _retain_recent(self, now: datetime) -> bool:
        """Drop attempts outside the fixed privacy-safe retention window."""
        retention_start = now - timedelta(days=_HISTORY_RETENTION_DAYS)
        retained = [
            item
            for item in self._attempts
            if (attempt := self._parse_datetime(item["attempt_at"])) is not None
            and attempt >= retention_start
        ]
        if len(retained) == len(self._attempts):
            return False
        self._attempts = retained
        return True

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
        changed = self._ensure_tracking_started(now)
        changed = self._record_attempt(last_attempt) or changed
        self._attempts.sort(key=lambda item: item["attempt_at"])
        changed = self._match_success(last_success) or changed
        changed = self._resolve_pending(now=now, in_progress=in_progress) or changed
        changed = self._retain_recent(now) or changed
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
