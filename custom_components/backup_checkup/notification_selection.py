"""Helpers for selecting Companion App notification targets."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


def normalize_notification_targets(value: Any) -> list[str]:
    """Return unique notification entity IDs as a JSON-serializable list."""
    if isinstance(value, str):
        values: Iterable[Any] = (value,)
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        entity_id = item.strip()
        if (
            not entity_id.startswith("notify.")
            or len(entity_id) > 255
            or entity_id in seen
        ):
            continue
        seen.add(entity_id)
        result.append(entity_id)
    return result


def mobile_notification_options(
    hass: HomeAssistant,
    selected: Iterable[str] = (),
) -> list[dict[str, str]]:
    """Return friendly multi-select options for Companion App notify entities."""
    selected_ids = set(normalize_notification_targets(list(selected)))
    registry = er.async_get(hass)
    options: dict[str, str] = {}

    for entry in registry.entities.values():
        entity_id = getattr(entry, "entity_id", "")
        if (
            not isinstance(entity_id, str)
            or not entity_id.startswith("notify.")
            or getattr(entry, "platform", None) != "mobile_app"
        ):
            continue
        if (
            getattr(entry, "disabled_by", None) is not None
            and entity_id not in selected_ids
        ):
            continue

        state = hass.states.get(entity_id)
        label = (
            getattr(state, "name", None)
            or getattr(entry, "name", None)
            or getattr(entry, "original_name", None)
            or entity_id
        )
        options[entity_id] = str(label)

    # Keep an already configured target selectable even if its entity is temporarily
    # unavailable or was renamed. The normal validation and send path will surface it.
    for entity_id in selected_ids:
        options.setdefault(entity_id, entity_id)

    return [
        {"value": entity_id, "label": label}
        for entity_id, label in sorted(
            options.items(),
            key=lambda item: (item[1].casefold(), item[0]),
        )
    ]
