"""Optional isolated Home Assistant runtime-test runner support."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import ssl
import time
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .datetime_utils import parse_stored_utc_datetime

RUNTIME_STATUS_NOT_AVAILABLE = "not_available"
RUNTIME_STATUS_NOT_RUN = "not_run"
RUNTIME_STATUS_RUNNING = "running"
RUNTIME_STATUS_PASSED = "passed"
RUNTIME_STATUS_FAILED = "failed"
RUNTIME_STATUS_ABORTED = "aborted"
RUNTIME_STATUS_INCONCLUSIVE = "inconclusive"
RUNTIME_STATUS_OPTIONS = (
    RUNTIME_STATUS_NOT_AVAILABLE,
    RUNTIME_STATUS_NOT_RUN,
    RUNTIME_STATUS_RUNNING,
    RUNTIME_STATUS_PASSED,
    RUNTIME_STATUS_FAILED,
    RUNTIME_STATUS_ABORTED,
    RUNTIME_STATUS_INCONCLUSIVE,
)

RUNTIME_STAGE_PREPARE = "runtime_prepare"
RUNTIME_STAGE_UPLOAD = "runtime_upload"
RUNTIME_STAGE_RESTORE = "runtime_restore"
RUNTIME_STAGE_BOOT = "runtime_boot"
RUNTIME_STAGE_PROBE = "runtime_probe"
RUNTIME_STAGE_CLEANUP = "runtime_cleanup"
RUNTIME_STAGE_COMPLETE = "runtime_complete"
RUNTIME_STAGE_OPTIONS = (
    RUNTIME_STAGE_PREPARE,
    RUNTIME_STAGE_UPLOAD,
    RUNTIME_STAGE_RESTORE,
    RUNTIME_STAGE_BOOT,
    RUNTIME_STAGE_PROBE,
    RUNTIME_STAGE_CLEANUP,
    RUNTIME_STAGE_COMPLETE,
)

_TERMINAL_STATUSES = {
    RUNTIME_STATUS_PASSED,
    RUNTIME_STATUS_FAILED,
    RUNTIME_STATUS_ABORTED,
    RUNTIME_STATUS_INCONCLUSIVE,
}
_STORAGE_VERSION = 1
_PROTOCOL_VERSION = 1
_CHUNK_SIZE = 1024 * 1024
_MAX_IDENTIFIER_LENGTH = 160
_MAX_ERROR_CODE_LENGTH = 96
_MAX_RUNNER_VERSION_LENGTH = 64
_MAX_TLS_CERTIFICATE_LENGTH = 8192
_MIN_POLL_INTERVAL = 0.25
_MAX_POLL_INTERVAL = 5.0


class RuntimeRunnerError(Exception):
    """A bounded, privacy-safe runtime-runner failure."""

    def __init__(self, code: str) -> None:
        """Initialize the error from one stable code."""
        normalized = _bounded_text(code, maximum=_MAX_ERROR_CODE_LENGTH)
        self.code = normalized or "runner_error"
        super().__init__(self.code)


def _bounded_text(value: Any, *, maximum: int) -> str | None:
    """Return a bounded printable string or None."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(character for character in value if character.isprintable())
    cleaned = cleaned.strip()
    return cleaned[:maximum] if cleaned else None


def _bounded_percent(value: Any) -> int:
    """Return a strict progress percentage."""
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(value, 100))


def _empty_stages() -> dict[str, str]:
    """Return the stable runtime pipeline shape."""
    return {stage: "pending" for stage in RUNTIME_STAGE_OPTIONS}


def _tls_context(certificate: str) -> ssl.SSLContext | None:
    """Build a TLS context pinned to the runner's discovered certificate."""
    try:
        context = ssl.create_default_context(cadata=certificate)
    except ssl.SSLError:
        return None
    context.check_hostname = False
    return context


@dataclass(frozen=True, slots=True)
class RuntimeRunnerConnection:
    """Authenticated endpoint discovered from the companion app."""

    base_url: str
    token: str
    runner_id: str
    tls_certificate: str

    @classmethod
    def from_discovery(
        cls, value: Mapping[str, Any]
    ) -> RuntimeRunnerConnection | None:
        """Build a pinned private connection from Supervisor discovery data."""
        host = value.get("host")
        port = value.get("port")
        if (
            value.get("protocol") != _PROTOCOL_VERSION
            or value.get("ssl") is not True
            or not isinstance(host, str)
            or not host
            or any(character in host for character in "/\\?#@")
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            return None
        return cls.from_mapping(
            {
                "base_url": f"https://{host}:{port}/",
                "token": value.get("token"),
                "runner_id": value.get("runner_id"),
                "tls_certificate": value.get("tls_certificate"),
            }
        )

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, Any] | None
    ) -> RuntimeRunnerConnection | None:
        """Validate persisted or discovered connection information."""
        if not isinstance(value, Mapping):
            return None
        base_url = _bounded_text(value.get("base_url"), maximum=512)
        token = _bounded_text(value.get("token"), maximum=512)
        runner_id = _bounded_text(value.get("runner_id"), maximum=128)
        raw_certificate = value.get("tls_certificate")
        tls_certificate = (
            raw_certificate.strip()
            if isinstance(raw_certificate, str)
            and len(raw_certificate) <= _MAX_TLS_CERTIFICATE_LENGTH
            and "\x00" not in raw_certificate
            else None
        )
        if not base_url or not token or not runner_id or not tls_certificate:
            return None
        if not base_url.startswith("https://") or _tls_context(tls_certificate) is None:
            return None
        return cls(
            base_url=base_url.rstrip("/") + "/",
            token=token,
            runner_id=runner_id,
            tls_certificate=tls_certificate,
        )

    def as_dict(self) -> dict[str, str]:
        """Serialize private connection information."""
        return {
            "base_url": self.base_url,
            "token": self.token,
            "runner_id": self.runner_id,
            "tls_certificate": self.tls_certificate,
        }


@dataclass(frozen=True, slots=True)
class RuntimeTestSnapshot:
    """Privacy-safe result of one isolated Home Assistant start attempt."""

    status: str = RUNTIME_STATUS_NOT_RUN
    backup_reference: str | None = None
    backup_sha256: str | None = None
    checked_at: datetime | None = None
    duration_seconds: float | None = None
    runner_id: str | None = None
    runner_version: str | None = None
    home_assistant_version: str | None = None
    isolation_verified: bool = False
    ready: bool = False
    recovery_mode: bool = True
    error_code: str | None = None

    @property
    def passed(self) -> bool | None:
        """Return tri-state result semantics."""
        if self.status == RUNTIME_STATUS_PASSED:
            return True
        if self.status in {RUNTIME_STATUS_FAILED, RUNTIME_STATUS_ABORTED}:
            return False
        return None

    def verified_for(
        self, backup_reference: str | None, backup_sha256: str | None
    ) -> bool:
        """Return whether this proves the exact structurally verified backup."""
        return bool(
            self.passed is True
            and self.isolation_verified
            and self.ready
            and backup_reference
            and backup_sha256
            and hmac.compare_digest(self.backup_reference or "", backup_reference)
            and hmac.compare_digest(self.backup_sha256 or "", backup_sha256)
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe attributes without credentials or paths."""
        return {
            "status": self.status,
            "passed": self.passed,
            "backup_reference": self.backup_reference,
            "backup_sha256": self.backup_sha256,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "duration_seconds": self.duration_seconds,
            "runner_id": self.runner_id,
            "runner_version": self.runner_version,
            "home_assistant_version": self.home_assistant_version,
            "isolation_verified": self.isolation_verified,
            "ready": self.ready,
            "recovery_mode": self.recovery_mode,
            "error_code": self.error_code,
            "destructive_actions_performed": False,
            "production_instance_modified": False,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RuntimeTestSnapshot:
        """Parse bounded persisted or remotely returned data."""
        status = value.get("status")
        if status not in RUNTIME_STATUS_OPTIONS:
            status = RUNTIME_STATUS_INCONCLUSIVE
        checked_at = parse_stored_utc_datetime(value.get("checked_at"))
        raw_duration = value.get("duration_seconds")
        duration = (
            round(float(raw_duration), 2)
            if isinstance(raw_duration, (int, float))
            and not isinstance(raw_duration, bool)
            and 0 <= raw_duration <= 86_400
            else None
        )
        return cls(
            status=status,
            backup_reference=_bounded_text(
                value.get("backup_reference"), maximum=_MAX_IDENTIFIER_LENGTH
            ),
            backup_sha256=_bounded_sha256(value.get("backup_sha256")),
            checked_at=checked_at,
            duration_seconds=duration,
            runner_id=_bounded_text(value.get("runner_id"), maximum=128),
            runner_version=_bounded_text(
                value.get("runner_version"), maximum=_MAX_RUNNER_VERSION_LENGTH
            ),
            home_assistant_version=_bounded_text(
                value.get("home_assistant_version"),
                maximum=_MAX_RUNNER_VERSION_LENGTH,
            ),
            isolation_verified=value.get("isolation_verified") is True,
            ready=value.get("ready") is True,
            recovery_mode=value.get("recovery_mode") is not False,
            error_code=_bounded_text(
                value.get("error_code"), maximum=_MAX_ERROR_CODE_LENGTH
            ),
        )


def _bounded_sha256(value: Any) -> str | None:
    """Validate one lowercase SHA-256 digest."""
    if not isinstance(value, str) or len(value) != 64:
        return None
    lowered = value.lower()
    return (
        lowered
        if all(character in "0123456789abcdef" for character in lowered)
        else None
    )


class RuntimeTestStore:
    """Persist only the latest privacy-safe runtime result."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the private store."""
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.runtime_test",
            private=True,
            atomic_writes=True,
        )
        self._loaded = False
        self._lock = asyncio.Lock()
        self._snapshot = RuntimeTestSnapshot()

    async def async_load(self) -> RuntimeTestSnapshot:
        """Load once and safely discard malformed state."""
        async with self._lock:
            if self._loaded:
                return self._snapshot
            stored = await self._store.async_load()
            if isinstance(stored, Mapping):
                self._snapshot = RuntimeTestSnapshot.from_mapping(stored)
            self._loaded = True
            return self._snapshot

    async def async_save(self, snapshot: RuntimeTestSnapshot) -> None:
        """Persist one completed result."""
        async with self._lock:
            self._snapshot = snapshot
            self._loaded = True
            await self._store.async_save(snapshot.as_dict())

    def snapshot(self) -> RuntimeTestSnapshot:
        """Return current in-memory state."""
        return self._snapshot

    async def async_remove(self) -> None:
        """Remove persisted state."""
        async with self._lock:
            await self._store.async_remove()
            self._snapshot = RuntimeTestSnapshot()
            self._loaded = False


@dataclass(slots=True)
class RuntimeTestProgress:
    """Track and publish the optional runner phase."""

    running: bool = False
    status: str = RUNTIME_STATUS_NOT_RUN
    stage: str = RUNTIME_STAGE_PREPARE
    progress_percent: int = 0
    backup_reference: str | None = None
    started_at: datetime | None = None
    duration_seconds: float | None = None
    error_code: str | None = None
    stages: dict[str, str] = field(default_factory=_empty_stages)
    _started_monotonic: float | None = field(default=None, repr=False)

    def start(self, backup_reference: str) -> None:
        """Start a new live runtime test."""
        self.running = True
        self.status = RUNTIME_STATUS_RUNNING
        self.stage = RUNTIME_STAGE_PREPARE
        self.progress_percent = 0
        self.backup_reference = backup_reference
        self.started_at = datetime.now(UTC)
        self.duration_seconds = None
        self.error_code = None
        self.stages = _empty_stages()
        self.stages[RUNTIME_STAGE_PREPARE] = "running"
        self._started_monotonic = time.monotonic()

    def update(self, stage: str, percent: int) -> None:
        """Advance monotonically from a validated runner state."""
        if not self.running or stage not in RUNTIME_STAGE_OPTIONS:
            return
        if self.stage != stage and self.stages.get(self.stage) == "running":
            self.stages[self.stage] = "passed"
        self.stage = stage
        self.progress_percent = max(self.progress_percent, _bounded_percent(percent))
        self.stages[stage] = "running"

    def finish(self, snapshot: RuntimeTestSnapshot) -> None:
        """Finish the live state from one authenticated result."""
        if self.stages.get(self.stage) == "running":
            self.stages[self.stage] = (
                "passed" if snapshot.passed is True else "failed"
            )
        self.running = False
        self.status = snapshot.status
        self.stage = RUNTIME_STAGE_COMPLETE
        self.progress_percent = 100
        self.stages[RUNTIME_STAGE_COMPLETE] = (
            "passed" if snapshot.passed is True else "failed"
        )
        self.error_code = snapshot.error_code
        self.duration_seconds = snapshot.duration_seconds
        self._started_monotonic = None

    def cancel(self) -> None:
        """Cancel a pending test during shutdown."""
        if not self.running:
            return
        self.running = False
        self.status = RUNTIME_STATUS_ABORTED
        self.stages[self.stage] = "failed"
        self.error_code = "cancelled"
        self._started_monotonic = None

    def as_dict(self) -> dict[str, Any]:
        """Return bounded live frontend state."""
        duration = self.duration_seconds
        if self.running and self._started_monotonic is not None:
            duration = round(max(0.0, time.monotonic() - self._started_monotonic), 2)
        return {
            "running": self.running,
            "status": self.status,
            "stage": self.stage,
            "progress_percent": self.progress_percent,
            "backup_reference": self.backup_reference,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_seconds": duration,
            "error_code": self.error_code,
            "stages": dict(self.stages),
        }


ProgressCallback = Callable[[str, int], None]


class RuntimeRunnerClient:
    """Protocol-v1 client for the isolated companion runner."""

    def __init__(self, session: Any, connection: RuntimeRunnerConnection) -> None:
        """Initialize the authenticated HTTP client."""
        self._session = session
        self._connection = connection
        self._ssl_context = _tls_context(connection.tls_certificate)
        if self._ssl_context is None:
            raise RuntimeRunnerError("runner_tls_invalid")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._connection.token}",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return urljoin(self._connection.base_url, path.lstrip("/"))

    @staticmethod
    def _error_from_payload(payload: Any, fallback: str) -> RuntimeRunnerError:
        """Preserve one bounded runner error without exposing response details."""
        if isinstance(payload, Mapping):
            error = _bounded_text(payload.get("error"), maximum=_MAX_ERROR_CODE_LENGTH)
            if error:
                return RuntimeRunnerError(f"runner_{error}")
        return RuntimeRunnerError(fallback)

    async def async_health(self) -> dict[str, Any]:
        """Return validated runner capability information."""
        try:
            async with self._session.get(
                self._url("v1/health"),
                headers=self._headers,
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                if response.status != 200:
                    raise RuntimeRunnerError("runner_unavailable")
                payload = await response.json()
        except RuntimeRunnerError:
            raise
        except Exception as err:
            raise RuntimeRunnerError("runner_unavailable") from err
        if (
            not isinstance(payload, Mapping)
            or payload.get("protocol") != _PROTOCOL_VERSION
        ):
            raise RuntimeRunnerError("runner_protocol_mismatch")
        if payload.get("isolation_available") is not True:
            raise RuntimeRunnerError("runner_isolation_unavailable")
        return dict(payload)

    async def async_run(
        self,
        archive_path: Path,
        *,
        backup_reference: str,
        backup_sha256: str,
        password: str | None,
        timeout_seconds: int,
        progress_callback: ProgressCallback,
    ) -> RuntimeTestSnapshot:
        """Upload and execute one isolated runtime test."""
        await self.async_health()
        run_id: str | None = None
        try:
            run_id = await self._async_create_run(
                archive_path,
                backup_reference=backup_reference,
                backup_sha256=backup_sha256,
                password=password,
                timeout_seconds=timeout_seconds,
            )
            await self._async_upload(run_id, archive_path, progress_callback)
            await self._async_start(run_id)
            payload = await self._async_poll(
                run_id,
                timeout_seconds=timeout_seconds,
                progress_callback=progress_callback,
            )
            self._verify_signature(payload)
            snapshot = RuntimeTestSnapshot.from_mapping(payload)
            if not snapshot.backup_reference or not hmac.compare_digest(
                snapshot.backup_reference, backup_reference
            ):
                raise RuntimeRunnerError("runner_backup_mismatch")
            if not snapshot.backup_sha256 or not hmac.compare_digest(
                snapshot.backup_sha256, backup_sha256
            ):
                raise RuntimeRunnerError("runner_checksum_mismatch")
            if not snapshot.runner_id or not hmac.compare_digest(
                snapshot.runner_id, self._connection.runner_id
            ):
                raise RuntimeRunnerError("runner_identity_mismatch")
            return snapshot
        finally:
            if run_id is not None:
                await self._async_delete(run_id)

    async def _async_create_run(
        self,
        archive_path: Path,
        *,
        backup_reference: str,
        backup_sha256: str,
        password: str | None,
        timeout_seconds: int,
    ) -> str:
        size = archive_path.stat().st_size
        payload = {
            "protocol": _PROTOCOL_VERSION,
            "backup_reference": backup_reference,
            "backup_sha256": backup_sha256,
            "archive_size": size,
            "password": password,
            "timeout_seconds": timeout_seconds,
        }
        try:
            async with self._session.post(
                self._url("v1/runs"),
                headers=self._headers,
                json=payload,
                timeout=15,
                ssl=self._ssl_context,
            ) as response:
                data = await response.json()
                if response.status != 201 or not isinstance(data, Mapping):
                    raise self._error_from_payload(data, "runner_create_failed")
        except RuntimeRunnerError:
            raise
        except Exception as err:
            raise RuntimeRunnerError("runner_create_failed") from err
        run_id = _bounded_text(data.get("run_id"), maximum=128)
        if not run_id:
            raise RuntimeRunnerError("runner_response_invalid")
        return run_id

    async def _archive_chunks(
        self,
        archive_path: Path,
        progress_callback: ProgressCallback,
    ) -> AsyncIterator[bytes]:
        total = archive_path.stat().st_size
        sent = 0
        last_progress = -1
        file_handle = await asyncio.to_thread(archive_path.open, "rb")
        try:
            while chunk := await asyncio.to_thread(file_handle.read, _CHUNK_SIZE):
                sent += len(chunk)
                upload_percent = min(100, int(sent * 100 / total)) if total else 100
                progress = 5 + int(upload_percent * 25 / 100)
                if progress != last_progress:
                    progress_callback(RUNTIME_STAGE_UPLOAD, progress)
                    last_progress = progress
                yield chunk
        finally:
            await asyncio.to_thread(file_handle.close)

    async def _async_upload(
        self,
        run_id: str,
        archive_path: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        headers = {
            **self._headers,
            "Content-Type": "application/octet-stream",
            "Content-Length": str(archive_path.stat().st_size),
        }
        progress_callback(RUNTIME_STAGE_UPLOAD, 5)
        try:
            async with self._session.put(
                self._url(f"v1/runs/{run_id}/archive"),
                headers=headers,
                data=self._archive_chunks(archive_path, progress_callback),
                timeout=None,
                ssl=self._ssl_context,
            ) as response:
                if response.status != 204:
                    try:
                        data = await response.json()
                    except Exception:  # noqa: BLE001 - untrusted HTTP body
                        data = None
                    raise self._error_from_payload(data, "runner_upload_failed")
        except RuntimeRunnerError:
            raise
        except Exception as err:
            raise RuntimeRunnerError("runner_upload_failed") from err

    async def _async_start(self, run_id: str) -> None:
        try:
            async with self._session.post(
                self._url(f"v1/runs/{run_id}/start"),
                headers=self._headers,
                timeout=15,
                ssl=self._ssl_context,
            ) as response:
                if response.status != 202:
                    try:
                        data = await response.json()
                    except Exception:  # noqa: BLE001 - untrusted HTTP body
                        data = None
                    raise self._error_from_payload(data, "runner_start_failed")
        except RuntimeRunnerError:
            raise
        except Exception as err:
            raise RuntimeRunnerError("runner_start_failed") from err

    async def _async_poll(
        self,
        run_id: str,
        *,
        timeout_seconds: int,
        progress_callback: ProgressCallback,
    ) -> Mapping[str, Any]:
        deadline = time.monotonic() + timeout_seconds + 30
        poll_interval = _MIN_POLL_INTERVAL
        while time.monotonic() < deadline:
            try:
                async with self._session.get(
                    self._url(f"v1/runs/{run_id}"),
                    headers=self._headers,
                    timeout=10,
                    ssl=self._ssl_context,
                ) as response:
                    payload = await response.json()
                    if response.status != 200 or not isinstance(payload, Mapping):
                        raise self._error_from_payload(
                            payload, "runner_response_invalid"
                        )
            except RuntimeRunnerError:
                raise
            except Exception as err:
                raise RuntimeRunnerError("runner_poll_failed") from err
            stage = payload.get("stage")
            if stage in RUNTIME_STAGE_OPTIONS:
                progress_callback(
                    stage, _bounded_percent(payload.get("progress_percent"))
                )
            if payload.get("status") in _TERMINAL_STATUSES:
                return payload
            await asyncio.sleep(poll_interval)
            poll_interval = min(_MAX_POLL_INTERVAL, poll_interval * 1.35)
        raise RuntimeRunnerError("runner_timeout")

    async def _async_delete(self, run_id: str) -> None:
        try:
            async with self._session.delete(
                self._url(f"v1/runs/{run_id}"),
                headers=self._headers,
                timeout=10,
                ssl=self._ssl_context,
            ):
                pass
        except Exception:  # noqa: BLE001 - best-effort remote cleanup
            return

    def _verify_signature(self, payload: Mapping[str, Any]) -> None:
        signature = payload.get("signature")
        if not isinstance(signature, str):
            raise RuntimeRunnerError("runner_signature_missing")
        unsigned = {key: value for key, value in payload.items() if key != "signature"}
        message = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
        expected = hmac.new(
            self._connection.token.encode(), message, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RuntimeRunnerError("runner_signature_invalid")
