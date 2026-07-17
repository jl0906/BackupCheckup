"""Read native Home Assistant backup state without relying on mutable entity IDs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CORE_AUTOMATIC_BACKUP_EVENT,
    CORE_BACKUP_MANAGER_STATE,
    CORE_LAST_AUTOMATIC_ATTEMPT,
    CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP,
    CORE_NEXT_AUTOMATIC_BACKUP,
)

_EVENT_MATCH_TOLERANCE = timedelta(minutes=2)


@dataclass(frozen=True, slots=True)
class NativeBackupState:
    """Stable native automatic-backup state used by BackupCheckup."""

    last_attempt: datetime | None
    last_success: datetime | None
    next_scheduled: datetime | None
    manager_state: str
    event_type: str
    event_at: datetime | None
    in_progress: bool


def _as_datetime(value: Any) -> datetime | None:
    """Convert a value to an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = dt_util.parse_datetime(value)
    else:
        return None
    if parsed is None:
        return None
    return dt_util.as_utc(parsed)


def _enum_value(value: Any) -> str:
    """Return a normalized enum/string value."""
    raw = getattr(value, "value", value)
    return str(raw).strip().casefold() if raw is not None else ""


def _registry_entity_id(
    hass: HomeAssistant,
    *,
    unique_id: str,
    fallback: str,
) -> str:
    """Resolve a Backup integration entity by stable unique ID."""
    try:
        registry = er.async_get(hass)
        for entry in registry.entities.values():
            if (
                getattr(entry, "platform", None) == "backup"
                and getattr(entry, "unique_id", None) == unique_id
            ):
                entity_id = getattr(entry, "entity_id", None)
                if isinstance(entity_id, str) and entity_id:
                    return entity_id
    except (AttributeError, TypeError):
        pass
    return fallback


def _state_datetime(hass: HomeAssistant, entity_id: str) -> datetime | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE, "", "none"}:
        return None
    return _as_datetime(state.state)


def _manager_config_value(manager: Any, *path: str) -> Any:
    value: Any = manager
    try:
        for part in path:
            value = getattr(value, part)
    except AttributeError:
        return None
    return value


def read_native_backup_state(
    hass: HomeAssistant,
    manager: Any,
    *,
    now: datetime,
) -> NativeBackupState:
    """Read current native state with manager data preferred over UI entities."""
    last_attempt = _as_datetime(
        _manager_config_value(
            manager, "config", "data", "last_attempted_automatic_backup"
        )
    )
    last_success = _as_datetime(
        _manager_config_value(
            manager, "config", "data", "last_completed_automatic_backup"
        )
    )
    next_scheduled = _as_datetime(
        _manager_config_value(
            manager, "config", "data", "schedule", "next_automatic_backup"
        )
    )

    if last_attempt is None:
        last_attempt = _state_datetime(
            hass,
            _registry_entity_id(
                hass,
                unique_id="last_attempted_automatic_backup",
                fallback=CORE_LAST_AUTOMATIC_ATTEMPT,
            ),
        )
    if last_success is None:
        last_success = _state_datetime(
            hass,
            _registry_entity_id(
                hass,
                unique_id="last_successful_automatic_backup",
                fallback=CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP,
            ),
        )
    if next_scheduled is None:
        next_scheduled = _state_datetime(
            hass,
            _registry_entity_id(
                hass,
                unique_id="next_scheduled_automatic_backup",
                fallback=CORE_NEXT_AUTOMATIC_BACKUP,
            ),
        )

    manager_state = _enum_value(getattr(manager, "state", None))
    if not manager_state:
        manager_entity = _registry_entity_id(
            hass,
            unique_id="backup_manager_state",
            fallback=CORE_BACKUP_MANAGER_STATE,
        )
        state = hass.states.get(manager_entity)
        manager_state = state.state.casefold() if state is not None else STATE_UNKNOWN

    action_event = getattr(manager, "last_action_event", None)
    event_type = _enum_value(getattr(action_event, "state", None))
    event_at: datetime | None = None
    event_entity_id = _registry_entity_id(
        hass,
        unique_id="automatic_backup_event",
        fallback=CORE_AUTOMATIC_BACKUP_EVENT,
    )
    event_state = hass.states.get(event_entity_id)
    if event_state is not None:
        attr_type = _enum_value(event_state.attributes.get("event_type"))
        if attr_type:
            event_type = attr_type
        event_at = _as_datetime(
            getattr(event_state, "last_changed", None)
            or getattr(event_state, "last_updated", None)
        )

    manager_in_progress = manager_state in {
        "create_backup",
        "creating_a_backup",
        "creating a backup",
        "receive_backup",
        "receiving_a_backup",
        "receiving a backup",
    }
    event_relevant = bool(
        event_at is not None
        and last_attempt is not None
        and event_at >= last_attempt - _EVENT_MATCH_TOLERANCE
        and event_at <= now + _EVENT_MATCH_TOLERANCE
    )
    if event_type in {"completed", "failed"} and not event_relevant:
        event_type = ""
    if event_type in {"in_progress", "in progress"} and not (
        manager_in_progress or event_relevant
    ):
        event_type = ""

    return NativeBackupState(
        last_attempt=last_attempt,
        last_success=last_success,
        next_scheduled=next_scheduled,
        manager_state=manager_state,
        event_type=event_type,
        event_at=event_at,
        in_progress=manager_in_progress or event_type in {"in_progress", "in progress"},
    )
