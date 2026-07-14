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
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .coordinator import BackupCheckupCoordinator
from .entity import BackupCheckupAgentEntity, BackupCheckupEntity
from .models import BackupAgentSummary, BackupCheckupData


@dataclass(frozen=True, kw_only=True)
class BackupCheckupBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a BackupCheckup binary sensor."""

    value_fn: Callable[[BackupCheckupData], bool]


BINARY_SENSORS: tuple[BackupCheckupBinarySensorDescription, ...] = (
    BackupCheckupBinarySensorDescription(
        key="backup_integrity_problem",
        translation_key="backup_integrity_problem",
        entity_registry_enabled_default=False,
        icon="mdi:archive-cancel-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: bool(
            data.backups
            and data.integrity.backup_id == data.backups[0].backup_id
            and data.integrity.status in {"corrupt", "unreadable"}
        ),
    ),
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
        entity_registry_enabled_default=False,
        icon="mdi:archive-off-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.no_backup,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_stale",
        translation_key="backup_stale",
        entity_registry_enabled_default=False,
        icon="mdi:clock-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.backup_stale,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_backup_overdue",
        translation_key="automatic_backup_overdue",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_backup_overdue,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_backup_failed",
        translation_key="automatic_backup_failed",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:backup-restore",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_backup_failed,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_schedule_missing",
        translation_key="automatic_schedule_missing",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-remove",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_schedule_missing,
    ),
    BackupCheckupBinarySensorDescription(
        key="automatic_schedule_overdue",
        translation_key="automatic_schedule_overdue",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.automatic_schedule_overdue,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_manager_unavailable",
        translation_key="backup_manager_unavailable",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:database-off-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.manager_unavailable,
    ),
    BackupCheckupBinarySensorDescription(
        key="storage_error",
        translation_key="storage_error",
        entity_registry_enabled_default=False,
        icon="mdi:cloud-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.storage_error,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_size_suspicious",
        translation_key="backup_size_suspicious",
        entity_registry_enabled_default=False,
        icon="mdi:database-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.backup_size_suspicious,
    ),
    BackupCheckupBinarySensorDescription(
        key="latest_backup_incomplete",
        translation_key="latest_backup_incomplete",
        entity_registry_enabled_default=False,
        icon="mdi:archive-alert-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.latest_backup_incomplete,
    ),
    BackupCheckupBinarySensorDescription(
        key="backup_not_redundant",
        translation_key="backup_not_redundant",
        entity_registry_enabled_default=False,
        icon="mdi:server-network-off",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.backup_not_redundant,
    ),
    BackupCheckupBinarySensorDescription(
        key="required_location_missing",
        translation_key="required_location_missing",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:server-off",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.required_location_missing,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BackupCheckup binary sensors."""
    coordinator: BackupCheckupCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        BackupCheckupBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    ]

    known_agents = {summary.agent_id for summary in coordinator.data.agent_summaries}
    entities.extend(
        BackupCheckupAgentProblemBinarySensor(coordinator, entry, agent_id)
        for agent_id in sorted(known_agents)
    )
    async_add_entities(entities)

    def _add_new_agents() -> None:
        current_agents = {
            summary.agent_id for summary in coordinator.data.agent_summaries
        }
        new_agents = current_agents - known_agents
        if not new_agents:
            return
        known_agents.update(new_agents)
        async_add_entities(
            BackupCheckupAgentProblemBinarySensor(coordinator, entry, agent_id)
            for agent_id in sorted(new_agents)
        )

    entry.async_on_unload(coordinator.async_add_listener(_add_new_agents))


class BackupCheckupBinarySensor(BackupCheckupEntity, BinarySensorEntity):
    """A BackupCheckup binary sensor."""

    entity_description: BackupCheckupBinarySensorDescription

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        description: BackupCheckupBinarySensorDescription,
    ) -> None:
        """Initialize a BackupCheckup binary sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self.entity_id = f"binary_sensor.backup_checkup_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the problem state."""
        return self.entity_description.value_fn(self.coordinator.data)


class BackupCheckupAgentProblemBinarySensor(
    BackupCheckupAgentEntity,
    BinarySensorEntity,
):
    """Problem state for one Home Assistant backup storage location."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:server-network"
    _attr_translation_key = "agent_problem"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        agent_id: str,
    ) -> None:
        """Initialize a storage location problem sensor."""
        super().__init__(coordinator, entry, agent_id)
        agent_slug = slugify(agent_id)
        self._attr_unique_id = f"{entry.entry_id}_agent_{agent_id}_problem"
        self.entity_id = f"binary_sensor.backup_checkup_{agent_slug}_problem"

    def _summary(self) -> BackupAgentSummary | None:
        """Return the current storage location summary."""
        return next(
            (
                item
                for item in self.coordinator.data.agent_summaries
                if item.agent_id == self.agent_id
            ),
            None,
        )

    @property
    def is_on(self) -> bool:
        """Return whether this storage location has a problem."""
        summary = self._summary()
        return True if summary is None else summary.problem

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return storage location details."""
        summary = self._summary()
        return summary.as_dict() if summary else {"agent_id": self.agent_id}
