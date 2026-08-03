"""Recovery-readiness assessment for BackupCheckup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupAgentSummary, BackupIntegrityResult, BackupRecord
from .recovery_inventory import RecoveryInventory, build_recovery_inventory

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
RECOVERY_RECOMMENDATION_REVIEW_CONTENTS = "review_backup_contents"
RECOVERY_RECOMMENDATION_DATABASE = "enable_database_check"
RECOVERY_RECOMMENDATION_NONE = "none"
RECOVERY_RECOMMENDATION_OPTIONS = (
    RECOVERY_RECOMMENDATION_NONE,
    RECOVERY_RECOMMENDATION_VERIFY,
    RECOVERY_RECOMMENDATION_EXTERNAL_COPY,
    RECOVERY_RECOMMENDATION_COMPLETE_BACKUP,
    RECOVERY_RECOMMENDATION_REVIEW_CONTENTS,
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
    content_inventory: dict[str, Any]
    content_comparison: dict[str, Any]
    storage_resilience: dict[str, Any]
    backup_content_changed: bool
    external_copy_missing: bool


def _status(score: int, has_backup: bool) -> str:
    if not has_backup:
        return RECOVERY_STATUS_INSUFFICIENT
    if score >= 85:
        return RECOVERY_STATUS_READY
    if score >= 55:
        return RECOVERY_STATUS_LIMITED
    return RECOVERY_STATUS_INSUFFICIENT


def _checks(
    latest: BackupRecord | None,
    inventory: RecoveryInventory,
    integrity: BackupIntegrityResult,
    *,
    backup_stale: bool,
    database_check_enabled: bool,
) -> dict[str, bool | None]:
    """Return all recovery checks from current inventory and verification state."""
    applies_to_latest = bool(latest and integrity.backup_id == latest.backup_id)
    verified = applies_to_latest and integrity.status in {
        INTEGRITY_STATUS_VALID,
        INTEGRITY_STATUS_VALID_WITH_WARNINGS,
    }
    database_verified = bool(
        verified and integrity.database_status == INTEGRITY_DATABASE_PASSED
    )
    copy_count = inventory.storage.copy_count
    return {
        "backup_available": latest is not None,
        "backup_current": None if latest is None else not backup_stale,
        "backup_complete": None if latest is None else not latest.incomplete,
        "homeassistant_included": (
            None if latest is None else latest.homeassistant_included
        ),
        "database_included": None if latest is None else latest.database_included,
        "integrity_verified": verified,
        "database_verified": database_verified if database_check_enabled else None,
        "independent_copy": inventory.storage.independent_copy,
        "multiple_failure_domains": inventory.storage.multiple_failure_domains,
        "copy_sizes_consistent": (
            None if latest is None or copy_count < 2 else not latest.copy_size_mismatch
        ),
        "content_stable": (
            None
            if latest is None
            or latest.incomplete
            or inventory.comparison.material_regression is None
            else not inventory.comparison.material_regression
        ),
    }


def _deductions(
    latest: BackupRecord | None,
    checks: dict[str, bool | None],
) -> dict[str, int]:
    """Return weighted deductions while treating uncertain metadata conservatively."""
    if latest is None:
        return {"backup_available": 100}
    weights = {
        "backup_available": 20,
        "backup_current": 12,
        "backup_complete": 12,
        "homeassistant_included": 10,
        "database_included": 5,
        "integrity_verified": 15,
        "database_verified": 5,
        "independent_copy": 8,
        "multiple_failure_domains": 4,
        "copy_sizes_consistent": 4,
        "content_stable": 5,
    }
    deductions = {
        key: weight for key, weight in weights.items() if checks[key] is False
    }
    for key in (
        "homeassistant_included",
        "database_included",
        "independent_copy",
        "multiple_failure_domains",
    ):
        if checks[key] is None:
            deductions[key] = max(1, weights[key] // 2)
    return deductions


def _recommendation(
    latest: BackupRecord | None,
    checks: dict[str, bool | None],
    inventory: RecoveryInventory,
    *,
    database_check_enabled: bool,
) -> str:
    """Return one highest-priority recovery action."""
    if latest is None or latest.incomplete:
        return RECOVERY_RECOMMENDATION_COMPLETE_BACKUP
    if inventory.comparison.material_regression is True:
        return RECOVERY_RECOMMENDATION_REVIEW_CONTENTS
    if checks["integrity_verified"] is not True:
        return RECOVERY_RECOMMENDATION_VERIFY
    if checks["independent_copy"] is not True:
        return RECOVERY_RECOMMENDATION_EXTERNAL_COPY
    if database_check_enabled and checks["database_verified"] is not True:
        return RECOVERY_RECOMMENDATION_DATABASE
    return RECOVERY_RECOMMENDATION_NONE


def assess_recovery_readiness(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    *,
    backup_stale: bool,
    required_locations: int,
    database_check_enabled: bool,
    backups: tuple[BackupRecord, ...] = (),
    agent_summaries: tuple[BackupAgentSummary, ...] = (),
) -> RecoveryReadiness:
    """Assess whether the latest backup is suitable for disaster recovery."""
    del required_locations  # Replaced by failure-domain-aware redundancy in alpha4.
    inventory = build_recovery_inventory(latest, backups, agent_summaries)
    checks = _checks(
        latest,
        inventory,
        integrity,
        backup_stale=backup_stale,
        database_check_enabled=database_check_enabled,
    )
    deductions = _deductions(latest, checks)
    score = max(0, 100 - sum(deductions.values()))
    recommendation = _recommendation(
        latest,
        checks,
        inventory,
        database_check_enabled=database_check_enabled,
    )
    return RecoveryReadiness(
        score=score,
        status=_status(score, latest is not None),
        recommendation=recommendation,
        deductions=deductions,
        checks=checks,
        content_inventory=inventory.content.as_dict(),
        content_comparison=inventory.comparison.as_dict(),
        storage_resilience=inventory.storage.as_dict(),
        backup_content_changed=inventory.comparison.material_regression is True,
        external_copy_missing=bool(
            latest is not None and inventory.storage.independent_copy is False
        ),
    )
