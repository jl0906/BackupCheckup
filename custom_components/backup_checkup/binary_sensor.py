"""Binary sensor platform for BackupCheckup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BackupCheckupCoordinator
from .entity import BackupCheckupEntity
from .models import BackupCheckupData


@dataclass(frozen=True, kw_only=True)
class BackupCheckupBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a BackupCheckup binary sensor."""

    value_fn: Callable[[BackupCheckupData], bool]


BINARY_SENSORS: tuple[BackupCheckupBinarySensorDescription, ...] = (
    BackupCheckupBinarySensorDescription(
        key="problem",
        translation_key="problem",
        icon="mdi:backup-restore",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.problem,
    ),
    BackupCheckupBinarySensorDescription(
        key="no_backup",
        translation_key="no_backup",
        icon="mdi:archive-off-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.no_backup,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_stale",
        translation_key="backup_stale",
        icon="mdi:clock-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.backup_stale,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_backup_overdue",
        translation_key="automatic_backup_overdue",
        icon="mdi:calendar-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_backup_overdue,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_backup_failed",
        translation_key="automatic_backup_failed",
        icon="mdi:backup-restore",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_backup_failed,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_schedule_missing",
        translation_key="automatic_schedule_missing",
        icon="mdi:calendar-remove",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_schedule_missing,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_schedule_overdue",
        translation_key="automatic_schedule_overdue",
        icon="mdi:calendar-clock",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_schedule_overdue,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_manager_unavailable",
        translation_key="backup_manager_unavailable",
        icon="mdi:database-off-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.manager_unavailable,
    ),
    BackupCheckupBinarySensorDescription(
        key="storage_error",
        translation_key="storage_error",
        icon="mdi:cloud-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.storage_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BackupCheckup binary sensors."""
    coordinator: BackupCheckupCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BackupCheckupBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class BackupCheckupBinarySensor(BackupCheckupEntity, BinarySensorEntity):
    """A BackupCheckup binary sensor."""

    entity_description: BackupCheckupBinarySensorDescription

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        description: BackupCheckupBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self.entity_id = f"binary_sensor.backup_checkup_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return whether the monitored problem is active."""
        return self.entity_description.value_fn(self.coordinator.data)
