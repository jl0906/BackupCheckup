"""Validate the restore-simulation view with a stubbed Home Assistant."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _install_homeassistant_stubs() -> None:
    """Provide the two Home Assistant symbols the model modules import."""
    if "homeassistant" in sys.modules:
        return
    homeassistant = ModuleType("homeassistant")
    const = ModuleType("homeassistant.const")

    class Platform(StrEnum):
        """Only the members BackupCheckup lists in PLATFORMS."""

        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        BUTTON = "button"

    const.Platform = Platform
    util = ModuleType("homeassistant.util")
    dt_util = ModuleType("homeassistant.util.dt")
    dt_util.utcnow = lambda: datetime.now(UTC)
    dt_util.parse_datetime = lambda value: None
    dt_util.as_utc = lambda value: value
    util.dt = dt_util
    homeassistant.const = const
    homeassistant.util = util
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.util"] = util
    sys.modules["homeassistant.util.dt"] = dt_util


def _load():
    """Import the model modules without executing the integration package."""
    _install_homeassistant_stubs()
    package = ModuleType("backup_checkup")
    # A synthetic package keeps __init__.py, and its Home Assistant setup code,
    # out of this check.
    package.__path__ = [str(ROOT / "custom_components" / "backup_checkup")]
    sys.modules.setdefault("backup_checkup", package)
    return (
        importlib.import_module("backup_checkup.recovery_simulation"),
        importlib.import_module("backup_checkup.models"),
        importlib.import_module("backup_checkup.progress"),
    )


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


def _record(models):
    """Return one minimal backup record."""
    return models.BackupRecord(
        backup_id="backup-1",
        backup_reference="reference-1",
        name="probe",
        date=datetime(2026, 1, 1, tzinfo=UTC),
        automatic=True,
        purpose="automatic",
        included_addons=(),
        included_folders=(),
        scope_fingerprint="fingerprint",
        agents=("backup.local",),
        agent_copies=(
            models.BackupAgentRecord(
                agent_id="backup.local",
                agent_reference="storage-1",
                size=1000,
                protected=False,
            ),
        ),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=1000,
        incomplete=False,
    )


def _integrity(models, status, *, checked_at=None, error_code=None):
    """Return one integrity result for the record above."""
    return models.BackupIntegrityResult(
        status=status,
        checked_at=checked_at or datetime(2026, 1, 1, 12, tzinfo=UTC),
        backup_id="backup-1",
        backup_reference="reference-1",
        backup_date=datetime(2026, 1, 1, tzinfo=UTC),
        agent_id="backup.local",
        sha256="0" * 64,
        verified_size=1000,
        duration_seconds=12.5,
        archive_count=3,
        file_count=120,
        protected=False,
        database_status="not_checked",
        warnings=(),
        error_code=error_code,
        checksum_changed=False,
    )


def main() -> None:
    """Run every simulation-view assertion."""
    simulation, models, progress_module = _load()
    record = _record(models)

    # A run in progress is rendered from the live measurement.
    reporter = progress_module.ProgressReporter(
        progress_module.JobProgress.create(progress_module.JOB_VERIFICATION)
    )
    reporter.start(reference="reference-1")
    reporter.begin_step("prepare")
    reporter.complete_step("prepare")
    reporter.begin_step("download", total=1000)
    reporter.update("download", done=500)
    live = simulation.simulate_restore(
        record,
        _integrity(models, "not_checked", checked_at=None),
        database_check_enabled=False,
        live_progress=reporter.snapshot(),
    ).as_dict()
    _require(live["status"] == "running", "A running job must be rendered as running")
    _require(
        live["progress_percent"] == live["overall_percent"] == 17,
        f"Expected 2 + half of 30 = 17, got {live['progress_percent']}",
    )
    _require(len(live["steps"]) == 8, "The live view must carry all eight steps")
    _require(live["current_step"] == "download", "The current step must be exposed")

    # A failed run keeps the position it reached.
    reporter.finish(progress_module.JOB_FAILED, error_code="archive_invalid")
    failed = simulation.simulate_restore(
        record,
        _integrity(models, "corrupt", error_code="archive_invalid"),
        database_check_enabled=False,
        live_progress=reporter.snapshot(),
    ).as_dict()
    _require(failed["status"] == "failed", "A corrupt archive must fail")
    _require(
        failed["progress_percent"] == 17,
        f"A failed run must stop at 17, got {failed['progress_percent']}",
    )
    _require(
        failed["error_code"] == "archive_invalid",
        "The error code must reach the view",
    )

    # A stored result without live data is reconstructed from the weights.
    stored = simulation.simulate_restore(
        record,
        _integrity(models, "valid"),
        database_check_enabled=False,
        live_progress=None,
    ).as_dict()
    _require(stored["status"] in {"passed", "warning"}, "A valid backup must pass")
    _require(
        stored["progress_percent"] == 100,
        f"A complete stored run must reach 100, got {stored['progress_percent']}",
    )
    _require(
        stored["stages"]["database_check"] == "skipped",
        "A disabled database check must be reported as skipped",
    )

    # A stored failure never claims a completed pipeline.
    broken = replace(
        _integrity(models, "corrupt", error_code="archive_invalid"),
        archive_count=0,
        file_count=0,
    )
    stored_failure = simulation.simulate_restore(
        record, broken, database_check_enabled=False, live_progress=None
    ).as_dict()
    _require(
        stored_failure["progress_percent"] < 100,
        "A stored failure must not report a complete pipeline",
    )

    # An unrelated live run never leaks into another backup's view.
    other = progress_module.ProgressReporter(
        progress_module.JobProgress.create(progress_module.JOB_VERIFICATION)
    )
    other.start(reference="different-backup")
    other.begin_step("download", total=1000)
    other.update("download", done=900)
    isolated = simulation.simulate_restore(
        record,
        _integrity(models, "valid"),
        database_check_enabled=False,
        live_progress=other.snapshot(),
    ).as_dict()
    _require(
        isolated["status"] != "running",
        "A run for a different backup must not be shown here",
    )
    _require(
        isolated["progress_percent"] == 100,
        "The stored result of this backup must stay intact",
    )

    # A complete run reports every step, including the cleanup that runs last.
    full = progress_module.ProgressReporter(
        progress_module.JobProgress.create(progress_module.JOB_VERIFICATION)
    )
    full.start(reference="reference-1")
    for key in ("prepare", "staging", "download", "archive_scan", "nested_archives"):
        full.begin_step(key)
        full.complete_step(key)
    full.skip_step("database_check")
    full.begin_step("evaluate")
    full.complete_step("evaluate")
    # The cleanup only starts after the optional runtime test returned.
    full.begin_step("cleanup", promote=False)
    full.complete_step("cleanup")
    full.finish(progress_module.JOB_PASSED)
    complete = simulation.simulate_restore(
        record,
        _integrity(models, "valid"),
        database_check_enabled=False,
        live_progress=full.snapshot(),
    ).as_dict()
    _require(
        complete["stages"]["cleanup"] == "passed",
        f"The cleanup step must be reported, got {complete['stages']['cleanup']}",
    )
    _require(
        complete["progress_percent"] == 100,
        f"A complete run must reach 100, got {complete['progress_percent']}",
    )

    # The aliases automations rely on stay present.
    for key in ("progress_percent", "stage", "stages", "steps", "overall_percent"):
        _require(key in stored, f"The view must keep the {key!r} attribute")

    print("Restore simulation view passed")


if __name__ == "__main__":
    main()
