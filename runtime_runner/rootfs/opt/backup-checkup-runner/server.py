"""Authenticated BackupCheckup protocol-v1 runtime runner."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from securetar import SecureTarArchive

PROTOCOL_VERSION = 1
RUNNER_VERSION = "3.0.11"
LISTEN_PORT = 8099
DATA_DIR = Path("/data")
TOKEN_PATH = DATA_DIR / "api_token"
OPTIONS_PATH = DATA_DIR / "options.json"
TLS_CERT_PATH = DATA_DIR / "runner.crt"
TLS_KEY_PATH = DATA_DIR / "runner.key"
RUN_ROOT = Path("/run/backup-checkup-runtime")
ISOLATED_BOOT = Path("/opt/backup-checkup-runner/isolated_boot.py")
# Home Assistant exposes this mandatory authenticated proxy only on its private
# app network. It is never used for client traffic or outside the Supervisor.
SUPERVISOR_API = "http://supervisor"  # NOSONAR
BACKUP_METADATA_NAME = "backup.json"
BACKUP_METADATA_PATH = (BACKUP_METADATA_NAME,)
CHUNK_SIZE = 1024 * 1024
MAX_REQUEST_JSON = 64 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_MEMBERS = 1_000_000
MAX_ARCHIVE_PATH_LENGTH = 4096
MAX_ARCHIVE_PATH_DEPTH = 64
SANDBOX_UID = 65534
SANDBOX_GID = 65534
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
CLIENT_SOCKET_TIMEOUT = 30
CHILD_ERROR_CODES = frozenset(
    {
        "home_assistant_cli_incompatible",
        "home_assistant_exited",
        "home_assistant_file_limit",
        "home_assistant_memory_limit",
        "home_assistant_permission_denied",
        "home_assistant_runtime_missing",
        "home_assistant_start_timeout",
        "sandbox_preflight_failed",
    }
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s backup_checkup.runner %(message)s",
)
_LOGGER = logging.getLogger("backup_checkup.runner")


class RunnerFailure(Exception):
    """One stable runner error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _load_options() -> dict[str, int]:
    defaults = {
        "maximum_archive_gb": 50,
        "maximum_expanded_gb": 250,
        "runtime_timeout_minutes": 20,
    }
    try:
        value = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(value, dict):
        return defaults
    result = dict(defaults)
    for key, default in defaults.items():
        candidate = value.get(key)
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            result[key] = candidate
        else:
            result[key] = default
    return result


def _load_or_create_token() -> str:
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)
    try:
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if len(token) < 32:
        token = secrets.token_urlsafe(48)
        temporary = TOKEN_PATH.with_suffix(".tmp")
        temporary.write_text(token, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, TOKEN_PATH)
    os.chmod(TOKEN_PATH, 0o600)
    return token


def _load_or_create_tls_certificate() -> str:
    """Return a persistent self-signed certificate for pinned internal TLS."""
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        context.load_cert_chain(TLS_CERT_PATH, TLS_KEY_PATH)
        return TLS_CERT_PATH.read_text(encoding="ascii")
    except OSError:
        TLS_CERT_PATH.unlink(missing_ok=True)
        TLS_KEY_PATH.unlink(missing_ok=True)

    temporary_cert = TLS_CERT_PATH.with_suffix(".crt.tmp")
    temporary_key = TLS_KEY_PATH.with_suffix(".key.tmp")
    temporary_cert.unlink(missing_ok=True)
    temporary_key.unlink(missing_ok=True)
    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-sha256",
                "-nodes",
                "-days",
                "3650",
                "-subj",
                "/CN=backup-checkup-runtime",
                "-keyout",
                str(temporary_key),
                "-out",
                str(temporary_cert),
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        os.chmod(temporary_cert, 0o600)
        os.chmod(temporary_key, 0o600)
        os.replace(temporary_cert, TLS_CERT_PATH)
        os.replace(temporary_key, TLS_KEY_PATH)
        context.load_cert_chain(TLS_CERT_PATH, TLS_KEY_PATH)
        return TLS_CERT_PATH.read_text(encoding="ascii")
    finally:
        temporary_cert.unlink(missing_ok=True)
        temporary_key.unlink(missing_ok=True)


def _probe_isolation() -> bool:
    try:
        completed = subprocess.run(
            _namespace_command(["ip", "link", "set", "lo", "up"]),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _namespace_command(command: list[str]) -> list[str]:
    """Run a command without access to the runner's network."""
    return [
        "unshare",
        "--net",
        "--fork",
        "--kill-child",
        *command,
    ]


def _sandbox_environment(home: Path) -> dict[str, str]:
    """Return the complete, secret-free environment for isolated processes."""
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "PATH": SAFE_PATH,
        "PYTHONUNBUFFERED": "1",
    }


def _safe_run_id(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name
        or len(name) > MAX_ARCHIVE_PATH_LENGTH
        or len(path.parts) > MAX_ARCHIVE_PATH_DEPTH
        or path.is_absolute()
        or ".." in path.parts
        or "\x00" in name
    ):
        raise RunnerFailure("unsafe_archive_path")
    return path


def _find_backup_metadata_member(archive: tarfile.TarFile) -> tarfile.TarInfo:
    """Locate the single root metadata file while validating every path."""
    member = None
    for members, candidate in enumerate(archive, start=1):
        if members > MAX_MEMBERS:
            raise RunnerFailure("archive_member_limit")
        candidate_path = _safe_member_path(candidate.name)
        if (
            candidate_path.name == BACKUP_METADATA_NAME
            and candidate_path.parts != BACKUP_METADATA_PATH
        ):
            raise RunnerFailure("backup_metadata_invalid")
        if candidate_path.parts == BACKUP_METADATA_PATH:
            if member is not None:
                raise RunnerFailure("backup_metadata_invalid")
            member = candidate
    if member is None:
        raise RunnerFailure("backup_metadata_missing")
    return member


def _read_backup_metadata(archive_path: Path, password: str | None) -> dict[str, Any]:
    with SecureTarArchive(archive_path, "r", password=password) as outer:
        member = _find_backup_metadata_member(outer.tar)
        if not member.isfile() or member.size > MAX_METADATA_BYTES:
            raise RunnerFailure("backup_metadata_invalid")
        reader = outer.tar.extractfile(member)
        if reader is None:
            raise RunnerFailure("backup_metadata_unreadable")
        with closing(reader):
            raw = reader.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise RunnerFailure("backup_metadata_too_large")
    try:
        metadata = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise RunnerFailure("backup_metadata_invalid") from err
    if not isinstance(metadata, dict):
        raise RunnerFailure("backup_metadata_invalid")
    return metadata


@contextmanager
def _homeassistant_stream(
    archive_path: Path, password: str | None
) -> Iterator[BinaryIO]:
    metadata = _read_backup_metadata(archive_path, password)
    protected = metadata.get("protected") is True
    if protected and not password:
        raise RunnerFailure("password_required")
    with SecureTarArchive(archive_path, "r", password=password) as outer:
        candidates = []
        for members, member in enumerate(outer.tar, start=1):
            if members > MAX_MEMBERS:
                raise RunnerFailure("archive_member_limit")
            member_path = _safe_member_path(member.name)
            if len(member_path.parts) == 1 and member_path.name in {
                "homeassistant.tar",
                "homeassistant.tar.gz",
                "homeassistant.tgz",
            }:
                candidates.append(member)
        if len(candidates) != 1:
            raise RunnerFailure("homeassistant_archive_missing")
        member = candidates[0]
        if protected:
            with outer.extract_tar(member) as stream:
                yield stream
            return
        reader = outer.tar.extractfile(member)
        if reader is None:
            raise RunnerFailure("homeassistant_archive_unreadable")
        with closing(reader):
            yield reader


def _extract_homeassistant(
    archive_path: Path,
    target: Path,
    password: str | None,
    maximum_expanded_bytes: int,
) -> Path:
    target.mkdir(mode=0o700, parents=True)
    expanded = 0
    members = 0
    with (
        _homeassistant_stream(archive_path, password) as stream,
        tarfile.open(fileobj=stream, mode="r|*") as inner,
    ):
        for member in inner:
            members += 1
            if members > MAX_MEMBERS:
                raise RunnerFailure("archive_member_limit")
            path = _safe_member_path(member.name)
            destination = target.joinpath(*path.parts)
            if member.isdir():
                destination.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RunnerFailure("unsupported_archive_member")
            expanded += member.size
            if expanded > maximum_expanded_bytes:
                raise RunnerFailure("expanded_size_limit")
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            reader = inner.extractfile(member)
            if reader is None:
                raise RunnerFailure("archive_member_unreadable")
            with closing(reader), destination.open("xb") as output:
                os.chmod(destination, 0o600)
                while chunk := reader.read(CHUNK_SIZE):
                    output.write(chunk)
    config_dir = target / "data"
    if not config_dir.is_dir():
        raise RunnerFailure("homeassistant_config_missing")
    return config_dir


@dataclass(slots=True)
class RunState:
    run_id: str
    directory: Path
    backup_reference: str
    backup_sha256: str
    archive_size: int
    password: str | None
    timeout_seconds: int
    runner_id: str
    status: str = "running"
    stage: str = "runtime_prepare"
    progress_percent: int = 0
    started_monotonic: float = field(default_factory=time.monotonic)
    checked_at: str | None = None
    duration_seconds: float | None = None
    ready: bool = False
    isolation_verified: bool = False
    recovery_mode: bool = True
    home_assistant_version: str | None = None
    error_code: str | None = None
    archive_verified: bool = False
    uploading: bool = False
    thread: threading.Thread | None = field(default=None, repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _logged_progress_percent: int = field(default=0, repr=False)

    @property
    def archive_path(self) -> Path:
        return self.directory / "backup.tar"

    def update(self, stage: str, percent: int) -> None:
        with self.lock:
            previous_stage = self.stage
            self.stage = stage
            self.progress_percent = max(self.progress_percent, min(100, percent))
            progress_bucket = self.progress_percent // 10 * 10
            first_bucket = self._logged_progress_percent + 10
            progress_updates = tuple(range(first_bucket, progress_bucket + 1, 10))
            if progress_updates:
                self._logged_progress_percent = progress_updates[-1]
        if stage != previous_stage:
            _LOGGER.info("run stage_changed stage=%s", stage)
        for progress in progress_updates:
            _LOGGER.info(
                "run progress stage=%s progress_percent=%d", stage, progress
            )

    def public(self) -> dict[str, Any]:
        with self.lock:
            return {
                "protocol": PROTOCOL_VERSION,
                "status": self.status,
                "stage": self.stage,
                "progress_percent": self.progress_percent,
                "backup_reference": self.backup_reference,
                "backup_sha256": self.backup_sha256,
                "checked_at": self.checked_at,
                "duration_seconds": self.duration_seconds,
                "runner_id": self.runner_id,
                "runner_version": RUNNER_VERSION,
                "home_assistant_version": self.home_assistant_version,
                "isolation_verified": self.isolation_verified,
                "ready": self.ready,
                "recovery_mode": self.recovery_mode,
                "error_code": self.error_code,
            }


class RunManager:
    def __init__(self, token: str, runner_id: str, options: dict[str, int]) -> None:
        self.token = token
        self.runner_id = runner_id
        self.options = options
        self.isolation_available = _probe_isolation()
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)
        RUN_ROOT.mkdir(mode=0o710, parents=True, exist_ok=True)
        os.chown(RUN_ROOT, 0, SANDBOX_GID)
        os.chmod(RUN_ROOT, 0o710)

    def create(self, payload: dict[str, Any]) -> RunState:
        if payload.get("protocol") != PROTOCOL_VERSION:
            raise RunnerFailure("protocol_mismatch")
        reference = payload.get("backup_reference")
        digest = payload.get("backup_sha256")
        archive_size = payload.get("archive_size")
        password = payload.get("password")
        timeout_seconds = payload.get("timeout_seconds")
        maximum_size = self.options["maximum_archive_gb"] * 1_000_000_000
        if not isinstance(reference, str) or not 1 <= len(reference) <= 160:
            raise RunnerFailure("backup_reference_invalid")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise RunnerFailure("backup_checksum_invalid")
        if (
            isinstance(archive_size, bool)
            or not isinstance(archive_size, int)
            or archive_size <= 0
            or archive_size > maximum_size
        ):
            raise RunnerFailure("archive_size_limit")
        if password is not None and (
            not isinstance(password, str) or len(password) > 1024
        ):
            raise RunnerFailure("password_invalid")
        configured_timeout = self.options["runtime_timeout_minutes"] * 60
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
            timeout_seconds = configured_timeout
        timeout_seconds = max(60, min(timeout_seconds, configured_timeout))
        with self._lock:
            if any(run.status == "running" for run in self._runs.values()):
                raise RunnerFailure("runner_busy")
            run_id = str(uuid.uuid4())
            directory = Path(tempfile.mkdtemp(prefix=f"{run_id}-", dir=RUN_ROOT))
            os.chown(directory, 0, SANDBOX_GID)
            os.chmod(directory, 0o710)
            run = RunState(
                run_id=run_id,
                directory=directory,
                backup_reference=reference,
                backup_sha256=digest,
                archive_size=archive_size,
                password=password,
                timeout_seconds=timeout_seconds,
                runner_id=self.runner_id,
            )
            self._runs[run_id] = run
            _LOGGER.info(
                "run created archive_bytes=%d timeout_seconds=%d",
                archive_size,
                timeout_seconds,
            )
            return run

    def get(self, run_id: str) -> RunState:
        with self._lock:
            run = self._runs.get(run_id)
        if run is None:
            raise RunnerFailure("run_not_found")
        return run

    def delete(self, run_id: str) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            if run.thread is not None and run.thread.is_alive():
                raise RunnerFailure("run_still_active")
            self._runs.pop(run_id, None)
        shutil.rmtree(run.directory, ignore_errors=True)
        _LOGGER.info("run deleted")

    def start(self, run: RunState) -> None:
        if not self.isolation_available:
            raise RunnerFailure("isolation_unavailable")
        with run.lock:
            if run.uploading or not run.archive_verified:
                raise RunnerFailure("archive_not_verified")
            if run.thread is not None:
                raise RunnerFailure("run_already_started")
            run.thread = threading.Thread(
                target=self._execute,
                args=(run,),
                name=f"runtime-{run.run_id}",
                daemon=True,
            )
            run.thread.start()
        _LOGGER.info("run started")

    def _execute(self, run: RunState) -> None:
        try:
            progress_path, result_path, command = self._prepare_runtime(run)
            process = self._start_runtime(command)
            self._wait_for_runtime(run, process, progress_path)
            self._apply_runtime_result(run, self._load_runtime_result(result_path))
        except RunnerFailure as err:
            run.status = self._failure_status(err.code)
            run.error_code = err.code
            _LOGGER.exception("run failed with controlled runner error")
        except Exception:
            run.status = "inconclusive"
            run.error_code = "runner_internal_error"
            _LOGGER.exception("run failed error_code=runner_internal_error")
        finally:
            self._finish_run(run)

    def _prepare_runtime(
        self, run: RunState
    ) -> tuple[Path, Path, list[str]]:
        """Extract the verified archive and construct the isolated command."""
        run.update("runtime_restore", 35)
        config_dir = _extract_homeassistant(
            run.archive_path,
            run.directory / "restored",
            run.password,
            self.options["maximum_expanded_gb"] * 1_000_000_000,
        )
        self._assign_sandbox_tree(config_dir.parent)
        run.password = None
        run.archive_path.unlink(missing_ok=True)
        run.update("runtime_restore", 58)
        _LOGGER.info("run archive_restored")
        progress_path = run.directory / "progress.json"
        result_path = run.directory / "result.json"
        command = _namespace_command([
            "python3",
            str(ISOLATED_BOOT),
            str(config_dir),
            str(progress_path),
            str(result_path),
            str(run.timeout_seconds),
        ])
        return progress_path, result_path, command

    @staticmethod
    def _assign_sandbox_tree(root: Path) -> None:
        """Give only the extracted copy to the unprivileged runtime account."""
        for directory, names, files in os.walk(root):
            current = Path(directory)
            os.chown(current, SANDBOX_UID, SANDBOX_GID)
            os.chmod(current, 0o700)
            for name in (*names, *files):
                child = current / name
                os.chown(child, SANDBOX_UID, SANDBOX_GID, follow_symlinks=False)

    @staticmethod
    def _start_runtime(command: list[str]) -> subprocess.Popen[bytes]:
        """Start the namespace owner and retain its error stream in app logs."""
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=None,
            env=_sandbox_environment(RUN_ROOT),
            close_fds=True,
        )

    @staticmethod
    def _read_runtime_progress(
        run: RunState, progress_path: Path, previous_mtime: int
    ) -> int:
        """Apply one valid child progress update and return its file version."""
        try:
            mtime = progress_path.stat().st_mtime_ns
            if mtime == previous_mtime:
                return previous_mtime
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return previous_mtime
        if not isinstance(progress, dict):
            return mtime
        stage = progress.get("stage")
        percent = progress.get("progress_percent")
        if isinstance(stage, str) and isinstance(percent, int):
            run.update(stage, percent)
        return mtime

    def _wait_for_runtime(
        self,
        run: RunState,
        process: subprocess.Popen[bytes],
        progress_path: Path,
    ) -> None:
        """Follow the child until completion or the hard timeout."""
        deadline = time.monotonic() + run.timeout_seconds + 45
        last_progress_mtime = 0
        while process.poll() is None and time.monotonic() < deadline:
            last_progress_mtime = self._read_runtime_progress(
                run, progress_path, last_progress_mtime
            )
            time.sleep(0.25)
        if process.poll() is not None:
            _LOGGER.info("run isolated_process_exited exit_code=%s", process.returncode)
            return
        _LOGGER.error("run isolated_process_timeout")
        self._stop_timed_out_process(process)
        raise RunnerFailure("runtime_timeout")

    @staticmethod
    def _stop_timed_out_process(process: subprocess.Popen[bytes]) -> None:
        """Terminate and, if required, kill a timed-out namespace owner."""
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    @staticmethod
    def _load_runtime_result(result_path: Path) -> dict[str, Any]:
        """Load one bounded-shape child result."""
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            raise RunnerFailure("runtime_result_missing") from err
        if not isinstance(result, dict):
            raise RunnerFailure("runtime_result_invalid")
        return result

    @staticmethod
    def _apply_runtime_result(run: RunState, result: dict[str, Any]) -> None:
        """Copy bounded evidence from the isolated child into public state."""
        run.ready = result.get("ready") is True
        run.isolation_verified = result.get("isolation_verified") is True
        run.recovery_mode = result.get("recovery_mode") is True
        version = result.get("home_assistant_version")
        run.home_assistant_version = version[:64] if isinstance(version, str) else None
        error_code = result.get("error_code")
        run.error_code = error_code if error_code in CHILD_ERROR_CODES else None
        run.status = (
            "passed"
            if run.ready and run.isolation_verified and run.recovery_mode
            else "failed"
        )
        _LOGGER.info(
            "run result_applied ready=%s isolation_verified=%s recovery_mode=%s has_error=%s",
            run.ready,
            run.isolation_verified,
            run.recovery_mode,
            run.error_code is not None,
        )

    @staticmethod
    def _failure_status(code: str) -> str:
        """Classify controlled resource failures separately from test failures."""
        return "aborted" if "limit" in code or "timeout" in code else "failed"

    @staticmethod
    def _cleanup_run(run: RunState) -> None:
        """Remove every sensitive artifact while retaining tiny result files."""
        for child in tuple(run.directory.iterdir()):
            if child.name in {"result.json", "progress.json"}:
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    def _finish_run(self, run: RunState) -> None:
        """Clear secrets, clean artifacts, and publish one terminal state."""
        run.password = None
        run.update("runtime_cleanup", 98)
        try:
            self._cleanup_run(run)
        except OSError:
            _LOGGER.exception("run cleanup_failed")
            if run.status == "passed":
                run.status = "inconclusive"
                run.error_code = "cleanup_failed"
        run.update("runtime_complete", 100)
        with run.lock:
            run.checked_at = datetime.now(UTC).isoformat()
            run.duration_seconds = round(
                time.monotonic() - run.started_monotonic, 2
            )
        _LOGGER.info(
            "run completed status=%s error_code=%s duration_seconds=%.2f",
            run.status,
            run.error_code or "none",
            run.duration_seconds,
        )


TOKEN: str
RUNNER_ID: str
TLS_CERTIFICATE: str
MANAGER: RunManager


def _initialize_runtime() -> None:
    """Initialize private persistent state immediately before serving requests."""
    global MANAGER, RUNNER_ID, TLS_CERTIFICATE, TOKEN
    TOKEN = _load_or_create_token()
    RUNNER_ID = hashlib.sha256(TOKEN.encode()).hexdigest()[:32]
    TLS_CERTIFICATE = _load_or_create_tls_certificate()
    MANAGER = RunManager(TOKEN, RUNNER_ID, _load_options())
    _LOGGER.info(
        "runner initialized version=%s isolation_available=%s",
        RUNNER_VERSION,
        MANAGER.isolation_available,
    )


def _signed_payload(payload: dict[str, Any]) -> dict[str, Any]:
    message = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return {
        **payload,
        "signature": hmac.new(TOKEN.encode(), message, hashlib.sha256).hexdigest(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BackupCheckupRuntime/3.0"

    def setup(self) -> None:
        """Bound slow or stalled clients before reading any request body."""
        super().setup()
        self.connection.settimeout(CLIENT_SOCKET_TIMEOUT)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {TOKEN}"
        return hmac.compare_digest(supplied, expected)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError as err:
            raise RunnerFailure("content_length_invalid") from err
        if not 0 < length <= MAX_REQUEST_JSON:
            raise RunnerFailure("request_size_invalid")
        try:
            payload = json.loads(self.rfile.read(length))
        except OSError as err:
            raise RunnerFailure("request_body_failed") from err
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise RunnerFailure("request_json_invalid") from err
        if not isinstance(payload, dict):
            raise RunnerFailure("request_json_invalid")
        return payload

    def _route_run_id(self, suffix: str = "") -> str | None:
        parts = self.path.split("?")[0].strip("/").split("/")
        expected_length = 4 if suffix else 3
        if len(parts) != expected_length or parts[:2] != ["v1", "runs"]:
            return None
        if suffix and parts[3] != suffix:
            return None
        return parts[2] if _safe_run_id(parts[2]) else None

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        _LOGGER.warning("request rejected error_code=unauthorized")
        return False

    def do_GET(self) -> None:
        if not self._require_auth():
            return
        if self.path == "/v1/health":
            self._json(
                HTTPStatus.OK,
                {
                    "protocol": PROTOCOL_VERSION,
                    "runner_id": RUNNER_ID,
                    "runner_version": RUNNER_VERSION,
                    "isolation_available": MANAGER.isolation_available,
                },
            )
            return
        run_id = self._route_run_id()
        if run_id is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = MANAGER.get(run_id).public()
        except RunnerFailure as err:
            self._json(HTTPStatus.NOT_FOUND, {"error": err.code})
            return
        if payload["status"] in {"passed", "failed", "aborted", "inconclusive"}:
            payload = _signed_payload(payload)
        self._json(HTTPStatus.OK, payload)

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        try:
            if self.path == "/v1/runs":
                run = MANAGER.create(self._read_json())
                self._json(HTTPStatus.CREATED, {"run_id": run.run_id})
                return
            run_id = self._route_run_id("start")
            if run_id is None:
                raise RunnerFailure("not_found")
            MANAGER.start(MANAGER.get(run_id))
            self._empty(HTTPStatus.ACCEPTED)
        except RunnerFailure as err:
            status = HTTPStatus.CONFLICT if err.code == "runner_busy" else HTTPStatus.BAD_REQUEST
            self._json(status, {"error": err.code})

    def do_PUT(self) -> None:
        if not self._require_auth():
            return
        run_id = self._route_run_id("archive")
        if run_id is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            run = MANAGER.get(run_id)
            length = int(self.headers.get("Content-Length", ""))
            if length != run.archive_size:
                raise RunnerFailure("archive_size_mismatch")
            with run.lock:
                if run.uploading or run.archive_verified or run.thread is not None:
                    raise RunnerFailure("archive_state_invalid")
                run.uploading = True
            digest = hashlib.sha256()
            remaining = length
            upload_verified = False
            try:
                with run.archive_path.open("xb") as output:
                    os.chmod(run.archive_path, 0o600)
                    while remaining:
                        chunk = self.rfile.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            raise RunnerFailure("archive_upload_incomplete")
                        output.write(chunk)
                        digest.update(chunk)
                        remaining -= len(chunk)
                        uploaded = length - remaining
                        run.update("runtime_upload", uploaded * 30 // length)
                if not hmac.compare_digest(digest.hexdigest(), run.backup_sha256):
                    raise RunnerFailure("archive_checksum_mismatch")
                upload_verified = True
            except Exception:
                run.archive_path.unlink(missing_ok=True)
                raise
            finally:
                with run.lock:
                    run.uploading = False
                    run.archive_verified = upload_verified
            run.update("runtime_upload", 30)
            _LOGGER.info("run archive_uploaded bytes=%d checksum_verified=true", length)
            self._empty(HTTPStatus.NO_CONTENT)
        except (OSError, ValueError, RunnerFailure) as err:
            code = err.code if isinstance(err, RunnerFailure) else "archive_upload_failed"
            _LOGGER.error("run archive_upload_failed error_code=%s", code)
            self._json(HTTPStatus.BAD_REQUEST, {"error": code})

    def do_DELETE(self) -> None:
        if not self._require_auth():
            return
        run_id = self._route_run_id()
        if run_id is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            MANAGER.delete(run_id)
        except RunnerFailure as err:
            self._json(HTTPStatus.CONFLICT, {"error": err.code})
            return
        self._empty(HTTPStatus.NO_CONTENT)


def _register_discovery_once(supervisor_token: str) -> None:
    """Publish one authenticated endpoint through the Supervisor proxy."""
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    request = urllib.request.Request(
        f"{SUPERVISOR_API}/addons/self/info", headers=headers
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        info = json.load(response)
    hostname = info.get("data", {}).get("hostname")
    if (
        not isinstance(hostname, str)
        or not hostname
        or any(character in hostname for character in "/\\?#@")
    ):
        raise RunnerFailure("supervisor_hostname_invalid")
    payload = json.dumps(
        {
            "service": "backup_checkup",
            "config": {
                "host": hostname,
                "port": LISTEN_PORT,
                "protocol": PROTOCOL_VERSION,
                "ssl": True,
                "token": TOKEN,
                "runner_id": RUNNER_ID,
                "tls_certificate": TLS_CERTIFICATE,
            },
        }
    ).encode()
    discovery = urllib.request.Request(
        f"{SUPERVISOR_API}/discovery",
        data=payload,
        method="POST",
        headers={**headers, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(discovery, timeout=10) as response:
        response.read(0)


def _register_discovery() -> None:
    """Retry discovery until Supervisor accepts the service registration."""
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        _LOGGER.error("discovery disabled error_code=supervisor_token_missing")
        return
    retry_delay = 1
    while True:
        try:
            _register_discovery_once(supervisor_token)
        except (OSError, ValueError, KeyError, RunnerFailure) as err:
            _LOGGER.warning(
                "discovery failed error_type=%s retry_seconds=%d",
                type(err).__name__,
                retry_delay,
            )
            time.sleep(retry_delay)
            retry_delay = min(60, retry_delay * 2)
            continue
        _LOGGER.info("discovery registered")
        return


def main() -> None:
    _initialize_runtime()
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
    tls_context.load_cert_chain(TLS_CERT_PATH, TLS_KEY_PATH)
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=_register_discovery, daemon=True).start()
    _LOGGER.info("runner listening port=%d tls=true", LISTEN_PORT)
    # The listening socket was wrapped in TLS immediately above. Sonar cannot
    # infer that reassignment through ssl.wrap_socket secures this HTTP server.
    server.serve_forever(poll_interval=0.25)  # NOSONAR


if __name__ == "__main__":
    main()
