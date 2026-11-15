"""Validate the shared progress model without importing Home Assistant."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRESS_PATH = ROOT / "custom_components" / "backup_checkup" / "progress.py"


def _load_progress():
    """Import progress.py directly so no Home Assistant package is required."""
    spec = importlib.util.spec_from_file_location(
        "backup_checkup_progress_check", PROGRESS_PATH
    )
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load the progress module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


class _Clock:
    """Deterministic monotonic and wall clock for throttling assertions."""

    def __init__(self) -> None:
        self.seconds = 0.0
        self.base = datetime(2026, 1, 1, tzinfo=UTC)

    def advance(self, seconds: float) -> None:
        """Move both clocks forward."""
        self.seconds += seconds

    def monotonic(self) -> float:
        """Return the fake monotonic time."""
        return self.seconds

    def now(self) -> datetime:
        """Return the fake wall-clock time."""
        return self.base + timedelta(seconds=self.seconds)


def _reporter(progress_module, job: str, clock: _Clock, published: list[int]):
    """Return a reporter that records every published overall percentage."""
    progress = progress_module.JobProgress.create(job)
    reporter = progress_module.ProgressReporter(
        progress,
        lambda: published.append(progress.overall_percent),
        monotonic=clock.monotonic,
        now=clock.now,
    )
    return progress, reporter


def _check_weights(progress_module) -> None:
    """Every job must distribute exactly one hundred weight points."""
    for job, steps in progress_module.JOB_STEPS.items():
        total = sum(step.weight for step in steps)
        _require(total == 100, f"Weights for {job} sum to {total} instead of 100")
        keys = [step.key for step in steps]
        _require(len(keys) == len(set(keys)), f"Duplicate step keys in {job}")


def _check_calculation(progress_module) -> None:
    """Determinate steps contribute proportionally, indeterminate ones do not."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start(reference="backup")
    reporter.begin_step("prepare")
    reporter.complete_step("prepare")
    reporter.begin_step("staging")
    reporter.complete_step("staging")
    _require(progress.overall_percent == 5, "Completed steps must add their weight")

    reporter.begin_step("download", total=1000)
    reporter.update("download", done=500)
    _require(
        progress.overall_percent == 20,
        f"Half a 30-point step must add 15, got {progress.overall_percent}",
    )
    reporter.update("download", done=1000)
    _require(progress.overall_percent == 35, "A finished download must add 30")

    reporter.begin_step("archive_scan", total=2000)
    reporter.update("archive_scan", done=1000)
    _require(progress.overall_percent == 55, "Archive progress must be proportional")

    # An indeterminate step keeps the overall value at the start of its phase.
    reporter.begin_step("archive_scan", determinate=False)
    reporter.update("archive_scan", detail="quick_check")
    _require(
        progress.overall_percent == 55,
        "An indeterminate step must not invent progress",
    )
    _require(
        progress.determinate is False,
        "determinate must follow the running step",
    )


def _check_monotonicity(progress_module) -> None:
    """A late, smaller measurement must never move the bar backwards."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start()
    reporter.begin_step("download", total=1000)
    reporter.update("download", done=900)
    peak = progress.overall_percent
    reporter.update("download", done=100)
    _require(
        progress.overall_percent == peak,
        "Overall progress must never decrease inside one run",
    )
    reporter.start()
    _require(progress.overall_percent == 0, "A new run must reset the overall value")


def _check_terminal_states(progress_module) -> None:
    """Failure, abort and not_started must never claim a completed run."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.begin_step("runtime_prepare")
    reporter.begin_step("runtime_upload", total=1000)
    reporter.update("runtime_upload", done=500)
    before = progress.overall_percent
    reporter.finish(progress_module.JOB_FAILED, error_code="runner_start_failed")
    _require(
        progress.overall_percent == before,
        f"A failed job must stop at {before}, got {progress.overall_percent}",
    )
    _require(
        progress.step("runtime_upload").state == progress_module.STEP_FAILED,
        "The running step must fail with the job",
    )

    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.begin_step("runtime_prepare")
    reporter.finish(progress_module.JOB_NOT_STARTED, error_code="runner_unavailable")
    _require(progress.overall_percent == 0, "not_started must report zero progress")
    _require(
        all(
            step.state == progress_module.STEP_PENDING for step in progress.steps
        ),
        "not_started must leave every step pending",
    )

    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.begin_step("runtime_probe")
    reporter.finish(
        progress_module.JOB_INCONCLUSIVE, error_code="runner_internal_error"
    )
    _require(
        progress.step("runtime_probe").state == progress_module.STEP_INCONCLUSIVE,
        "An inconclusive job must mark the running step inconclusive",
    )
    _require(
        progress.overall_percent < 100,
        "An inconclusive job must not reach one hundred percent",
    )

    progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start()
    reporter.begin_step("prepare")
    reporter.finish(progress_module.JOB_PASSED)
    _require(
        progress.overall_percent == 100,
        "A successful job must reach one hundred percent",
    )


def _check_no_false_completion(progress_module) -> None:
    """Nothing but a passed job may read as one hundred percent."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    # A runner that reports every step as passed and then an unclear result.
    reporter.apply_runner_state(
        {
            "runner_version": "3",
            "steps": [
                {"key": key, "state": "passed", "percent": 100}
                for key in progress_module.RUNTIME_STEP_KEYS
            ],
        }
    )
    reporter.finish(
        progress_module.JOB_INCONCLUSIVE, error_code="runner_internal_error"
    )
    _require(
        progress.overall_percent <= 99,
        f"An unclear result must not read as complete, got "
        f"{progress.overall_percent}",
    )

    # A step that is still running when another begins is not a success.
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start()
    reporter.begin_step("archive_scan", total=1000)
    reporter.update("archive_scan", done=100)
    reporter.begin_step("cleanup", promote=False)
    _require(
        progress.step("archive_scan").state == progress_module.STEP_RUNNING,
        "An interrupted step must not be promoted to passed",
    )
    reporter.finish(progress_module.JOB_FAILED, error_code="internal_error")
    _require(
        progress.step("archive_scan").state == progress_module.STEP_FAILED,
        "Every step still running must end with the job",
    )
    _require(
        progress.step("cleanup").state == progress_module.STEP_FAILED,
        "The step that was current must end with the job",
    )


def _check_hostile_payload(progress_module) -> None:
    """A malformed runner answer must not break the poll loop."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.apply_runner_state(
        {
            "runner_version": 3,
            "step": {
                "key": "runtime_upload",
                "state": "running",
                "percent": float("nan"),
                "done": -5,
                "total": "many",
                "unit": 7,
                "detail": "x" * 500,
            },
            "steps": [{"key": "definitely_unknown", "state": "passed"}, "nonsense"],
            "events": None,
        }
    )
    step = progress.step("runtime_upload")
    _require(step.percent is None, "A non-finite percentage must be ignored")
    _require(step.done is None, "A negative counter must be ignored")
    _require(step.total is None, "A non-integer total must be ignored")
    _require(len(step.detail) <= 120, "The detail text must stay bounded")
    _require(
        progress.overall_percent <= 100,
        "A hostile payload must not push the bar past 100",
    )

    reporter.apply_runner_state({"step": {"key": "runtime_upload", "state": "failed"}})
    _require(
        progress.step("runtime_upload").state == progress_module.STEP_FAILED,
        "A reported terminal step state must be adopted",
    )


def _check_phase_classification(progress_module) -> None:
    """A failure while preparing never counts as a test that ran."""
    _require(
        progress_module.runtime_status_for_error(
            "runner_busy", phase=progress_module.PHASE_PREPARE
        )
        == progress_module.JOB_NOT_STARTED,
        "Any failure before the upload means the test never started",
    )
    _require(
        progress_module.runtime_status_for_error(
            "runner_start_failed", phase=progress_module.PHASE_RUN
        )
        == progress_module.JOB_FAILED,
        "A failed start of a transferred archive is a failure",
    )
    _require(
        progress_module.runtime_status_for_error("runner_poll_failed")
        == progress_module.JOB_INCONCLUSIVE,
        "A lost connection during the test leaves the outcome unknown",
    )


def _check_throttling(progress_module) -> None:
    """Publication is limited to one per second unless something changed."""
    clock = _Clock()
    published: list[int] = []
    _progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start()
    reporter.begin_step("download", total=1_000_000)
    published.clear()
    # Many tiny updates inside the same second and the same percentage.
    for index in range(1, 200):
        clock.advance(0.001)
        reporter.update("download", done=index)
    _require(
        len(published) <= 1,
        f"Sub-percent updates must be throttled, got {len(published)} publications",
    )
    published.clear()
    clock.advance(2.0)
    reporter.update("download", done=200)
    _require(len(published) == 1, "A publication must follow the throttle window")

    published.clear()
    reporter.update("download", done=500_000)
    _require(len(published) == 1, "A percentage change must publish immediately")

    # Inside the same second and at the same percentage nothing is published.
    published.clear()
    reporter.update("download", done=500_000)
    _require(
        not published,
        "An unchanged measurement inside the window must not publish",
    )
    # A step change publishes even though neither timer nor percentage moved.
    reporter.begin_step("archive_scan")
    _require(len(published) == 1, "A step change must always publish")


def _check_heartbeat(progress_module) -> None:
    """Indeterminate steps refresh their liveness at most every five seconds."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_VERIFICATION, clock, published
    )
    reporter.start()
    reporter.begin_step("database_check", determinate=False)
    first = progress.step("database_check").heartbeat_at
    clock.advance(1.0)
    reporter.heartbeat("database_check")
    _require(
        progress.step("database_check").heartbeat_at == first,
        "A heartbeat inside the interval must be ignored",
    )
    clock.advance(
        progress_module.HEARTBEAT_INTERVAL_SECONDS + 1.0
    )
    reporter.heartbeat("database_check")
    _require(
        progress.step("database_check").heartbeat_at != first,
        "A heartbeat after the interval must refresh the timestamp",
    )
    _require(
        progress.heartbeat_at == progress.step("database_check").heartbeat_at,
        "The job must expose the heartbeat of the running step",
    )


def _check_activity_records(progress_module) -> None:
    """The journal receives step transitions and one record per ten percent."""
    clock = _Clock()
    records: list[tuple[str, str, dict]] = []
    progress = progress_module.JobProgress.create(progress_module.JOB_VERIFICATION)
    reporter = progress_module.ProgressReporter(
        progress,
        None,
        monotonic=clock.monotonic,
        now=clock.now,
        activity=lambda key, outcome, details: records.append(
            (key, outcome, details)
        ),
    )
    reporter.start()
    reporter.begin_step("download", total=1000)
    records.clear()
    for done in range(1, 1001):
        reporter.update("download", done=done)
    buckets = [record[2]["progress_percent"] for record in records]
    _require(
        buckets == [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        f"Expected one record per ten percent, got {buckets}",
    )
    records.clear()
    reporter.complete_step("download")
    _require(
        records == [("download", "completed", {})],
        f"A completed step writes exactly one record, got {records}",
    )


def _check_runner_status_mapping(progress_module) -> None:
    """Runner failures map to the status that describes what really happened."""
    expected = {
        "runner_unavailable": progress_module.JOB_NOT_STARTED,
        "runner_protocol_mismatch": progress_module.JOB_NOT_STARTED,
        "runner_tls_invalid": progress_module.JOB_NOT_STARTED,
        "runner_too_old": progress_module.JOB_NOT_STARTED,
        "runner_create_failed": progress_module.JOB_NOT_STARTED,
        "runner_upload_failed": progress_module.JOB_FAILED,
        "runner_start_failed": progress_module.JOB_FAILED,
        "runner_isolation_unavailable": progress_module.JOB_ABORTED,
        "runner_timeout": progress_module.JOB_ABORTED,
        "cancelled": progress_module.JOB_ABORTED,
        "runner_internal_error": progress_module.JOB_INCONCLUSIVE,
        "runner_backup_mismatch": progress_module.JOB_FAILED,
        "definitely_unknown_code": progress_module.JOB_FAILED,
    }
    for code, status in expected.items():
        actual = progress_module.runtime_status_for_error(code)
        _require(
            actual == status,
            f"{code} mapped to {actual} instead of {status}",
        )


def _check_runner_payload(progress_module) -> None:
    """A runner-3 payload drives the steps, a runner-2 payload stays coarse."""
    clock = _Clock()
    published: list[int] = []
    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.apply_runner_state(
        {
            "runner_version": "3",
            "step": {
                "key": "runtime_restore",
                "state": "running",
                "determinate": True,
                "done": 500,
                "total": 1000,
                "unit": "bytes",
            },
            "steps": [
                {"key": "runtime_prepare", "state": "passed"},
                {"key": "runtime_upload", "state": "passed", "percent": 100},
            ],
        }
    )
    _require(progress.runner_version == "3", "The runner version must be adopted")
    _require(progress.current_step == "runtime_restore", "The step must be adopted")
    _require(
        progress.overall_percent == 43,
        f"3 + 25 + 15 must be 43, got {progress.overall_percent}",
    )
    _require(progress.determinate is True, "A runner-3 step reports real progress")

    progress, reporter = _reporter(
        progress_module, progress_module.JOB_RUNTIME_TEST, clock, published
    )
    reporter.start()
    reporter.apply_runner_state({"stage": "runtime_boot", "progress_percent": 65})
    _require(
        progress.current_step == "runtime_boot",
        "A runner-2 stage must still select the step",
    )
    _require(
        progress.determinate is False,
        "A runner-2 stage must be reported as indeterminate",
    )
    _require(
        progress.overall_percent == 58,
        f"Only finished steps may count, got {progress.overall_percent}",
    )


def main() -> None:
    """Run every progress-model assertion."""
    progress_module = _load_progress()
    _check_weights(progress_module)
    _check_calculation(progress_module)
    _check_monotonicity(progress_module)
    _check_terminal_states(progress_module)
    _check_no_false_completion(progress_module)
    _check_hostile_payload(progress_module)
    _check_phase_classification(progress_module)
    _check_throttling(progress_module)
    _check_heartbeat(progress_module)
    _check_activity_records(progress_module)
    _check_runner_status_mapping(progress_module)
    _check_runner_payload(progress_module)
    print("Progress model behavior passed")


if __name__ == "__main__":
    main()
