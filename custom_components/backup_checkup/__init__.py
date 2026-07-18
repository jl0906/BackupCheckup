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

from .activity import (
    ACTIVITY_OUTCOME_COMPLETED,
    ACTIVITY_OUTCOME_FAILED,
    ACTIVITY_OUTCOME_STARTED,
)
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
    CONFIG_ENTRY_VERSION,
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
    ENTITY_MODE_EXPERT,
    PLATFORMS,
    PROFILE_CUSTOM,
    SERVICE_REFRESH,
    SERVICE_TEST_NOTIFICATION,
    SERVICE_VERIFY_LATEST_BACKUP,
    VERSION,
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
from .security import (
    TempCleanupResult,
    cleanup_stale_temp_directories,
    safe_error_type,
)
from .storage_cleanup import cleanup_entry_store_files, cleanup_orphaned_store_files

_LOGGER = logging.getLogger(__name__)


def _record_activity(
    coordinator: object,
    action: str,
    outcome: str,
    *,
    level: int = logging.INFO,
    details: dict[str, object] | None = None,
) -> None:
    """Record activity when the coordinator exposes a runtime journal."""
    activity = getattr(coordinator, "activity", None)
    record = getattr(activity, "record", None)
    if callable(record):
        record(action, outcome, level=level, details=details)


def _entry_activity_logging_enabled(entry: ConfigEntry) -> bool:
    """Return whether the config entry selected Expert entity mode."""
    configuration = normalize_configuration(entry.data, entry.options)
    return configuration[CONF_ENTITY_MODE] == ENTITY_MODE_EXPERT


def _loaded_coordinator(hass: HomeAssistant) -> BackupCheckupCoordinator:
    """Return the loaded coordinator or raise a translated service error."""
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


async def _async_cleanup_orphaned_stores(hass: HomeAssistant) -> None:
    """Best-effort cleanup that must never block integration startup."""
    active_entry_ids = {
        entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)
    }
    try:
        result = await hass.async_add_executor_job(
            cleanup_orphaned_store_files,
            Path(hass.config.path(".storage")),
            active_entry_ids,
        )
    except Exception as err:  # noqa: BLE001 - filesystem executor boundary
        _LOGGER.warning(
            "Unable to inspect orphaned BackupCheckup stores: error_type=%s",
            safe_error_type(err),
        )
        return
    if result.removed:
        _LOGGER.info(
            "Removed orphaned BackupCheckup storage files: count=%s",
            result.removed,
        )
    if result.failed:
        _LOGGER.warning(
            "Unable to remove some orphaned BackupCheckup storage files: count=%s",
            result.failed,
        )


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Register actions and remove stores left by deleted config entries."""
    await _async_cleanup_orphaned_stores(hass)

    async def _async_verify_latest_backup(_call: ServiceCall) -> None:
        coordinator = _loaded_coordinator(hass)
        _record_activity(
            coordinator, "service_verify_latest_backup", ACTIVITY_OUTCOME_STARTED
        )
        await coordinator.async_start_integrity_check(source="manual")

    async def _async_refresh(_call: ServiceCall) -> None:
        coordinator = _loaded_coordinator(hass)
        _record_activity(coordinator, "service_refresh", ACTIVITY_OUTCOME_STARTED)
        await coordinator.async_request_refresh()
        _record_activity(coordinator, "service_refresh", ACTIVITY_OUTCOME_COMPLETED)

    async def _async_test_notification(_call: ServiceCall) -> None:
        coordinator = _loaded_coordinator(hass)
        _record_activity(
            coordinator, "service_test_notification", ACTIVITY_OUTCOME_STARTED
        )
        if (
            not coordinator.notifications_enabled
            or not coordinator.notification_targets
        ):
            _record_activity(
                coordinator,
                "service_test_notification",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
                details={"reason": "not_configured"},
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="notification_not_configured",
            )
        if not await coordinator.notification_manager.async_send_test(
            coordinator.notification_targets
        ):
            _record_activity(
                coordinator,
                "service_test_notification",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="notification_failed",
            )
        _record_activity(
            coordinator, "service_test_notification", ACTIVITY_OUTCOME_COMPLETED
        )

    for service, handler in (
        (SERVICE_VERIFY_LATEST_BACKUP, _async_verify_latest_backup),
        (SERVICE_REFRESH, _async_refresh),
        (SERVICE_TEST_NOTIFICATION, _async_test_notification),
    ):
        async_register_admin_service(hass, DOMAIN, service, handler)
    return True


def _legacy_schema_defaults(version: int) -> dict[str, object]:
    """Return defaults introduced after one historic config-entry version."""
    defaults: dict[str, object] = {}
    if version < 5:
        defaults.update(
            {
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
            }
        )
    if version < 6:
        defaults.update(
            {
                CONF_MAX_VERIFICATION_SIZE_GB: DEFAULT_MAX_VERIFICATION_SIZE_GB,
                CONF_MAX_EXPANDED_SIZE_GB: DEFAULT_MAX_EXPANDED_SIZE_GB,
                CONF_VERIFICATION_TIMEOUT_MINUTES: DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
                CONF_DATABASE_TIMEOUT_MINUTES: DEFAULT_DATABASE_TIMEOUT_MINUTES,
                CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
                    DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES
                ),
                CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
            }
        )
    return defaults


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate data atomically without changing the entity registry."""
    if entry.version > CONFIG_ENTRY_VERSION:
        if _entry_activity_logging_enabled(entry):
            _LOGGER.warning(
                "activity action=config_migration outcome=failed "
                "reason=newer_schema source_version=%s target_version=%s",
                entry.version,
                CONFIG_ENTRY_VERSION,
            )
        return False
    if entry.version == CONFIG_ENTRY_VERSION:
        return True

    migrated = {
        **_legacy_schema_defaults(entry.version),
        **dict(entry.data),
    }
    normalized = normalize_configuration(migrated, entry.options)
    source_version = entry.version
    hass.config_entries.async_update_entry(
        entry,
        data=normalized,
        options=normalized,
        version=CONFIG_ENTRY_VERSION,
    )
    if normalized[CONF_ENTITY_MODE] == ENTITY_MODE_EXPERT:
        _LOGGER.info(
            "activity action=config_migration outcome=completed "
            "source_version=%s target_version=%s",
            source_version,
            CONFIG_ENTRY_VERSION,
        )
    return True


async def _async_cleanup_stale_temporary_data(
    hass: HomeAssistant,
) -> TempCleanupResult:
    """Run best-effort stale temporary-data cleanup."""
    try:
        return await hass.async_add_executor_job(cleanup_stale_temp_directories)
    except Exception as err:  # noqa: BLE001 - filesystem executor boundary
        _LOGGER.warning(
            "Unable to inspect stale BackupCheckup temporary data: error_type=%s",
            safe_error_type(err),
        )
        return TempCleanupResult(failures=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BackupCheckup from a config entry."""
    coordinator = BackupCheckupCoordinator(hass, entry)
    _record_activity(
        coordinator,
        "config_entry_setup",
        ACTIVITY_OUTCOME_STARTED,
        details={"version": VERSION},
    )

    # Registry changes are setup concerns, not config-entry migration side effects.
    async_apply_entity_mode(
        hass,
        entry,
        coordinator.entity_mode,
        disable_others=False,
    )

    stale_cleanup = await _async_cleanup_stale_temporary_data(hass)
    _record_activity(
        coordinator,
        "temporary_data_cleanup",
        (
            ACTIVITY_OUTCOME_FAILED
            if stale_cleanup.issue_active
            else ACTIVITY_OUTCOME_COMPLETED
        ),
        level=logging.WARNING if stale_cleanup.issue_active else logging.INFO,
        details={
            "failures": stale_cleanup.failures,
            "remaining": stale_cleanup.remaining,
        },
    )
    if coordinator.repair_issues_enabled:
        async_set_temporary_cleanup_issue(hass, active=stale_cleanup.issue_active)

    await coordinator.async_config_entry_first_refresh()
    _record_activity(coordinator, "first_refresh", ACTIVITY_OUTCOME_COMPLETED)

    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    def _sync_repair_issues() -> None:
        if coordinator.repair_issues_enabled:
            async_update_issues(hass, coordinator.data)
        else:
            async_remove_issues(hass)

    _sync_repair_issues()
    _record_activity(
        coordinator,
        "repair_issue_sync",
        ACTIVITY_OUTCOME_COMPLETED,
        details={"enabled": coordinator.repair_issues_enabled},
    )
    entry.async_on_unload(coordinator.async_add_listener(_sync_repair_issues))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _record_activity(
        coordinator,
        "entity_platform_setup",
        ACTIVITY_OUTCOME_COMPLETED,
        details={"platform_count": len(PLATFORMS)},
    )

    async_apply_entity_mode(
        hass,
        entry,
        coordinator.entity_mode,
        disable_others=False,
    )
    _record_activity(
        coordinator,
        "config_entry_setup",
        ACTIVITY_OUTCOME_COMPLETED,
        details={"entity_mode": coordinator.entity_mode},
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a BackupCheckup config entry."""
    coordinator = getattr(entry, "runtime_data", None)
    if isinstance(coordinator, BackupCheckupCoordinator):
        _record_activity(coordinator, "config_entry_unload", ACTIVITY_OUTCOME_STARTED)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_remove_issues(hass)
    if isinstance(coordinator, BackupCheckupCoordinator):
        _record_activity(
            coordinator,
            "config_entry_unload",
            ACTIVITY_OUTCOME_COMPLETED if unload_ok else ACTIVITY_OUTCOME_FAILED,
            level=logging.INFO if unload_ok else logging.WARNING,
        )
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload BackupCheckup after its options change."""
    coordinator = getattr(entry, "runtime_data", None)
    if isinstance(coordinator, BackupCheckupCoordinator):
        _record_activity(coordinator, "config_entry_reload", ACTIVITY_OUTCOME_STARTED)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove every private BackupCheckup store when the entry is deleted."""
    coordinator = getattr(entry, "runtime_data", None)
    if isinstance(coordinator, BackupCheckupCoordinator):
        _record_activity(coordinator, "config_entry_remove", ACTIVITY_OUTCOME_STARTED)
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
        except Exception as err:  # noqa: BLE001 - Home Assistant Store boundary
            _LOGGER.warning(
                "Unable to remove a BackupCheckup private store: error_type=%s",
                safe_error_type(err),
            )

    try:
        cleanup_result = await hass.async_add_executor_job(
            cleanup_entry_store_files,
            Path(hass.config.path(".storage")),
            entry.entry_id,
        )
    except Exception as err:  # noqa: BLE001 - filesystem executor boundary
        _LOGGER.warning(
            "Unable to perform exact-path BackupCheckup store cleanup: error_type=%s",
            safe_error_type(err),
        )
        if isinstance(coordinator, BackupCheckupCoordinator):
            _record_activity(
                coordinator,
                "config_entry_remove",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
                details={"error_type": safe_error_type(err)},
            )
        return
    if cleanup_result.failed:
        _LOGGER.warning(
            "Unable to remove all BackupCheckup private stores: count=%s",
            cleanup_result.failed,
        )
    if isinstance(coordinator, BackupCheckupCoordinator):
        _record_activity(
            coordinator,
            "config_entry_remove",
            (
                ACTIVITY_OUTCOME_FAILED
                if cleanup_result.failed
                else ACTIVITY_OUTCOME_COMPLETED
            ),
            level=logging.WARNING if cleanup_result.failed else logging.INFO,
            details={
                "failed_store_count": cleanup_result.failed,
                "removed_store_count": getattr(cleanup_result, "removed", 0),
            },
        )


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a storage device only after its agent disappeared."""
    del hass
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
