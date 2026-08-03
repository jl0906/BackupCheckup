"""Recovery-readiness assessment for BackupCheckup."""

from __future__ import annotations

from dataclasses import dataclass

from .const import (
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord

RECOVERY_STATUS_READY = "ready"
RECOVERY_STATUS_LIMITED = "limited"
RECOVERY_STATUS_INSUFFICIENT = "insufficient"
RECOVERY_STATUS_UNKNOWN = "unknown"
RECOVERY_STATUS_OPTIONS = (
    RECOVERY_STATUS_READY,
    RECOVERY_STATUS_LIMITED,
    RECOVERY_STATUS_INSUFFICIENT,
    RECOVERY_STATUS_UNKNOWN,
)

RECOVERY_RECOMMENDATION_VERIFY = "verify_latest_backup"
RECOVERY_RECOMMENDATION_EXTERNAL_COPY = "create_external_copy"
RECOVERY_RECOMMENDATION_COMPLETE_BACKUP = "create_complete_backup"
RECOVERY_RECOMMENDATION_DATABASE = "enable_database_check"
RECOVERY_RECOMMENDATION_NONE = "none"
RECOVERY_RECOMMENDATION_OPTIONS = (
    RECOVERY_RECOMMENDATION_NONE,
    RECOVERY_RECOMMENDATION_VERIFY,
    RECOVERY_RECOMMENDATION_EXTERNAL_COPY,
    RECOVERY_RECOMMENDATION_COMPLETE_BACKUP,
    RECOVERY_RECOMMENDATION_DATABASE,
)


@dataclass(frozen=True, slots=True)
class RecoveryReadiness:
    """Privacy-safe recovery-readiness result."""

    score: int
    status: str
    recommendation: str
    deductions: dict[str, int]
    checks: dict[str, bool | None]


def _status(score: int, has_backup: bool) -> str:
    if not has_backup:
        return RECOVERY_STATUS_INSUFFICIENT
    if score >= 85:
        return RECOVERY_STATUS_READY
    if score >= 55:
        return RECOVERY_STATUS_LIMITED
    return RECOVERY_STATUS_INSUFFICIENT


def assess_recovery_readiness(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    *,
    backup_stale: bool,
    required_locations: int,
    database_check_enabled: bool,
) -> RecoveryReadiness:
    """Assess whether the latest backup is suitable for disaster recovery."""
    applies_to_latest = bool(latest and integrity.backup_id == latest.backup_id)
    verified = applies_to_latest and integrity.status in {
        INTEGRITY_STATUS_VALID,
        INTEGRITY_STATUS_VALID_WITH_WARNINGS,
    }
    database_verified = bool(
        verified and integrity.database_status == INTEGRITY_DATABASE_PASSED
    )
    checks: dict[str, bool | None] = {
        "backup_available": latest is not None,
        "backup_current": None if latest is None else not backup_stale,
        "backup_complete": None if latest is None else not latest.incomplete,
        "homeassistant_included": (
            None if latest is None else latest.homeassistant_included
        ),
        "database_included": None if latest is None else latest.database_included,
        "integrity_verified": verified,
        "database_verified": database_verified if database_check_enabled else None,
        "independent_copy": (
            None if latest is None else len(latest.agents) >= max(2, required_locations)
        ),
        "copy_sizes_consistent": (
            None if latest is None else not latest.copy_size_mismatch
        ),
    }

    weights = {
        "backup_available": 20,
        "backup_current": 15,
        "backup_complete": 15,
        "homeassistant_included": 10,
        "database_included": 5,
        "integrity_verified": 15,
        "database_verified": 5,
        "independent_copy": 10,
        "copy_sizes_consistent": 5,
    }
    if latest is None:
        deductions = {"backup_available": 100}
        score = 0
    else:
        deductions = {
            key: weight
            for key, weight in weights.items()
            if checks[key] is False
        }
        # Unknown optional metadata should not claim readiness, but is penalized less
        # than a confirmed missing component.
        for key in ("homeassistant_included", "database_included"):
            if checks[key] is None:
                deductions[key] = weights[key] // 2
        score = max(0, 100 - sum(deductions.values()))
    recommendation = RECOVERY_RECOMMENDATION_NONE
    if latest is None or latest.incomplete:
        recommendation = RECOVERY_RECOMMENDATION_COMPLETE_BACKUP
    elif not verified:
        recommendation = RECOVERY_RECOMMENDATION_VERIFY
    elif not checks["independent_copy"]:
        recommendation = RECOVERY_RECOMMENDATION_EXTERNAL_COPY
    elif database_check_enabled and not database_verified:
        recommendation = RECOVERY_RECOMMENDATION_DATABASE

    return RecoveryReadiness(
        score=score,
        status=_status(score, latest is not None),
        recommendation=recommendation,
        deductions=deductions,
        checks=checks,
    )
