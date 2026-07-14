"""Button platform for BackupCheckup."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
            bool(self.coordinator.data.backups)
            and not self.coordinator.integrity_check_running
        )

    async def async_press(self) -> None:
        """Start the integrity check without blocking the UI."""
        await self.coordinator.async_start_integrity_check()


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
        await self.coordinator.async_request_refresh()
