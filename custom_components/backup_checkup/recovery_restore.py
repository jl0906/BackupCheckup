"""Private, enum-only documentation of externally performed restore tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models import BackupRecord

_STORAGE_VERSION = 1
DEFAULT_RESTORE_TEST_VALID_DAYS = 365

RESTORE_TEST_RESULT_SUCCESSFUL = "successful"
RESTORE_TEST_RESULT_FAILED = "failed"
RESTORE_TEST_RESULT_OPTIONS = (
    RESTORE_TEST_RESULT_SUCCESSFUL,
    RESTORE_TEST_RESULT_FAILED,
)

RESTORE_TEST_SCOPE_FULL = "full"
RESTORE_TEST_SCOPE_PARTIAL = "partial"
RESTORE_TEST_SCOPE_OPTIONS = (
    RESTORE_TEST_SCOPE_FULL,
    RESTORE_TEST_SCOPE_PARTIAL,
)


@dataclass(frozen=True, slots=True)
class RestoreTestRecord:
    """One privacy-safe confirmation of a restore performed outside production."""

    tested_at: datetime
    backup_reference: str
    result: str
    scope: str

    def as_dict(self) -> dict[str, Any]:
        """Return bounded JSON-compatible data."""
        return {
            "tested_at": self.tested_at.isoformat(),
            "backup_reference": self.backup_reference,
            "result": self.result,
            "scope": self.scope,
        }


@dataclass(frozen=True, slots=True)
class RestoreTestSnapshot:
    """Effective restore-test state used by the score and frontend."""

    tested_at: datetime | None
    backup_reference: str | None
    result: str | None
    scope: str | None
    age_days: int | None
    valid: bool | None
    passed: bool | None
    expired: bool
    validity_days: int

    @classmethod
    def empty(cls, *, validity_days: int = DEFAULT_RESTORE_TEST_VALID_DAYS) -> RestoreTestSnapshot:
        """Return an unassessed restore-test state."""
        return cls(
            tested_at=None,
            backup_reference=None,
            result=None,
            scope=None,
            age_days=None,
            valid=None,
            passed=None,
            expired=False,
            validity_days=validity_days,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return privacy-safe entity attributes."""
        return {
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
            "backup_reference": self.backup_reference,
            "result": self.result,
            "scope": self.scope,
            "age_days": self.age_days,
            "valid": self.valid,
            "passed": self.passed,
            "expired": self.expired,
            "validity_days": self.validity_days,
        }


class RecoveryRestoreTestStore:
    """Persist the latest documented test restore in a private Home Assistant Store."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        validity_days: int = DEFAULT_RESTORE_TEST_VALID_DAYS,
    ) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.recovery_restore",
            private=True,
            atomic_writes=True,
        )
        self._validity_days = max(30, min(int(validity_days), 3650))
        self._record: RestoreTestRecord | None = None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse a stored timestamp and normalize it to UTC."""
        if not isinstance(value, str):
            return None
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return dt_util.as_utc(parsed)

    @classmethod
    def _parse_record(cls, value: Any) -> RestoreTestRecord | None:
        """Reject malformed or unbounded persisted values."""
        if not isinstance(value, dict):
            return None
        tested_at = cls._parse_datetime(value.get("tested_at"))
        backup_reference = value.get("backup_reference")
        result = value.get("result")
        scope = value.get("scope")
        if (
            tested_at is None
            or not isinstance(backup_reference, str)
            or not backup_reference
            or len(backup_reference) > 128
            or result not in RESTORE_TEST_RESULT_OPTIONS
            or scope not in RESTORE_TEST_SCOPE_OPTIONS
        ):
            return None
        return RestoreTestRecord(
            tested_at=tested_at,
            backup_reference=backup_reference,
            result=result,
            scope=scope,
        )

    async def async_load(self) -> None:
        """Load one valid record and discard corrupted content."""
        try:
            raw = await self._store.async_load()
        except Exception:  # noqa: BLE001 - corrupted private Store boundary
            raw = None
        self._record = self._parse_record(raw)

    async def async_record(
        self,
        latest: BackupRecord | None,
        result: str,
        scope: str,
        *,
        now: datetime | None = None,
    ) -> RestoreTestRecord:
        """Document a restore test against the current latest monitored backup."""
        if latest is None:
            raise ValueError("no backup available")
        if result not in RESTORE_TEST_RESULT_OPTIONS:
            raise ValueError("unsupported restore-test result")
        if scope not in RESTORE_TEST_SCOPE_OPTIONS:
            raise ValueError("unsupported restore-test scope")
        record = RestoreTestRecord(
            tested_at=dt_util.as_utc(now or dt_util.utcnow()),
            backup_reference=latest.backup_reference,
            result=result,
            scope=scope,
        )
        self._record = record
        await self._store.async_save(record.as_dict())
        return record

    async def async_clear(self) -> None:
        """Clear the documented test result while keeping the store initialized."""
        self._record = None
        await self._store.async_save({})

    async def async_remove(self) -> None:
        """Remove the private restore-test store."""
        self._record = None
        await self._store.async_remove()

    def snapshot(self, *, now: datetime | None = None) -> RestoreTestSnapshot:
        """Return the current result with expiry and pass/fail semantics."""
        if self._record is None:
            return RestoreTestSnapshot.empty(validity_days=self._validity_days)
        current = dt_util.as_utc(now or dt_util.utcnow())
        delta = max(timedelta(0), current - self._record.tested_at)
        age_days = delta.days
        expired = delta > timedelta(days=self._validity_days)
        valid = not expired
        passed = (
            self._record.result == RESTORE_TEST_RESULT_SUCCESSFUL
            and self._record.scope == RESTORE_TEST_SCOPE_FULL
            and valid
        )
        return RestoreTestSnapshot(
            tested_at=self._record.tested_at,
            backup_reference=self._record.backup_reference,
            result=self._record.result,
            scope=self._record.scope,
            age_days=age_days,
            valid=valid,
            passed=passed,
            expired=expired,
            validity_days=self._validity_days,
        )
