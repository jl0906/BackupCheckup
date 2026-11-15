"""Exercise the runner's step model without a Home Assistant image."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import tempfile
import threading
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = (
    ROOT
    / "runtime_runner"
    / "rootfs"
    / "opt"
    / "backup-checkup-runner"
    / "server.py"
)


def _load_server() -> ModuleType:
    """Import the runner module with the securetar dependency stubbed out."""
    securetar = ModuleType("securetar")
    securetar.SecureTarArchive = object
    sys.modules.setdefault("securetar", securetar)
    spec = importlib.util.spec_from_file_location("runner_server_progress", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load runner server module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


def _run(server, archive_size: int = 1000):
    """Return one RunState that is not attached to a manager."""
    run = server.RunState(
        "probe",
        Path("."),
        "reference",
        "0" * 64,
        archive_size,
        None,
        60,
        250_000_000_000,
        "runner",
    )
    run.lock = threading.Lock()
    return run


def _check_public_shape(server) -> None:
    """The status payload must expose the runner-3 fields additively."""
    run = _run(server)
    payload = run.public()
    for key in (
        "protocol",
        "status",
        "stage",
        "progress_percent",
        "runner_version",
        "step",
        "steps",
        "events",
        "backup_reference",
        "backup_sha256",
        "runner_id",
        "isolation_verified",
        "ready",
        "recovery_mode",
        "error_code",
    ):
        _require(key in payload, f"Runner status payload is missing {key!r}")
    _require(payload["protocol"] == 2, "The protocol version must stay 2")
    _require(payload["runner_version"] == "4", "This runner must report version 4")
    _require(
        [step["key"] for step in payload["steps"]] == list(server.RUNTIME_STEP_KEYS),
        "The step list must follow the shared step order",
    )
    _require(
        all(step["state"] == server.STEP_PENDING for step in payload["steps"]),
        "A fresh run must report only pending steps",
    )
    _require(payload["events"] == [], "A fresh run must not report boot events")


def _check_weighted_progress(server) -> None:
    """The overall percentage must follow the shared weights."""
    run = _run(server, archive_size=1000)
    run.begin("runtime_prepare", determinate=False)
    _require(
        run.progress_percent == 0,
        f"An indeterminate first step must stay at 0, got {run.progress_percent}",
    )
    run.begin("runtime_upload", determinate=True, total=1000, unit="bytes")
    run.measure("runtime_upload", done=500, total=1000)
    _require(
        run.progress_percent == 15,
        f"3 + half of 25 must be 15, got {run.progress_percent}",
    )
    run.finish_step("runtime_upload")
    run.begin("runtime_restore", determinate=True, total=1000, unit="bytes")
    run.measure("runtime_restore", done=500, total=1000)
    _require(
        run.progress_percent == 43,
        f"3 + 25 + half of 30 must be 43, got {run.progress_percent}",
    )
    run.measure("runtime_restore", done=100, total=1000)
    _require(
        run.progress_percent == 43,
        "A smaller late measurement must not move the bar backwards",
    )
    payload = run.public()
    _require(payload["step"]["key"] == "runtime_restore", "The step must be current")
    _require(payload["step"]["done"] == 500, "The step must carry real byte counts")
    _require(payload["step"]["unit"] == "bytes", "The step must carry its unit")


def _check_failed_run_keeps_position(server) -> None:
    """A failed run must never claim a completed pipeline."""
    run = _run(server)
    run.begin("runtime_prepare", determinate=False)
    run.begin("runtime_upload", determinate=True, total=1000)
    run.measure("runtime_upload", done=1000, total=1000)
    run.finish_step("runtime_upload")
    run.begin("runtime_boot", determinate=False)
    before = run.progress_percent
    run.fail_open()
    _require(
        run.progress_percent == before,
        f"A failed run must stop at {before}, got {run.progress_percent}",
    )
    payload = run.public()
    states = {step["key"]: step["state"] for step in payload["steps"]}
    _require(
        states["runtime_boot"] == server.STEP_FAILED,
        "The running step must fail with the run",
    )
    _require(
        states["runtime_complete"] == server.STEP_FAILED,
        "A failed run must not report a completed final step",
    )


def _check_events(server) -> None:
    """Boot events are recorded once and stay bounded."""
    run = _run(server)
    run.record_event("process_started")
    run.record_event("process_started")
    run.record_event("definitely_not_an_event")
    run.record_event("port_listening")
    keys = [event["key"] for event in run.public()["events"]]
    _require(
        keys == ["process_started", "port_listening"],
        f"Unexpected recorded events: {keys}",
    )
    for index in range(server.MAX_RUN_EVENTS + 5):
        run.record_event(server.RUNTIME_EVENT_KEYS[index % len(server.RUNTIME_EVENT_KEYS)])
    _require(
        len(run.public()["events"]) <= server.MAX_RUN_EVENTS,
        "The event list must stay bounded",
    )


def _check_health_payload(server) -> None:
    """The health endpoint must advertise the runner-3 capabilities."""
    _require(
        set(server.CAPABILITIES) == {"step_progress", "boot_events"},
        f"Unexpected runner capabilities: {server.CAPABILITIES}",
    )
    _require(
        server.Handler.server_version == "BackupCheckupRuntime/4",
        f"Unexpected server banner: {server.Handler.server_version}",
    )


def _manager(server):
    """Return a RunManager that never touched the filesystem."""
    manager = server.RunManager.__new__(server.RunManager)
    manager._lock = threading.Lock()
    manager._runs = {}
    return manager


def _check_finish_after_failure(server) -> None:
    """A failed run must not report the steps it never reached as passed."""
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        run = _run(server)
        run.directory = directory
        run.begin("runtime_prepare", determinate=False)
        run.begin("runtime_upload", determinate=True, total=1000)
        run.measure("runtime_upload", done=1000, total=1000)
        run.finish_step("runtime_upload")
        run.begin("runtime_boot", determinate=False)
        run.pending_status = "failed"
        run.error_code = "home_assistant_exited"
        before = run.progress_percent

        _manager(server)._finish_run(run)

        payload = run.public()
        states = {step["key"]: step["state"] for step in payload["steps"]}
        for key in ("runtime_boot", "runtime_probe", "runtime_complete"):
            _require(
                states[key] == server.STEP_FAILED,
                f"{key} must not be reported as passed after a failure, "
                f"got {states[key]}",
            )
        _require(
            states["runtime_cleanup"] == server.STEP_PASSED,
            "The cleanup step itself really ran",
        )
        _require(
            payload["progress_percent"] <= before + 5,
            f"A failed run must not climb to {payload['progress_percent']}%",
        )
        _require(
            payload["progress_percent"] < 100,
            "A failed run must never report a complete pipeline",
        )
        _require(payload["status"] == "failed", "The staged status must be published")
        _require(
            payload["checked_at"] is not None
            and payload["duration_seconds"] is not None,
            "A terminal answer must already carry its timestamp and duration",
        )


def _check_terminal_status_carries_evidence(server) -> None:
    """The status only becomes terminal once the evidence fields are set."""
    with tempfile.TemporaryDirectory() as temporary:
        run = _run(server)
        run.directory = Path(temporary)
        run.begin("runtime_prepare", determinate=False)
        run.pending_status = "passed"
        run.ready = True
        run.isolation_verified = True
        _require(
            run.public()["status"] == "running",
            "A staged result must stay non-terminal until it is complete",
        )
        _manager(server)._finish_run(run)
        payload = run.public()
        _require(payload["status"] == "passed", "The result must become terminal")
        _require(
            payload["progress_percent"] == 100,
            f"A passed run must reach 100 %, got {payload['progress_percent']}",
        )
        _require(
            payload["checked_at"] is not None,
            "A terminal answer must carry checked_at",
        )


def _check_indeterminate_restore(server) -> None:
    """An unmeasurable extraction is reported as indeterminate, not as zero."""
    run = _run(server)
    run.begin("runtime_restore", determinate=True, unit="bytes")
    report = server.RunManager._restore_progress(run)
    report(None, 0)
    step = run.public()["step"]
    _require(step["key"] == "runtime_restore", "The restore step must be current")
    _require(
        step["determinate"] is False,
        "An unmeasurable extraction must be reported as indeterminate",
    )
    _require(step["percent"] is None, "An indeterminate step reports no percentage")

    measured = _run(server)
    measured.begin("runtime_restore", determinate=True, unit="bytes")
    server.RunManager._restore_progress(measured)(400, 800)
    measured_step = measured.public()["step"]
    _require(
        measured_step["total"] == 800 and measured_step["done"] == 400,
        f"The inner archive size must be the reference, got {measured_step}",
    )
    _require(
        measured_step["percent"] == 50,
        f"Half of the inner archive must be 50 %, got {measured_step['percent']}",
    )


def _check_protocol_2_compatibility(server) -> None:
    """A BackupCheckup 3.1.0 client must still understand this runner.

    The extra runner-3 fields are additive, and the HMAC covers the whole
    payload on both sides, so an older client keeps verifying the evidence.
    """
    run = _run(server)
    run.begin("runtime_prepare", determinate=False)
    run.begin("runtime_complete", determinate=False)
    run.finish_step("runtime_complete")
    run.status = "passed"
    run.checked_at = "2026-01-01T00:00:00+00:00"
    run.duration_seconds = 12.0
    run.ready = True
    run.isolation_verified = True

    server.TOKEN = "compatibility-probe-token"
    payload = run.public()
    signed = server._signed_payload(payload)

    # The verification an older integration performs, character for character.
    unsigned = {key: value for key, value in signed.items() if key != "signature"}
    message = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    expected = hmac.new(
        server.TOKEN.encode(), message, hashlib.sha256
    ).hexdigest()
    _require(
        hmac.compare_digest(signed["signature"], expected),
        "A protocol-2 client must be able to verify the signed evidence",
    )

    legacy_stages = {
        "runtime_prepare", "runtime_upload", "runtime_restore",
        "runtime_boot", "runtime_probe", "runtime_cleanup", "runtime_complete",
    }
    _require(
        signed["stage"] in legacy_stages,
        f"stage {signed['stage']!r} is unknown to a 3.1.0 client",
    )
    _require(
        isinstance(signed["progress_percent"], int)
        and 0 <= signed["progress_percent"] <= 100,
        "progress_percent must stay a bounded integer",
    )
    for key, kind in (
        ("status", str),
        ("backup_reference", str),
        ("backup_sha256", str),
        ("runner_id", str),
        ("isolation_verified", bool),
        ("ready", bool),
        ("recovery_mode", bool),
    ):
        _require(
            isinstance(signed[key], kind),
            f"{key} must stay a {kind.__name__} for older clients",
        )
    _require(
        signed["status"] in {"passed", "failed", "aborted", "inconclusive"},
        "A terminal status must stay one an older client knows",
    )


def main() -> None:
    """Run every runner progress assertion."""
    server = _load_server()
    _check_public_shape(server)
    _check_weighted_progress(server)
    _check_failed_run_keeps_position(server)
    _check_events(server)
    _check_health_payload(server)
    _check_finish_after_failure(server)
    _check_terminal_status_carries_evidence(server)
    _check_indeterminate_restore(server)
    _check_protocol_2_compatibility(server)
    print("Runner progress model passed")


if __name__ == "__main__":
    main()
