"""Private guided recovery-preparedness checklist and dependency inventory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models import BackupAgentSummary, BackupRecord
from .recovery_inventory import (
    STORAGE_CLASS_CLOUD,
    STORAGE_CLASS_LOCAL_NETWORK,
    STORAGE_CLASS_REMOTE,
    classify_storage,
)

_STORAGE_VERSION = 1
DEFAULT_REVIEW_INTERVAL_DAYS = 180

SECTION_CHECKLIST = "checklist"
SECTION_DEPENDENCIES = "dependencies"
SECTION_OPTIONS = (SECTION_CHECKLIST, SECTION_DEPENDENCIES)

CHECK_STATUS_UNKNOWN = "unknown"
CHECK_STATUS_CONFIRMED = "confirmed"
CHECK_STATUS_MISSING = "missing"
CHECK_STATUS_NOT_REQUIRED = "not_required"
CHECK_STATUS_OPTIONS = (
    CHECK_STATUS_UNKNOWN,
    CHECK_STATUS_CONFIRMED,
    CHECK_STATUS_MISSING,
    CHECK_STATUS_NOT_REQUIRED,
)

DEPENDENCY_STATUS_UNKNOWN = "unknown"
DEPENDENCY_STATUS_PROTECTED = "protected"
DEPENDENCY_STATUS_UNPROTECTED = "unprotected"
DEPENDENCY_STATUS_NOT_APPLICABLE = "not_applicable"
DEPENDENCY_STATUS_OPTIONS = (
    DEPENDENCY_STATUS_UNKNOWN,
    DEPENDENCY_STATUS_PROTECTED,
    DEPENDENCY_STATUS_UNPROTECTED,
    DEPENDENCY_STATUS_NOT_APPLICABLE,
)

CHECKLIST_KEYS = (
    "backup_password_available",
    "storage_access_documented",
    "restore_method_known",
    "replacement_hardware_available",
    "network_access_documented",
    "recovery_contacts_documented",
)

DEPENDENCY_KEYS = (
    "external_database",
    "mqtt",
    "zigbee",
    "zwave",
    "thread",
    "esphome",
    "network_storage",
    "reverse_proxy",
    "certificates",
    "cloud_services",
)


def detect_recovery_dependencies(
    hass: HomeAssistant,
    latest: BackupRecord | None,
    summaries: tuple[BackupAgentSummary, ...],
) -> set[str]:
    """Infer fixed dependency categories without reading integration secrets."""
    detected: set[str] = set()
    try:
        entries = hass.config_entries.async_entries()
    except Exception:  # noqa: BLE001 - Home Assistant registry boundary
        entries = ()
    domains = {str(getattr(entry, "domain", "")) for entry in entries}
    domain_groups = {
        "mqtt": {"mqtt"},
        "zigbee": {"zha", "deconz"},
        "zwave": {"zwave_js"},
        "thread": {"thread", "matter"},
        "esphome": {"esphome"},
    }
    for dependency, candidates in domain_groups.items():
        if domains & candidates:
            detected.add(dependency)
    if latest is not None and latest.database_included is False:
        detected.add("external_database")
    if latest is not None:
        names = {summary.agent_id: summary.storage_name for summary in summaries}
        storage_classes = {
            classify_storage(copy.agent_id, names.get(copy.agent_id))
            for copy in latest.agent_copies
        }
        if storage_classes & {
            STORAGE_CLASS_LOCAL_NETWORK,
            STORAGE_CLASS_REMOTE,
            STORAGE_CLASS_CLOUD,
        }:
            detected.add("network_storage")
    return detected


@dataclass(frozen=True, slots=True)
class PreparednessItem:
    """One fixed, privacy-safe checklist or dependency state."""

    status: str
    updated_at: datetime | None = None

    def effective_status(self, now: datetime, *, review_days: int) -> str:
        """Return unknown when a previous confirmation is older than the review age."""
        if self.status in {CHECK_STATUS_UNKNOWN, DEPENDENCY_STATUS_UNKNOWN}:
            return self.status
        if self.updated_at is None:
            return CHECK_STATUS_UNKNOWN
        if now - self.updated_at > timedelta(days=review_days):
            return CHECK_STATUS_UNKNOWN
        return self.status

    def as_dict(self, now: datetime, *, review_days: int) -> dict[str, Any]:
        """Return a JSON-compatible state without free-form personal information."""
        effective = self.effective_status(now, review_days=review_days)
        return {
            "status": self.status,
            "effective_status": effective,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expired": self.status != CHECK_STATUS_UNKNOWN and effective == CHECK_STATUS_UNKNOWN,
        }


@dataclass(frozen=True, slots=True)
class RecoveryPreparednessSnapshot:
    """Current guided checklist and external-dependency assessment."""

    checklist: dict[str, dict[str, Any]]
    dependencies: dict[str, dict[str, Any]]
    checklist_complete: bool | None
    dependencies_protected: bool | None
    checklist_confirmed_count: int
    checklist_missing_count: int
    checklist_unknown_count: int
    dependency_detected_count: int
    dependency_protected_count: int
    dependency_unprotected_count: int
    dependency_unknown_count: int
    expired_count: int
    review_interval_days: int

    @classmethod
    def empty(cls) -> RecoveryPreparednessSnapshot:
        """Return an unassessed initial snapshot."""
        return cls(
            checklist={},
            dependencies={},
            checklist_complete=None,
            dependencies_protected=None,
            checklist_confirmed_count=0,
            checklist_missing_count=0,
            checklist_unknown_count=len(CHECKLIST_KEYS),
            dependency_detected_count=0,
            dependency_protected_count=0,
            dependency_unprotected_count=0,
            dependency_unknown_count=len(DEPENDENCY_KEYS),
            expired_count=0,
            review_interval_days=DEFAULT_REVIEW_INTERVAL_DAYS,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return privacy-safe state attributes for entities and the frontend."""
        return {
            "checklist": self.checklist,
            "dependencies": self.dependencies,
            "checklist_complete": self.checklist_complete,
            "dependencies_protected": self.dependencies_protected,
            "checklist_confirmed_count": self.checklist_confirmed_count,
            "checklist_missing_count": self.checklist_missing_count,
            "checklist_unknown_count": self.checklist_unknown_count,
            "dependency_detected_count": self.dependency_detected_count,
            "dependency_protected_count": self.dependency_protected_count,
            "dependency_unprotected_count": self.dependency_unprotected_count,
            "dependency_unknown_count": self.dependency_unknown_count,
            "expired_count": self.expired_count,
            "review_interval_days": self.review_interval_days,
        }


class RecoveryPreparednessStore:
    """Persist fixed recovery-preparedness states in a private Home Assistant Store."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        review_interval_days: int = DEFAULT_REVIEW_INTERVAL_DAYS,
    ) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.recovery",
            private=True,
            atomic_writes=True,
        )
        self._review_interval_days = max(30, min(int(review_interval_days), 3650))
        self._checklist = {
            key: PreparednessItem(CHECK_STATUS_UNKNOWN) for key in CHECKLIST_KEYS
        }
        self._dependencies = {
            key: PreparednessItem(DEPENDENCY_STATUS_UNKNOWN) for key in DEPENDENCY_KEYS
        }

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return dt_util.as_utc(parsed)

    @classmethod
    def _load_items(
        cls,
        raw: Any,
        *,
        keys: tuple[str, ...],
        allowed: tuple[str, ...],
    ) -> dict[str, PreparednessItem]:
        source = raw if isinstance(raw, dict) else {}
        result: dict[str, PreparednessItem] = {}
        for key in keys:
            item = source.get(key)
            if not isinstance(item, dict):
                result[key] = PreparednessItem(allowed[0])
                continue
            status = item.get("status")
            result[key] = PreparednessItem(
                status if status in allowed else allowed[0],
                cls._parse_datetime(item.get("updated_at")),
            )
        return result

    async def async_load(self) -> None:
        """Load bounded enum-only state and discard malformed values."""
        try:
            stored = await self._store.async_load()
        except Exception:  # noqa: BLE001 - corrupted/private Store boundary
            stored = None
        root = stored if isinstance(stored, dict) else {}
        self._checklist = self._load_items(
            root.get(SECTION_CHECKLIST),
            keys=CHECKLIST_KEYS,
            allowed=CHECK_STATUS_OPTIONS,
        )
        self._dependencies = self._load_items(
            root.get(SECTION_DEPENDENCIES),
            keys=DEPENDENCY_KEYS,
            allowed=DEPENDENCY_STATUS_OPTIONS,
        )

    def _serialize(self) -> dict[str, Any]:
        def serialize(items: dict[str, PreparednessItem]) -> dict[str, Any]:
            return {
                key: {
                    "status": item.status,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
                for key, item in items.items()
            }

        return {
            SECTION_CHECKLIST: serialize(self._checklist),
            SECTION_DEPENDENCIES: serialize(self._dependencies),
        }

    async def async_set_item(
        self,
        section: str,
        key: str,
        status: str,
        *,
        now: datetime | None = None,
    ) -> None:
        """Update one fixed state after strict section/key/status validation."""
        if section == SECTION_CHECKLIST:
            target = self._checklist
            allowed_keys = CHECKLIST_KEYS
            allowed_statuses = CHECK_STATUS_OPTIONS
        elif section == SECTION_DEPENDENCIES:
            target = self._dependencies
            allowed_keys = DEPENDENCY_KEYS
            allowed_statuses = DEPENDENCY_STATUS_OPTIONS
        else:
            raise ValueError("unsupported preparedness section")
        if key not in allowed_keys:
            raise ValueError("unsupported preparedness item")
        if status not in allowed_statuses:
            raise ValueError("unsupported preparedness status")
        timestamp = dt_util.as_utc(now or dt_util.utcnow())
        target[key] = PreparednessItem(status, timestamp)
        await self._store.async_save(self._serialize())

    async def async_reset(self) -> None:
        """Reset all guided states without leaving stale free-form data."""
        self._checklist = {
            key: PreparednessItem(CHECK_STATUS_UNKNOWN) for key in CHECKLIST_KEYS
        }
        self._dependencies = {
            key: PreparednessItem(DEPENDENCY_STATUS_UNKNOWN) for key in DEPENDENCY_KEYS
        }
        await self._store.async_save(self._serialize())

    async def async_remove(self) -> None:
        """Remove the private recovery-preparedness store."""
        await self._store.async_remove()

    def snapshot(
        self,
        *,
        now: datetime | None = None,
        detected_dependencies: set[str] | frozenset[str] = frozenset(),
    ) -> RecoveryPreparednessSnapshot:
        """Build the current effective checklist and dependency result."""
        current = dt_util.as_utc(now or dt_util.utcnow())
        checklist: dict[str, dict[str, Any]] = {}
        checklist_effective: list[str] = []
        expired = 0
        for key, item in self._checklist.items():
            serialized = item.as_dict(current, review_days=self._review_interval_days)
            checklist[key] = serialized
            checklist_effective.append(serialized["effective_status"])
            expired += int(serialized["expired"])

        configured_checklist = any(status != CHECK_STATUS_UNKNOWN for status in checklist_effective)
        checklist_complete: bool | None
        if not configured_checklist:
            checklist_complete = None
        else:
            checklist_complete = all(
                status in {CHECK_STATUS_CONFIRMED, CHECK_STATUS_NOT_REQUIRED}
                for status in checklist_effective
            )

        dependencies: dict[str, dict[str, Any]] = {}
        dependency_effective: list[str] = []
        detected_count = 0
        for key, item in self._dependencies.items():
            serialized = item.as_dict(current, review_days=self._review_interval_days)
            detected = key in detected_dependencies
            serialized["detected"] = detected
            dependencies[key] = serialized
            expired += int(serialized["expired"])
            dependency_effective.append(serialized["effective_status"])
            detected_count += int(detected)

        configured_dependencies = any(
            status != DEPENDENCY_STATUS_UNKNOWN for status in dependency_effective
        )
        if not detected_count and not configured_dependencies:
            dependencies_protected: bool | None = None
        else:
            dependencies_protected = all(
                status in {
                    DEPENDENCY_STATUS_PROTECTED,
                    DEPENDENCY_STATUS_NOT_APPLICABLE,
                }
                for status in dependency_effective
            )

        return RecoveryPreparednessSnapshot(
            checklist=checklist,
            dependencies=dependencies,
            checklist_complete=checklist_complete,
            dependencies_protected=dependencies_protected,
            checklist_confirmed_count=checklist_effective.count(CHECK_STATUS_CONFIRMED),
            checklist_missing_count=checklist_effective.count(CHECK_STATUS_MISSING),
            checklist_unknown_count=checklist_effective.count(CHECK_STATUS_UNKNOWN),
            dependency_detected_count=detected_count,
            dependency_protected_count=dependency_effective.count(
                DEPENDENCY_STATUS_PROTECTED
            ),
            dependency_unprotected_count=dependency_effective.count(
                DEPENDENCY_STATUS_UNPROTECTED
            ),
            dependency_unknown_count=dependency_effective.count(
                DEPENDENCY_STATUS_UNKNOWN
            ),
            expired_count=expired,
            review_interval_days=self._review_interval_days,
        )
