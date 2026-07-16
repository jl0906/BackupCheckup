"""Entity visibility presets for BackupCheckup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from .const import DOMAIN, ENTITY_MODE_EXPERT

STANDARD_SENSOR_KEYS = frozenset(
    {
        "integrity_status",
        "last_integrity_check",
        "health_score",
        "health_rating",
        "size_trend",
        "average_backup_size",
        "automatic_success_rate",
        "consecutive_automatic_failures",
        "status",
        "recommendation",
        "problem_count",
        "stored_backups",
        "automatic_backups",
        "latest_backup",
        "latest_automatic_backup",
        "latest_backup_age",
        "automatic_backup_age",
        "latest_backup_size",
        "latest_automatic_backup_size",
        "latest_backup_result",
        "latest_backup_locations",
    }
)

STANDARD_BINARY_SENSOR_KEYS = frozenset(
    {
        "problem",
        "no_backup",
        "backup_stale",
        "automatic_backup_overdue",
        "automatic_backup_failed",
        "automatic_schedule_missing",
        "automatic_schedule_overdue",
        "backup_manager_unavailable",
        "storage_error",
        "backup_size_suspicious",
        "latest_backup_incomplete",
        "backup_not_redundant",
        "backup_integrity_problem",
        "backup_integrity_warning",
        "backup_checksum_changed",
    }
)

STANDARD_BUTTON_KEYS = frozenset(
    {
        "verify_latest_backup",
        "refresh",
        "test_notification",
    }
)


def entity_enabled_by_default(
    entity_domain: str,
    key: str,
    entity_mode: str,
    *,
    agent_entity: bool = False,
) -> bool:
    """Return whether an entity should initially be enabled."""
    if entity_mode == ENTITY_MODE_EXPERT:
        return True
    if agent_entity:
        return False
    if entity_domain == "sensor":
        return key in STANDARD_SENSOR_KEYS
    if entity_domain == "binary_sensor":
        return key in STANDARD_BINARY_SENSOR_KEYS
    if entity_domain == "button":
        return key in STANDARD_BUTTON_KEYS
    return False


def _registry_entry_should_be_enabled(
    entity_domain: str,
    unique_id: str,
    entry_id: str,
    entity_mode: str,
) -> bool:
    """Return the requested enabled state for a registered entity."""
    prefix = f"{entry_id}_"
    if not unique_id.startswith(prefix):
        return False
    key = unique_id.removeprefix(prefix)
    if key.startswith("agent_"):
        return entity_mode == ENTITY_MODE_EXPERT
    return entity_enabled_by_default(entity_domain, key, entity_mode)


@callback
def async_apply_entity_mode(
    hass: HomeAssistant,
    entry: ConfigEntry,
    entity_mode: str,
    *,
    disable_others: bool = True,
) -> None:
    """Apply a newly selected entity preset to existing registry entries.

    User-disabled entities stay disabled. The preset only changes entities that are
    enabled or disabled by BackupCheckup itself.
    """
    registry = er.async_get(hass)
    for registry_entry in tuple(registry.entities.values()):
        if (
            registry_entry.config_entry_id != entry.entry_id
            or registry_entry.platform != DOMAIN
        ):
            continue

        should_enable = _registry_entry_should_be_enabled(
            registry_entry.domain,
            registry_entry.unique_id,
            entry.entry_id,
            entity_mode,
        )
        if should_enable:
            if registry_entry.disabled_by is RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(
                    registry_entry.entity_id,
                    disabled_by=None,
                )
            continue

        if disable_others and registry_entry.disabled_by is None:
            registry.async_update_entity(
                registry_entry.entity_id,
                disabled_by=RegistryEntryDisabler.INTEGRATION,
            )
