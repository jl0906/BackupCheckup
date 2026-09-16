"""Optional isolated Home Assistant runtime-test runner support."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import ssl
import time
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MIN_RUNNER_VERSION, RECOMMENDED_RUNNER_VERSION
from .datetime_utils import parse_stored_utc_datetime
from .progress import PHASE_PREPARE, PHASE_RUN, ProgressReporter

RUNTIME_STATUS_NOT_AVAILABLE = "not_available"
RUNTIME_STATUS_NOT_RUN = "not_run"
RUNTIME_STATUS_NOT_STARTED = "not_started"
RUNTIME_STATUS_RUNNING = "running"
RUNTIME_STATUS_PASSED = "passed"
RUNTIME_STATUS_FAILED = "failed"
RUNTIME_STATUS_ABORTED = "aborted"
RUNTIME_STATUS_INCONCLUSIVE = "inconclusive"
RUNTIME_STATUS_OPTIONS = (
    RUNTIME_STATUS_NOT_AVAILABLE,
    RUNTIME_STATUS_NOT_RUN,
    RUNTIME_STATUS_NOT_STARTED,
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
_PROTOCOL_VERSION = 2
_CHUNK_SIZE = 1024 * 1024
_MAX_IDENTIFIER_LENGTH = 160
_MAX_ERROR_CODE_LENGTH = 96
_MAX_RUNNER_VERSION_LENGTH = 64
_MAX_TLS_CERTIFICATE_LENGTH = 8192
_MIN_POLL_INTERVAL = 0.25
# A live step display needs a fast poll; two seconds still keeps a long runtime
# test cheap on low-power hardware.
_MAX_POLL_INTERVAL = 2.0
_HEALTH_TIMEOUT_SECONDS = 10
_MAX_CAPABILITIES = 12
CAPABILITY_STEP_PROGRESS = "step_progress"
CAPABILITY_BOOT_EVENTS = "boot_events"


class RuntimeRunnerError(Exception):
    """A bounded, privacy-safe runtime-runner failure."""

    def __init__(self, code: str, *, phase: str = PHASE_RUN) -> None:
        """Initialize the error from one stable code and the phase it hit.

        The phase decides whether the isolated test ever started, which no
        error code alone can express.
        """
        normalized = _bounded_text(code, maximum=_MAX_ERROR_CODE_LENGTH)
        self.code = normalized or "runner_error"
        self.phase = phase
        super().__init__(self.code)


def _bounded_text(value: Any, *, maximum: int) -> str | None:
    """Return a bounded printable string or None."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(character for character in value if character.isprintable())
    cleaned = cleaned.strip()
    return cleaned[:maximum] if cleaned else None


def _tls_fingerprint(certificate: str) -> aiohttp.Fingerprint | None:
    """Build an aiohttp pin from the runner's discovered certificate."""
    try:
        der_certificate = ssl.PEM_cert_to_DER_cert(certificate)
    except ValueError:
        return None
    return aiohttp.Fingerprint(hashlib.sha256(der_certificate).digest())


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
        if not base_url.startswith("https://") or _tls_fingerprint(tls_certificate) is None:
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


async def async_discover_supervisor_runner(
    hass: HomeAssistant,
) -> RuntimeRunnerConnection | None:
    """Recover a registered runner directly from Supervisor discovery state."""
    try:
        from homeassistant.components.hassio.handler import (
            get_supervisor_client,
        )
    except ImportError:
        return None
    try:
        discoveries = await get_supervisor_client(hass).discovery.list()
    except Exception:  # noqa: BLE001 - optional Supervisor integration boundary
        return None
    for discovery in discoveries:
        service = getattr(discovery, "service", None)
        config = getattr(discovery, "config", None)
        if service != DOMAIN or not isinstance(config, Mapping):
            continue
        if connection := RuntimeRunnerConnection.from_discovery(config):
            return connection
    return None


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
        unknown_status = status not in RUNTIME_STATUS_OPTIONS
        if unknown_status:
            status = RUNTIME_STATUS_FAILED
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
            )
            or ("runner_status_unknown" if unknown_status else None),
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


@dataclass(frozen=True, slots=True)
class RunnerHealth:
    """Validated capability information of one companion runner."""

    reachable: bool = False
    configured: bool = False
    protocol: int | None = None
    runner_version: str | None = None
    runner_id: str | None = None
    capabilities: tuple[str, ...] = ()
    isolation_available: bool = False
    uptime_seconds: int | None = None
    active_runs: int | None = None
    checked_at: datetime | None = None
    error_code: str | None = None
    update_recommended: bool = False
    check_source: str | None = None

    @property
    def usable(self) -> bool:
        """Return whether a runtime test may be started right now."""
        return self.reachable and self.error_code is None

    @property
    def version_number(self) -> int | None:
        """Return the leading major version of the reported runner version.

        A runner that reports "3" or "3.1" is runner 3; only text without any
        leading digit leaves the version unknown.
        """
        if self.runner_version is None:
            return None
        digits = ""
        for character in self.runner_version.strip():
            if not character.isdigit():
                break
            digits += character
        return int(digits) if digits else None

    @property
    def supports_step_progress(self) -> bool:
        """Return whether the runner reports measured step progress."""
        return CAPABILITY_STEP_PROGRESS in self.capabilities

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-safe representation used by entities and the panel."""
        return {
            "reachable": self.reachable,
            "configured": self.configured,
            "protocol": self.protocol,
            "runner_version": self.runner_version,
            "runner_id": self.runner_id,
            "capabilities": list(self.capabilities),
            "isolation_available": self.isolation_available,
            "uptime_seconds": self.uptime_seconds,
            "active_runs": self.active_runs,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "error_code": self.error_code,
            "update_recommended": self.update_recommended,
            "check_source": self.check_source,
        }

    @classmethod
    def not_configured(cls, *, check_source: str | None = None) -> RunnerHealth:
        """Return the state used while no runner connection exists."""
        return cls(
            reachable=False,
            configured=False,
            checked_at=datetime.now(UTC),
            error_code="runner_not_configured",
            check_source=check_source,
        )

    @classmethod
    def unreachable(
        cls, code: str, *, check_source: str | None = None
    ) -> RunnerHealth:
        """Return the state used after a failed health request."""
        return cls(
            reachable=False,
            configured=True,
            checked_at=datetime.now(UTC),
            error_code=code,
            check_source=check_source,
        )

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any], *, check_source: str | None = None
    ) -> RunnerHealth:
        """Build bounded health information from one runner response."""
        version = (
            _bounded_text(
                payload.get("runner_version"), maximum=_MAX_RUNNER_VERSION_LENGTH
            )
            # A protocol-2 runner that predates the version field is runner 2.
            or "2"
        )
        raw_capabilities = payload.get("capabilities")
        capabilities = (
            tuple(
                text
                for value in list(raw_capabilities)[:_MAX_CAPABILITIES]
                if (text := _bounded_text(value, maximum=64))
            )
            if isinstance(raw_capabilities, list)
            else ()
        )
        health = cls(
            reachable=True,
            configured=True,
            protocol=payload.get("protocol")
            if isinstance(payload.get("protocol"), int)
            else None,
            runner_version=version,
            runner_id=_bounded_text(payload.get("runner_id"), maximum=128),
            capabilities=capabilities,
            isolation_available=payload.get("isolation_available") is True,
            uptime_seconds=_bounded_positive(payload.get("uptime_seconds")),
            active_runs=_bounded_positive(payload.get("active_runs")),
            checked_at=datetime.now(UTC),
            check_source=check_source,
        )
        return health.validated()

    def validated(self) -> RunnerHealth:
        """Return this health with the version policy applied."""
        number = self.version_number
        if number is not None and number < MIN_RUNNER_VERSION:
            return replace(self, error_code="runner_too_old")
        if not self.isolation_available:
            return replace(self, error_code="runner_isolation_unavailable")
        return replace(
            self,
            update_recommended=number is not None
            and number < RECOMMENDED_RUNNER_VERSION,
        )


def _bounded_positive(value: Any) -> int | None:
    """Return a non-negative bounded counter or None."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return min(value, 10**9)


class RuntimeRunnerClient:
    """Protocol-v2 client for the isolated companion runner."""

    def __init__(self, session: Any, connection: RuntimeRunnerConnection) -> None:
        """Initialize the authenticated HTTP client."""
        self._session = session
        self._connection = connection
        self._tls_pin = _tls_fingerprint(connection.tls_certificate)
        if self._tls_pin is None:
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
    def _error_from_payload(
        payload: Any, fallback: str, *, phase: str = PHASE_RUN
    ) -> RuntimeRunnerError:
        """Preserve one bounded runner error without exposing response details."""
        if isinstance(payload, Mapping):
            error = _bounded_text(payload.get("error"), maximum=_MAX_ERROR_CODE_LENGTH)
            if error:
                return RuntimeRunnerError(f"runner_{error}", phase=phase)
        return RuntimeRunnerError(fallback, phase=phase)

    async def async_health(self, *, check_source: str | None = None) -> RunnerHealth:
        """Return validated runner capability information without raising."""
        try:
            async with self._session.get(
                self._url("v1/health"),
                headers=self._headers,
                timeout=_HEALTH_TIMEOUT_SECONDS,
                ssl=self._tls_pin,
            ) as response:
                if response.status != 200:
                    return RunnerHealth.unreachable(
                        "runner_unavailable", check_source=check_source
                    )
                payload = await response.json()
        except Exception:  # noqa: BLE001 - optional companion runner boundary
            return RunnerHealth.unreachable(
                "runner_unavailable", check_source=check_source
            )
        if not isinstance(payload, Mapping):
            return RunnerHealth.unreachable(
                "runner_response_invalid", check_source=check_source
            )
        if payload.get("protocol") != _PROTOCOL_VERSION:
            return RunnerHealth.unreachable(
                "runner_protocol_mismatch", check_source=check_source
            )
        return RunnerHealth.from_payload(payload, check_source=check_source)

    async def async_require_health(self) -> RunnerHealth:
        """Return usable health or raise the stable error the run must report."""
        health = await self.async_health()
        if not health.usable:
            raise RuntimeRunnerError(
                health.error_code or "runner_unavailable", phase=PHASE_PREPARE
            )
        return health

    async def async_run(
        self,
        archive_path: Path,
        *,
        backup_reference: str,
        backup_sha256: str,
        password: str | None,
        maximum_archive_gb: int,
        maximum_expanded_gb: int,
        timeout_minutes: int,
        reporter: ProgressReporter,
    ) -> RuntimeTestSnapshot:
        """Upload and execute one isolated runtime test."""
        health = await self.async_require_health()
        reporter.begin_step(RUNTIME_STAGE_PREPARE)
        run_id: str | None = None
        try:
            run_id = await self._async_create_run(
                archive_path,
                backup_reference=backup_reference,
                backup_sha256=backup_sha256,
                password=password,
                maximum_archive_gb=maximum_archive_gb,
                maximum_expanded_gb=maximum_expanded_gb,
                timeout_minutes=timeout_minutes,
            )
            reporter.complete_step(RUNTIME_STAGE_PREPARE)
            await self._async_upload(run_id, archive_path, reporter)
            await self._async_start(run_id)
            payload = await self._async_poll(
                run_id,
                timeout_seconds=timeout_minutes * 60,
                reporter=reporter,
                health=health,
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
        maximum_archive_gb: int,
        maximum_expanded_gb: int,
        timeout_minutes: int,
    ) -> str:
        size = archive_path.stat().st_size
        payload = {
            "protocol": _PROTOCOL_VERSION,
            "backup_reference": backup_reference,
            "backup_sha256": backup_sha256,
            "archive_size": size,
            "password": password,
            "maximum_archive_gb": maximum_archive_gb,
            "maximum_expanded_gb": maximum_expanded_gb,
            "runtime_timeout_minutes": timeout_minutes,
        }
        try:
            async with self._session.post(
                self._url("v1/runs"),
                headers=self._headers,
                json=payload,
                timeout=15,
                ssl=self._tls_pin,
            ) as response:
                data = await response.json()
                if response.status != 201 or not isinstance(data, Mapping):
                    raise self._error_from_payload(
                        data, "runner_create_failed", phase=PHASE_PREPARE
                    )
        except RuntimeRunnerError:
            raise
        except Exception as err:
            raise RuntimeRunnerError(
                "runner_create_failed", phase=PHASE_PREPARE
            ) from err
        run_id = _bounded_text(data.get("run_id"), maximum=128)
        if not run_id:
            raise RuntimeRunnerError("runner_response_invalid", phase=PHASE_PREPARE)
        return run_id

    async def _archive_chunks(
        self,
        archive_path: Path,
        reporter: ProgressReporter,
    ) -> AsyncIterator[bytes]:
        total = archive_path.stat().st_size
        sent = 0
        file_handle = await asyncio.to_thread(archive_path.open, "rb")
        try:
            while chunk := await asyncio.to_thread(file_handle.read, _CHUNK_SIZE):
                sent += len(chunk)
                reporter.update(RUNTIME_STAGE_UPLOAD, done=sent, total=total)
                yield chunk
        finally:
            await asyncio.to_thread(file_handle.close)

    async def _async_upload(
        self,
        run_id: str,
        archive_path: Path,
        reporter: ProgressReporter,
    ) -> None:
        size = archive_path.stat().st_size
        headers = {
            **self._headers,
            "Content-Type": "application/octet-stream",
            "Content-Length": str(size),
        }
        reporter.begin_step(RUNTIME_STAGE_UPLOAD, determinate=bool(size), total=size)
        try:
            async with self._session.put(
                self._url(f"v1/runs/{run_id}/archive"),
                headers=headers,
                data=self._archive_chunks(archive_path, reporter),
                timeout=None,
                ssl=self._tls_pin,
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
        reporter.complete_step(RUNTIME_STAGE_UPLOAD)

    async def _async_start(self, run_id: str) -> None:
        try:
            async with self._session.post(
                self._url(f"v1/runs/{run_id}/start"),
                headers=self._headers,
                timeout=15,
                ssl=self._tls_pin,
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
        reporter: ProgressReporter,
        health: RunnerHealth,
    ) -> Mapping[str, Any]:
        deadline = time.monotonic() + timeout_seconds + 30
        poll_interval = _MIN_POLL_INTERVAL
        if not health.supports_step_progress:
            # Runner 2 only reports coarse stages; never invent a percentage.
            reporter.mark_indeterminate()
        while time.monotonic() < deadline:
            try:
                async with self._session.get(
                    self._url(f"v1/runs/{run_id}"),
                    headers=self._headers,
                    timeout=10,
                    ssl=self._tls_pin,
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
            reporter.apply_runner_state(payload)
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
                ssl=self._tls_pin,
            ) as response:
                response.release()
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
