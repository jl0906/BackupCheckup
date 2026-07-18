"""Tests for isolated best-effort dynamic agent cleanup."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.backup_checkup import agent_cleanup


class _Entity:
    def __init__(self, unique_id: str, *, fail: bool = False) -> None:
        self.unique_id = unique_id
        self.fail = fail
        self.removed = False

    async def async_remove(self) -> None:
        if self.fail:
            raise RuntimeError("remove failed")
        self.removed = True


class _Registry:
    def __init__(self) -> None:
        self.removed: list[str] = []

    def async_get_entity_id(self, platform: str, domain: str, unique_id: str) -> str:
        return f"{platform}.{domain}_{unique_id}"

    def async_remove(self, entity_id: str) -> None:
        self.removed.append(entity_id)


class _DeviceRegistry:
    def __init__(self) -> None:
        self.removed: list[str] = []

    def async_get_device(self, **_kwargs: Any) -> Any:
        return SimpleNamespace(id="device-1")

    def async_remove_device(self, device_id: str) -> None:
        self.removed.append(device_id)


@pytest.mark.asyncio
async def test_cleanup_continues_after_one_entity_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _Registry()
    devices = _DeviceRegistry()
    first = _Entity("first", fail=True)
    second = _Entity("second")
    monkeypatch.setattr(agent_cleanup.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        agent_cleanup.dr, "async_get", lambda _hass: devices, raising=False
    )
    monkeypatch.setattr(
        agent_cleanup.er,
        "async_entries_for_device",
        lambda *_args, **_kwargs: [],
        raising=False,
    )

    await agent_cleanup.async_remove_agent_entities(
        object(),
        entry_id="entry",
        platform="sensor",
        agent_id="agent",
        entities=(first, second),
    )

    assert first.removed is False
    assert second.removed is True
    assert registry.removed == ["sensor.backup_checkup_second"]
    assert devices.removed == ["device-1"]


@pytest.mark.asyncio
async def test_cleanup_keeps_device_with_remaining_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _Registry()
    devices = _DeviceRegistry()
    monkeypatch.setattr(agent_cleanup.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        agent_cleanup.dr, "async_get", lambda _hass: devices, raising=False
    )
    monkeypatch.setattr(
        agent_cleanup.er,
        "async_entries_for_device",
        lambda *_args, **_kwargs: [object()],
        raising=False,
    )

    await agent_cleanup.async_remove_agent_entities(
        object(),
        entry_id="entry",
        platform="sensor",
        agent_id="agent",
        entities=(),
    )

    assert devices.removed == []


@pytest.mark.asyncio
async def test_cleanup_swallows_registry_and_device_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        agent_cleanup.er,
        "async_get",
        lambda _hass: (_ for _ in ()).throw(RuntimeError("registry")),
    )
    await agent_cleanup.async_remove_agent_entities(
        object(),
        entry_id="entry",
        platform="sensor",
        agent_id="agent",
        entities=(),
    )

    registry = _Registry()
    monkeypatch.setattr(agent_cleanup.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        agent_cleanup.dr,
        "async_get",
        lambda _hass: (_ for _ in ()).throw(RuntimeError("device")),
        raising=False,
    )
    await agent_cleanup.async_remove_agent_entities(
        object(),
        entry_id="entry",
        platform="sensor",
        agent_id="agent",
        entities=(),
    )
