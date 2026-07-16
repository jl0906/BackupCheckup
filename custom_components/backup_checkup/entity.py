"""Base entities for BackupCheckup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import BackupCheckupCoordinator
from .security import anonymous_agent_reference


class BackupCheckupEntity(CoordinatorEntity[BackupCheckupCoordinator]):
    """Base entity attached to the main BackupCheckup device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize a BackupCheckup entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="BackupCheckup",
            model="Home Assistant backup health monitor",
            sw_version=VERSION,
        )


class BackupCheckupAgentEntity(BackupCheckupEntity):
    """Base entity attached to one backup storage location device."""

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        agent_id: str,
    ) -> None:
        """Initialize a backup storage location entity."""
        super().__init__(coordinator, entry)
        self.agent_id = agent_id
        self.agent_reference = anonymous_agent_reference(entry.entry_id, agent_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}:{agent_id}")},
            name=f"Backup storage {self.agent_reference}",
            manufacturer="Home Assistant",
            model="Backup storage location",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def available(self) -> bool:
        """Return unavailable when the storage agent disappeared."""
        return super().available and any(
            item.agent_id == self.agent_id
            for item in self.coordinator.data.agent_summaries
        )
