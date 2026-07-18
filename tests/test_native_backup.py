"""Functional and branch tests for native Home Assistant backup state reads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.backup_checkup import native_backup


class _States:
    def __init__(self, states: dict[str, Any] | None = None) -> None:
        self._states = states or {}

    def get(self, entity_id: str) -> Any:
        return self._states.get(entity_id)


class _Hass:
    def __init__(self, states: dict[str, Any] | None = None) -> None:
        self.states = _States(states)


def _state(
    value: str,
    *,
    attributes: dict[str, Any] | None = None,
    changed: datetime | None = None,
) -> Any:
    return SimpleNamespace(
        state=value,
        attributes=attributes or {},
        last_changed=changed,
        last_updated=changed,
    )


def test_datetime_and_enum_boundaries() -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    assert native_backup._as_datetime(now) == now
    assert native_backup._as_datetime(datetime(2026, 7, 17, 12)).tzinfo is UTC
    assert native_backup._as_datetime("2026-07-17T12:00:00Z") == now
    assert native_backup._as_datetime("invalid") is None
    assert native_backup._as_datetime(17) is None
    assert native_backup._as_datetime(None) is None

    class _Value(Enum):
        RUNNING = " Running "

    assert native_backup._enum_value(_Value.RUNNING) == "running"
    assert native_backup._enum_value(None) == ""

    class _Broken:
        @property
        def value(self) -> str:
            raise RuntimeError("broken")

    assert native_backup._enum_value(_Broken()) == ""


def test_registry_resolution_and_state_datetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = {
        "sensor.match": SimpleNamespace(
            platform="backup", unique_id="wanted", entity_id="sensor.custom"
        ),
        "sensor.other": SimpleNamespace(
            platform="other", unique_id="wanted", entity_id="sensor.nope"
        ),
    }
    monkeypatch.setattr(
        native_backup.er,
        "async_get",
        lambda _hass: SimpleNamespace(entities=entries),
    )
    hass = _Hass(
        {
            "sensor.custom": _state("2026-07-17T12:00:00+00:00"),
            "sensor.unknown": _state("unknown"),
        }
    )
    assert (
        native_backup._registry_entity_id(
            hass, unique_id="wanted", fallback="sensor.fallback"
        )
        == "sensor.custom"
    )
    assert native_backup._state_datetime(hass, "sensor.custom") == datetime(
        2026, 7, 17, 12, tzinfo=UTC
    )
    assert native_backup._state_datetime(hass, "sensor.unknown") is None
    assert native_backup._state_datetime(hass, "sensor.missing") is None

    entries["sensor.match"].entity_id = ""
    assert (
        native_backup._registry_entity_id(
            hass, unique_id="wanted", fallback="sensor.fallback"
        )
        == "sensor.fallback"
    )
    monkeypatch.setattr(
        native_backup.er,
        "async_get",
        lambda _hass: (_ for _ in ()).throw(RuntimeError("registry")),
    )
    assert (
        native_backup._registry_entity_id(
            hass, unique_id="wanted", fallback="sensor.fallback"
        )
        == "sensor.fallback"
    )


def test_manager_path_and_event_validation() -> None:
    manager = SimpleNamespace(config=SimpleNamespace(data=SimpleNamespace(value=3)))
    assert native_backup._manager_config_value(manager, "config", "data", "value") == 3
    assert native_backup._manager_config_value(manager, "config", "missing") is None

    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    attempt = now - timedelta(minutes=10)
    assert native_backup._event_is_relevant(now, attempt, now) is True
    assert native_backup._event_is_relevant(None, attempt, now) is False
    assert native_backup._event_is_relevant(now, None, now) is False
    assert (
        native_backup._event_is_relevant(attempt - timedelta(minutes=3), attempt, now)
        is False
    )
    assert (
        native_backup._validated_event_type(
            "completed", event_relevant=False, manager_in_progress=False
        )
        == ""
    )
    assert (
        native_backup._validated_event_type(
            "failed", event_relevant=True, manager_in_progress=False
        )
        == "failed"
    )
    assert (
        native_backup._validated_event_type(
            "in_progress", event_relevant=False, manager_in_progress=False
        )
        == ""
    )
    assert (
        native_backup._validated_event_type(
            "in progress", event_relevant=False, manager_in_progress=True
        )
        == "in progress"
    )


def test_read_native_state_prefers_manager_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    attempt = now - timedelta(minutes=5)
    success = now - timedelta(days=1)
    scheduled = now + timedelta(days=1)
    manager = SimpleNamespace(
        config=SimpleNamespace(
            data=SimpleNamespace(
                last_attempted_automatic_backup=attempt,
                last_completed_automatic_backup=success,
                schedule=SimpleNamespace(next_automatic_backup=scheduled),
            )
        ),
        state=SimpleNamespace(value="create_backup"),
        last_action_event=SimpleNamespace(state=SimpleNamespace(value="in_progress")),
    )
    monkeypatch.setattr(
        native_backup.er,
        "async_get",
        lambda _hass: SimpleNamespace(entities={}),
    )
    result = native_backup.read_native_backup_state(_Hass(), manager, now=now)
    assert result.last_attempt == attempt
    assert result.last_success == success
    assert result.next_scheduled == scheduled
    assert result.manager_state == "create_backup"
    assert result.event_type == "in_progress"
    assert result.in_progress is True


def test_read_native_state_uses_registry_entities_and_filters_stale_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    attempt = now - timedelta(hours=1)
    stale = now - timedelta(days=2)
    entries = {
        key: SimpleNamespace(platform="backup", unique_id=unique, entity_id=entity_id)
        for key, unique, entity_id in (
            ("attempt", "last_attempted_automatic_backup", "sensor.attempt"),
            ("success", "last_successful_automatic_backup", "sensor.success"),
            ("next", "next_scheduled_automatic_backup", "sensor.next"),
            ("manager", "backup_manager_state", "sensor.manager"),
            ("event", "automatic_backup_event", "event.backup"),
        )
    }
    monkeypatch.setattr(
        native_backup.er,
        "async_get",
        lambda _hass: SimpleNamespace(entities=entries),
    )
    hass = _Hass(
        {
            "sensor.attempt": _state(attempt.isoformat()),
            "sensor.success": _state((attempt - timedelta(days=1)).isoformat()),
            "sensor.next": _state((now + timedelta(days=1)).isoformat()),
            "sensor.manager": _state("Idle"),
            "event.backup": _state(
                "event",
                attributes={"event_type": "completed"},
                changed=stale,
            ),
        }
    )
    manager = SimpleNamespace(
        config=SimpleNamespace(data=SimpleNamespace()),
        state=None,
        last_action_event=SimpleNamespace(state="failed"),
    )

    result = native_backup.read_native_backup_state(hass, manager, now=now)
    assert result.last_attempt == attempt
    assert result.manager_state == "idle"
    assert result.event_type == ""
    assert result.event_at == stale
    assert result.in_progress is False


def test_native_event_without_entity_uses_manager_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        native_backup.er,
        "async_get",
        lambda _hass: SimpleNamespace(entities={}),
    )
    hass = _Hass()
    manager = SimpleNamespace(last_action_event=SimpleNamespace(state="failed"))
    assert native_backup._native_event_state(hass, manager) == ("failed", None)
    assert (
        native_backup._native_manager_state(hass, SimpleNamespace(state=None))
        == "unknown"
    )
