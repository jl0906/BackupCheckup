"""Cleanup helpers for backup storage entities and devices."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .security import safe_error_type

_LOGGER = logging.getLogger(__name__)


async def async_remove_agent_entities(
    hass: HomeAssistant,
    *,
    entry_id: str,
    platform: str,
    agent_id: str,
    entities: Iterable[Entity],
) -> None:
    """Remove entities for a storage agent confirmed absent without leaking errors."""
    try:
        registry = er.async_get(hass)
        for entity in tuple(entities):
            unique_id = entity.unique_id
            entity_id = (
                registry.async_get_entity_id(platform, DOMAIN, unique_id)
                if unique_id is not None
                else None
            )
            await entity.async_remove()
            if entity_id is not None:
                registry.async_remove(entity_id)

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, f"{entry_id}:{agent_id}")}
        )
        if device is None:
            return
        if not er.async_entries_for_device(
            registry,
            device.id,
            include_disabled_entities=True,
        ):
            device_registry.async_remove_device(device.id)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Unable to remove stale backup storage entities: error_type=%s",
            safe_error_type(err),
        )
