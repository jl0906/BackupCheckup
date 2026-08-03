"""Non-destructive simulated restore assessment derived from verified backup data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord

SIMULATION_STATUS_PASSED = "passed"
SIMULATION_STATUS_WARNING = "warning"
SIMULATION_STATUS_FAILED = "failed"
SIMULATION_STATUS_NOT_RUN = "not_run"
SIMULATION_STATUS_OPTIONS = (
    SIMULATION_STATUS_PASSED,
    SIMULATION_STATUS_WARNING,
    SIMULATION_STATUS_FAILED,
    SIMULATION_STATUS_NOT_RUN,
)


@dataclass(frozen=True, slots=True)
class RecoverySimulation:
    """Privacy-safe structural restore simulation result."""

    status: str
    checks: dict[str, bool | None]
    blocking_failures: tuple[str, ...]
    warnings: tuple[str, ...]
    backup_reference: str | None
    checked_at: str | None

    @property
    def passed(self) -> bool | None:
        """Return tri-state pass semantics for the readiness score."""
        if self.status in {SIMULATION_STATUS_PASSED, SIMULATION_STATUS_WARNING}:
            return True
        if self.status == SIMULATION_STATUS_FAILED:
            return False
        return None

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible frontend and diagnostic data."""
        return {
            "status": self.status,
            "passed": self.passed,
            "checks": self.checks,
            "blocking_failures": list(self.blocking_failures),
            "warnings": list(self.warnings),
            "backup_reference": self.backup_reference,
            "checked_at": self.checked_at,
            "destructive_actions_performed": False,
        }


def simulate_restore(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    *,
    database_check_enabled: bool,
) -> RecoverySimulation:
    """Assess whether verified metadata and archive structure support a restore."""
    if latest is None:
        checks = {"backup_available": False}
        return RecoverySimulation(
            status=SIMULATION_STATUS_FAILED,
            checks=checks,
            blocking_failures=("backup_available",),
            warnings=(),
            backup_reference=None,
            checked_at=None,
        )

    applies_to_latest = integrity.backup_id == latest.backup_id
    integrity_verified = applies_to_latest and integrity.status in {
        INTEGRITY_STATUS_VALID,
        INTEGRITY_STATUS_VALID_WITH_WARNINGS,
    }
    has_run = integrity.checked_at is not None and applies_to_latest
    checks: dict[str, bool | None] = {
        "backup_available": True,
        "latest_backup_selected": applies_to_latest if integrity.checked_at else None,
        "metadata_readable": bool(latest.backup_reference and latest.date),
        "backup_complete": not latest.incomplete,
        "homeassistant_included": latest.homeassistant_included,
        "database_included": latest.database_included,
        "integrity_verified": integrity_verified if has_run else None,
        "archive_structure_readable": (
            integrity.archive_count > 0 and integrity.file_count > 0
            if integrity_verified
            else None
        ),
        "verified_size_plausible": (
            integrity.verified_size > 0
            if integrity_verified and integrity.verified_size is not None
            else None
        ),
        "database_verified": (
            integrity.database_status == INTEGRITY_DATABASE_PASSED
            if integrity_verified and database_check_enabled
            else None
        ),
        "encrypted_backup_readable": (
            integrity_verified if integrity.protected is True else None
        ),
        "storage_copy_available": bool(latest.agent_copies),
    }
    blocking_keys = (
        "backup_available",
        "latest_backup_selected",
        "metadata_readable",
        "backup_complete",
        "homeassistant_included",
        "integrity_verified",
        "archive_structure_readable",
        "storage_copy_available",
    )
    if database_check_enabled:
        blocking_keys += ("database_verified",)
    blocking = tuple(key for key in blocking_keys if checks.get(key) is False)
    non_applicable = {"encrypted_backup_readable"}
    if not database_check_enabled:
        non_applicable.add("database_verified")
    warnings = tuple(
        key
        for key, value in checks.items()
        if value is None and key not in non_applicable
    )
    if not has_run:
        status = SIMULATION_STATUS_NOT_RUN
    elif blocking:
        status = SIMULATION_STATUS_FAILED
    elif warnings or integrity.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS:
        status = SIMULATION_STATUS_WARNING
    else:
        status = SIMULATION_STATUS_PASSED
    return RecoverySimulation(
        status=status,
        checks=checks,
        blocking_failures=blocking,
        warnings=warnings,
        backup_reference=latest.backup_reference,
        checked_at=integrity.checked_at.isoformat() if integrity.checked_at else None,
    )
