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

SANDBOX_UID = 65534
SANDBOX_GID = 65534
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
MAX_VIRTUAL_MEMORY_BYTES = 8 * 1024 * 1024 * 1024
MAX_OUTPUT_FILE_BYTES = 2 * 1024 * 1024 * 1024
STARTUP_LOG_TAIL_BYTES = 128 * 1024
STARTUP_ERROR_SIGNATURES = (
    (
        "home_assistant_memory_limit",
        ("memoryerror", "cannot allocate memory", "failed to map segment"),
    ),
    (
        "home_assistant_file_limit",
        ("file size limit exceeded", "errno 27"),
    ),
    (
        "home_assistant_permission_denied",
        ("permissionerror", "permission denied"),
    ),
    (
        "home_assistant_runtime_missing",
        ("no module named homeassistant",),
    ),
    (
        "home_assistant_cli_incompatible",
        ("unrecognized arguments",),
    ),
)


def _sandbox_environment(home: Path) -> dict[str, str]:
    """Return a minimal environment with no inherited runner credentials."""
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "PATH": SAFE_PATH,
        "PYTHONUNBUFFERED": "1",
    }


def _sandbox_command(command: list[str]) -> list[str]:
    """Drop identity, capabilities, privilege gains, and basic process limits."""
    return [
        "setpriv",
        f"--reuid={SANDBOX_UID}",
        f"--regid={SANDBOX_GID}",
        "--clear-groups",
        "--bounding-set=-all",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        "--no-new-privs",
        "--",
        "prlimit",
        f"--as={MAX_VIRTUAL_MEMORY_BYTES}:{MAX_VIRTUAL_MEMORY_BYTES}",
        "--nproc=256:256",
        "--nofile=1024:1024",
        f"--fsize={MAX_OUTPUT_FILE_BYTES}:{MAX_OUTPUT_FILE_BYTES}",
        "--core=0:0",
        "--",
        *command,
    ]


def _sandbox_preflight(config_dir: Path) -> bool:
    """Verify the exact privilege boundary used for Home Assistant."""
    check = (
        "import os,pathlib;"
        "s={};"
        "[s.setdefault(*line.split(':',1)) for line in "
        "pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line];"
        f"ok=os.getuid()=={SANDBOX_UID} and os.getgid()=={SANDBOX_GID} "
        "and 'SUPERVISOR_TOKEN' not in os.environ "
        "and int(s.get('CapEff','1').strip(),16)==0 "
        "and s.get('NoNewPrivs','').strip()=='1';"
        "raise SystemExit(0 if ok else 1)"
    )
    try:
        completed = subprocess.run(
            _sandbox_command([sys.executable, "-c", check]),
            check=False,
            cwd=config_dir,
            env=_sandbox_environment(config_dir.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


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


def _classify_startup_failure(log_path: Path, *, timed_out: bool) -> str:
    """Map a bounded log tail to one stable, non-sensitive error code."""
    if timed_out:
        return "home_assistant_start_timeout"
    try:
        with log_path.open("rb") as log_file:
            log_file.seek(0, os.SEEK_END)
            size = log_file.tell()
            log_file.seek(max(0, size - STARTUP_LOG_TAIL_BYTES))
            tail = log_file.read(STARTUP_LOG_TAIL_BYTES).decode(
                "utf-8", errors="replace"
            )
    except OSError:
        return "home_assistant_exited"
    normalized = tail.casefold()
    for error_code, signatures in STARTUP_ERROR_SIGNATURES:
        if any(signature in normalized for signature in signatures):
            return error_code
    return "home_assistant_exited"


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

    if not _sandbox_preflight(config_dir):
        _write_json(
            result_path,
            {
                "ready": False,
                "isolation_verified": False,
                "recovery_mode": True,
                "error_code": "sandbox_preflight_failed",
            },
        )
        return 3

    log_path = config_dir.parent / "ephemeral-home-assistant.log"
    command = _sandbox_command([
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
    ])
    started = time.monotonic()
    with log_path.open("ab", buffering=0) as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=config_dir,
            env=_sandbox_environment(config_dir.parent),
            start_new_session=True,
            close_fds=True,
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
        result["error_code"] = _classify_startup_failure(
            log_path,
            timed_out=timed_out,
        )
    _write_json(result_path, result)
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
