"""Recovery-readiness assessment for BackupCheckup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .adaptive_policy import AdaptiveRecoveryPolicy
from .const import (
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupAgentSummary, BackupIntegrityResult, BackupRecord
from .recovery_evidence import (
    EVIDENCE_FULL,
    EVIDENCE_LIMITED,
    EVIDENCE_NOT_RECOVERABLE,
    EVIDENCE_RUNTIME,
    EVIDENCE_STRUCTURAL,
    RecoveryEvidence,
    resolve_recovery_evidence,
)
from .recovery_inventory import RecoveryInventory, build_recovery_inventory
from .recovery_plan import build_recovery_plan
from .recovery_preparedness import RecoveryPreparednessSnapshot
from .recovery_restore import RestoreTestSnapshot
from .recovery_runtime import (
    RUNTIME_STATUS_NOT_AVAILABLE,
    RUNTIME_STATUS_NOT_RUN,
    RuntimeTestSnapshot,
)
from .recovery_simulation import simulate_restore

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
RECOVERY_RECOMMENDATION_CHECKLIST = "complete_recovery_checklist"
RECOVERY_RECOMMENDATION_DEPENDENCIES = "protect_external_dependencies"
RECOVERY_RECOMMENDATION_SIMULATION = "run_restore_simulation"
RECOVERY_RECOMMENDATION_RESTORE_TEST = "document_restore_test"
RECOVERY_RECOMMENDATION_NONE = "none"
RECOVERY_RECOMMENDATION_OPTIONS = (
    RECOVERY_RECOMMENDATION_NONE,
    RECOVERY_RECOMMENDATION_VERIFY,
    RECOVERY_RECOMMENDATION_EXTERNAL_COPY,
    RECOVERY_RECOMMENDATION_COMPLETE_BACKUP,
    RECOVERY_RECOMMENDATION_REVIEW_CONTENTS,
    RECOVERY_RECOMMENDATION_DATABASE,
    RECOVERY_RECOMMENDATION_CHECKLIST,
    RECOVERY_RECOMMENDATION_DEPENDENCIES,
    RECOVERY_RECOMMENDATION_SIMULATION,
    RECOVERY_RECOMMENDATION_RESTORE_TEST,
)


@dataclass(frozen=True, slots=True)
class RecoveryAssessmentContext:
    """Environment metadata shared by one recovery assessment."""

    generated_at: datetime | None = None
    installation_type: str | None = None
    language: str = "en"


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
    preparedness: dict[str, Any]
    restore_simulation: dict[str, Any]
    runtime_test: dict[str, Any]
    restore_test: dict[str, Any]
    recovery_plan: dict[str, Any]
    evidence: dict[str, Any]
    adaptive_policy: dict[str, Any]
    open_risks: tuple[str, ...]
    backup_content_changed: bool
    external_copy_missing: bool


def _status(score: int, evidence: RecoveryEvidence) -> str:
    """Map the evidence model to the compatible recovery-status entity."""
    if evidence.level == EVIDENCE_NOT_RECOVERABLE:
        return RECOVERY_STATUS_INSUFFICIENT
    if evidence.level == EVIDENCE_LIMITED:
        return RECOVERY_STATUS_LIMITED if score >= 55 else RECOVERY_STATUS_INSUFFICIENT
    if (
        evidence.level
        in {
            EVIDENCE_STRUCTURAL,
            EVIDENCE_RUNTIME,
            EVIDENCE_FULL,
        }
        and score >= 85
    ):
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
    preparedness: RecoveryPreparednessSnapshot,
    simulated_restore_passed: bool | None,
    restore_test_passed: bool | None,
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
        "preparedness_checklist_complete": preparedness.checklist_complete,
        "external_dependencies_protected": preparedness.dependencies_protected,
        "simulated_restore_passed": simulated_restore_passed,
        "test_restore_documented": restore_test_passed,
    }


def _deductions(
    latest: BackupRecord | None,
    checks: dict[str, bool | None],
) -> dict[str, int]:
    """Return a balanced 100-point recovery model with conservative uncertainty."""
    if latest is None:
        return {"backup_available": 100}
    weights = {
        "backup_current": 8,
        "backup_complete": 10,
        "homeassistant_included": 8,
        "database_included": 4,
        "integrity_verified": 16,
        "database_verified": 4,
        "independent_copy": 8,
        "multiple_failure_domains": 4,
        "copy_sizes_consistent": 3,
        "content_stable": 4,
        "external_dependencies_protected": 5,
    }
    deductions = {
        key: weight for key, weight in weights.items() if checks[key] is False
    }
    uncertain = (
        "homeassistant_included",
        "database_included",
        "independent_copy",
        "multiple_failure_domains",
    )
    for key in uncertain:
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
    if checks["simulated_restore_passed"] is not True:
        return RECOVERY_RECOMMENDATION_SIMULATION
    if checks["external_dependencies_protected"] is False:
        return RECOVERY_RECOMMENDATION_DEPENDENCIES
    return RECOVERY_RECOMMENDATION_NONE


def _open_risks(
    checks: dict[str, bool | None],
    preparedness: RecoveryPreparednessSnapshot,
    inventory: RecoveryInventory,
) -> tuple[str, ...]:
    """Return concise actionable risks without promoting optional evidence to errors."""
    risks: list[str] = []
    if checks.get("backup_current") is False:
        risks.append("backup_stale")
    if checks.get("independent_copy") is False:
        risks.append("independent_copy_missing")
    if inventory.comparison.material_regression is True:
        risks.append("backup_content_regression")
    if preparedness.dependency_unprotected_count:
        risks.append("external_dependency_unprotected")
    if preparedness.dependency_review_required_count:
        risks.append("external_dependency_confirmation_required")
    return tuple(risks)


def assess_recovery_readiness(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    *,
    backup_stale: bool,
    required_locations: int,
    database_check_enabled: bool,
    backups: tuple[BackupRecord, ...] = (),
    agent_summaries: tuple[BackupAgentSummary, ...] = (),
    preparedness: RecoveryPreparednessSnapshot | None = None,
    restore_test: RestoreTestSnapshot | None = None,
    context: RecoveryAssessmentContext | None = None,
    simulation_progress: dict[str, Any] | None = None,
    adaptive_policy: AdaptiveRecoveryPolicy | None = None,
    runtime_test: RuntimeTestSnapshot | None = None,
) -> RecoveryReadiness:
    """Assess whether the latest backup is suitable for disaster recovery."""
    del required_locations  # Superseded by failure-domain-aware redundancy.
    assessment_context = context or RecoveryAssessmentContext()
    inventory = build_recovery_inventory(latest, backups, agent_summaries)
    preparedness_snapshot = preparedness or RecoveryPreparednessSnapshot.empty()
    restore_test_snapshot = restore_test or RestoreTestSnapshot.empty()
    runtime_test_snapshot = runtime_test or RuntimeTestSnapshot()
    if (
        runtime_test_snapshot.status == RUNTIME_STATUS_NOT_RUN
        and adaptive_policy is not None
        and not adaptive_policy.ephemeral_runner_available
    ):
        runtime_test_snapshot = RuntimeTestSnapshot(
            status=RUNTIME_STATUS_NOT_AVAILABLE
        )
    simulation = simulate_restore(
        latest,
        integrity,
        database_check_enabled=database_check_enabled,
        live_progress=simulation_progress,
    )
    checks = _checks(
        latest,
        inventory,
        integrity,
        backup_stale=backup_stale,
        database_check_enabled=database_check_enabled,
        preparedness=preparedness_snapshot,
        simulated_restore_passed=simulation.passed,
        restore_test_passed=restore_test_snapshot.passed,
    )
    deductions = _deductions(latest, checks)
    score = max(0, 100 - sum(deductions.values()))
    evidence = resolve_recovery_evidence(
        has_backup=latest is not None,
        backup_usable=bool(latest and not latest.incomplete),
        structural_passed=simulation.passed,
        restore_test=restore_test_snapshot,
        runtime_verified=runtime_test_snapshot.verified_for(
            latest.backup_reference if latest else None,
            integrity.sha256,
        ),
    )
    plan = build_recovery_plan(
        latest,
        integrity,
        preparedness_snapshot,
        simulation,
        restore_test_snapshot,
        generated_at=assessment_context.generated_at or datetime.now(UTC),
        installation_type=assessment_context.installation_type,
        language=assessment_context.language,
    )
    recommendation = _recommendation(
        latest,
        checks,
        inventory,
        database_check_enabled=database_check_enabled,
    )
    return RecoveryReadiness(
        score=score,
        status=_status(score, evidence),
        recommendation=recommendation,
        deductions=deductions,
        checks=checks,
        content_inventory=inventory.content.as_dict(),
        content_comparison=inventory.comparison.as_dict(),
        storage_resilience=inventory.storage.as_dict(),
        preparedness=preparedness_snapshot.as_dict(),
        restore_simulation=simulation.as_dict(),
        runtime_test=runtime_test_snapshot.as_dict(),
        restore_test=restore_test_snapshot.as_dict(),
        recovery_plan=plan.as_dict(),
        evidence=evidence.as_dict(),
        adaptive_policy=adaptive_policy.as_dict() if adaptive_policy else {},
        open_risks=_open_risks(checks, preparedness_snapshot, inventory),
        backup_content_changed=inventory.comparison.material_regression is True,
        external_copy_missing=bool(
            latest is not None and inventory.storage.independent_copy is False
        ),
    )
