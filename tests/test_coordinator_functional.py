"""Functional coverage for coordinator orchestration and control paths."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.backup_checkup import coordinator as coordinator_module
from custom_components.backup_checkup.const import (
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_VALID,
    SIZE_CHECK_AUTO,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OFF,
)
from custom_components.backup_checkup.coordinator import (
    BackupCheckupCoordinator,
    SizeChangeAnalysis,
)
from custom_components.backup_checkup.history import AutomaticHistoryMetrics
from custom_components.backup_checkup.models import BackupIntegrityResult
from custom_components.backup_checkup.native_backup import NativeBackupState


class _States:
    def get(self, _entity_id: str) -> None:
        return None


class _Hass:
    def __init__(self) -> None:
        self.states = _States()
        self.config = SimpleNamespace(language="en")
        self.services = SimpleNamespace(async_call=AsyncMock())
        self.tasks: list[asyncio.Task[Any]] = []

    def async_create_task(
        self,
        coroutine: Any,
        *,
        name: str | None = None,
    ) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


class _Manager:
    def __init__(self, backups: Any = None, errors: Any = None) -> None:
        self.backups = {} if backups is None else backups
        self.errors = {} if errors is None else errors
        self.backup_agents = {
            "backup.local": SimpleNamespace(name="Local backup"),
            "backup.remote": SimpleNamespace(name=None),
        }
        self.config = SimpleNamespace(
            data=SimpleNamespace(
                create_backup=SimpleNamespace(password="secret")
            )
        )

    async def async_get_backups(self) -> tuple[Any, Any]:
        return self.backups, self.errors


def _backup(
    backup_id: str,
    date: datetime,
    *,
    automatic: bool = True,
    size: int = 2_000_000,
    agents: dict[str, Any] | None = None,
) -> Any:
    return SimpleNamespace(
        backup_id=backup_id,
        name=f"Backup {backup_id}",
        date=date,
        agents=agents
        or {"backup.local": {"size": size, "protected": False}},
        failed_agent_ids=[],
        failed_addons=[],
        failed_folders=[],
        with_automatic_settings=automatic,
        addons=[],
        folders=["config"],
        database_included=True,
        homeassistant_included=True,
        size=size,
        extra_metadata={},
    )


def _native(now: datetime, *, event_type: str = "completed") -> NativeBackupState:
    return NativeBackupState(
        last_attempt=now - timedelta(minutes=5),
        last_success=now - timedelta(minutes=4),
        next_scheduled=now + timedelta(days=1),
        manager_state="idle",
        event_type=event_type,
        event_at=now - timedelta(minutes=4),
        in_progress=False,
    )


def _history(now: datetime) -> AutomaticHistoryMetrics:
    return AutomaticHistoryMetrics(
        success_rate=100.0,
        resolved_attempts=1,
        successful_attempts=1,
        failed_attempts=0,
        consecutive_failures=0,
        tracking_started_at=now - timedelta(days=1),
    )


def _coordinator() -> BackupCheckupCoordinator:
    return BackupCheckupCoordinator(_Hass(), ConfigEntry(entry_id="entry"))


@pytest.mark.asyncio
async def test_build_snapshot_covers_inventory_storage_and_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    backups = {
        "latest": _backup("latest", now - timedelta(hours=1)),
        "older": _backup("older", now - timedelta(days=1), size=4_000_000),
        "manual": _backup(
            "manual", now - timedelta(hours=2), automatic=False, size=3_000_000
        ),
    }
    manager = _Manager(backups, {"backup.local": RuntimeError("offline")})
    coordinator = _coordinator()
    coordinator.minimum_redundant_locations = 2
    coordinator.history.async_observe = AsyncMock(return_value=_history(now))
    monkeypatch.setattr(
        coordinator_module,
        "read_native_backup_state",
        lambda *_args, **_kwargs: _native(now),
    )

    data = await coordinator._async_build_snapshot(
        manager=manager,
        backups=backups,
        agent_errors_raw=manager.errors,
        now=now,
    )

    assert data.total_backups == 3
    assert data.automatic_backups == 2
    assert data.manual_backups == 1
    assert data.latest_backup == now - timedelta(hours=1)
    assert data.latest_backup_size_change_percent == -50.0
    assert data.backup_not_redundant is True
    assert data.storage_error is True
    assert data.required_location_missing is True
    assert data.problem is True
    assert data.agent_summaries[0].storage_name == "Local backup"
    assert data.last_inventory_success_at == now
    assert data.latest_backup_location_ids != ("backup.local",)

    coordinator.expose_backup_metadata = True
    raw = coordinator._evaluate_storage(
        manager=manager,
        records=data.backups,
        monitoring_records=data.monitored_backups,
        agent_errors_raw=manager.errors,
        latest_location_ids=("backup.local",),
        now=now,
    )
    assert raw.public_errors == {"backup.local": "unknown_error"}
    assert coordinator._public_location_ids(("backup.local",)) == ("backup.local",)


@pytest.mark.asyncio
async def test_build_snapshot_without_backups(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    coordinator = _coordinator()
    coordinator.history.async_observe = AsyncMock(return_value=_history(now))
    monkeypatch.setattr(
        coordinator_module,
        "read_native_backup_state",
        lambda *_args, **_kwargs: _native(now, event_type="failed"),
    )
    data = await coordinator._async_build_snapshot(
        manager=_Manager(), backups={}, agent_errors_raw={}, now=now
    )
    assert data.no_backup is True
    assert data.latest_backup_result == "unknown"
    assert data.total_backups == 0
    assert data.automatic_backup_overdue is True
    assert data.agent_summaries


@pytest.mark.asyncio
async def test_fetch_inventory_and_manager_error_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _coordinator()
    manager = _Manager({"one": object()}, ["invalid errors"])
    monkeypatch.setattr(coordinator_module, "async_get_manager", lambda _hass: manager)
    fetched = await coordinator._async_fetch_inventory()
    assert fetched == (manager, manager.backups, {})

    manager.backups = []
    with pytest.raises(UpdateFailed):
        await coordinator._async_fetch_inventory()

    manager.async_get_backups = AsyncMock(side_effect=HomeAssistantError("not ready"))
    with pytest.raises(UpdateFailed):
        await coordinator._async_fetch_inventory()

    manager.async_get_backups = AsyncMock(side_effect=RuntimeError("agent"))
    with pytest.raises(UpdateFailed):
        await coordinator._async_fetch_inventory()


@pytest.mark.asyncio
async def test_update_data_orchestrates_all_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    coordinator = _coordinator()
    manager = _Manager()
    expected = SimpleNamespace(latest_monitored_backup_record=None)
    coordinator._async_fetch_inventory = AsyncMock(return_value=(manager, {}, {}))
    coordinator._async_load_integrity_state = AsyncMock()
    coordinator._async_update_backup_password_marker = AsyncMock(return_value=True)
    coordinator._async_build_snapshot = AsyncMock(return_value=expected)
    coordinator._async_process_notifications = AsyncMock()
    coordinator._schedule_automatic_verification = MagicMock()
    monkeypatch.setattr(coordinator_module.dt_util, "utcnow", lambda: now)

    result = await coordinator._async_update_data()
    assert result is expected
    coordinator._async_load_integrity_state.assert_awaited_once()
    coordinator._async_process_notifications.assert_awaited_once_with(expected)
    coordinator._schedule_automatic_verification.assert_called_once_with(
        None, now=now, password_changed=True
    )


@pytest.mark.asyncio
async def test_integrity_state_password_and_persistence_controls() -> None:
    coordinator = _coordinator()
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    state = SimpleNamespace(
        result=BackupIntegrityResult.not_checked(),
        retry_key=("backup", "error"),
        retry_attempts=2,
        retry_not_before=now,
        password_marker="marker",
        last_manual_verification_at=now,
    )
    coordinator.integrity_verifier.store.async_load_state = AsyncMock(
        return_value=state
    )
    await coordinator._async_load_integrity_state()
    await coordinator._async_load_integrity_state()
    assert coordinator.integrity_verifier.store.async_load_state.await_count == 1
    assert coordinator._integrity_retry_attempts == 2

    coordinator.integrity_verifier.store.async_update_runtime = AsyncMock()
    coordinator._backup_password_marker_initialized = False
    assert await coordinator._async_update_backup_password_marker(_Manager()) is False
    coordinator.integrity_verifier.store.async_update_runtime.assert_awaited_once()
    assert await coordinator._async_update_backup_password_marker(_Manager()) is False

    changed = _Manager()
    changed.config.data.create_backup.password = "new"
    assert await coordinator._async_update_backup_password_marker(changed) is True

    coordinator.integrity_verifier.store.async_update_runtime = AsyncMock(
        side_effect=RuntimeError("store")
    )
    await coordinator._async_persist_runtime_state()


@pytest.mark.asyncio
async def test_notifications_manager_error_snapshot_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    coordinator = _coordinator()
    coordinator.history.async_observe = AsyncMock(return_value=_history(now))
    monkeypatch.setattr(
        coordinator_module,
        "read_native_backup_state",
        lambda *_args, **_kwargs: _native(now),
    )
    data = await coordinator._async_build_snapshot(
        manager=_Manager(),
        backups={"one": _backup("one", now - timedelta(hours=1))},
        agent_errors_raw={},
        now=now,
    )
    coordinator.data = data
    coordinator.notification_manager.async_process = AsyncMock()
    await coordinator._async_process_notifications(data)
    coordinator.notification_manager.async_process.assert_awaited_once()
    coordinator.notification_manager.async_process = AsyncMock(
        side_effect=RuntimeError("notify")
    )
    await coordinator._async_process_notifications(data)

    snapshot = coordinator._manager_error_snapshot("manager_error")
    assert snapshot.manager_unavailable is True
    assert snapshot.agent_errors["manager"] == "manager_error"
    result = await coordinator._async_manager_error_result(
        RuntimeError("manager"), "failed"
    )
    assert result.manager_unavailable is True
    assert result.agent_errors["manager"] == "unknown_error"

    sleeper = asyncio.create_task(asyncio.sleep(10))
    coordinator._integrity_task = sleeper
    await coordinator.async_shutdown()
    assert sleeper.cancelled()


@pytest.mark.parametrize(
    ("mode", "size", "analysis", "expected"),
    [
        (SIZE_CHECK_OFF, 1, SizeChangeAnalysis(None, None, 0), False),
        (SIZE_CHECK_FIXED, 0, SizeChangeAnalysis(None, None, 0), True),
        (SIZE_CHECK_FIXED, 500_000, SizeChangeAnalysis(None, None, 0), True),
        ("unsupported", 2_000_000, SizeChangeAnalysis(None, None, 0), False),
        (SIZE_CHECK_AUTO, 2_000_000, SizeChangeAnalysis(-80.0, -80.0, 3), True),
    ],
)
def test_size_check_modes(
    mode: str,
    size: int,
    analysis: SizeChangeAnalysis,
    expected: bool,
) -> None:
    coordinator = _coordinator()
    coordinator.size_check_mode = mode
    coordinator.minimum_backup_size_bytes = 1_000_000
    record = coordinator._normalize_backups(
        {"one": _backup("one", datetime.now(UTC), size=size)}
    )[0]
    assert coordinator._is_size_suspicious(record, analysis) is expected
    assert coordinator._is_size_suspicious(None, analysis) is False


def _result(
    *,
    status: str,
    backup_id: str = "one",
    checked_at: datetime | None = None,
    error_code: str | None = None,
) -> BackupIntegrityResult:
    return BackupIntegrityResult(
        status=status,
        checked_at=checked_at,
        backup_id=backup_id,
        backup_reference="reference",
        backup_date=checked_at,
        agent_id=None,
        sha256=None,
        verified_size=None,
        duration_seconds=None,
        archive_count=0,
        file_count=0,
        protected=None,
        database_status=INTEGRITY_DATABASE_NOT_CHECKED,
        warnings=(),
        error_code=error_code,
        checksum_changed=False,
    )


def test_retry_policy_and_password_marker() -> None:
    coordinator = _coordinator()
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    record = coordinator._normalize_backups({"one": _backup("one", now)})[0]
    coordinator.integrity_result = BackupIntegrityResult.not_checked()
    assert coordinator._automatic_verification_due(record, now=now) is True
    assert coordinator._automatic_verification_due(None, now=now) is False

    password = _result(
        status=INTEGRITY_STATUS_PASSWORD_REQUIRED,
        checked_at=now,
    )
    coordinator.integrity_result = password
    coordinator._backup_password_marker = None
    assert (
        coordinator._automatic_verification_due(
            record, now=now, password_changed=True
        )
        is False
    )
    coordinator._backup_password_marker = "marker"
    assert coordinator._automatic_verification_due(
        record, now=now, password_changed=True
    )

    retryable = _result(
        status=INTEGRITY_STATUS_ABORTED,
        checked_at=now,
        error_code="verification_timeout",
    )
    coordinator.integrity_result = retryable
    coordinator._update_integrity_retry_state(retryable)
    assert coordinator._integrity_retry_attempts == 1
    coordinator._update_integrity_retry_state(retryable)
    assert coordinator._integrity_retry_attempts == 2
    assert coordinator._automatic_verification_due(
        record, now=now + timedelta(hours=2)
    )

    valid = _result(status=INTEGRITY_STATUS_VALID, checked_at=now)
    coordinator._update_integrity_retry_state(valid)
    assert coordinator._integrity_retry_key is None

    marker = coordinator._password_marker(_Manager())
    assert marker is not None and "secret" not in marker
    manager = _Manager()
    manager.config.data.create_backup.password = None
    assert coordinator._password_marker(manager) is None


@pytest.mark.asyncio
async def test_integrity_check_execution_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _coordinator()
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    record = coordinator._normalize_backups({"one": _backup("one", now)})[0]
    coordinator.data = None
    coordinator.async_request_refresh = AsyncMock()
    coordinator._async_save_integrity_result = AsyncMock()
    valid = _result(status=INTEGRITY_STATUS_VALID, checked_at=now)
    coordinator.integrity_verifier.async_verify = AsyncMock(return_value=valid)
    monkeypatch.setattr(coordinator_module.dt_util, "utcnow", lambda: now)

    await coordinator._async_run_integrity_check(record, source="manual")
    assert coordinator.integrity_result == valid
    assert coordinator._last_manual_verification_at == now
    coordinator._async_save_integrity_result.assert_awaited_once()
    coordinator.async_request_refresh.assert_awaited_once()

    coordinator.integrity_verifier.async_verify = AsyncMock(
        side_effect=RuntimeError("verify")
    )
    coordinator._async_save_integrity_result.reset_mock()
    await coordinator._async_run_integrity_check(record, source="automatic")
    assert coordinator.integrity_result.status == INTEGRITY_STATUS_INTERNAL_ERROR
    coordinator._async_save_integrity_result.assert_awaited_once()

    coordinator.integrity_check_running = True
    await coordinator._async_run_integrity_check(record, source="manual")


@pytest.mark.asyncio
async def test_start_check_guards_schedule_and_task_consumption() -> None:
    coordinator = _coordinator()
    now = datetime.now(UTC)
    record = coordinator._normalize_backups({"one": _backup("one", now)})[0]
    coordinator.data = SimpleNamespace(latest_monitored_backup_record=record)
    coordinator._async_run_integrity_check = AsyncMock()

    assert await coordinator.async_start_integrity_check() is True
    await asyncio.gather(*coordinator.hass.tasks)

    coordinator.integrity_check_running = True
    with pytest.raises(HomeAssistantError):
        await coordinator.async_start_integrity_check()
    coordinator.integrity_check_running = False
    coordinator._integrity_task = None
    coordinator.data = SimpleNamespace(latest_monitored_backup_record=None)
    with pytest.raises(HomeAssistantError):
        await coordinator.async_start_integrity_check()

    coordinator.data = SimpleNamespace(latest_monitored_backup_record=record)
    coordinator.manual_verification_cooldown_minutes = 10
    coordinator._last_manual_verification_at = datetime.now(UTC)
    with pytest.raises(HomeAssistantError):
        await coordinator.async_start_integrity_check()

    coordinator.auto_verify_new_backups = False
    coordinator._schedule_automatic_verification(
        record, now=now, password_changed=False
    )
    coordinator.auto_verify_new_backups = True
    coordinator.integrity_result = BackupIntegrityResult.not_checked()
    coordinator._last_manual_verification_at = None
    coordinator._schedule_automatic_verification(
        record, now=now, password_changed=False
    )
    await asyncio.gather(*coordinator.hass.tasks)

    failed_task = asyncio.create_task(asyncio.sleep(0))
    coordinator._set_integrity_task(failed_task)
    await failed_task
    coordinator._consume_integrity_task_result(failed_task)
    assert coordinator.integrity_check_pending_or_running is False
