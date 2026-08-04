"""Non-destructive restore simulation built on the verified backup pipeline."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
STAGE_STORAGE = "storage"
STAGE_DOWNLOAD = "download"
STAGE_ARCHIVES = "archives"
STAGE_DATABASE = "database"
STAGE_EVALUATE = "evaluate"
STAGE_CLEANUP = "cleanup"
STAGE_COMPLETE = "complete"
SIMULATION_STAGE_OPTIONS = (
    STAGE_PREPARE,
    STAGE_STORAGE,
    STAGE_DOWNLOAD,
    STAGE_ARCHIVES,
    STAGE_DATABASE,
    STAGE_EVALUATE,
    STAGE_CLEANUP,
    STAGE_COMPLETE,
)

STAGE_PENDING = "pending"
STAGE_RUNNING = "running"
STAGE_PASSED = "passed"
STAGE_WARNING = "warning"
STAGE_FAILED = "failed"
STAGE_NOT_APPLICABLE = "not_applicable"

_ACTION_STAGES = {
    "verification_prepare": (STAGE_PREPARE, 5, 8),
    "storage_copy_prepare": (STAGE_STORAGE, 9, 14),
    "backup_download": (STAGE_DOWNLOAD, 15, 45),
    # Archive inspection also contains the optional SQLite check. Keep the
    # long-running combined operation in one broad range instead of reporting
    # the database stage as started before archive inspection has done work.
    "backup_extract": (STAGE_ARCHIVES, 46, 88),
    "encrypted_backup_extract": (STAGE_ARCHIVES, 46, 88),
    "database_read": (STAGE_DATABASE, 88, 91),
    "temporary_data_cleanup": (STAGE_CLEANUP, 94, 98),
}
_OUTCOME_CHANGED = "changed"
_OUTCOME_STARTED = "started"
_FAILED_OUTCOMES = {"cancelled", "failed", "skipped"}


def _empty_stages(*, database_check_enabled: bool) -> dict[str, str]:
    """Return a stable ordered stage mapping for the frontend pipeline."""
    stages = dict.fromkeys(SIMULATION_STAGE_OPTIONS, STAGE_PENDING)
    if not database_check_enabled:
        stages[STAGE_DATABASE] = STAGE_NOT_APPLICABLE
    return stages


@dataclass(slots=True)
class RecoverySimulationProgress:
    """Track one live execution of the existing safe verification pipeline."""

    running: bool = False
    backup_reference: str | None = None
    database_check_enabled: bool = False
    stage: str = STAGE_PREPARE
    progress_percent: int = 0
    started_at: datetime | None = None
    duration_seconds: float | None = None
    stages: dict[str, str] = field(
        default_factory=lambda: _empty_stages(database_check_enabled=False)
    )
    _started_monotonic: float | None = field(default=None, repr=False)

    def start(self, record: BackupRecord, *, database_check_enabled: bool) -> None:
        """Start a live simulation for one anonymous backup reference."""
        self.running = True
        self.backup_reference = record.backup_reference
        self.database_check_enabled = database_check_enabled
        self.stage = STAGE_PREPARE
        self.progress_percent = 1
        self.started_at = datetime.now(UTC)
        self.duration_seconds = None
        self.stages = _empty_stages(database_check_enabled=database_check_enabled)
        self.stages[STAGE_PREPARE] = STAGE_RUNNING
        self._started_monotonic = time.monotonic()

    def activity(
        self,
        action: str,
        outcome: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Advance the graphical pipeline from privacy-safe verifier activity."""
        if not self.running or action not in _ACTION_STAGES:
            return
        stage, start_percent, end_percent = _ACTION_STAGES[action]
        self.stage = stage
        if outcome == _OUTCOME_CHANGED and stage == STAGE_DOWNLOAD:
            raw_progress = (details or {}).get("progress_percent")
            download_progress = raw_progress if isinstance(raw_progress, int) else 0
            bounded = max(0, min(download_progress, 100))
            self.progress_percent = max(
                self.progress_percent,
                start_percent + ((end_percent - start_percent) * bounded // 100),
            )
            self.stages[stage] = STAGE_RUNNING
            return
        if outcome == _OUTCOME_STARTED:
            self.progress_percent = max(self.progress_percent, start_percent)
            self.stages[stage] = STAGE_RUNNING
            return
        self.progress_percent = max(self.progress_percent, end_percent)
        self.stages[stage] = (
            STAGE_FAILED if outcome in _FAILED_OUTCOMES else STAGE_PASSED
        )

    def finish(self, result: BackupIntegrityResult) -> None:
        """Finish the live pipeline and retain its timing for the result view."""
        if not self.running:
            return
        self.running = False
        self.stage = STAGE_COMPLETE
        self.progress_percent = 100
        if self.stages[STAGE_EVALUATE] == STAGE_PENDING:
            self.stages[STAGE_EVALUATE] = (
                STAGE_PASSED
                if result.status
                in {INTEGRITY_STATUS_VALID, INTEGRITY_STATUS_VALID_WITH_WARNINGS}
                else STAGE_FAILED
            )
        if self.stages[STAGE_CLEANUP] == STAGE_PENDING:
            self.stages[STAGE_CLEANUP] = STAGE_PASSED
        self.stages[STAGE_COMPLETE] = (
            STAGE_PASSED
            if result.status
            in {INTEGRITY_STATUS_VALID, INTEGRITY_STATUS_VALID_WITH_WARNINGS}
            else STAGE_FAILED
        )
        if self._started_monotonic is not None:
            self.duration_seconds = round(
                max(0.0, time.monotonic() - self._started_monotonic), 2
            )
        self._started_monotonic = None

    def cancel(self) -> None:
        """Mark a running simulation as cancelled during integration shutdown."""
        if not self.running:
            return
        self.running = False
        self.stages[self.stage] = STAGE_FAILED
        self.duration_seconds = None
        self._started_monotonic = None

    def as_dict(self) -> dict[str, Any]:
        """Return bounded live state suitable for entity attributes."""
        return {
            "running": self.running,
            "mode": SIMULATION_MODE_STANDARD,
            "stage": self.stage,
            "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_seconds": self.duration_seconds,
            "stages": dict(self.stages),
            "backup_reference": self.backup_reference,
        }


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
    stage: str = STAGE_COMPLETE
    progress_percent: int = 100
    running: bool = False
    started_at: str | None = None
    duration_seconds: float | None = None
    stages: dict[str, str] = field(default_factory=dict)
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
    stages[STAGE_STORAGE] = STAGE_PASSED if integrity.agent_id else STAGE_FAILED
    stages[STAGE_DOWNLOAD] = (
        STAGE_PASSED
        if integrity.verified_size and integrity.verified_size > 0
        else STAGE_FAILED
    )
    stages[STAGE_ARCHIVES] = STAGE_PASSED if successful_read else STAGE_FAILED
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
    stages[STAGE_COMPLETE] = stages[STAGE_EVALUATE]
    return stages


def _live_simulation(
    latest: BackupRecord,
    progress: Mapping[str, Any],
) -> RecoverySimulation:
    """Render an in-progress run without treating incomplete checks as failures."""
    return RecoverySimulation(
        status=SIMULATION_STATUS_RUNNING,
        checks={"backup_available": True},
        blocking_failures=(),
        warnings=(),
        backup_reference=latest.backup_reference,
        checked_at=None,
        stage=str(progress.get("stage") or STAGE_PREPARE),
        progress_percent=max(0, min(int(progress.get("progress_percent") or 0), 100)),
        running=True,
        started_at=progress.get("started_at"),
        duration_seconds=progress.get("duration_seconds"),
        stages=dict(progress.get("stages") or {}),
    )


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
    return RecoverySimulation(
        status=status,
        checks=checks,
        blocking_failures=blocking,
        warnings=warnings,
        backup_reference=latest.backup_reference,
        checked_at=integrity.checked_at.isoformat() if integrity.checked_at else None,
        stage=STAGE_COMPLETE if has_run else STAGE_PREPARE,
        progress_percent=100 if has_run else 0,
        started_at=progress.get("started_at"),
        duration_seconds=integrity.duration_seconds,
        stages=stages,
        archive_count=integrity.archive_count,
        file_count=integrity.file_count,
        verified_size=integrity.verified_size,
        database_status=integrity.database_status,
    )
