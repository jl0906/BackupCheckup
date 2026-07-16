"""Button platform for BackupCheckup."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SERVICE_REFRESH,
    SERVICE_TEST_NOTIFICATION,
    SERVICE_VERIFY_LATEST_BACKUP,
)
from .coordinator import BackupCheckupCoordinator
from .entity import BackupCheckupEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BackupCheckup buttons."""
    coordinator: BackupCheckupCoordinator = entry.runtime_data
    async_add_entities(
        [
            BackupCheckupVerifyButton(coordinator, entry),
            BackupCheckupRefreshButton(coordinator, entry),
            BackupCheckupTestNotificationButton(coordinator, entry),
        ]
    )


class BackupCheckupVerifyButton(BackupCheckupEntity, ButtonEntity):
    """Start a full verification of the newest backup."""

    _attr_translation_key = "verify_latest_backup"
    _attr_icon = "mdi:shield-search"

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the verification button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_verify_latest_backup"
        self.entity_id = "button.backup_checkup_verify_latest_backup"

    @property
    def available(self) -> bool:
        """Only allow a check when a backup exists and no check is running."""
        return (
            super().available
            and bool(self.coordinator.data.monitored_backups)
            and not self.coordinator.integrity_check_pending_or_running
            and not self.coordinator.manual_verification_cooldown_active
        )

    async def async_press(self) -> None:
        """Start the administrator-protected integrity-check action."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_VERIFY_LATEST_BACKUP,
            blocking=True,
            context=self._context,
        )


class BackupCheckupRefreshButton(BackupCheckupEntity, ButtonEntity):
    """Request an immediate refresh of all backup health data."""

    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self.entity_id = "button.backup_checkup_refresh"

    async def async_press(self) -> None:
        """Refresh BackupCheckup data immediately."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            blocking=True,
            context=self._context,
        )


class BackupCheckupTestNotificationButton(BackupCheckupEntity, ButtonEntity):
    """Send a test message to configured mobile devices."""

    _attr_translation_key = "test_notification"
    _attr_icon = "mdi:cellphone-message"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the test-notification button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_test_notification"
        self.entity_id = "button.backup_checkup_test_notification"

    @property
    def available(self) -> bool:
        """Only allow testing when mobile notifications are configured."""
        return bool(
            super().available
            and self.coordinator.notifications_enabled
            and self.coordinator.notification_targets
        )

    async def async_press(self) -> None:
        """Send a localized test message."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_TEST_NOTIFICATION,
            blocking=True,
            context=self._context,
        )
