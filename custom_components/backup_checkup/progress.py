"""Typed live progress model shared by verification and runtime tests.

This module is deliberately free of Home Assistant and third-party imports so
the calculation, monotonicity, and throttling rules can be validated by the
standalone checks in ``.github/scripts``. The runtime runner mirrors the step
weights defined here in ``runtime_runner/rootfs/opt/backup-checkup-runner
/server.py``; ``.github/scripts/check_progress_weights.py`` keeps both in sync.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

JOB_VERIFICATION = "verification"
JOB_RUNTIME_TEST = "runtime_test"

SOURCE_INTEGRATION = "integration"
SOURCE_RUNNER = "runner"

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_PASSED = "passed"
STEP_FAILED = "failed"
STEP_SKIPPED = "skipped"
STEP_INCONCLUSIVE = "inconclusive"
STEP_STATES = (
    STEP_PENDING,
    STEP_RUNNING,
    STEP_PASSED,
    STEP_FAILED,
    STEP_SKIPPED,
    STEP_INCONCLUSIVE,
)
#: Steps whose weight counts towards the overall percentage.
_COMPLETED_STEP_STATES = frozenset({STEP_PASSED, STEP_SKIPPED})

JOB_IDLE = "idle"
JOB_RUNNING = "running"
JOB_PASSED = "passed"
JOB_FAILED = "failed"
JOB_ABORTED = "aborted"
JOB_INCONCLUSIVE = "inconclusive"
JOB_NOT_STARTED = "not_started"
JOB_STATUSES = (
    JOB_IDLE,
    JOB_RUNNING,
    JOB_PASSED,
    JOB_FAILED,
    JOB_ABORTED,
    JOB_INCONCLUSIVE,
    JOB_NOT_STARTED,
)
#: Statuses that must never move the overall percentage to 100.
_INCOMPLETE_JOB_STATUSES = frozenset(
    {JOB_FAILED, JOB_ABORTED, JOB_INCONCLUSIVE, JOB_NOT_STARTED}
)

UNIT_BYTES = "bytes"
UNIT_FILES = "files"
UNIT_MEMBERS = "members"

#: Publish at most once per second unless the percentage or the step changed.
PUBLISH_INTERVAL_SECONDS = 1.0
#: Refresh the liveness timestamp of an indeterminate step at most this often.
HEARTBEAT_INTERVAL_SECONDS = 5.0
#: Write one activity record per completed tenth of a determinate step.
ACTIVITY_PERCENT_STEP = 10


@dataclass(frozen=True, slots=True)
class StepDefinition:
    """Static description of one step inside a job."""

    key: str
    label_key: str
    weight: int
    determinate: bool = True
    unit: str | None = None


VERIFICATION_STEPS: tuple[StepDefinition, ...] = (
    StepDefinition("prepare", "step_prepare", 2, determinate=False),
    StepDefinition("staging", "step_staging", 3, determinate=False),
    StepDefinition("download", "step_download", 30, unit=UNIT_BYTES),
    StepDefinition("archive_scan", "step_archive_scan", 40, unit=UNIT_BYTES),
    StepDefinition("nested_archives", "step_nested_archives", 10, unit=UNIT_MEMBERS),
    StepDefinition("database_check", "step_database_check", 8, determinate=False),
    StepDefinition("evaluate", "step_evaluate", 2, determinate=False),
    StepDefinition("cleanup", "step_cleanup", 5, unit=UNIT_FILES),
)

RUNTIME_STEPS: tuple[StepDefinition, ...] = (
    StepDefinition("runtime_prepare", "step_runtime_prepare", 3, determinate=False),
    StepDefinition("runtime_upload", "step_runtime_upload", 25, unit=UNIT_BYTES),
    StepDefinition("runtime_restore", "step_runtime_restore", 30, unit=UNIT_BYTES),
    StepDefinition("runtime_boot", "step_runtime_boot", 20, determinate=False),
    StepDefinition("runtime_probe", "step_runtime_probe", 12, determinate=False),
    StepDefinition("runtime_cleanup", "step_runtime_cleanup", 5, determinate=False),
    StepDefinition("runtime_complete", "step_runtime_complete", 5, determinate=False),
)

JOB_STEPS: dict[str, tuple[StepDefinition, ...]] = {
    JOB_VERIFICATION: VERIFICATION_STEPS,
    JOB_RUNTIME_TEST: RUNTIME_STEPS,
}

VERIFICATION_STEP_KEYS: tuple[str, ...] = tuple(step.key for step in VERIFICATION_STEPS)
RUNTIME_STEP_KEYS: tuple[str, ...] = tuple(step.key for step in RUNTIME_STEPS)

#: Boot events the runner may report while the started instance is opaque.
RUNTIME_EVENT_KEYS: tuple[str, ...] = (
    "sandbox_preflight_ok",
    "process_started",
    "port_listening",
    "http_responding",
)

#: Runner failures that happen before any data left this installation.
RUNNER_NOT_STARTED_CODES = frozenset(
    {
        "runner_unavailable",
        "runner_not_configured",
        "runner_protocol_mismatch",
        "runner_tls_invalid",
        "runner_too_old",
        "runner_create_failed",
    }
)
#: Runner failures that stopped a started test without a usable verdict.
RUNNER_ABORTED_CODES = frozenset(
    {
        "runner_isolation_unavailable",
        "runner_timeout",
        "cancelled",
    }
)
#: Runner failures that leave the outcome of a started test unknown.
RUNNER_INCONCLUSIVE_CODES = frozenset(
    {
        "runner_internal_error",
        "runner_cleanup_failed",
        "runner_poll_failed",
        "runner_response_invalid",
    }
)

#: The test never left this installation while the client was still preparing.
PHASE_PREPARE = "prepare"
#: The archive was transferred or the isolated instance was already running.
PHASE_RUN = "run"


def runtime_status_for_error(code: str | None, *, phase: str | None = None) -> str:
    """Map one runner failure to the job status it really describes.

    A failure while preparing means the isolated test never ran, so it must not
    be reported as an inconclusive or failed result of a test that did run.
    """
    if phase == PHASE_PREPARE:
        return JOB_NOT_STARTED
    if not code:
        return JOB_FAILED
    if code in RUNNER_NOT_STARTED_CODES:
        return JOB_NOT_STARTED
    if code in RUNNER_ABORTED_CODES:
        return JOB_ABORTED
    if code in RUNNER_INCONCLUSIVE_CODES:
        return JOB_INCONCLUSIVE
    return JOB_FAILED


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _bounded_percent(value: Any) -> int | None:
    """Return a strict 0-100 percentage or None.

    JSON allows NaN and Infinity literals, so a malformed remote answer must
    not reach int().
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return max(0, min(int(value), 100))


def _bounded_count(value: Any) -> int | None:
    """Return a non-negative counter or None."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _isoformat(value: datetime | None) -> str | None:
    """Return an ISO timestamp or None."""
    return value.isoformat() if value is not None else None


def _parse_timestamp(value: Any) -> datetime | None:
    """Return one bounded aware timestamp reported by a runner."""
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


@dataclass(slots=True)
class StepProgress:
    """Live state of one step inside a job."""

    key: str
    label_key: str
    weight: int
    state: str = STEP_PENDING
    determinate: bool = True
    percent: int | None = None
    done: int | None = None
    total: int | None = None
    unit: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    heartbeat_at: datetime | None = None
    detail: str | None = None

    @classmethod
    def from_definition(cls, definition: StepDefinition) -> StepProgress:
        """Return a pending step for one static definition."""
        return cls(
            key=definition.key,
            label_key=definition.label_key,
            weight=definition.weight,
            determinate=definition.determinate,
            unit=definition.unit,
        )

    @property
    def completed_percent(self) -> int:
        """Return the percentage this step contributes to the overall value."""
        if self.state in _COMPLETED_STEP_STATES:
            return self.weight
        if self.state != STEP_RUNNING or not self.determinate:
            return 0
        if self.percent is None:
            return 0
        return self.weight * self.percent // 100

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-safe representation used by entities and the panel."""
        return {
            "key": self.key,
            "label_key": self.label_key,
            "weight": self.weight,
            "state": self.state,
            "determinate": self.determinate,
            "percent": self.percent,
            "done": self.done,
            "total": self.total,
            "unit": self.unit,
            "started_at": _isoformat(self.started_at),
            "finished_at": _isoformat(self.finished_at),
            "heartbeat_at": _isoformat(self.heartbeat_at),
            "detail": self.detail,
        }


@dataclass(slots=True)
class JobProgress:
    """Live state of one verification or runtime-test run."""

    job: str
    status: str = JOB_IDLE
    current_step: str | None = None
    steps: list[StepProgress] = field(default_factory=list)
    overall_percent: int = 0
    started_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    source: str = SOURCE_INTEGRATION
    runner_version: str | None = None
    events: list[str] = field(default_factory=list)
    reference: str | None = None
    duration_seconds: float | None = None
    _monotonic_start: float | None = field(default=None, repr=False)

    @classmethod
    def create(cls, job: str) -> JobProgress:
        """Return an idle job with all steps pending."""
        return cls(
            job=job,
            steps=[
                StepProgress.from_definition(definition)
                for definition in JOB_STEPS.get(job, ())
            ],
        )

    def step(self, key: str) -> StepProgress | None:
        """Return one step by key."""
        return next((item for item in self.steps if item.key == key), None)

    @property
    def running(self) -> bool:
        """Return whether this job is currently executing."""
        return self.status == JOB_RUNNING

    @property
    def determinate(self) -> bool:
        """Return whether the currently running step reports real progress."""
        current = self.step(self.current_step) if self.current_step else None
        return bool(current and current.determinate)

    @property
    def heartbeat_at(self) -> datetime | None:
        """Return the last sign of life of the currently running step."""
        current = self.step(self.current_step) if self.current_step else None
        return current.heartbeat_at if current else None

    def recalculate(self) -> int:
        """Recalculate the monotonically increasing overall percentage."""
        total = sum(item.completed_percent for item in self.steps)
        self.overall_percent = max(self.overall_percent, min(total, 100))
        return self.overall_percent

    def as_dict(self) -> dict[str, Any]:
        """Return exactly the payload delivered to entities and the panel."""
        return {
            "job": self.job,
            "status": self.status,
            "running": self.running,
            "current_step": self.current_step,
            "steps": [item.as_dict() for item in self.steps],
            "overall_percent": self.overall_percent,
            "determinate": self.determinate,
            "started_at": _isoformat(self.started_at),
            "updated_at": _isoformat(self.updated_at),
            "finished_at": _isoformat(self.finished_at),
            "heartbeat_at": _isoformat(self.heartbeat_at),
            "error_code": self.error_code,
            "source": self.source,
            "runner_version": self.runner_version,
            "events": list(self.events),
            "backup_reference": self.reference,
            "duration_seconds": self.duration_seconds,
            # Stable aliases for automations written against 3.1.0.
            "progress_percent": self.overall_percent,
            "stage": self.current_step or (self.steps[0].key if self.steps else None),
            "stages": {item.key: item.state for item in self.steps},
        }


class ProgressReporter:
    """Thread-safe, throttled writer for one :class:`JobProgress`.

    Every mutation is serialized by an internal lock so worker threads may
    report progress while the event loop renders a snapshot. Publication is
    always handed to the event loop; the reporter itself never touches Home
    Assistant objects.
    """

    def __init__(
        self,
        progress: JobProgress,
        publish: Callable[[], None] | None = None,
        *,
        loop: Any = None,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = _utc_now,
        activity: Callable[[str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Initialize a reporter for one job."""
        self.progress = progress
        self._publish = publish
        self._loop = loop
        self._monotonic = monotonic
        self._now = now
        self._activity = activity
        self._lock = threading.RLock()
        self._last_publish: float | None = None
        self._last_published_percent = -1
        self._last_published_step: str | None = None
        self._last_activity_bucket: dict[str, int] = {}

    # -- lifecycle ---------------------------------------------------------

    def start(
        self,
        *,
        reference: str | None = None,
        source: str = SOURCE_INTEGRATION,
        runner_version: str | None = None,
    ) -> None:
        """Reset the job and mark it as running."""
        with self._lock:
            fresh = JobProgress.create(self.progress.job)
            self.progress.status = JOB_RUNNING
            self.progress.current_step = None
            self.progress.steps = fresh.steps
            self.progress.overall_percent = 0
            self.progress.started_at = self._now()
            self.progress.updated_at = self.progress.started_at
            self.progress.finished_at = None
            self.progress.error_code = None
            self.progress.source = source
            self.progress.runner_version = runner_version
            self.progress.reference = reference
            self.progress.events = []
            self.progress.duration_seconds = None
            self.progress._monotonic_start = self._monotonic()
            self._last_publish = None
            self._last_published_percent = -1
            self._last_published_step = None
            self._last_activity_bucket = {}
        self._emit(force=True)

    def finish(self, status: str, *, error_code: str | None = None) -> None:
        """Close the job without inventing a completed percentage."""
        if self.progress.status != JOB_RUNNING:
            # A job that already reported its result keeps it.
            return
        with self._lock:
            if status not in JOB_STATUSES:
                status = JOB_FAILED
            terminal = self._terminal_step_state(status)
            finished = self._now()
            for item in self.progress.steps:
                if item.state == STEP_RUNNING:
                    item.state = terminal
                    item.finished_at = finished
            if status == JOB_NOT_STARTED:
                self._reset_steps_locked()
            if status == JOB_PASSED:
                self._pass_remaining_locked()
            self.progress.status = status
            self.progress.error_code = error_code
            self.progress.finished_at = self._now()
            self.progress.updated_at = self.progress.finished_at
            if self.progress._monotonic_start is not None:
                self.progress.duration_seconds = round(
                    max(0.0, self._monotonic() - self.progress._monotonic_start), 2
                )
            self.progress._monotonic_start = None
            if status == JOB_NOT_STARTED:
                self.progress.overall_percent = 0
                self.progress.current_step = None
            elif status in _INCOMPLETE_JOB_STATUSES:
                # An unfinished run keeps its position but never reads as
                # complete, even when every step happened to be marked passed.
                self.progress.overall_percent = min(
                    self.progress.overall_percent, 99
                )
            else:
                self.progress.recalculate()
        self._emit(force=True)

    def cancel(self) -> None:
        """Abort a running job during shutdown."""
        if self.progress.status != JOB_RUNNING:
            return
        self.finish(JOB_ABORTED, error_code="cancelled")

    @staticmethod
    def _terminal_step_state(status: str) -> str:
        """Return the state a still-running step receives when a job ends."""
        if status == JOB_PASSED:
            return STEP_PASSED
        if status == JOB_INCONCLUSIVE:
            return STEP_INCONCLUSIVE
        if status == JOB_NOT_STARTED:
            return STEP_PENDING
        return STEP_FAILED

    def _reset_steps_locked(self) -> None:
        """Return every step to pending for a test that never started."""
        for item in self.progress.steps:
            item.state = STEP_PENDING
            item.percent = None
            item.done = None
            item.total = None
            item.started_at = None
            item.finished_at = None
            item.heartbeat_at = None
            item.detail = None

    def _pass_remaining_locked(self) -> None:
        """Complete untouched steps of a successful run."""
        finished = self._now()
        for item in self.progress.steps:
            if item.state in {STEP_PENDING, STEP_RUNNING}:
                item.state = STEP_PASSED
                item.finished_at = finished

    # -- step transitions --------------------------------------------------

    def begin_step(
        self,
        key: str,
        *,
        detail: str | None = None,
        determinate: bool | None = None,
        total: int | None = None,
        promote: bool = True,
    ) -> None:
        """Start one step and complete the step that was running before it.

        ``promote`` is false for a step that runs after a failure, such as the
        cleanup: it must never mark the step it interrupted as passed.
        """
        with self._lock:
            step = self.progress.step(key)
            if step is None or self.progress.status != JOB_RUNNING:
                return
            previous = self._current_locked()
            if (
                promote
                and previous is not None
                and previous is not step
                and previous.state == STEP_RUNNING
            ):
                previous.state = STEP_PASSED
                previous.percent = 100 if previous.determinate else None
                previous.finished_at = self._now()
            if step.state in {STEP_PASSED, STEP_FAILED, STEP_SKIPPED}:
                # A retried storage copy repeats earlier steps with its own
                # size, so no counter of the previous copy may survive.
                step.percent = None
                step.done = None
                step.total = None
                step.finished_at = None
                self._last_activity_bucket.pop(key, None)
            step.state = STEP_RUNNING
            step.started_at = step.started_at or self._now()
            step.heartbeat_at = self._now()
            if determinate is not None:
                step.determinate = determinate
            if total is not None:
                step.total = _bounded_count(total)
            if detail is not None:
                step.detail = detail
            self.progress.current_step = key
            self.progress.updated_at = self._now()
            self.progress.recalculate()
        self._record_activity(key, "started", {})
        self._emit(force=True)

    def complete_step(
        self,
        key: str,
        *,
        state: str = STEP_PASSED,
        detail: str | None = None,
    ) -> None:
        """Finish one step with an explicit result."""
        with self._lock:
            step = self.progress.step(key)
            if step is None or self.progress.status != JOB_RUNNING:
                # A job that already reported its result is not reopened.
                return
            step.state = state if state in STEP_STATES else STEP_PASSED
            if step.state == STEP_PASSED and step.determinate:
                step.percent = 100
            step.finished_at = self._now()
            step.heartbeat_at = step.finished_at
            if detail is not None:
                step.detail = detail
            self.progress.updated_at = step.finished_at
            self.progress.recalculate()
        outcome = "completed" if state == STEP_PASSED else state
        self._record_activity(key, outcome, {})
        self._emit(force=True)

    def skip_step(self, key: str, *, detail: str | None = None) -> None:
        """Mark one step as not applicable for this run."""
        self.complete_step(key, state=STEP_SKIPPED, detail=detail)

    def fail_open(self, *keys: str) -> None:
        """Fail every named step that has not produced a result yet."""
        changed = False
        with self._lock:
            if self.progress.status != JOB_RUNNING:
                return
            for key in keys:
                step = self.progress.step(key)
                if step is None or step.state not in {STEP_PENDING, STEP_RUNNING}:
                    continue
                step.state = STEP_FAILED
                step.finished_at = self._now()
                changed = True
            if changed:
                self.progress.updated_at = self._now()
        if changed:
            self._emit(force=True)

    # -- live updates ------------------------------------------------------

    def update(
        self,
        key: str,
        *,
        percent: int | None = None,
        done: int | None = None,
        total: int | None = None,
        detail: str | None = None,
        determinate: bool | None = None,
    ) -> None:
        """Report measured progress for one step from any thread."""
        with self._lock:
            step = self.progress.step(key)
            if step is None or self.progress.status != JOB_RUNNING:
                return
            if step.state != STEP_RUNNING:
                return
            if total is not None:
                step.total = _bounded_count(total)
            if (counted := _bounded_count(done)) is not None:
                # Counters only ever grow inside one step.
                step.done = max(step.done or 0, counted)
            if determinate is not None:
                step.determinate = determinate
            if detail is not None:
                step.detail = detail
            resolved = self._resolve_percent(step, percent)
            if resolved is not None:
                step.percent = max(step.percent or 0, resolved)
            step.heartbeat_at = self._now()
            self.progress.updated_at = step.heartbeat_at
            self.progress.recalculate()
            bucket = self._activity_bucket_locked(step)
        if bucket is not None:
            self._record_activity(key, "changed", {"progress_percent": bucket})
        self._emit()

    @staticmethod
    def _resolve_percent(step: StepProgress, percent: int | None) -> int | None:
        """Return the step percentage from an explicit value or byte counters."""
        explicit = _bounded_percent(percent)
        if explicit is not None:
            return explicit
        if step.total and step.done is not None:
            return max(0, min(step.done * 100 // step.total, 100))
        return None

    def _activity_bucket_locked(self, step: StepProgress) -> int | None:
        """Return a new ten-percent bucket for the activity journal, or None."""
        if not step.determinate or step.percent is None:
            return None
        bucket = step.percent // ACTIVITY_PERCENT_STEP * ACTIVITY_PERCENT_STEP
        if bucket <= 0 or bucket <= self._last_activity_bucket.get(step.key, 0):
            return None
        self._last_activity_bucket[step.key] = bucket
        return bucket

    def heartbeat(self, key: str | None = None) -> None:
        """Refresh the sign of life of an indeterminate step."""
        with self._lock:
            step = self.progress.step(key) if key else self._current_locked()
            if step is None or step.state != STEP_RUNNING:
                return
            moment = self._now()
            previous = step.heartbeat_at
            if previous is not None:
                elapsed = (moment - previous).total_seconds()
                if elapsed < HEARTBEAT_INTERVAL_SECONDS:
                    return
            step.heartbeat_at = moment
            self.progress.updated_at = moment
        self._emit()

    def apply_runner_state(self, payload: Mapping[str, Any]) -> None:
        """Adopt one authenticated runner status payload."""
        with self._lock:
            if self.progress.status != JOB_RUNNING:
                return
            version = payload.get("runner_version")
            if isinstance(version, str) and version:
                self.progress.runner_version = version[:64]
            self.progress.source = SOURCE_RUNNER
            events = payload.get("events")
            if isinstance(events, list):
                self._apply_runner_events_locked(events)
            steps = payload.get("steps")
            step_payload = payload.get("step")
            if isinstance(steps, Iterable) and not isinstance(steps, (str, bytes)):
                self._apply_runner_steps_locked(steps)
            if isinstance(step_payload, Mapping):
                self._apply_runner_step_locked(step_payload)
            elif not isinstance(steps, Iterable) or isinstance(steps, (str, bytes)):
                self._apply_runner_stage_locked(payload)
            self.progress.updated_at = self._now()
            self.progress.recalculate()
        self._emit()

    def _apply_runner_events_locked(self, events: Iterable[Any]) -> None:
        """Adopt the bounded boot milestones a runner reports."""
        for event in events:
            key = event.get("key") if isinstance(event, Mapping) else event
            if key in RUNTIME_EVENT_KEYS and key not in self.progress.events:
                self.progress.events.append(key)

    def _apply_runner_steps_locked(self, steps: Iterable[Any]) -> None:
        """Copy bounded step states reported by a runner that knows them."""
        for entry in steps:
            if not isinstance(entry, Mapping):
                continue
            step = self.progress.step(str(entry.get("key")))
            if step is None:
                continue
            state = entry.get("state")
            if state in STEP_STATES:
                step.state = state
            percent = _bounded_percent(entry.get("percent"))
            if percent is not None:
                step.percent = max(step.percent or 0, percent)

    def _apply_runner_step_locked(self, payload: Mapping[str, Any]) -> None:
        """Copy the currently running step reported by a runner."""
        step = self.progress.step(str(payload.get("key")))
        if step is None:
            return
        determinate = payload.get("determinate")
        if isinstance(determinate, bool):
            step.determinate = determinate
        reported = payload.get("state")
        step.state = reported if reported in STEP_STATES else STEP_RUNNING
        step.started_at = step.started_at or self._now()
        total = _bounded_count(payload.get("total"))
        done = _bounded_count(payload.get("done"))
        if total is not None:
            step.total = total
        if done is not None:
            step.done = done
        unit = payload.get("unit")
        step.unit = unit if isinstance(unit, str) and unit else step.unit
        detail = payload.get("detail")
        step.detail = detail[:120] if isinstance(detail, str) and detail else None
        resolved = self._resolve_percent(step, payload.get("percent"))
        if resolved is not None:
            step.percent = max(step.percent or 0, resolved)
        step.heartbeat_at = _parse_timestamp(payload.get("heartbeat_at")) or self._now()
        self._mark_previous_steps_locked(step.key)
        self.progress.current_step = step.key

    def _apply_runner_stage_locked(self, payload: Mapping[str, Any]) -> None:
        """Derive a coarse state from a protocol-2 runner without step data."""
        stage = payload.get("stage")
        step = self.progress.step(str(stage))
        if step is None:
            return
        step.determinate = False
        step.state = STEP_RUNNING
        step.percent = None
        step.started_at = step.started_at or self._now()
        step.heartbeat_at = self._now()
        self._mark_previous_steps_locked(step.key)
        self.progress.current_step = step.key

    def _mark_previous_steps_locked(self, key: str) -> None:
        """Complete every step that precedes the reported one."""
        for item in self.progress.steps:
            if item.key == key:
                return
            if item.state in {STEP_PENDING, STEP_RUNNING}:
                item.state = STEP_PASSED
                item.percent = 100 if item.determinate else None
                item.finished_at = item.finished_at or self._now()

    def mark_indeterminate(self) -> None:
        """Mark every step as indeterminate for a runner without live data."""
        with self._lock:
            for item in self.progress.steps:
                item.determinate = False
                item.percent = None
            self.progress.updated_at = self._now()
        self._emit(force=True)

    # -- publication -------------------------------------------------------

    def _current_locked(self) -> StepProgress | None:
        """Return the currently running step."""
        if self.progress.current_step is None:
            return None
        return self.progress.step(self.progress.current_step)

    def snapshot(self) -> dict[str, Any]:
        """Return a consistent JSON-safe snapshot."""
        with self._lock:
            return self.progress.as_dict()

    def _should_publish_locked(self, moment: float) -> bool:
        """Return whether this change is significant enough to publish."""
        if self.progress.current_step != self._last_published_step:
            return True
        if self.progress.overall_percent != self._last_published_percent:
            return True
        if self._last_publish is None:
            return True
        return moment - self._last_publish >= PUBLISH_INTERVAL_SECONDS

    def _emit(self, *, force: bool = False) -> None:
        """Hand one throttled publication to the event loop."""
        if self._publish is None:
            return
        moment = self._monotonic()
        with self._lock:
            if not force and not self._should_publish_locked(moment):
                return
            self._last_publish = moment
            self._last_published_percent = self.progress.overall_percent
            self._last_published_step = self.progress.current_step
        self._dispatch(self._publish)

    def _dispatch(self, action: Callable[[], None]) -> None:
        """Run one callback on the event loop, from any thread."""
        loop = self._loop
        if loop is None:
            action()
            return
        try:
            import asyncio

            running = asyncio.get_running_loop()
        except (ImportError, RuntimeError):
            running = None
        if running is loop:
            action()
            return
        loop.call_soon_threadsafe(action)

    def _record_activity(self, key: str, outcome: str, details: dict[str, Any]) -> None:
        """Write one bounded journal record for a step transition."""
        if self._activity is None:
            return
        self._dispatch(lambda: self._activity(key, outcome, details))
