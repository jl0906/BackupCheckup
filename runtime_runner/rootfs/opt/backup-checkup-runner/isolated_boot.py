"""Boot one restored Home Assistant configuration inside a network namespace."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _write_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _progress(path: Path, stage: str, percent: int) -> None:
    _write_json(path, {"stage": stage, "progress_percent": percent})


def _endpoint_ready() -> bool:
    try:
        # This is a loopback-only readiness probe inside the isolated namespace.
        with urllib.request.urlopen(
            "http://127.0.0.1:8123/", timeout=2
        ) as response:
            return 100 <= response.status < 500
    except urllib.error.HTTPError as err:
        return 100 <= err.code < 500
    except OSError:
        return False


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def main() -> int:
    if len(sys.argv) != 5:
        return 2
    config_dir = Path(sys.argv[1]).resolve()
    progress_path = Path(sys.argv[2]).resolve()
    result_path = Path(sys.argv[3]).resolve()
    timeout_seconds = max(60, int(sys.argv[4]))

    subprocess.run(
        ["ip", "link", "set", "lo", "up"],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    _progress(progress_path, "runtime_boot", 65)

    log_path = config_dir.parent / "ephemeral-home-assistant.log"
    command = [
        sys.executable,
        "-m",
        "homeassistant",
        "--config",
        str(config_dir),
        "--recovery-mode",
        "--skip-pip",
        "--log-no-color",
        "--log-file",
        str(log_path),
    ]
    started = time.monotonic()
    with log_path.open("ab", buffering=0) as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            _progress(progress_path, "runtime_probe", 72)
            ready = False
            timed_out = False
            while time.monotonic() - started < timeout_seconds:
                if process.poll() is not None:
                    break
                if _endpoint_ready():
                    ready = True
                    break
                elapsed = time.monotonic() - started
                percent = min(94, 72 + int(22 * elapsed / timeout_seconds))
                _progress(progress_path, "runtime_probe", percent)
                time.sleep(1)
            timed_out = not ready and process.poll() is None
        finally:
            _progress(progress_path, "runtime_cleanup", 96)
            _stop_process(process)

    try:
        from homeassistant.const import __version__ as home_assistant_version
    except ImportError:
        home_assistant_version = None
    result: dict[str, object] = {
        "ready": ready,
        "isolation_verified": True,
        "recovery_mode": True,
        "home_assistant_version": home_assistant_version,
        "child_exit_code": process.returncode,
    }
    if not ready:
        result["error_code"] = (
            "home_assistant_start_timeout" if timed_out else "home_assistant_exited"
        )
    _write_json(result_path, result)
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
