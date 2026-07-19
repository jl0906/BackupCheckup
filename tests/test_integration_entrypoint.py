"""Functional tests for the integration entrypoint lifecycle."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from custom_components.backup_checkup.const import (
    CONF_ENTITY_MODE,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    ENTITY_MODE_EXPERT,
    SERVICE_REFRESH,
    SERVICE_TEST_NOTIFICATION,
    SERVICE_VERIFY_LATEST_BACKUP,
)
from custom_components.backup_checkup.security import TempCleanupResult


def _load_entrypoint() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "backup_checkup"
        / "__init__.py"
    )
    name = "custom_components.backup_checkup"
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[str(path.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules[name]
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules[name] = previous
    return module


class _ConfigEntries:
    def __init__(self, entries: list[Any] | None = None) -> None:
        self.entries = entries or []
        self.updated: dict[str, Any] | None = None
        self.forwarded = False
        self.unload_result = True
        self.reloaded: list[str] = []

    def async_entries(self, _domain: str) -> list[Any]:
        return self.entries

    def async_update_entry(self, _entry: Any, **kwargs: Any) -> None:
        self.updated = kwargs

    async def async_forward_entry_setups(self, _entry: Any, _platforms: Any) -> None:
        self.forwarded = True

    async def async_unload_platforms(self, _entry: Any, _platforms: Any) -> bool:
        return self.unload_result

    async def async_reload(self, entry_id: str) -> None:
        self.reloaded.append(entry_id)


class _Hass:
    def __init__(self, entries: list[Any] | None = None) -> None:
        self.config_entries = _ConfigEntries(entries)
        self.config = SimpleNamespace(path=lambda value: f"/config/{value}")
        self.executor_result: Any = SimpleNamespace(removed=0, failed=0)
        self.executor_error: Exception | None = None

    async def async_add_executor_job(self, function: Any, *args: Any) -> Any:
        if self.executor_error is not None:
            raise self.executor_error
        if callable(self.executor_result):
            return self.executor_result(function, *args)
        return self.executor_result


class _Coordinator:
    def __init__(self) -> None:
        self.notifications_enabled = True
        self.notification_targets = ("notify.mobile_app_phone",)
        self.notification_manager = SimpleNamespace(
            async_send_test=AsyncMock(return_value=True),
            async_remove=AsyncMock(),
        )
        self.async_start_integrity_check = AsyncMock()
        self.async_request_refresh = AsyncMock()
        self.entity_mode = "recommended"
        self.repair_issues_enabled = True
        self.data = SimpleNamespace(agent_summaries=())
        self.history = SimpleNamespace(async_remove=AsyncMock())
        self.integrity_verifier = SimpleNamespace(
            store=SimpleNamespace(async_remove=AsyncMock())
        )
        self.async_shutdown = AsyncMock()
        self.async_config_entry_first_refresh = AsyncMock()
        self.async_start_adaptive_polling = lambda: setattr(
            self, "adaptive_started", True
        )
        self.listener: Any = None

    def async_add_listener(self, listener: Any) -> Any:
        self.listener = listener
        return listener


def test_loaded_coordinator_success_and_failure() -> None:
    module = _load_entrypoint()
    module.BackupCheckupCoordinator = _Coordinator
    coordinator = _Coordinator()
    hass = _Hass([SimpleNamespace(runtime_data=coordinator)])
    assert module._loaded_coordinator(hass) is coordinator

    with pytest.raises(HomeAssistantError) as error:
        module._loaded_coordinator(_Hass([SimpleNamespace(runtime_data=None)]))
    assert error.value.translation_key == "integration_not_loaded"


@pytest.mark.asyncio
async def test_orphan_cleanup_success_and_failure() -> None:
    module = _load_entrypoint()
    hass = _Hass([SimpleNamespace(entry_id="active")])
    hass.executor_result = SimpleNamespace(removed=2, failed=1)
    await module._async_cleanup_orphaned_stores(hass)

    hass.executor_error = RuntimeError("filesystem")
    await module._async_cleanup_orphaned_stores(hass)


@pytest.mark.asyncio
async def test_setup_registers_and_executes_admin_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_entrypoint()
    module.BackupCheckupCoordinator = _Coordinator
    coordinator = _Coordinator()
    hass = _Hass([SimpleNamespace(runtime_data=coordinator)])
    handlers: dict[str, Any] = {}
    monkeypatch.setattr(module, "_async_cleanup_orphaned_stores", AsyncMock())
    monkeypatch.setattr(
        module,
        "async_register_admin_service",
        lambda _hass, _domain, service, handler: handlers.__setitem__(service, handler),
    )

    assert await module.async_setup(hass, {}) is True
    assert set(handlers) == {
        SERVICE_VERIFY_LATEST_BACKUP,
        SERVICE_REFRESH,
        SERVICE_TEST_NOTIFICATION,
    }
    await handlers[SERVICE_VERIFY_LATEST_BACKUP](object())
    await handlers[SERVICE_REFRESH](object())
    await handlers[SERVICE_TEST_NOTIFICATION](object())
    coordinator.async_start_integrity_check.assert_awaited_once_with(source="manual")
    coordinator.async_request_refresh.assert_awaited_once()
    coordinator.notification_manager.async_send_test.assert_awaited_once()

    coordinator.notifications_enabled = False
    with pytest.raises(HomeAssistantError) as error:
        await handlers[SERVICE_TEST_NOTIFICATION](object())
    assert error.value.translation_key == "notification_not_configured"

    coordinator.notifications_enabled = True
    coordinator.notification_manager.async_send_test = AsyncMock(return_value=False)
    with pytest.raises(HomeAssistantError) as error:
        await handlers[SERVICE_TEST_NOTIFICATION](object())
    assert error.value.translation_key == "notification_failed"


@pytest.mark.asyncio
async def test_schema_migration_paths() -> None:
    module = _load_entrypoint()
    assert module._legacy_schema_defaults(4)
    assert module._legacy_schema_defaults(5)
    assert module._legacy_schema_defaults(6) == {}

    hass = _Hass()
    assert (
        await module.async_migrate_entry(
            hass, ConfigEntry(data={}, options={}, version=CONFIG_ENTRY_VERSION + 1)
        )
        is False
    )
    assert (
        await module.async_migrate_entry(
            hass, ConfigEntry(data={}, options={}, version=CONFIG_ENTRY_VERSION)
        )
        is True
    )
    old = ConfigEntry(data={"max_age_days": 7}, options={}, version=4)
    assert await module.async_migrate_entry(hass, old) is True
    assert hass.config_entries.updated is not None
    assert hass.config_entries.updated["version"] == CONFIG_ENTRY_VERSION
    assert hass.config_entries.updated["data"]["max_age_days"] == 7


@pytest.mark.asyncio
async def test_migration_activity_logging_follows_entity_mode(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Migration activity is silent in Standard and visible in Expert mode."""
    module = _load_entrypoint()
    hass = _Hass()

    with caplog.at_level("INFO", logger=module.__name__):
        assert (
            await module.async_migrate_entry(
                hass,
                ConfigEntry(data={}, options={}, version=CONFIG_ENTRY_VERSION + 1),
            )
            is False
        )
    assert "config_migration" not in caplog.text

    caplog.clear()
    with caplog.at_level("INFO", logger=module.__name__):
        assert (
            await module.async_migrate_entry(
                hass,
                ConfigEntry(
                    data={},
                    options={CONF_ENTITY_MODE: ENTITY_MODE_EXPERT},
                    version=CONFIG_ENTRY_VERSION + 1,
                ),
            )
            is False
        )
    assert "activity action=config_migration outcome=failed" in caplog.text


@pytest.mark.asyncio
async def test_temporary_cleanup_and_setup_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_entrypoint()
    hass = _Hass()
    hass.executor_result = TempCleanupResult()
    cleanup = await module._async_cleanup_stale_temporary_data(hass)
    assert cleanup.issue_active is False
    hass.executor_error = RuntimeError("temp")
    assert (await module._async_cleanup_stale_temporary_data(hass)).failures == 1
    hass.executor_error = None

    coordinator = _Coordinator()
    entry = ConfigEntry(entry_id="entry")
    applied: list[tuple[str, bool]] = []
    issue_states: list[bool] = []
    updates: list[Any] = []
    monkeypatch.setattr(module, "BackupCheckupCoordinator", lambda *_args: coordinator)
    monkeypatch.setattr(
        module,
        "async_apply_entity_mode",
        lambda _hass, _entry, mode, *, disable_others=False: applied.append(
            (mode, disable_others)
        ),
    )
    monkeypatch.setattr(
        module,
        "_async_cleanup_stale_temporary_data",
        AsyncMock(return_value=TempCleanupResult(failures=1)),
    )
    monkeypatch.setattr(
        module,
        "async_set_temporary_cleanup_issue",
        lambda _hass, *, active: issue_states.append(active),
    )
    monkeypatch.setattr(
        module,
        "async_update_issues",
        lambda _hass, data: updates.append(data),
    )

    assert await module.async_setup_entry(hass, entry) is True
    assert entry.runtime_data is coordinator
    assert coordinator.async_config_entry_first_refresh.await_count == 1
    assert hass.config_entries.forwarded is True
    assert applied == [("recommended", False), ("recommended", False)]
    assert issue_states == [True]
    assert updates == [coordinator.data]

    coordinator.repair_issues_enabled = False
    removed = []
    monkeypatch.setattr(
        module, "async_remove_issues", lambda _hass: removed.append(True)
    )
    coordinator.listener()
    assert removed == [True]


@pytest.mark.asyncio
async def test_unload_reload_remove_and_device_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_entrypoint()
    coordinator = _Coordinator()
    module.BackupCheckupCoordinator = _Coordinator
    entry = ConfigEntry(entry_id="entry")
    entry.runtime_data = coordinator
    hass = _Hass()
    removed_issues: list[bool] = []
    monkeypatch.setattr(
        module,
        "async_remove_issues",
        lambda _hass: removed_issues.append(True),
    )

    assert await module.async_unload_entry(hass, entry) is True
    assert removed_issues == [True]
    hass.config_entries.unload_result = False
    assert await module.async_unload_entry(hass, entry) is False

    hass.executor_result = SimpleNamespace(failed=1)
    await module.async_remove_entry(hass, entry)
    coordinator.history.async_remove.assert_awaited_once()
    coordinator.integrity_verifier.store.async_remove.assert_awaited_once()
    coordinator.notification_manager.async_remove.assert_awaited_once()

    coordinator.data.agent_summaries = (SimpleNamespace(agent_id="present"),)
    device = SimpleNamespace(
        identifiers={(DOMAIN, "entry:present"), ("other", "entry:gone")}
    )
    assert await module.async_remove_config_entry_device(hass, entry, device) is False
    device.identifiers = {(DOMAIN, "entry:gone")}
    assert await module.async_remove_config_entry_device(hass, entry, device) is True
    device.identifiers = {("other", "entry:gone")}
    assert await module.async_remove_config_entry_device(hass, entry, device) is False

    entry.runtime_data = None
    assert await module.async_remove_config_entry_device(hass, entry, device) is False


@pytest.mark.asyncio
async def test_remove_entry_isolates_store_and_filesystem_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_entrypoint()
    module.BackupCheckupCoordinator = _Coordinator
    coordinator = _Coordinator()
    coordinator.history.async_remove = AsyncMock(side_effect=RuntimeError("store"))
    entry = ConfigEntry(entry_id="entry")
    entry.runtime_data = coordinator
    hass = _Hass()
    hass.executor_error = RuntimeError("filesystem")

    await module.async_remove_entry(hass, entry)
    coordinator.integrity_verifier.store.async_remove.assert_awaited_once()
    coordinator.notification_manager.async_remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_setup_registers_shutdown_before_first_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partially initialized coordinators are cleaned up when setup aborts."""
    module = _load_entrypoint()
    coordinator = _Coordinator()
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=RuntimeError("first refresh failed")
    )
    entry = ConfigEntry(entry_id="entry")
    hass = _Hass()
    monkeypatch.setattr(module, "BackupCheckupCoordinator", lambda *_args: coordinator)
    monkeypatch.setattr(
        module, "async_apply_entity_mode", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        module,
        "_async_cleanup_stale_temporary_data",
        AsyncMock(return_value=TempCleanupResult()),
    )

    with pytest.raises(RuntimeError, match="first refresh failed"):
        await module.async_setup_entry(hass, entry)

    assert entry._unloads == [coordinator.async_shutdown]
    assert entry.runtime_data is None
