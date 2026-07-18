"""Regression tests for BackupCheckup 2.3.0 final hardening."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.backup_checkup import integrity as integrity_module
from custom_components.backup_checkup.const import (
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
)
from custom_components.backup_checkup.integrity import (
    BackupIntegrityStore,
    BackupIntegrityVerifier,
)
from custom_components.backup_checkup.models import (
    BackupAgentRecord,
    BackupIntegrityResult,
    BackupRecord,
)
from custom_components.backup_checkup.security import TempCleanupResult


def _result() -> BackupIntegrityResult:
    """Return one complete result for persistence tests."""
    now = datetime(2026, 7, 18, tzinfo=UTC)
    return BackupIntegrityResult(
        status=INTEGRITY_STATUS_VALID,
        checked_at=now,
        backup_id="backup",
        backup_reference="reference",
        backup_date=now,
        agent_id="backup.local",
        sha256="a" * 64,
        verified_size=1024,
        duration_seconds=1.0,
        archive_count=1,
        file_count=2,
        protected=False,
        database_status="not_checked",
        warnings=(),
        error_code=None,
        checksum_changed=False,
    )


def _record() -> BackupRecord:
    """Return one normalized backup record for verifier boundary tests."""
    now = datetime(2026, 7, 18, tzinfo=UTC)
    return BackupRecord(
        backup_id="backup",
        backup_reference="reference",
        name="Backup",
        date=now,
        automatic=True,
        purpose="automatic",
        included_addons=(),
        included_folders=(),
        scope_fingerprint="scope",
        agents=("backup.local",),
        agent_copies=(
            BackupAgentRecord("backup.local", "storage-reference", 1024, False),
        ),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=1024,
        incomplete=False,
    )


class _BlockingStore:
    """Backend exposing whether remove can overtake an in-flight save."""

    def __init__(self) -> None:
        self.data: dict[str, Any] | None = None
        self.save_started = asyncio.Event()
        self.release_save = asyncio.Event()
        self.remove_calls = 0

    async def async_load(self) -> None:
        return None

    async def async_save(self, data: dict[str, Any]) -> None:
        self.save_started.set()
        await self.release_save.wait()
        self.data = data

    async def async_remove(self) -> None:
        self.remove_calls += 1
        self.data = None


@pytest.mark.asyncio
async def test_integrity_store_remove_cannot_be_overtaken_by_pending_save() -> None:
    """Deleting an entry must not let an older save recreate its private store."""
    store = BackupIntegrityStore(object(), "entry")
    backend = _BlockingStore()
    store._store = backend

    save_task = asyncio.create_task(store.async_save(_result()))
    await backend.save_started.wait()
    remove_task = asyncio.create_task(store.async_remove())
    await asyncio.sleep(0)

    assert remove_task.done() is False
    backend.release_save.set()
    await asyncio.gather(save_task, remove_task)

    assert backend.remove_calls == 1
    assert backend.data is None
    assert store._loaded is False


class _ExecutorHass:
    """Run executor jobs inline while proving the boundary was used."""

    def __init__(self) -> None:
        self.in_executor = False
        self.calls: list[Any] = []

    async def async_add_executor_job(self, function: Any, *args: Any) -> Any:
        self.calls.append(function)
        self.in_executor = True
        try:
            return function(*args)
        finally:
            self.in_executor = False


class _GuardedPath:
    """Reject unlink calls made directly from the event loop."""

    def __init__(self, hass: _ExecutorHass) -> None:
        self.hass = hass
        self.unlinked = False

    def unlink(self, *, missing_ok: bool = False) -> None:
        assert missing_ok is True
        assert self.hass.in_executor is True
        self.unlinked = True


@pytest.mark.asyncio
async def test_failed_candidate_file_removal_runs_in_executor() -> None:
    """Backup archive deletion must not perform blocking disk I/O in the loop."""
    hass = _ExecutorHass()
    verifier = BackupIntegrityVerifier(hass, "entry")
    path = _GuardedPath(hass)

    await verifier._async_remove_candidate_file(path)  # type: ignore[arg-type]

    assert path.unlinked is True
    assert verifier._unlink_missing_ok in hass.calls


@pytest.mark.asyncio
async def test_cleanup_boundary_failures_do_not_mask_verification_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both cleanup stages remain best-effort and activate the Repair issue."""
    calls: list[Any] = []

    async def _executor(function: Any, *args: Any) -> Any:
        calls.append(function)
        if function is integrity_module.cleanup_temp_directory:
            raise RuntimeError("cleanup executor failed")
        return TempCleanupResult()

    hass = SimpleNamespace(async_add_executor_job=_executor)
    verifier = BackupIntegrityVerifier(hass, "entry")
    issue_states: list[bool] = []
    monkeypatch.setattr(
        integrity_module,
        "async_set_temporary_cleanup_issue",
        lambda _hass, *, active: issue_states.append(active),
    )

    await verifier._async_cleanup_verification_data(
        Path("/tmp/backup_checkup-test"),
        repair_issues_enabled=True,
    )

    assert calls == [
        integrity_module.cleanup_temp_directory,
        integrity_module.cleanup_stale_temp_directories,
    ]
    assert issue_states == [True]


@pytest.mark.asyncio
async def test_unexpected_temp_directory_executor_error_is_stable_failure() -> None:
    """Executor boundary errors use the same user-facing temporary-storage result."""

    async def _executor(_function: Any, *_args: Any) -> Any:
        raise RuntimeError("executor unavailable")

    verifier = BackupIntegrityVerifier(
        SimpleNamespace(async_add_executor_job=_executor),
        "entry",
    )

    result = await verifier._async_create_temp_directory(_record(), 0.0)

    assert isinstance(result, BackupIntegrityResult)
    assert result.status == INTEGRITY_STATUS_UNREADABLE
    assert result.error_code == "temporary_storage_unavailable"


@pytest.mark.asyncio
async def test_complete_integrity_state_save_remains_supported() -> None:
    """The explicit full-state persistence API stays covered and functional."""
    from custom_components.backup_checkup.integrity import IntegrityStoreState

    store = BackupIntegrityStore(object(), "entry")
    state = IntegrityStoreState(
        result=_result(),
        retry_backup_id="backup",
        retry_error_key="internal_error",
        retry_attempts=1,
        password_marker="marker",
    )

    await store.async_save_state(state)

    assert store._state == state
    assert store._result is state.result
    assert store._store.data["result"]["status"] == INTEGRITY_STATUS_VALID
