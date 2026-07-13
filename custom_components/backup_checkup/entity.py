"""Base entity for BackupCheckup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import BackupCheckupCoordinator


class BackupCheckupEntity(CoordinatorEntity[BackupCheckupCoordinator]):
    """Base BackupCheckup entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize a BackupCheckup entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="BackupCheckup",
            model="Home Assistant backup monitor",
            sw_version=VERSION,
        )
