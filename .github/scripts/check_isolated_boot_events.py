"""Verify the isolated boot reports events instead of a time estimate."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOT_PATH = (
    ROOT
    / "runtime_runner"
    / "rootfs"
    / "opt"
    / "backup-checkup-runner"
    / "isolated_boot.py"
)


def _load_boot():
    """Import the isolated boot helper directly."""
    spec = importlib.util.spec_from_file_location("runner_isolated_boot", BOOT_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load the isolated boot module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


def _check_no_time_estimate() -> None:
    """The removed estimate must not come back through a copy-paste."""
    source = BOOT_PATH.read_text(encoding="utf-8")
    for marker in ("progress_percent\": percent", "72 + int(", "min(94,"):
        _require(
            marker not in source,
            f"The boot progress estimate is back: {marker!r}",
        )
    _require(
        "_port_is_listening" in source,
        "The boot probe must detect a listening port",
    )


def _check_event_order(boot) -> None:
    """Events are written once, in order, and always with a heartbeat."""
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "progress.json"
        progress = boot._Progress(path)
        progress.stage("runtime_boot")
        first = json.loads(path.read_text(encoding="utf-8"))
        _require(first["stage"] == "runtime_boot", "The first phase must be the boot")
        _require(
            first["determinate"] is False,
            "The isolated boot must never claim measurable progress",
        )
        _require("heartbeat_at" in first, "Every write must carry a heartbeat")

        for event in ("sandbox_preflight_ok", "process_started", "process_started"):
            progress.event(event)
        progress.stage("runtime_probe")
        progress.event("port_listening")
        progress.event("http_responding")
        final = json.loads(path.read_text(encoding="utf-8"))
        _require(
            final["events"]
            == [
                "sandbox_preflight_ok",
                "process_started",
                "port_listening",
                "http_responding",
            ],
            f"Unexpected event order: {final['events']}",
        )
        _require(final["stage"] == "runtime_probe", "The probe phase must be current")

        progress.stage("runtime_cleanup")
        cleanup = json.loads(path.read_text(encoding="utf-8"))
        _require(
            cleanup["stage"] == "runtime_cleanup",
            "The cleanup phase must be published",
        )
        _require(
            not list(path.parent.glob("*.tmp")),
            "The atomic write must not leave a temporary file behind",
        )


class _FakeSocket:
    """Minimal context manager standing in for an accepted connection."""

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _check_socket_probe(boot) -> None:
    """The port probe follows the loopback socket, not a timer."""
    original_port = boot.HOME_ASSISTANT_PORT
    original_create = boot.socket.create_connection
    try:
        # Port 1 is never served by the isolated instance.
        boot.HOME_ASSISTANT_PORT = 1
        _require(
            boot._port_is_listening() is False,
            "A closed port must not be reported as listening",
        )

        attempts: list[tuple] = []

        def _accept(address, timeout=None):
            attempts.append((address, timeout))
            return _FakeSocket()

        boot.socket.create_connection = _accept
        boot.HOME_ASSISTANT_PORT = 8123
        _require(
            boot._port_is_listening() is True,
            "An accepted connection must be reported as listening",
        )
        _require(
            attempts and attempts[0][0] == ("127.0.0.1", 8123),
            f"The probe must target the loopback port, got {attempts}",
        )

        def _refuse(_address, timeout=None):
            raise OSError("connection refused")

        boot.socket.create_connection = _refuse
        _require(
            boot._port_is_listening() is False,
            "A refused connection must not be reported as listening",
        )
    finally:
        boot.socket.create_connection = original_create
        boot.HOME_ASSISTANT_PORT = original_port


def main() -> None:
    """Run every isolated-boot assertion."""
    boot = _load_boot()
    _check_no_time_estimate()
    _check_event_order(boot)
    _check_socket_probe(boot)
    print("Isolated boot events passed")


if __name__ == "__main__":
    main()
