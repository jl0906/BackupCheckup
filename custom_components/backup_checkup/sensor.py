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
from homeassistant.const import (
    CONF_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    BACKUP_RESULT_OPTIONS,
    DOMAIN,
    HEALTH_RATING_OPTIONS,
    INTEGRITY_DATABASE_OPTIONS,
    INTEGRITY_STATUS_CHECKING,
    INTEGRITY_STATUS_NOT_CHECKED,
    INTEGRITY_STATUS_OPTIONS,
    RECOMMENDATION_OPTIONS,
    SIZE_TREND_OPTIONS,
    STATUS_OPTIONS,
)
from .coordinator import BackupCheckupCoordinator
from .entity import BackupCheckupAgentEntity, BackupCheckupEntity
from .models import BackupAgentSummary, BackupCheckupData


@dataclass(frozen=True, kw_only=True)
class BackupCheckupSensorDescription(SensorEntityDescription):
    """Describe a BackupCheckup sensor."""

    value_fn: Callable[[BackupCheckupData], Any]
    attributes_fn: Callable[[BackupCheckupData], dict[str, Any]] | None = None


SENSORS: tuple[BackupCheckupSensorDescription, ...] = (
    BackupCheckupSensorDescription(
        key="integrity_status",
        translation_key="integrity_status",
        icon="mdi:shield-search",
        device_class=SensorDeviceClass.ENUM,
        options=INTEGRITY_STATUS_OPTIONS,
        value_fn=lambda data: (
            INTEGRITY_STATUS_CHECKING
            if data.integrity_check_running
            else (
                data.integrity.status
                if data.backups
                and data.integrity.backup_id == data.backups[0].backup_id
                else INTEGRITY_STATUS_NOT_CHECKED
            )
        ),
        attributes_fn=lambda data: {
            "applies_to_latest_backup": bool(
                data.backups and data.integrity.backup_id == data.backups[0].backup_id
            ),
            "checked_at": (
                data.integrity.checked_at.isoformat()
                if data.integrity.checked_at
                else None
            ),
            "backup_date": (
                data.integrity.backup_date.isoformat()
                if data.integrity.backup_date
                else None
            ),
            "storage_location": data.integrity.agent_id,
            "archive_count": data.integrity.archive_count,
            "file_count": data.integrity.file_count,
            "protected": data.integrity.protected,
            "database_status": data.integrity.database_status,
            "warnings": list(data.integrity.warnings),
            "error_code": data.integrity.error_code,
        },
    ),
    BackupCheckupSensorDescription(
        key="last_integrity_check",
        translation_key="last_integrity_check",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.integrity.checked_at,
    ),
    BackupCheckupSensorDescription(
        key="integrity_checksum",
        translation_key="integrity_checksum",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fingerprint",
        value_fn=lambda data: data.integrity.sha256,
        attributes_fn=lambda data: {
            "algorithm": "SHA-256",
            "checksum_changed": data.integrity.checksum_changed,
            "applies_to_latest_backup": bool(
                data.backups and data.integrity.backup_id == data.backups[0].backup_id
            ),
        },
    ),
    BackupCheckupSensorDescription(
        key="verified_backup_size",
        translation_key="verified_backup_size",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:database-check-outline",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        value_fn=lambda data: (
            round(data.integrity.verified_size / 1_000_000, 2)
            if data.integrity.verified_size is not None
            else None
        ),
    ),
    BackupCheckupSensorDescription(
        key="integrity_check_duration",
        translation_key="integrity_check_duration",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-check-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda data: data.integrity.duration_seconds,
    ),
    BackupCheckupSensorDescription(
        key="database_integrity_status",
        translation_key="database_integrity_status",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:database-search-outline",
        device_class=SensorDeviceClass.ENUM,
        options=INTEGRITY_DATABASE_OPTIONS,
        value_fn=lambda data: data.integrity.database_status,
    ),
    BackupCheckupSensorDescription(
        key="health_score",
        translation_key="health_score",
        icon="mdi:shield-check-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.health_score,
        attributes_fn=lambda data: {
            "rating": data.health_rating,
            "deductions": data.health_score_deductions,
            "analysis_window_days": data.analytics_window_days,
            "automatic_success_rate": data.automatic_success_rate,
            "consecutive_automatic_failures": (data.consecutive_automatic_failures),
        },
    ),
    BackupCheckupSensorDescription(
        key="health_rating",
        translation_key="health_rating",
        entity_registry_enabled_default=False,
        icon="mdi:shield-star-outline",
        device_class=SensorDeviceClass.ENUM,
        options=HEALTH_RATING_OPTIONS,
        value_fn=lambda data: data.health_rating,
        attributes_fn=lambda data: {
            "score": data.health_score,
            "deductions": data.health_score_deductions,
        },
    ),
    BackupCheckupSensorDescription(
        key="size_trend",
        translation_key="size_trend",
        entity_registry_enabled_default=False,
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.ENUM,
        options=SIZE_TREND_OPTIONS,
        value_fn=lambda data: data.size_trend,
        attributes_fn=lambda data: {
            "change_percent": data.size_trend_percent,
            "analyzed_backup_count": data.analyzed_backup_count,
            "analysis_window_days": data.analytics_window_days,
        },
    ),
    BackupCheckupSensorDescription(
        key="average_backup_size",
        translation_key="average_backup_size",
        entity_registry_enabled_default=False,
        icon="mdi:database-arrow-left-outline",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            round(data.average_backup_size / 1_000_000, 2)
            if data.average_backup_size is not None
            else None
        ),
        attributes_fn=lambda data: {
            "average_backup_size_bytes": data.average_backup_size,
            "analyzed_backup_count": data.analyzed_backup_count,
            "analysis_window_days": data.analytics_window_days,
        },
    ),
    BackupCheckupSensorDescription(
        key="longest_backup_gap",
        translation_key="longest_backup_gap",
        entity_registry_enabled_default=False,
        icon="mdi:timeline-clock-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.longest_backup_gap_days,
        attributes_fn=lambda data: {
            "analyzed_backup_count": data.analyzed_backup_count,
            "analysis_window_days": data.analytics_window_days,
        },
    ),
    BackupCheckupSensorDescription(
        key="automatic_success_rate",
        translation_key="automatic_success_rate",
        entity_registry_enabled_default=False,
        icon="mdi:check-decagram-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.automatic_success_rate,
        attributes_fn=lambda data: {
            "observed_attempts": data.automatic_attempts_observed,
            "successful_attempts": data.automatic_successes_observed,
            "failed_attempts": data.automatic_failures_observed,
            "tracking_started_at": (
                data.history_tracking_started_at.isoformat()
                if data.history_tracking_started_at
                else None
            ),
            "analysis_window_days": data.analytics_window_days,
        },
    ),
    BackupCheckupSensorDescription(
        key="consecutive_automatic_failures",
        translation_key="consecutive_automatic_failures",
        entity_registry_enabled_default=False,
        icon="mdi:alert-circle-check-outline",
        value_fn=lambda data: data.consecutive_automatic_failures,
        attributes_fn=lambda data: {
            "observed_attempts": data.automatic_attempts_observed,
            "tracking_started_at": (
                data.history_tracking_started_at.isoformat()
                if data.history_tracking_started_at
                else None
            ),
        },
    ),
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
            "problem_count": data.problem_count,
            "health_score": data.health_score,
            "health_rating": data.health_rating,
            "active_problems": list(data.active_problems),
        },
    ),
    BackupCheckupSensorDescription(
        key="recommendation",
        translation_key="recommendation",
        icon="mdi:lightbulb-on-outline",
        device_class=SensorDeviceClass.ENUM,
        options=RECOMMENDATION_OPTIONS,
        value_fn=lambda data: data.recommendation,
        attributes_fn=lambda data: {
            "active_problems": list(data.active_problems),
            "problem_count": data.problem_count,
            "health_score": data.health_score,
            "health_rating": data.health_rating,
        },
    ),
    BackupCheckupSensorDescription(
        key="problem_count",
        translation_key="problem_count",
        entity_registry_enabled_default=False,
        icon="mdi:counter",
        value_fn=lambda data: data.problem_count,
        attributes_fn=lambda data: {
            "active_problems": list(data.active_problems),
        },
    ),
    BackupCheckupSensorDescription(
        key="stored_backups",
        translation_key="stored_backups",
        icon="mdi:archive-multiple",
        value_fn=lambda data: data.total_backups,
        attributes_fn=lambda data: {
            "automatic_backups": data.automatic_backups,
            "manual_or_other_backups": data.manual_backups,
            "agent_errors": data.agent_errors,
            "agents": [item.as_dict() for item in data.agent_summaries],
            "checked_at": data.checked_at.isoformat(),
        },
    ),
    BackupCheckupSensorDescription(
        key="automatic_backups",
        translation_key="automatic_backups",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-sync",
        value_fn=lambda data: data.automatic_backups,
    ),
    BackupCheckupSensorDescription(
        key="manual_backups",
        translation_key="manual_backups",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:hand-back-right",
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
        entity_registry_enabled_default=False,
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.latest_automatic_backup,
    ),
    BackupCheckupSensorDescription(
        key="latest_manual_backup",
        translation_key="latest_manual_backup",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
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
        entity_registry_enabled_default=False,
        icon="mdi:timer-alert-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.automatic_backup_age_days,
        attributes_fn=lambda data: {
            "precise_age_days": data.automatic_backup_age_days_precise,
        },
    ),
    BackupCheckupSensorDescription(
        key="manual_backup_age",
        translation_key="manual_backup_age",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.manual_backup_age_days,
    ),
    BackupCheckupSensorDescription(
        key="latest_backup_size",
        translation_key="latest_backup_size",
        icon="mdi:database",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.latest_backup_size,
        attributes_fn=lambda data: {
            "size_check_mode": data.size_check_mode,
            "minimum_backup_size_bytes": data.minimum_backup_size_bytes,
            "size_change_percent": data.latest_backup_size_change_percent,
            "maximum_size_drop_percent": data.maximum_size_drop_percent,
        },
    ),
    BackupCheckupSensorDescription(
        key="latest_automatic_backup_size",
        translation_key="latest_automatic_backup_size",
        entity_registry_enabled_default=False,
        icon="mdi:database-clock",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.latest_automatic_backup_size,
    ),
    BackupCheckupSensorDescription(
        key="latest_backup_size_change",
        translation_key="latest_backup_size_change",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.latest_backup_size_change_percent,
    ),
    BackupCheckupSensorDescription(
        key="latest_backup_result",
        translation_key="latest_backup_result",
        entity_registry_enabled_default=False,
        icon="mdi:clipboard-check-outline",
        device_class=SensorDeviceClass.ENUM,
        options=BACKUP_RESULT_OPTIONS,
        value_fn=lambda data: data.latest_backup_result,
        attributes_fn=lambda data: data.backups[0].as_dict() if data.backups else {},
    ),
    BackupCheckupSensorDescription(
        key="latest_backup_locations",
        translation_key="latest_backup_locations",
        entity_registry_enabled_default=False,
        icon="mdi:server-network",
        value_fn=lambda data: data.latest_backup_locations,
        attributes_fn=lambda data: {
            "location_ids": list(data.latest_backup_location_ids),
            "minimum_required": data.minimum_redundant_locations,
        },
    ),
    BackupCheckupSensorDescription(
        key="last_automatic_attempt",
        translation_key="last_automatic_attempt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:backup-restore",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_automatic_attempt,
    ),
    BackupCheckupSensorDescription(
        key="last_successful_automatic_event",
        translation_key="last_successful_automatic_event",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:check-circle-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_successful_automatic_event,
    ),
    BackupCheckupSensorDescription(
        key="next_automatic_backup",
        translation_key="next_automatic_backup",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.next_automatic_backup,
    ),
    BackupCheckupSensorDescription(
        key="backup_manager_state",
        translation_key="backup_manager_state",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:database-cog-outline",
        value_fn=lambda data: data.manager_state,
    ),
)


AGENT_METRICS: tuple[str, ...] = (
    "backups",
    "latest_backup",
    "latest_backup_age",
    "latest_backup_size",
    "stored_bytes",
)


def _migrate_average_backup_size_unit(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ensure the existing average-size sensor is displayed in megabytes."""
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_average_backup_size"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    if entity_id is None:
        return

    registry_entry = registry.async_get(entity_id)
    if registry_entry is None:
        return

    sensor_options = dict(registry_entry.options.get("sensor", {}))
    if sensor_options.get(CONF_UNIT_OF_MEASUREMENT) == UnitOfInformation.MEGABYTES:
        return

    sensor_options[CONF_UNIT_OF_MEASUREMENT] = UnitOfInformation.MEGABYTES
    registry.async_update_entity_options(entity_id, "sensor", sensor_options)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BackupCheckup sensors."""
    coordinator: BackupCheckupCoordinator = entry.runtime_data
    _migrate_average_backup_size_unit(hass, entry)
    entities: list[SensorEntity] = [
        BackupCheckupSensor(coordinator, entry, description) for description in SENSORS
    ]

    known_agents = {summary.agent_id for summary in coordinator.data.agent_summaries}
    entities.extend(
        BackupCheckupAgentSensor(coordinator, entry, agent_id, metric)
        for agent_id in sorted(known_agents)
        for metric in AGENT_METRICS
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
            BackupCheckupAgentSensor(coordinator, entry, agent_id, metric)
            for agent_id in sorted(new_agents)
            for metric in AGENT_METRICS
        )

    entry.async_on_unload(coordinator.async_add_listener(_add_new_agents))


class BackupCheckupSensor(BackupCheckupEntity, SensorEntity):
    """A BackupCheckup sensor."""

    entity_description: BackupCheckupSensorDescription

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        description: BackupCheckupSensorDescription,
    ) -> None:
        """Initialize a BackupCheckup sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        if description.device_class is SensorDeviceClass.ENUM:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(description.options or [])
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self.entity_id = f"sensor.backup_checkup_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return sensor attributes."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)


class BackupCheckupAgentSensor(BackupCheckupAgentEntity, SensorEntity):
    """A metric for one Home Assistant backup storage location."""

    def __init__(
        self,
        coordinator: BackupCheckupCoordinator,
        entry: ConfigEntry,
        agent_id: str,
        metric: str,
    ) -> None:
        """Initialize an agent sensor."""
        super().__init__(coordinator, entry, agent_id)
        self.metric = metric
        agent_slug = slugify(agent_id)
        self._attr_unique_id = f"{entry.entry_id}_agent_{agent_id}_{metric}"
        self.entity_id = f"sensor.backup_checkup_{agent_slug}_{metric}"
        self._attr_translation_key = f"agent_{metric}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._attr_entity_registry_enabled_default = False

        if metric == "latest_backup":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_icon = "mdi:archive-clock"
        elif metric == "latest_backup_age":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.DAYS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:timer-sand"
        elif metric in {"latest_backup_size", "stored_bytes"}:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:database"
        else:
            self._attr_icon = "mdi:archive-multiple"

    def _summary(self) -> BackupAgentSummary | None:
        """Return the current summary for this storage location."""
        return next(
            (
                item
                for item in self.coordinator.data.agent_summaries
                if item.agent_id == self.agent_id
            ),
            None,
        )

    @property
    def native_value(self) -> Any:
        """Return the storage location metric."""
        summary = self._summary()
        if summary is None:
            return None
        return {
            "backups": summary.backup_count,
            "latest_backup": summary.latest_backup,
            "latest_backup_age": summary.latest_backup_age_days,
            "latest_backup_size": summary.latest_backup_size,
            "stored_bytes": summary.stored_bytes,
        }[self.metric]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return storage location details."""
        summary = self._summary()
        return summary.as_dict() if summary else {"agent_id": self.agent_id}
