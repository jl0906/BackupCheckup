"""Admin-only WebSocket configuration API for the BackupCheckup panel."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .configuration import normalize_configuration
from .const import (
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
    CONF_ACTIVITY_LOG_PERSISTENCE,
    CONF_ACTIVITY_LOG_RETENTION_DAYS,
    CONF_ACTIVITY_LOGGING_ENABLED,
    CONF_ADAPTIVE_ERROR_THRESHOLD,
    CONF_ADAPTIVE_POLLING,
    CONF_ANALYTICS_WINDOW_DAYS,
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_DATABASE_TIMEOUT_MINUTES,
    CONF_ENTITY_MODE,
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_HARDWARE_DETECTION,
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
    CONF_PRESET_REVISION,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_RUNNER_MAXIMUM_ARCHIVE_GB,
    CONF_RUNNER_MAXIMUM_EXPANDED_GB,
    CONF_RUNNER_TIMEOUT_MINUTES,
    CONF_RUNTIME_PROFILE,
    CONF_RUNTIME_RUNNER,
    CONF_SHOW_SIDEBAR_PANEL,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_POLICY,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    DOMAIN,
    ENTITY_MODE_OPTIONS,
    MAX_ACTIVE_UPDATE_INTERVAL_MINUTES,
    MAX_ACTIVITY_LOG_RETENTION_DAYS,
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
    MAX_RUNNER_MAXIMUM_ARCHIVE_GB,
    MAX_RUNNER_MAXIMUM_EXPANDED_GB,
    MAX_RUNNER_TIMEOUT_MINUTES,
    MAX_UPDATE_INTERVAL_MINUTES,
    MAX_VERIFICATION_TIMEOUT_MINUTES,
    MIN_ACTIVE_UPDATE_INTERVAL_MINUTES,
    MIN_ACTIVITY_LOG_RETENTION_DAYS,
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
    MIN_RUNNER_MAXIMUM_ARCHIVE_GB,
    MIN_RUNNER_MAXIMUM_EXPANDED_GB,
    MIN_RUNNER_TIMEOUT_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
    MIN_VERIFICATION_TIMEOUT_MINUTES,
    MONITORING_POLICY_CUSTOM,
    MONITORING_POLICY_OPTIONS,
    PRESET_REVISION,
    RUNTIME_PROFILE_CUSTOM,
    RUNTIME_PROFILE_LEGACY,
    RUNTIME_PROFILE_OPTIONS,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OPTIONS,
    VERIFICATION_POLICY_CUSTOM,
    VERIFICATION_POLICY_STORED_OPTIONS,
    VERSION,
)
from .notification_selection import (
    mobile_notification_options,
    normalize_notification_targets,
)
from .presets import monitoring_values, runtime_values, verification_values

WS_TYPE_CONFIG_GET = f"{DOMAIN}/config/get"
WS_TYPE_CONFIG_UPDATE = f"{DOMAIN}/config/update"

_INTEGER_LIMITS: dict[str, tuple[int, int]] = {
    CONF_UPDATE_INTERVAL_MINUTES: (
        MIN_UPDATE_INTERVAL_MINUTES,
        MAX_UPDATE_INTERVAL_MINUTES,
    ),
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES: (
        MIN_ACTIVE_UPDATE_INTERVAL_MINUTES,
        MAX_ACTIVE_UPDATE_INTERVAL_MINUTES,
    ),
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES: (
        MIN_ERROR_BACKOFF_INTERVAL_MINUTES,
        MAX_ERROR_BACKOFF_INTERVAL_MINUTES,
    ),
    CONF_ADAPTIVE_ERROR_THRESHOLD: (
        MIN_ADAPTIVE_ERROR_THRESHOLD,
        MAX_ADAPTIVE_ERROR_THRESHOLD,
    ),
    CONF_MAX_VERIFICATION_SIZE_GB: (
        MIN_MAX_VERIFICATION_SIZE_GB,
        MAX_MAX_VERIFICATION_SIZE_GB,
    ),
    CONF_MAX_EXPANDED_SIZE_GB: (
        MIN_MAX_EXPANDED_SIZE_GB,
        MAX_MAX_EXPANDED_SIZE_GB,
    ),
    CONF_VERIFICATION_TIMEOUT_MINUTES: (
        MIN_VERIFICATION_TIMEOUT_MINUTES,
        MAX_VERIFICATION_TIMEOUT_MINUTES,
    ),
    CONF_DATABASE_TIMEOUT_MINUTES: (
        MIN_DATABASE_TIMEOUT_MINUTES,
        MAX_DATABASE_TIMEOUT_MINUTES,
    ),
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
        MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
        MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    ),
    CONF_MAX_AGE_DAYS: (MIN_MAX_AGE_DAYS, MAX_MAX_AGE_DAYS),
    CONF_MINIMUM_BACKUP_SIZE_MB: (
        MIN_MINIMUM_BACKUP_SIZE_MB,
        MAX_MINIMUM_BACKUP_SIZE_MB,
    ),
    CONF_MAXIMUM_SIZE_DROP_PERCENT: (
        MIN_MAXIMUM_SIZE_DROP_PERCENT,
        MAX_MAXIMUM_SIZE_DROP_PERCENT,
    ),
    CONF_MINIMUM_REDUNDANT_LOCATIONS: (
        MIN_REDUNDANT_LOCATIONS,
        MAX_REDUNDANT_LOCATIONS,
    ),
    CONF_ANALYTICS_WINDOW_DAYS: (
        MIN_ANALYTICS_WINDOW_DAYS,
        MAX_ANALYTICS_WINDOW_DAYS,
    ),
    CONF_ACTIVITY_LOG_RETENTION_DAYS: (
        MIN_ACTIVITY_LOG_RETENTION_DAYS,
        MAX_ACTIVITY_LOG_RETENTION_DAYS,
    ),
    CONF_RUNNER_MAXIMUM_ARCHIVE_GB: (
        MIN_RUNNER_MAXIMUM_ARCHIVE_GB,
        MAX_RUNNER_MAXIMUM_ARCHIVE_GB,
    ),
    CONF_RUNNER_MAXIMUM_EXPANDED_GB: (
        MIN_RUNNER_MAXIMUM_EXPANDED_GB,
        MAX_RUNNER_MAXIMUM_EXPANDED_GB,
    ),
    CONF_RUNNER_TIMEOUT_MINUTES: (
        MIN_RUNNER_TIMEOUT_MINUTES,
        MAX_RUNNER_TIMEOUT_MINUTES,
    ),
}

_BOOLEAN_KEYS = frozenset(
    {
        CONF_ADAPTIVE_POLLING,
        CONF_REPAIR_ISSUES_ENABLED,
        CONF_AUTO_VERIFY_NEW_BACKUPS,
        CONF_DATABASE_INTEGRITY_CHECK,
        CONF_NOTIFICATIONS_ENABLED,
        CONF_NOTIFY_ON_RECOVERY,
        CONF_EXPOSE_BACKUP_METADATA,
        CONF_SHOW_SIDEBAR_PANEL,
        CONF_ACTIVITY_LOGGING_ENABLED,
        CONF_ACTIVITY_LOG_PERSISTENCE,
    }
)

_ENUM_OPTIONS: dict[str, tuple[str, ...]] = {
    CONF_RUNTIME_PROFILE: tuple(RUNTIME_PROFILE_OPTIONS),
    CONF_MONITORING_POLICY: tuple(MONITORING_POLICY_OPTIONS),
    CONF_VERIFICATION_POLICY: tuple(VERIFICATION_POLICY_STORED_OPTIONS),
    CONF_ENTITY_MODE: tuple(ENTITY_MODE_OPTIONS),
    CONF_SIZE_CHECK_MODE: tuple(SIZE_CHECK_OPTIONS),
}

_READONLY_KEYS = frozenset({CONF_HARDWARE_DETECTION, CONF_PRESET_REVISION})

_FRONTEND_KEYS = frozenset(
    {
        *_INTEGER_LIMITS,
        *_BOOLEAN_KEYS,
        *_ENUM_OPTIONS,
        CONF_NOTIFICATION_TARGETS,
    }
)


class FrontendConfigurationError(ValueError):
    """Validation error with frontend-safe field error codes."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        super().__init__("Invalid BackupCheckup frontend configuration")
        self.errors = dict(errors)


def _entry_for_message(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Return the requested BackupCheckup entry only."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _strict_bool(value: Any, key: str, errors: dict[str, str]) -> bool:
    """Return a strict JSON boolean or retain a field error."""
    if isinstance(value, bool):
        return value
    errors[key] = "invalid_boolean"
    return False


def _bounded_int(value: Any, key: str, errors: dict[str, str]) -> int:
    """Return an integer inside the published range."""
    minimum, maximum = _INTEGER_LIMITS[key]
    if isinstance(value, bool) or not isinstance(value, int):
        errors[key] = "invalid_integer"
        return minimum
    if not minimum <= value <= maximum:
        errors[key] = "out_of_range"
    return min(max(value, minimum), maximum)


def _enum_value(value: Any, key: str, errors: dict[str, str]) -> str:
    """Return an allowed enum value or a deterministic fallback."""
    options = _ENUM_OPTIONS[key]
    if isinstance(value, str) and value in options:
        return value
    errors[key] = "invalid_option"
    return options[0]


def _notification_targets(value: Any, errors: dict[str, str]) -> list[str]:
    """Validate the JSON list before applying normal target normalization."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors[CONF_NOTIFICATION_TARGETS] = "invalid_notification_target"
        return []
    normalized = normalize_notification_targets(value)
    if len(normalized) != len(value):
        errors[CONF_NOTIFICATION_TARGETS] = "invalid_notification_target"
    return normalized


def _resolve_runtime_settings(
    source: Mapping[str, Any], values: dict[str, Any], errors: dict[str, str]
) -> None:
    """Apply one runtime preset or validate its custom resource limits."""
    profile = _enum_value(source[CONF_RUNTIME_PROFILE], CONF_RUNTIME_PROFILE, errors)
    adaptive = _strict_bool(
        source[CONF_ADAPTIVE_POLLING], CONF_ADAPTIVE_POLLING, errors
    )
    values[CONF_RUNTIME_PROFILE] = profile
    values[CONF_ADAPTIVE_POLLING] = adaptive
    if profile != RUNTIME_PROFILE_CUSTOM:
        values.update(runtime_values(profile, adaptive_polling=adaptive))
        return
    for key in (
        CONF_UPDATE_INTERVAL_MINUTES,
        CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
        CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
        CONF_ADAPTIVE_ERROR_THRESHOLD,
        CONF_MAX_VERIFICATION_SIZE_GB,
        CONF_MAX_EXPANDED_SIZE_GB,
        CONF_VERIFICATION_TIMEOUT_MINUTES,
        CONF_DATABASE_TIMEOUT_MINUTES,
        CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    ):
        values[key] = _bounded_int(source[key], key, errors)
    if (
        values[CONF_ACTIVE_UPDATE_INTERVAL_MINUTES]
        > values[CONF_UPDATE_INTERVAL_MINUTES]
    ):
        errors["runtime"] = "active_interval_too_slow"
    if (
        values[CONF_ERROR_BACKOFF_INTERVAL_MINUTES]
        < values[CONF_UPDATE_INTERVAL_MINUTES]
    ):
        errors["runtime"] = "backoff_interval_too_fast"
    if values[CONF_MAX_EXPANDED_SIZE_GB] < values[CONF_MAX_VERIFICATION_SIZE_GB]:
        errors[CONF_MAX_EXPANDED_SIZE_GB] = "expanded_size_too_small"


def _resolve_monitoring_settings(
    source: Mapping[str, Any], values: dict[str, Any], errors: dict[str, str]
) -> None:
    """Apply one monitoring policy or validate its custom thresholds."""
    policy = _enum_value(source[CONF_MONITORING_POLICY], CONF_MONITORING_POLICY, errors)
    values[CONF_MONITORING_POLICY] = policy
    if policy != MONITORING_POLICY_CUSTOM:
        values.update(monitoring_values(policy))
        return
    for key in (
        CONF_MAX_AGE_DAYS,
        CONF_MINIMUM_BACKUP_SIZE_MB,
        CONF_MAXIMUM_SIZE_DROP_PERCENT,
        CONF_MINIMUM_REDUNDANT_LOCATIONS,
        CONF_ANALYTICS_WINDOW_DAYS,
    ):
        values[key] = _bounded_int(source[key], key, errors)
    values[CONF_SIZE_CHECK_MODE] = _enum_value(
        source[CONF_SIZE_CHECK_MODE], CONF_SIZE_CHECK_MODE, errors
    )
    values[CONF_REPAIR_ISSUES_ENABLED] = _strict_bool(
        source[CONF_REPAIR_ISSUES_ENABLED], CONF_REPAIR_ISSUES_ENABLED, errors
    )
    if (
        values[CONF_SIZE_CHECK_MODE] == SIZE_CHECK_FIXED
        and values[CONF_MINIMUM_BACKUP_SIZE_MB] == 0
    ):
        errors["monitoring"] = "fixed_size_required"


def _resolve_verification_settings(
    source: Mapping[str, Any], values: dict[str, Any], errors: dict[str, str]
) -> None:
    """Apply one verification policy without silently deepening it."""
    policy = _enum_value(
        source[CONF_VERIFICATION_POLICY], CONF_VERIFICATION_POLICY, errors
    )
    values[CONF_VERIFICATION_POLICY] = policy
    values[CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES] = _bounded_int(
        source[CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES],
        CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
        errors,
    )
    if policy != VERIFICATION_POLICY_CUSTOM:
        values.update(verification_values(policy))
        return
    values[CONF_AUTO_VERIFY_NEW_BACKUPS] = _strict_bool(
        source[CONF_AUTO_VERIFY_NEW_BACKUPS], CONF_AUTO_VERIFY_NEW_BACKUPS, errors
    )
    values[CONF_DATABASE_INTEGRITY_CHECK] = _strict_bool(
        source[CONF_DATABASE_INTEGRITY_CHECK],
        CONF_DATABASE_INTEGRITY_CHECK,
        errors,
    )


def _resolve_presentation_settings(
    source: Mapping[str, Any], values: dict[str, Any], errors: dict[str, str]
) -> None:
    """Validate the smaller presentation, privacy, and notification fields."""
    for key in (
        CONF_ENTITY_MODE,
        CONF_NOTIFICATIONS_ENABLED,
        CONF_NOTIFY_ON_RECOVERY,
        CONF_EXPOSE_BACKUP_METADATA,
        CONF_SHOW_SIDEBAR_PANEL,
        CONF_ACTIVITY_LOGGING_ENABLED,
        CONF_ACTIVITY_LOG_PERSISTENCE,
        CONF_ACTIVITY_LOG_RETENTION_DAYS,
    ):
        if key in _BOOLEAN_KEYS:
            values[key] = _strict_bool(source[key], key, errors)
        elif key in _INTEGER_LIMITS:
            values[key] = _bounded_int(source[key], key, errors)
        else:
            values[key] = _enum_value(source[key], key, errors)
    values[CONF_NOTIFICATION_TARGETS] = _notification_targets(
        source[CONF_NOTIFICATION_TARGETS], errors
    )
    if (
        values[CONF_NOTIFICATIONS_ENABLED]
        and not values[CONF_NOTIFICATION_TARGETS]
        and CONF_NOTIFICATION_TARGETS not in errors
    ):
        errors[CONF_NOTIFICATION_TARGETS] = "notification_target_required"


def _resolve_runner_settings(
    source: Mapping[str, Any], values: dict[str, Any], errors: dict[str, str]
) -> None:
    """Validate limits sent to the optional runner for each test run."""
    for key in (
        CONF_RUNNER_MAXIMUM_ARCHIVE_GB,
        CONF_RUNNER_MAXIMUM_EXPANDED_GB,
        CONF_RUNNER_TIMEOUT_MINUTES,
    ):
        values[key] = _bounded_int(source[key], key, errors)
    if (
        values[CONF_RUNNER_MAXIMUM_EXPANDED_GB]
        < values[CONF_RUNNER_MAXIMUM_ARCHIVE_GB]
    ):
        errors[CONF_RUNNER_MAXIMUM_EXPANDED_GB] = "expanded_size_too_small"


def resolve_frontend_configuration(
    current: Mapping[str, Any], submitted: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate and resolve one complete configuration snapshot from the panel."""
    if not isinstance(submitted, Mapping):
        raise FrontendConfigurationError({"base": "invalid_payload"})

    unknown = sorted(set(submitted) - _FRONTEND_KEYS - _READONLY_KEYS)
    if unknown:
        raise FrontendConfigurationError({"base": "unknown_setting"})

    existing = normalize_configuration(current)
    source = {key: submitted.get(key, existing[key]) for key in _FRONTEND_KEYS}
    errors: dict[str, str] = {}
    values = dict(existing)

    _resolve_runtime_settings(source, values, errors)
    _resolve_monitoring_settings(source, values, errors)
    _resolve_verification_settings(source, values, errors)
    _resolve_presentation_settings(source, values, errors)
    _resolve_runner_settings(source, values, errors)

    if errors:
        raise FrontendConfigurationError(errors)

    values[CONF_PRESET_REVISION] = PRESET_REVISION
    values[CONF_HARDWARE_DETECTION] = existing[CONF_HARDWARE_DETECTION]
    return normalize_configuration(values)


def frontend_configuration_payload(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return an admin-only, JSON-safe settings model for the panel."""
    values = normalize_configuration(entry.data, entry.options)
    if values[CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_LEGACY:
        values[CONF_RUNTIME_PROFILE] = RUNTIME_PROFILE_CUSTOM
    return {
        "entry_id": entry.entry_id,
        "integration_version": VERSION,
        "values": {key: values[key] for key in sorted(_FRONTEND_KEYS)},
        "limits": {
            key: {"min": minimum, "max": maximum}
            for key, (minimum, maximum) in sorted(_INTEGER_LIMITS.items())
        },
        "options": {
            "runtime_profiles": list(RUNTIME_PROFILE_OPTIONS),
            "monitoring_policies": list(MONITORING_POLICY_OPTIONS),
            "verification_policies": list(VERIFICATION_POLICY_STORED_OPTIONS),
            "entity_modes": list(ENTITY_MODE_OPTIONS),
            "size_check_modes": list(SIZE_CHECK_OPTIONS),
            "notification_targets": mobile_notification_options(
                hass, values[CONF_NOTIFICATION_TARGETS]
            ),
        },
        "hardware": dict(values[CONF_HARDWARE_DETECTION]),
        "runner": {"available": CONF_RUNTIME_RUNNER in entry.data},
        "reload_required": True,
    }


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_CONFIG_GET,
        vol.Required("entry_id"): str,
    }
)
async def websocket_config_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current BackupCheckup configuration to an administrator."""
    entry = _entry_for_message(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return
    connection.send_result(msg["id"], frontend_configuration_payload(hass, entry))


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_CONFIG_UPDATE,
        vol.Required("entry_id"): str,
        vol.Required("values"): dict,
    }
)
async def websocket_config_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate, persist, acknowledge, and reload panel configuration."""
    entry = _entry_for_message(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    current = normalize_configuration(entry.data, entry.options)
    try:
        resolved = resolve_frontend_configuration(current, msg["values"])
    except FrontendConfigurationError as err:
        connection.send_result(
            msg["id"],
            {"success": False, "errors": err.errors, "values": current},
        )
        return

    hass.config_entries.async_update_entry(
        entry,
        data={
            **resolved,
            **(
                {CONF_RUNTIME_RUNNER: entry.data[CONF_RUNTIME_RUNNER]}
                if CONF_RUNTIME_RUNNER in entry.data
                else {}
            ),
        },
        options=resolved,
    )
    connection.send_result(
        msg["id"],
        {
            "success": True,
            "values": {key: resolved[key] for key in sorted(_FRONTEND_KEYS)},
            "reload_started": True,
        },
    )
    hass.async_create_task(
        hass.config_entries.async_reload(entry.entry_id),
        name=f"{DOMAIN}-frontend-config-reload",
    )


def async_register_frontend_config(hass: HomeAssistant) -> None:
    """Register the two admin-only panel configuration commands."""
    websocket_api.async_register_command(hass, websocket_config_get)
    websocket_api.async_register_command(hass, websocket_config_update)
