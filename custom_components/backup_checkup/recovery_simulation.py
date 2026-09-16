"""Non-destructive restore simulation built on the verified backup pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .const import (
    INTEGRITY_DATABASE_FAILED,
    INTEGRITY_DATABASE_NOT_APPLICABLE,
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_DATABASE_PASSED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_CORRUPT,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from .models import BackupIntegrityResult, BackupRecord
from .progress import (
    STEP_FAILED,
    STEP_PASSED,
    STEP_PENDING,
    STEP_SKIPPED,
    VERIFICATION_STEPS,
)

SIMULATION_STATUS_PASSED = "passed"
SIMULATION_STATUS_WARNING = "warning"
SIMULATION_STATUS_FAILED = "failed"
SIMULATION_STATUS_RUNNING = "running"
SIMULATION_STATUS_ABORTED = "aborted"
SIMULATION_STATUS_PASSWORD_REQUIRED = "password_required"
SIMULATION_STATUS_INCONCLUSIVE = "inconclusive"
SIMULATION_STATUS_NOT_RUN = "not_run"
SIMULATION_STATUS_OPTIONS = (
    SIMULATION_STATUS_PASSED,
    SIMULATION_STATUS_WARNING,
    SIMULATION_STATUS_FAILED,
    SIMULATION_STATUS_RUNNING,
    SIMULATION_STATUS_ABORTED,
    SIMULATION_STATUS_PASSWORD_REQUIRED,
    SIMULATION_STATUS_INCONCLUSIVE,
    SIMULATION_STATUS_NOT_RUN,
)

SIMULATION_MODE_STANDARD = "standard"

STAGE_PREPARE = "prepare"
STAGE_STAGING = "staging"
STAGE_DOWNLOAD = "download"
STAGE_ARCHIVE_SCAN = "archive_scan"
STAGE_NESTED_ARCHIVES = "nested_archives"
STAGE_DATABASE = "database_check"
STAGE_EVALUATE = "evaluate"
STAGE_CLEANUP = "cleanup"
# The pipeline the panel renders is the shared verification step list itself.
SIMULATION_STAGE_OPTIONS = tuple(step.key for step in VERIFICATION_STEPS)
_STAGE_WEIGHTS = {step.key: step.weight for step in VERIFICATION_STEPS}

STAGE_PENDING = STEP_PENDING
STAGE_RUNNING = "running"
STAGE_PASSED = STEP_PASSED
STAGE_WARNING = "warning"
STAGE_FAILED = STEP_FAILED
STAGE_NOT_APPLICABLE = STEP_SKIPPED

_TERMINAL_LIVE_STATUSES = frozenset(
    {"passed", "failed", "aborted", "inconclusive", "not_started"}
)


def _empty_stages(*, database_check_enabled: bool) -> dict[str, str]:
    """Return a stable ordered stage mapping for the frontend pipeline."""
    stages = dict.fromkeys(SIMULATION_STAGE_OPTIONS, STAGE_PENDING)
    if not database_check_enabled:
        stages[STAGE_DATABASE] = STAGE_NOT_APPLICABLE
    return stages


def _stage_percent(stages: Mapping[str, str]) -> int:
    """Return the percentage a reconstructed pipeline really reached."""
    reached = sum(
        _STAGE_WEIGHTS.get(key, 0)
        for key, state in stages.items()
        if state in {STAGE_PASSED, STAGE_NOT_APPLICABLE}
    )
    return max(0, min(reached, 100))


def _steps_from_stages(stages: Mapping[str, str]) -> list[dict[str, Any]]:
    """Return a step list for a persisted result without live measurements."""
    return [
        {
            "key": step.key,
            "label_key": step.label_key,
            "weight": step.weight,
            "state": stages.get(step.key, STAGE_PENDING),
            "determinate": False,
            "percent": None,
            "done": None,
            "total": None,
            "unit": step.unit,
            "started_at": None,
            "finished_at": None,
            "heartbeat_at": None,
            "detail": None,
        }
        for step in VERIFICATION_STEPS
    ]


@dataclass(frozen=True, slots=True)
class RecoverySimulation:
    """Privacy-safe structural restore simulation result."""

    status: str
    checks: dict[str, bool | None]
    blocking_failures: tuple[str, ...]
    warnings: tuple[str, ...]
    backup_reference: str | None
    checked_at: str | None
    mode: str = SIMULATION_MODE_STANDARD
    stage: str = STAGE_CLEANUP
    progress_percent: int = 0
    running: bool = False
    started_at: str | None = None
    duration_seconds: float | None = None
    stages: dict[str, str] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    current_step: str | None = None
    determinate: bool = False
    heartbeat_at: str | None = None
    error_code: str | None = None
    archive_count: int = 0
    file_count: int = 0
    verified_size: int | None = None
    database_status: str = INTEGRITY_DATABASE_NOT_CHECKED

    @property
    def passed(self) -> bool | None:
        """Return tri-state pass semantics for the readiness score."""
        if self.status in {SIMULATION_STATUS_PASSED, SIMULATION_STATUS_WARNING}:
            return True
        if self.status in {
            SIMULATION_STATUS_FAILED,
            SIMULATION_STATUS_ABORTED,
            SIMULATION_STATUS_PASSWORD_REQUIRED,
        }:
            return False
        return None

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible frontend and diagnostic data."""
        return {
            "status": self.status,
            "passed": self.passed,
            "mode": self.mode,
            "stage": self.stage,
            "progress_percent": self.progress_percent,
            "running": self.running,
            "started_at": self.started_at,
            "checked_at": self.checked_at,
            "duration_seconds": self.duration_seconds,
            "stages": self.stages,
            "steps": self.steps,
            "overall_percent": self.progress_percent,
            "current_step": self.current_step,
            "determinate": self.determinate,
            "heartbeat_at": self.heartbeat_at,
            "error_code": self.error_code,
            "source": "integration",
            "checks": self.checks,
            "blocking_failures": list(self.blocking_failures),
            "warnings": list(self.warnings),
            "backup_reference": self.backup_reference,
            "archive_count": self.archive_count,
            "file_count": self.file_count,
            "verified_size": self.verified_size,
            "database_status": self.database_status,
            "destructive_actions_performed": False,
            "real_restore_performed": False,
        }


def _checks(
    latest: BackupRecord,
    integrity: BackupIntegrityResult,
    *,
    database_check_enabled: bool,
) -> tuple[dict[str, bool | None], bool]:
    """Build simulation checks and whether a result applies to the latest backup."""
    applies_to_latest = integrity.backup_id == latest.backup_id
    has_run = integrity.checked_at is not None and applies_to_latest
    archive_readable = (
        integrity.archive_count > 0 and integrity.file_count > 0 if has_run else None
    )
    return {
        "backup_available": True,
        "latest_backup_selected": applies_to_latest if integrity.checked_at else None,
        "metadata_readable": bool(latest.backup_reference and latest.date),
        "backup_complete": not latest.incomplete,
        "homeassistant_included": latest.homeassistant_included,
        "database_included": latest.database_included,
        "integrity_verified": (
            integrity.status
            in {INTEGRITY_STATUS_VALID, INTEGRITY_STATUS_VALID_WITH_WARNINGS}
            if has_run
            else None
        ),
        "archive_structure_readable": archive_readable,
        "verified_size_plausible": (
            integrity.verified_size > 0
            if has_run and integrity.verified_size is not None
            else None
        ),
        "database_verified": (
            integrity.database_status == INTEGRITY_DATABASE_PASSED
            if has_run and database_check_enabled
            else None
        ),
        "encrypted_backup_readable": (
            archive_readable if integrity.protected is True else None
        ),
        "storage_copy_available": bool(latest.agent_copies),
    }, has_run


def _blocking_failures(
    checks: Mapping[str, bool | None], *, database_check_enabled: bool
) -> tuple[str, ...]:
    keys = [
        "backup_available",
        "latest_backup_selected",
        "metadata_readable",
        "backup_complete",
        "homeassistant_included",
        "integrity_verified",
        "archive_structure_readable",
        "storage_copy_available",
    ]
    if database_check_enabled:
        keys.append("database_verified")
    return tuple(key for key in keys if checks.get(key) is False)


def _warnings(
    checks: Mapping[str, bool | None], *, database_check_enabled: bool
) -> tuple[str, ...]:
    non_applicable = {"encrypted_backup_readable"}
    if not database_check_enabled:
        non_applicable.add("database_verified")
    return tuple(
        key
        for key, value in checks.items()
        if value is None and key not in non_applicable
    )


def _status(
    integrity: BackupIntegrityResult,
    *,
    has_run: bool,
    blocking: tuple[str, ...],
    warnings: tuple[str, ...],
) -> str:
    if not has_run:
        return SIMULATION_STATUS_NOT_RUN
    if integrity.status == INTEGRITY_STATUS_PASSWORD_REQUIRED:
        return SIMULATION_STATUS_PASSWORD_REQUIRED
    if integrity.status == INTEGRITY_STATUS_ABORTED:
        return SIMULATION_STATUS_ABORTED
    if integrity.status == INTEGRITY_STATUS_INTERNAL_ERROR:
        return SIMULATION_STATUS_INCONCLUSIVE
    if integrity.status in {INTEGRITY_STATUS_CORRUPT, INTEGRITY_STATUS_UNREADABLE}:
        return SIMULATION_STATUS_FAILED
    if blocking:
        return SIMULATION_STATUS_FAILED
    if warnings or integrity.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS:
        return SIMULATION_STATUS_WARNING
    return SIMULATION_STATUS_PASSED


def _final_stages(
    integrity: BackupIntegrityResult,
    *,
    database_check_enabled: bool,
    status: str,
) -> dict[str, str]:
    """Reconstruct a useful persisted pipeline after Home Assistant restarts."""
    stages = _empty_stages(database_check_enabled=database_check_enabled)
    successful_read = integrity.archive_count > 0 and integrity.file_count > 0
    stages[STAGE_PREPARE] = STAGE_PASSED
    stages[STAGE_STAGING] = STAGE_PASSED if integrity.agent_id else STAGE_FAILED
    stages[STAGE_DOWNLOAD] = (
        STAGE_PASSED
        if integrity.verified_size and integrity.verified_size > 0
        else STAGE_FAILED
    )
    stages[STAGE_ARCHIVE_SCAN] = STAGE_PASSED if successful_read else STAGE_FAILED
    stages[STAGE_NESTED_ARCHIVES] = (
        STAGE_PASSED if integrity.archive_count > 0 else STAGE_FAILED
    )
    if database_check_enabled:
        stages[STAGE_DATABASE] = {
            INTEGRITY_DATABASE_PASSED: STAGE_PASSED,
            INTEGRITY_DATABASE_NOT_APPLICABLE: STAGE_NOT_APPLICABLE,
            INTEGRITY_DATABASE_FAILED: STAGE_FAILED,
        }.get(integrity.database_status, STAGE_WARNING)
    stages[STAGE_EVALUATE] = (
        STAGE_PASSED
        if status in {SIMULATION_STATUS_PASSED, SIMULATION_STATUS_WARNING}
        else STAGE_FAILED
    )
    stages[STAGE_CLEANUP] = STAGE_PASSED
    return stages


def _live_simulation(
    latest: BackupRecord,
    progress: Mapping[str, Any],
) -> RecoverySimulation:
    """Render an in-progress run without treating incomplete checks as failures."""
    steps = progress.get("steps")
    return RecoverySimulation(
        status=SIMULATION_STATUS_RUNNING,
        checks={"backup_available": True},
        blocking_failures=(),
        warnings=(),
        backup_reference=latest.backup_reference,
        checked_at=None,
        stage=str(progress.get("stage") or STAGE_PREPARE),
        progress_percent=max(0, min(int(progress.get("overall_percent") or 0), 100)),
        running=True,
        started_at=progress.get("started_at"),
        duration_seconds=progress.get("duration_seconds"),
        stages=dict(progress.get("stages") or {}),
        steps=list(steps) if isinstance(steps, list) else [],
        current_step=progress.get("current_step"),
        determinate=bool(progress.get("determinate")),
        heartbeat_at=progress.get("heartbeat_at"),
        error_code=progress.get("error_code"),
    )


def _measured_pipeline(
    progress: Mapping[str, Any], reference: str | None
) -> Mapping[str, Any] | None:
    """Return the finished live pipeline belonging to this backup, if any."""
    if not progress or progress.get("backup_reference") != reference:
        return None
    if progress.get("status") not in _TERMINAL_LIVE_STATUSES:
        return None
    return progress


def simulate_restore(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    *,
    database_check_enabled: bool,
    live_progress: Mapping[str, Any] | None = None,
) -> RecoverySimulation:
    """Assess the real read-only pipeline used to prepare a Home Assistant restore."""
    if latest is None:
        return RecoverySimulation(
            status=SIMULATION_STATUS_FAILED,
            checks={"backup_available": False},
            blocking_failures=("backup_available",),
            warnings=(),
            backup_reference=None,
            checked_at=None,
            progress_percent=0,
            stage=STAGE_PREPARE,
            stages=_empty_stages(database_check_enabled=database_check_enabled),
            steps=_steps_from_stages(
                _empty_stages(database_check_enabled=database_check_enabled)
            ),
        )
    if (
        live_progress
        and live_progress.get("running") is True
        and live_progress.get("backup_reference") == latest.backup_reference
    ):
        return _live_simulation(latest, live_progress)

    checks, has_run = _checks(
        latest, integrity, database_check_enabled=database_check_enabled
    )
    blocking = _blocking_failures(checks, database_check_enabled=database_check_enabled)
    warnings = _warnings(checks, database_check_enabled=database_check_enabled)
    status = _status(integrity, has_run=has_run, blocking=blocking, warnings=warnings)
    stages = (
        _final_stages(
            integrity,
            database_check_enabled=database_check_enabled,
            status=status,
        )
        if has_run
        else _empty_stages(database_check_enabled=database_check_enabled)
    )
    progress = live_progress or {}
    # A finished run keeps the pipeline it really measured; only an older
    # result is reconstructed from the stored integrity outcome.
    measured = _measured_pipeline(progress, latest.backup_reference)
    if measured is not None and has_run:
        stages = dict(measured.get("stages") or stages)
        measured_steps = measured.get("steps")
        steps = (
            list(measured_steps)
            if isinstance(measured_steps, list)
            else _steps_from_stages(stages)
        )
        percent = max(0, min(int(measured.get("overall_percent") or 0), 100))
        stage = str(measured.get("stage") or STAGE_CLEANUP)
        error_code = measured.get("error_code") or integrity.error_code
    else:
        steps = _steps_from_stages(stages)
        percent = _stage_percent(stages) if has_run else 0
        stage = STAGE_CLEANUP if has_run else STAGE_PREPARE
        error_code = integrity.error_code
    return RecoverySimulation(
        status=status,
        checks=checks,
        blocking_failures=blocking,
        warnings=warnings,
        backup_reference=latest.backup_reference,
        checked_at=integrity.checked_at.isoformat() if integrity.checked_at else None,
        stage=stage,
        progress_percent=percent,
        started_at=progress.get("started_at"),
        duration_seconds=integrity.duration_seconds,
        stages=stages,
        steps=steps,
        error_code=error_code,
        archive_count=integrity.archive_count,
        file_count=integrity.file_count,
        verified_size=integrity.verified_size,
        database_status=integrity.database_status,
    )
