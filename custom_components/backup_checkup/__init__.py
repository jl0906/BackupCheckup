"""The BackupCheckup integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_MONITORING_PROFILE,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_SIZE_CHECK_MODE,
    DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    DEFAULT_DATABASE_INTEGRITY_CHECK,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_SIZE_CHECK_MODE,
    PLATFORMS,
    PROFILE_CUSTOM,
)
from .coordinator import BackupCheckupCoordinator
from .history import BackupCheckupHistory
from .integrity import BackupIntegrityStore
from .repairs import async_remove_issues, async_update_issues


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older BackupCheckup configuration entries."""
    if entry.version >= 3:
        return True

    migrated_data = {
        CONF_MONITORING_PROFILE: PROFILE_CUSTOM,
        CONF_MINIMUM_BACKUP_SIZE_MB: DEFAULT_MINIMUM_BACKUP_SIZE_MB,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
        CONF_SIZE_CHECK_MODE: DEFAULT_SIZE_CHECK_MODE,
        CONF_REPAIR_ISSUES_ENABLED: DEFAULT_REPAIR_ISSUES_ENABLED,
        CONF_AUTO_VERIFY_NEW_BACKUPS: DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
        CONF_DATABASE_INTEGRITY_CHECK: DEFAULT_DATABASE_INTEGRITY_CHECK,
        **dict(entry.data),
    }
    hass.config_entries.async_update_entry(
        entry,
        data=migrated_data,
        version=3,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BackupCheckup from a config entry."""
    coordinator = BackupCheckupCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    def _sync_repair_issues() -> None:
        if coordinator.repair_issues_enabled:
            async_update_issues(hass, coordinator.data)
        else:
            async_remove_issues(hass)

    _sync_repair_issues()
    entry.async_on_unload(coordinator.async_add_listener(_sync_repair_issues))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a BackupCheckup config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_remove_issues(hass)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload BackupCheckup after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove persistent BackupCheckup history when the entry is deleted."""
    coordinator = getattr(entry, "runtime_data", None)
    if isinstance(coordinator, BackupCheckupCoordinator):
        await coordinator.history.async_remove()
        await coordinator.integrity_verifier.store.async_remove()
        return
    history = BackupCheckupHistory(hass, entry.entry_id)
    await history.async_remove()
    await BackupIntegrityStore(hass, entry.entry_id).async_remove()
