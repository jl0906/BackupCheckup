"""Structured live activity logging for BackupCheckup."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from homeassistant.components.logbook import async_log_entry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN, NAME
from .security import safe_error_type, safe_log_value

_LOGGER = logging.getLogger(__name__)

ACTIVITY_OUTCOME_STARTED: Final = "started"
ACTIVITY_OUTCOME_COMPLETED: Final = "completed"
ACTIVITY_OUTCOME_CHANGED: Final = "changed"
ACTIVITY_OUTCOME_SKIPPED: Final = "skipped"
ACTIVITY_OUTCOME_FAILED: Final = "failed"
ACTIVITY_OUTCOME_CANCELLED: Final = "cancelled"

_ACTIVITY_BUFFER_SIZE = 250
_STORAGE_VERSION = 1
_MAX_DETAIL_ITEMS = 12
_MAX_DETAIL_KEY_LENGTH = 48
_MAX_DETAIL_VALUE_LENGTH = 120
_PRIVATE_DETAIL_KEYS = frozenset(
    {
        "agent_id",
        "backup_id",
        "backup_name",
        "backup_reference",
        "entity_id",
        "file_name",
        "password",
        "path",
        "storage_name",
        "target",
    }
)


@dataclass(frozen=True, slots=True)
class BackupCheckupActivityRecord:
    """One privacy-safe integration activity record."""

    timestamp: datetime
    action: str
    outcome: str
    level: str
    details: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation for diagnostics."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "outcome": self.outcome,
            "level": self.level,
            "details": dict(self.details),
        }


class BackupCheckupActivityLog:
    """Publish bounded activity records to logs and Home Assistant Activity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str = "runtime",
        *,
        enabled: bool = True,
        persistent: bool = False,
        retention_days: int = 7,
    ) -> None:
        """Initialize an optional in-memory activity journal."""
        self._hass = hass
        self._enabled = enabled
        self._persistent = enabled and persistent
        self._retention_days = max(1, min(retention_days, 30))
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.activity",
            private=True,
            atomic_writes=True,
        )
        self._records: deque[BackupCheckupActivityRecord] = deque(
            maxlen=_ACTIVITY_BUFFER_SIZE
        )
        self._sequence = 0
        self._listeners: set[Callable[[], None]] = set()
        self._save_pending = False
        self._save_task: object | None = None

    @property
    def enabled(self) -> bool:
        """Return whether detailed activity logging is enabled."""
        return self._enabled

    @property
    def count(self) -> int:
        """Return the number of records emitted during this runtime."""
        return self._sequence

    @property
    def persistent(self) -> bool:
        """Return whether the bounded journal survives Home Assistant restarts."""
        return self._persistent

    @property
    def retention_days(self) -> int:
        """Return the active retention period for persistent records."""
        return self._retention_days

    @property
    def latest(self) -> BackupCheckupActivityRecord | None:
        """Return the most recent activity record."""
        return self._records[-1] if self._records else None

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe an entity or frontend bridge to live journal changes."""
        self._listeners.add(listener)

        def _remove() -> None:
            self._listeners.discard(listener)

        return _remove

    def recent(self, *, limit: int = _ACTIVITY_BUFFER_SIZE) -> list[dict[str, object]]:
        """Return the newest bounded records for the live frontend."""
        bounded_limit = max(0, min(limit, _ACTIVITY_BUFFER_SIZE))
        records = list(self._records)[-bounded_limit:] if bounded_limit else []
        return [record.as_dict() for record in records]

    async def async_load(self) -> None:
        """Load and sanitize the optional persistent privacy-safe journal."""
        if not self._persistent:
            return
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001 - private Store boundary
            _LOGGER.warning(
                "Unable to load persistent activity log: error_type=%s",
                safe_error_type(err),
            )
            return
        if not isinstance(stored, Mapping):
            return
        records = stored.get("records")
        if not isinstance(records, list):
            return
        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
        loaded: list[BackupCheckupActivityRecord] = []
        for item in records[-_ACTIVITY_BUFFER_SIZE:]:
            record = self._record_from_stored(item)
            if record is not None and record.timestamp >= cutoff:
                loaded.append(record)
        self._records.extend(loaded)
        stored_sequence = stored.get("sequence")
        self._sequence = (
            stored_sequence
            if isinstance(stored_sequence, int) and stored_sequence >= len(loaded)
            else len(loaded)
        )

    async def async_clear(self) -> None:
        """Clear all buffered and persistent activity records."""
        self._records.clear()
        self._sequence += 1
        self._notify_listeners()
        if self._persistent:
            await self._store.async_save(self._storage_payload())

    async def async_remove(self) -> None:
        """Remove the private persistent activity store."""
        await self._store.async_remove()

    async def async_shutdown(self) -> None:
        """Flush the latest persistent journal before shutdown."""
        if not self._persistent:
            return
        await self._store.async_save(self._storage_payload())

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
        """Record one timestamped action when detailed logging is enabled."""
        if not self._enabled:
            return None
        record = BackupCheckupActivityRecord(
            timestamp=datetime.now(UTC),
            action=safe_log_value(action, max_length=80),
            outcome=safe_log_value(outcome, max_length=32),
            level=logging.getLevelName(level).lower(),
            details=self._safe_details(details),
        )
        self._sequence += 1
        self._records.append(record)
        self._notify_listeners()
        self._schedule_save()
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
            except Exception:
                _LOGGER.debug(
                    "Unable to publish BackupCheckup Activity entry",
                    exc_info=True,
                )
        return record

    def _notify_listeners(self) -> None:
        """Notify live consumers without allowing UI failures to escape."""
        for listener in tuple(self._listeners):
            try:
                listener()
            except Exception:
                _LOGGER.debug("Unable to update live activity view", exc_info=True)

    def _schedule_save(self) -> None:
        """Coalesce persistent Store writes generated by rapid progress events."""
        if not self._persistent:
            return
        self._save_pending = True
        if self._save_task is not None:
            return
        create_task = getattr(self._hass, "async_create_task", None)
        if not callable(create_task):
            return
        self._save_task = create_task(
            self._async_save_pending(),
            name=f"{DOMAIN}_activity_save",
        )

    async def _async_save_pending(self) -> None:
        """Write the newest coalesced activity snapshot."""
        try:
            while self._save_pending:
                self._save_pending = False
                await self._store.async_save(self._storage_payload())
        except Exception as err:  # noqa: BLE001 - private Store boundary
            _LOGGER.warning(
                "Unable to save persistent activity log: error_type=%s",
                safe_error_type(err),
            )
        finally:
            self._save_task = None

    def _storage_payload(self) -> dict[str, object]:
        """Return the bounded private Store payload."""
        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
        records = [record for record in self._records if record.timestamp >= cutoff]
        return {
            "sequence": self._sequence,
            "records": [record.as_dict() for record in records],
        }

    @classmethod
    def _record_from_stored(cls, value: object) -> BackupCheckupActivityRecord | None:
        """Return one validated stored activity record."""
        if not isinstance(value, Mapping):
            return None
        timestamp = value.get("timestamp")
        if not isinstance(timestamp, str):
            return None
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        action = value.get("action")
        outcome = value.get("outcome")
        level = value.get("level")
        details = value.get("details")
        if not all(isinstance(item, str) for item in (action, outcome, level)):
            return None
        return BackupCheckupActivityRecord(
            timestamp=parsed.astimezone(UTC),
            action=safe_log_value(action, max_length=80),
            outcome=safe_log_value(outcome, max_length=32),
            level=safe_log_value(level, max_length=16),
            details=cls._safe_details(
                details if isinstance(details, Mapping) else None
            ),
        )

    def diagnostics(self, *, limit: int = 100) -> dict[str, object]:
        """Return bounded recent activity for downloaded diagnostics."""
        bounded_limit = max(0, min(limit, _ACTIVITY_BUFFER_SIZE))
        return {
            "enabled": self._enabled,
            "persistent": self._persistent,
            "retention_days": self._retention_days,
            "runtime_event_count": self._sequence,
            "buffered_event_count": len(self._records),
            "latest": self.latest.as_dict() if self.latest else None,
            "recent": self.recent(limit=bounded_limit),
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
            if base_key in _PRIVATE_DETAIL_KEYS:
                continue
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
