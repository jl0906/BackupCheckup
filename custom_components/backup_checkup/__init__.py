"""The BackupCheckup integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType

from .configuration import normalize_configuration
from .const import (
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_DATABASE_TIMEOUT_MINUTES,
    CONF_ENTITY_MODE,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_MONITORING_PROFILE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_SIZE_CHECK_MODE,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    DEFAULT_DATABASE_INTEGRITY_CHECK,
    DEFAULT_DATABASE_TIMEOUT_MINUTES,
    DEFAULT_ENTITY_MODE,
    DEFAULT_EXPOSE_BACKUP_METADATA,
    DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    DEFAULT_MAX_EXPANDED_SIZE_GB,
    DEFAULT_MAX_VERIFICATION_SIZE_GB,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_NOTIFICATION_TARGETS,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFY_ON_RECOVERY,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_SIZE_CHECK_MODE,
    DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
    DOMAIN,
    PLATFORMS,
    PROFILE_CUSTOM,
    SERVICE_REFRESH,
    SERVICE_TEST_NOTIFICATION,
    SERVICE_VERIFY_LATEST_BACKUP,
)
from .coordinator import BackupCheckupCoordinator
from .entity_mode import async_apply_entity_mode
from .history import BackupCheckupHistory
from .integrity import BackupIntegrityStore
from .notifications import BackupCheckupNotificationManager
from .repairs import (
    async_remove_issues,
    async_set_temporary_cleanup_issue,
    async_update_issues,
)
from .security import cleanup_stale_temp_directories
from .storage_cleanup import (
    cleanup_entry_store_files,
    cleanup_orphaned_store_files,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions and remove stores left by deleted config entries."""
    active_entry_ids = {
        entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)
    }
    cleanup_result = await hass.async_add_executor_job(
        cleanup_orphaned_store_files,
        Path(hass.config.path(".storage")),
        active_entry_ids,
    )
    if cleanup_result.removed:
        _LOGGER.info(
            "Removed orphaned BackupCheckup storage files: count=%s",
            cleanup_result.removed,
        )
    if cleanup_result.failed:
        _LOGGER.warning(
            "Unable to remove some orphaned BackupCheckup storage files: count=%s",
            cleanup_result.failed,
        )

    def _coordinator() -> BackupCheckupCoordinator:
        coordinator = next(
            (
                runtime
                for entry in hass.config_entries.async_entries(DOMAIN)
                if isinstance(
                    (runtime := getattr(entry, "runtime_data", None)),
                    BackupCheckupCoordinator,
                )
            ),
            None,
        )
        if coordinator is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="integration_not_loaded",
            )
        return coordinator

    async def _async_verify_latest_backup(_call: ServiceCall) -> None:
        await _coordinator().async_start_integrity_check(source="manual")

    async def _async_refresh(_call: ServiceCall) -> None:
        await _coordinator().async_request_refresh()

    async def _async_test_notification(_call: ServiceCall) -> None:
        coordinator = _coordinator()
        if (
            not coordinator.notifications_enabled
            or not coordinator.notification_targets
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="notification_not_configured",
            )
        if not await coordinator.notification_manager.async_send_test(
            coordinator.notification_targets
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="notification_failed",
            )

    for service, handler in (
        (SERVICE_VERIFY_LATEST_BACKUP, _async_verify_latest_backup),
        (SERVICE_REFRESH, _async_refresh),
        (SERVICE_TEST_NOTIFICATION, _async_test_notification),
    ):
        async_register_admin_service(hass, DOMAIN, service, handler)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older BackupCheckup configuration entries."""
    if entry.version > 9:
        return False
    if entry.version == 9:
        return True

    migrated_data = dict(entry.data)
    version = entry.version

    if version < 5:
        migrated_data = {
            CONF_MONITORING_PROFILE: PROFILE_CUSTOM,
            CONF_MINIMUM_BACKUP_SIZE_MB: DEFAULT_MINIMUM_BACKUP_SIZE_MB,
            CONF_MAXIMUM_SIZE_DROP_PERCENT: DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
            CONF_MINIMUM_REDUNDANT_LOCATIONS: DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
            CONF_SIZE_CHECK_MODE: DEFAULT_SIZE_CHECK_MODE,
            CONF_REPAIR_ISSUES_ENABLED: DEFAULT_REPAIR_ISSUES_ENABLED,
            CONF_AUTO_VERIFY_NEW_BACKUPS: DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
            CONF_DATABASE_INTEGRITY_CHECK: DEFAULT_DATABASE_INTEGRITY_CHECK,
            CONF_ENTITY_MODE: DEFAULT_ENTITY_MODE,
            CONF_NOTIFICATIONS_ENABLED: DEFAULT_NOTIFICATIONS_ENABLED,
            CONF_NOTIFICATION_TARGETS: list(DEFAULT_NOTIFICATION_TARGETS),
            CONF_NOTIFY_ON_RECOVERY: DEFAULT_NOTIFY_ON_RECOVERY,
            **migrated_data,
        }
        async_apply_entity_mode(
            hass,
            entry,
            DEFAULT_ENTITY_MODE,
            disable_others=False,
        )
        version = 5

    if version < 6:
        security_defaults = {
            CONF_MAX_VERIFICATION_SIZE_GB: DEFAULT_MAX_VERIFICATION_SIZE_GB,
            CONF_MAX_EXPANDED_SIZE_GB: DEFAULT_MAX_EXPANDED_SIZE_GB,
            CONF_VERIFICATION_TIMEOUT_MINUTES: DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
            CONF_DATABASE_TIMEOUT_MINUTES: DEFAULT_DATABASE_TIMEOUT_MINUTES,
            CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
                DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES
            ),
            CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
        }
        migrated_data = {**security_defaults, **migrated_data}
        version = 6

    if version < 7:
        async_apply_entity_mode(
            hass,
            entry,
            str(migrated_data.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)),
            disable_others=True,
        )
        version = 7

    if version < 8:
        # Re-apply the selected preset so Expert mode also enables the exact
        # timestamp entities that beta6 intentionally left disabled. Only
        # integration-disabled entries are changed; user and config-entry
        # choices remain untouched.
        async_apply_entity_mode(
            hass,
            entry,
            str(migrated_data.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)),
            disable_others=False,
        )
        version = 8

    # Schema 9 canonicalizes both persistence layers. Home Assistant keeps the
    # original data and later options separately; stale 2.1.x options otherwise
    # override newly migrated values during the first form render.
    normalized = normalize_configuration(migrated_data, entry.options)
    version = 9
    hass.config_entries.async_update_entry(
        entry,
        data=normalized,
        options=normalized,
        version=version,
    )
    async_apply_entity_mode(
        hass,
        entry,
        str(normalized.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)),
        disable_others=False,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BackupCheckup from a config entry."""
    coordinator = BackupCheckupCoordinator(hass, entry)

    # Repair integration-disabled registry entries before the platforms decide
    # which entities to instantiate. User and config-entry disables are kept.
    async_apply_entity_mode(
        hass,
        entry,
        coordinator.entity_mode,
        disable_others=False,
    )

    stale_cleanup = await hass.async_add_executor_job(cleanup_stale_temp_directories)
    if coordinator.repair_issues_enabled:
        async_set_temporary_cleanup_issue(
            hass,
            active=stale_cleanup.issue_active,
        )

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

    # Apply the enabling side of the selected preset after all platforms have
    # registered their entities. This repairs integration-disabled entities
    # after upgrades without overriding entities disabled by the user or by
    # the config-entry system option.
    async_apply_entity_mode(
        hass,
        entry,
        coordinator.entity_mode,
        disable_others=False,
    )
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
    """Remove every private BackupCheckup store when the entry is deleted."""
    coordinator = getattr(entry, "runtime_data", None)
    if isinstance(coordinator, BackupCheckupCoordinator):
        removers = (
            coordinator.history.async_remove,
            coordinator.integrity_verifier.store.async_remove,
            coordinator.notification_manager.async_remove,
        )
    else:
        removers = (
            BackupCheckupHistory(hass, entry.entry_id).async_remove,
            BackupIntegrityStore(hass, entry.entry_id).async_remove,
            BackupCheckupNotificationManager(hass, entry.entry_id).async_remove,
        )

    for remove in removers:
        try:
            await remove()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Unable to remove a BackupCheckup private store: error_type=%s",
                type(err).__name__,
            )

    # Store.async_remove() is the primary cleanup. The exact-path fallback also
    # covers interrupted or partially completed removal without using wildcards.
    cleanup_result = await hass.async_add_executor_job(
        cleanup_entry_store_files,
        Path(hass.config.path(".storage")),
        entry.entry_id,
    )
    if cleanup_result.failed:
        _LOGGER.warning(
            "Unable to remove all BackupCheckup private stores: count=%s",
            cleanup_result.failed,
        )


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a storage device only after its agent disappeared."""
    coordinator = getattr(entry, "runtime_data", None)
    if not isinstance(coordinator, BackupCheckupCoordinator):
        return False
    current_agent_ids = {
        summary.agent_id for summary in coordinator.data.agent_summaries
    }
    for domain, identifier in device_entry.identifiers:
        if domain != DOMAIN or not identifier.startswith(f"{entry.entry_id}:"):
            continue
        agent_id = identifier.split(":", 1)[1]
        return agent_id not in current_agent_ids
    return False
