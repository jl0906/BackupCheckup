"""Reusable config-flow schemas for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
    CONF_ADAPTIVE_ERROR_THRESHOLD,
    CONF_ADAPTIVE_POLLING,
    CONF_ANALYTICS_WINDOW_DAYS,
    CONF_DATABASE_TIMEOUT_MINUTES,
    CONF_ENTITY_MODE,
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    CONF_MAX_AGE_DAYS,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_MONITORING_POLICY,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_RUNTIME_PROFILE,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_POLICY,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    ENTITY_MODE_OPTIONS,
    MAX_ACTIVE_UPDATE_INTERVAL_MINUTES,
    MAX_ADAPTIVE_ERROR_THRESHOLD,
    MAX_ANALYTICS_WINDOW_DAYS,
    MAX_DATABASE_TIMEOUT_MINUTES,
    MAX_ERROR_BACKOFF_INTERVAL_MINUTES,
    MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    MAX_MAX_AGE_DAYS,
    MAX_MAX_EXPANDED_SIZE_GB,
    MAX_MAX_VERIFICATION_SIZE_GB,
    MAX_MAXIMUM_SIZE_DROP_PERCENT,
    MAX_MINIMUM_BACKUP_SIZE_MB,
    MAX_REDUNDANT_LOCATIONS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MAX_VERIFICATION_TIMEOUT_MINUTES,
    MIN_ACTIVE_UPDATE_INTERVAL_MINUTES,
    MIN_ADAPTIVE_ERROR_THRESHOLD,
    MIN_ANALYTICS_WINDOW_DAYS,
    MIN_DATABASE_TIMEOUT_MINUTES,
    MIN_ERROR_BACKOFF_INTERVAL_MINUTES,
    MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    MIN_MAX_AGE_DAYS,
    MIN_MAX_EXPANDED_SIZE_GB,
    MIN_MAX_VERIFICATION_SIZE_GB,
    MIN_MAXIMUM_SIZE_DROP_PERCENT,
    MIN_MINIMUM_BACKUP_SIZE_MB,
    MIN_REDUNDANT_LOCATIONS,
    MIN_UPDATE_INTERVAL_MINUTES,
    MIN_VERIFICATION_TIMEOUT_MINUTES,
    MONITORING_POLICY_OPTIONS,
    RUNTIME_PROFILE_OPTIONS,
    SIZE_CHECK_OPTIONS,
    VERIFICATION_POLICY_CUSTOM,
    VERIFICATION_POLICY_OPTIONS,
)
from .notification_selection import mobile_notification_options

SUMMARY_HARDWARE = "summary_hardware"
SUMMARY_RUNTIME_PROFILE = "summary_runtime_profile"
SUMMARY_UPDATE_INTERVAL = "summary_update_interval"
SUMMARY_ACTIVE_INTERVAL = "summary_active_interval"
SUMMARY_ERROR_BACKOFF = "summary_error_backoff"
SUMMARY_ADAPTIVE_POLLING = "summary_adaptive_polling"
SUMMARY_DOWNLOAD_LIMIT = "summary_download_limit"
SUMMARY_EXPANDED_LIMIT = "summary_expanded_limit"
SUMMARY_MONITORING_POLICY = "summary_monitoring_policy"
SUMMARY_MAX_AGE = "summary_max_age"
SUMMARY_REDUNDANT_LOCATIONS = "summary_redundant_locations"
SUMMARY_REPAIR_ISSUES = "summary_repair_issues"
SUMMARY_VERIFICATION_POLICY = "summary_verification_policy"
SUMMARY_ENTITY_MODE = "summary_entity_mode"
SUMMARY_EXPOSE_METADATA = "summary_expose_metadata"
SUMMARY_NOTIFICATIONS_ENABLED = "summary_notifications_enabled"
SUMMARY_NOTIFICATION_COUNT = "summary_notification_count"
SUMMARY_NOTIFY_ON_RECOVERY = "summary_notify_on_recovery"

_ENABLED_STATE_OPTIONS = ["enabled", "disabled"]


def integer_selector(minimum: int, maximum: int) -> NumberSelector:
    """Return a whole-number selector."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )


def translated_select(options: list[str], translation_key: str) -> SelectSelector:
    """Return a translated dropdown selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key=translation_key,
        )
    )


def runtime_profile_schema(values: dict[str, Any]) -> vol.Schema:
    """Return the hardware/runtime profile form."""
    return vol.Schema(
        {
            vol.Required(
                CONF_RUNTIME_PROFILE, default=values[CONF_RUNTIME_PROFILE]
            ): translated_select(RUNTIME_PROFILE_OPTIONS, "runtime_profile"),
            vol.Required(
                CONF_ADAPTIVE_POLLING, default=values[CONF_ADAPTIVE_POLLING]
            ): BooleanSelector(),
        }
    )


def runtime_custom_schema(values: dict[str, Any]) -> vol.Schema:
    """Return custom performance and verification-budget settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=values[CONF_UPDATE_INTERVAL_MINUTES],
            ): integer_selector(
                MIN_UPDATE_INTERVAL_MINUTES, MAX_UPDATE_INTERVAL_MINUTES
            ),
            vol.Required(
                CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
                default=values[CONF_ACTIVE_UPDATE_INTERVAL_MINUTES],
            ): integer_selector(
                MIN_ACTIVE_UPDATE_INTERVAL_MINUTES,
                MAX_ACTIVE_UPDATE_INTERVAL_MINUTES,
            ),
            vol.Required(
                CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
                default=values[CONF_ERROR_BACKOFF_INTERVAL_MINUTES],
            ): integer_selector(
                MIN_ERROR_BACKOFF_INTERVAL_MINUTES,
                MAX_ERROR_BACKOFF_INTERVAL_MINUTES,
            ),
            vol.Required(
                CONF_ADAPTIVE_ERROR_THRESHOLD,
                default=values[CONF_ADAPTIVE_ERROR_THRESHOLD],
            ): integer_selector(
                MIN_ADAPTIVE_ERROR_THRESHOLD,
                MAX_ADAPTIVE_ERROR_THRESHOLD,
            ),
            vol.Required(
                CONF_MAX_VERIFICATION_SIZE_GB,
                default=values[CONF_MAX_VERIFICATION_SIZE_GB],
            ): integer_selector(
                MIN_MAX_VERIFICATION_SIZE_GB,
                MAX_MAX_VERIFICATION_SIZE_GB,
            ),
            vol.Required(
                CONF_MAX_EXPANDED_SIZE_GB,
                default=values[CONF_MAX_EXPANDED_SIZE_GB],
            ): integer_selector(MIN_MAX_EXPANDED_SIZE_GB, MAX_MAX_EXPANDED_SIZE_GB),
            vol.Required(
                CONF_VERIFICATION_TIMEOUT_MINUTES,
                default=values[CONF_VERIFICATION_TIMEOUT_MINUTES],
            ): integer_selector(
                MIN_VERIFICATION_TIMEOUT_MINUTES,
                MAX_VERIFICATION_TIMEOUT_MINUTES,
            ),
            vol.Required(
                CONF_DATABASE_TIMEOUT_MINUTES,
                default=values[CONF_DATABASE_TIMEOUT_MINUTES],
            ): integer_selector(
                MIN_DATABASE_TIMEOUT_MINUTES,
                MAX_DATABASE_TIMEOUT_MINUTES,
            ),
            vol.Required(
                CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
                default=values[CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES],
            ): integer_selector(
                MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
                MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            ),
        }
    )


def monitoring_policy_schema(values: dict[str, Any]) -> vol.Schema:
    """Return the monitoring-policy form."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MONITORING_POLICY, default=values[CONF_MONITORING_POLICY]
            ): translated_select(MONITORING_POLICY_OPTIONS, "monitoring_policy")
        }
    )


def monitoring_custom_schema(values: dict[str, Any]) -> vol.Schema:
    """Return custom backup-health thresholds."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MAX_AGE_DAYS, default=values[CONF_MAX_AGE_DAYS]
            ): integer_selector(MIN_MAX_AGE_DAYS, MAX_MAX_AGE_DAYS),
            vol.Required(
                CONF_SIZE_CHECK_MODE, default=values[CONF_SIZE_CHECK_MODE]
            ): translated_select(SIZE_CHECK_OPTIONS, "size_check_mode"),
            vol.Required(
                CONF_MINIMUM_BACKUP_SIZE_MB,
                default=values[CONF_MINIMUM_BACKUP_SIZE_MB],
            ): integer_selector(MIN_MINIMUM_BACKUP_SIZE_MB, MAX_MINIMUM_BACKUP_SIZE_MB),
            vol.Required(
                CONF_MAXIMUM_SIZE_DROP_PERCENT,
                default=values[CONF_MAXIMUM_SIZE_DROP_PERCENT],
            ): integer_selector(
                MIN_MAXIMUM_SIZE_DROP_PERCENT,
                MAX_MAXIMUM_SIZE_DROP_PERCENT,
            ),
            vol.Required(
                CONF_MINIMUM_REDUNDANT_LOCATIONS,
                default=values[CONF_MINIMUM_REDUNDANT_LOCATIONS],
            ): integer_selector(MIN_REDUNDANT_LOCATIONS, MAX_REDUNDANT_LOCATIONS),
            vol.Required(
                CONF_REPAIR_ISSUES_ENABLED,
                default=values[CONF_REPAIR_ISSUES_ENABLED],
            ): BooleanSelector(),
            vol.Required(
                CONF_ANALYTICS_WINDOW_DAYS,
                default=values[CONF_ANALYTICS_WINDOW_DAYS],
            ): integer_selector(MIN_ANALYTICS_WINDOW_DAYS, MAX_ANALYTICS_WINDOW_DAYS),
        }
    )


def verification_policy_schema(values: dict[str, Any]) -> vol.Schema:
    """Return the integrity-check strategy form."""
    selected = values[CONF_VERIFICATION_POLICY]
    options = list(VERIFICATION_POLICY_OPTIONS)
    if selected == VERIFICATION_POLICY_CUSTOM:
        options.append(VERIFICATION_POLICY_CUSTOM)
    return vol.Schema(
        {
            vol.Required(CONF_VERIFICATION_POLICY, default=selected): translated_select(
                options, "verification_policy"
            )
        }
    )


def presentation_schema(hass: HomeAssistant, values: dict[str, Any]) -> vol.Schema:
    """Return entity, privacy, repair, and notification settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_ENTITY_MODE, default=values[CONF_ENTITY_MODE]
            ): translated_select(ENTITY_MODE_OPTIONS, "entity_mode"),
            vol.Required(
                CONF_EXPOSE_BACKUP_METADATA,
                default=values[CONF_EXPOSE_BACKUP_METADATA],
            ): BooleanSelector(),
            vol.Required(
                CONF_NOTIFICATIONS_ENABLED,
                default=values[CONF_NOTIFICATIONS_ENABLED],
            ): BooleanSelector(),
            vol.Optional(
                CONF_NOTIFICATION_TARGETS,
                default=list(values[CONF_NOTIFICATION_TARGETS]),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=mobile_notification_options(
                        hass, values[CONF_NOTIFICATION_TARGETS]
                    ),
                    multiple=True,
                    custom_value=False,
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=True,
                )
            ),
            vol.Required(
                CONF_NOTIFY_ON_RECOVERY,
                default=values[CONF_NOTIFY_ON_RECOVERY],
            ): BooleanSelector(),
        }
    )


def _readonly_text(value: str) -> TextSelector:
    """Return a read-only text selector for resolved summary values."""
    del value
    return TextSelector(TextSelectorConfig(read_only=True))


def _readonly_select(options: list[str], translation_key: str) -> SelectSelector:
    """Return a translated read-only select selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key=translation_key,
            read_only=True,
        )
    )


def summary_schema(values: dict[str, Any]) -> vol.Schema:
    """Return a localized, read-only setup summary."""
    verification_options = list(VERIFICATION_POLICY_OPTIONS)
    if values[CONF_VERIFICATION_POLICY] == VERIFICATION_POLICY_CUSTOM:
        verification_options.append(VERIFICATION_POLICY_CUSTOM)

    enabled = "enabled"
    disabled = "disabled"
    return vol.Schema(
        {
            vol.Optional(
                SUMMARY_HARDWARE, default=str(values[SUMMARY_HARDWARE])
            ): _readonly_text(str(values[SUMMARY_HARDWARE])),
            vol.Optional(
                SUMMARY_RUNTIME_PROFILE, default=values[CONF_RUNTIME_PROFILE]
            ): _readonly_select(RUNTIME_PROFILE_OPTIONS, "runtime_profile"),
            vol.Optional(
                SUMMARY_UPDATE_INTERVAL,
                default=str(values[CONF_UPDATE_INTERVAL_MINUTES]),
            ): _readonly_text(str(values[CONF_UPDATE_INTERVAL_MINUTES])),
            vol.Optional(
                SUMMARY_ACTIVE_INTERVAL,
                default=str(values[CONF_ACTIVE_UPDATE_INTERVAL_MINUTES]),
            ): _readonly_text(str(values[CONF_ACTIVE_UPDATE_INTERVAL_MINUTES])),
            vol.Optional(
                SUMMARY_ERROR_BACKOFF,
                default=str(values[CONF_ERROR_BACKOFF_INTERVAL_MINUTES]),
            ): _readonly_text(str(values[CONF_ERROR_BACKOFF_INTERVAL_MINUTES])),
            vol.Optional(
                SUMMARY_ADAPTIVE_POLLING,
                default=enabled if values[CONF_ADAPTIVE_POLLING] else disabled,
            ): _readonly_select(_ENABLED_STATE_OPTIONS, "enabled_state"),
            vol.Optional(
                SUMMARY_DOWNLOAD_LIMIT,
                default=str(values[CONF_MAX_VERIFICATION_SIZE_GB]),
            ): _readonly_text(str(values[CONF_MAX_VERIFICATION_SIZE_GB])),
            vol.Optional(
                SUMMARY_EXPANDED_LIMIT,
                default=str(values[CONF_MAX_EXPANDED_SIZE_GB]),
            ): _readonly_text(str(values[CONF_MAX_EXPANDED_SIZE_GB])),
            vol.Optional(
                SUMMARY_MONITORING_POLICY, default=values[CONF_MONITORING_POLICY]
            ): _readonly_select(MONITORING_POLICY_OPTIONS, "monitoring_policy"),
            vol.Optional(
                SUMMARY_MAX_AGE, default=str(values[CONF_MAX_AGE_DAYS])
            ): _readonly_text(str(values[CONF_MAX_AGE_DAYS])),
            vol.Optional(
                SUMMARY_REDUNDANT_LOCATIONS,
                default=str(values[CONF_MINIMUM_REDUNDANT_LOCATIONS]),
            ): _readonly_text(str(values[CONF_MINIMUM_REDUNDANT_LOCATIONS])),
            vol.Optional(
                SUMMARY_REPAIR_ISSUES,
                default=enabled if values[CONF_REPAIR_ISSUES_ENABLED] else disabled,
            ): _readonly_select(_ENABLED_STATE_OPTIONS, "enabled_state"),
            vol.Optional(
                SUMMARY_VERIFICATION_POLICY,
                default=values[CONF_VERIFICATION_POLICY],
            ): _readonly_select(verification_options, "verification_policy"),
            vol.Optional(
                SUMMARY_ENTITY_MODE, default=values[CONF_ENTITY_MODE]
            ): _readonly_select(ENTITY_MODE_OPTIONS, "entity_mode"),
            vol.Optional(
                SUMMARY_EXPOSE_METADATA,
                default=enabled if values[CONF_EXPOSE_BACKUP_METADATA] else disabled,
            ): _readonly_select(_ENABLED_STATE_OPTIONS, "enabled_state"),
            vol.Optional(
                SUMMARY_NOTIFICATIONS_ENABLED,
                default=enabled if values[CONF_NOTIFICATIONS_ENABLED] else disabled,
            ): _readonly_select(_ENABLED_STATE_OPTIONS, "enabled_state"),
            vol.Optional(
                SUMMARY_NOTIFICATION_COUNT,
                default=str(len(values[CONF_NOTIFICATION_TARGETS])),
            ): _readonly_text(str(len(values[CONF_NOTIFICATION_TARGETS]))),
            vol.Optional(
                SUMMARY_NOTIFY_ON_RECOVERY,
                default=enabled if values[CONF_NOTIFY_ON_RECOVERY] else disabled,
            ): _readonly_select(_ENABLED_STATE_OPTIONS, "enabled_state"),
        }
    )
