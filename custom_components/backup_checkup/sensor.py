"""Sensor platform for BackupCheckup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUS_OPTIONS
from .coordinator import BackupCheckupCoordinator
from .entity import BackupCheckupEntity
from .models import BackupCheckupData


@dataclass(frozen=True, kw_only=True)
class BackupCheckupSensorDescription(SensorEntityDescription):
    """Describe a BackupCheckup sensor."""

    value_fn: Callable[[BackupCheckupData], Any]
    attributes_fn: Callable[[BackupCheckupData], dict[str, Any]] | None = None


SENSORS: tuple[BackupCheckupSensorDescription, ...] = (
    BackupCheckupSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:backup-restore",
        device_class=SensorDeviceClass.ENUM,
        options=STATUS_OPTIONS,
        value_fn=lambda data: data.status,
        attributes_fn=lambda data: {
            "max_age_days": data.max_age_days,
            "checked_at": data.checked_at.isoformat(),
            "problem": data.problem,
        },
    ),
    BackupCheckupSensorDescription(
        key="stored_backups",
        translation_key="stored_backups",
        icon="mdi:archive-multiple",
        native_unit_of_measurement="backups",
        value_fn=lambda data: data.total_backups,
        attributes_fn=lambda data: {
            "automatic_backups": data.automatic_backups,
            "manual_or_other_backups": data.manual_backups,
            "agent_errors": data.agent_errors,
            "backups": [item.as_dict() for item in data.backups[:25]],
            "checked_at": data.checked_at.isoformat(),
        },
    ),
    BackupCheckupSensorDescription(
        key="automatic_backups",
        translation_key="automatic_backups",
        icon="mdi:calendar-sync",
        native_unit_of_measurement="backups",
        value_fn=lambda data: data.automatic_backups,
    ),
    BackupCheckupSensorDescription(
        key="manual_backups",
        translation_key="manual_backups",
        icon="mdi:hand-back-right",
        native_unit_of_measurement="backups",
        value_fn=lambda data: data.manual_backups,
    ),
    BackupCheckupSensorDescription(
        key="latest_backup",
        translation_key="latest_backup",
        icon="mdi:archive-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.latest_backup,
    ),
    BackupCheckupSensorDescription(
        key="latest_automatic_backup",
        translation_key="latest_automatic_backup",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.latest_automatic_backup,
    ),
    BackupCheckupSensorDescription(
        key="latest_manual_backup",
        translation_key="latest_manual_backup",
        icon="mdi:hand-okay",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.latest_manual_backup,
    ),
    BackupCheckupSensorDescription(
        key="latest_backup_age",
        translation_key="latest_backup_age",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.latest_backup_age_days,
    ),
    BackupCheckupSensorDescription(
        key="automatic_backup_age",
        translation_key="automatic_backup_age",
        icon="mdi:timer-alert-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.automatic_backup_age_days,
    ),
    BackupCheckupSensorDescription(
        key="manual_backup_age",
        translation_key="manual_backup_age",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.manual_backup_age_days,
    ),
    BackupCheckupSensorDescription(
        key="last_automatic_attempt",
        translation_key="last_automatic_attempt",
        icon="mdi:backup-restore",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_automatic_attempt,
    ),
    BackupCheckupSensorDescription(
        key="last_successful_automatic_event",
        translation_key="last_successful_automatic_event",
        icon="mdi:backup-restore",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_successful_automatic_event,
    ),
    BackupCheckupSensorDescription(
        key="next_automatic_backup",
        translation_key="next_automatic_backup",
        icon="mdi:calendar-arrow-right",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.next_automatic_backup,
    ),
    BackupCheckupSensorDescription(
        key="backup_manager_state",
        translation_key="backup_manager_state",
        icon="mdi:state-machine",
        value_fn=lambda data: data.manager_state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BackupCheckup sensors."""
    coordinator: BackupCheckupCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BackupCheckupSensor(coordinator, entry, description)
        for description in SENSORS
    )


class BackupCheckupSensor(BackupCheckupEntity, SensorEntity):
    """A BackupCheckup sensor."""

    entity_description: BackupCheckupSensorDescription

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        description: BackupCheckupSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self.entity_id = f"sensor.backup_checkup_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
