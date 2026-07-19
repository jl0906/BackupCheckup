"""Independent runtime, monitoring, and verification presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES,
    CONF_ADAPTIVE_ERROR_THRESHOLD,
    CONF_ADAPTIVE_POLLING,
    CONF_ANALYTICS_WINDOW_DAYS,
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_DATABASE_TIMEOUT_MINUTES,
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES,
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    CONF_MAX_AGE_DAYS,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
    MONITORING_POLICY_BALANCED,
    MONITORING_POLICY_STRICT,
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_ENERGY_SAVING,
    RUNTIME_PROFILE_PERFORMANCE,
    RUNTIME_PROFILE_SERVER,
    SIZE_CHECK_AUTO,
    VERIFICATION_POLICY_AUTOMATIC,
    VERIFICATION_POLICY_DEEP,
    VERIFICATION_POLICY_MANUAL,
)


@dataclass(frozen=True, slots=True)
class RuntimePreset:
    """Concrete performance-sensitive settings for one hardware tier."""

    update_interval_minutes: int
    active_update_interval_minutes: int
    error_backoff_interval_minutes: int
    adaptive_error_threshold: int
    max_verification_size_gb: int
    max_expanded_size_gb: int
    verification_timeout_minutes: int
    database_timeout_minutes: int
    manual_verification_cooldown_minutes: int

    def as_dict(self, *, adaptive_polling: bool = True) -> dict[str, Any]:
        """Return config-entry values for this preset."""
        return {
            CONF_UPDATE_INTERVAL_MINUTES: self.update_interval_minutes,
            CONF_ACTIVE_UPDATE_INTERVAL_MINUTES: self.active_update_interval_minutes,
            CONF_ERROR_BACKOFF_INTERVAL_MINUTES: self.error_backoff_interval_minutes,
            CONF_ADAPTIVE_ERROR_THRESHOLD: self.adaptive_error_threshold,
            CONF_ADAPTIVE_POLLING: adaptive_polling,
            CONF_MAX_VERIFICATION_SIZE_GB: self.max_verification_size_gb,
            CONF_MAX_EXPANDED_SIZE_GB: self.max_expanded_size_gb,
            CONF_VERIFICATION_TIMEOUT_MINUTES: self.verification_timeout_minutes,
            CONF_DATABASE_TIMEOUT_MINUTES: self.database_timeout_minutes,
            CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
                self.manual_verification_cooldown_minutes
            ),
        }


RUNTIME_PRESETS: dict[str, RuntimePreset] = {
    RUNTIME_PROFILE_ENERGY_SAVING: RuntimePreset(
        update_interval_minutes=15,
        active_update_interval_minutes=2,
        error_backoff_interval_minutes=45,
        adaptive_error_threshold=DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
        max_verification_size_gb=25,
        max_expanded_size_gb=125,
        verification_timeout_minutes=90,
        database_timeout_minutes=20,
        manual_verification_cooldown_minutes=30,
    ),
    RUNTIME_PROFILE_APPLIANCE: RuntimePreset(
        update_interval_minutes=10,
        active_update_interval_minutes=1,
        error_backoff_interval_minutes=30,
        adaptive_error_threshold=DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
        max_verification_size_gb=50,
        max_expanded_size_gb=250,
        verification_timeout_minutes=60,
        database_timeout_minutes=15,
        manual_verification_cooldown_minutes=15,
    ),
    RUNTIME_PROFILE_PERFORMANCE: RuntimePreset(
        update_interval_minutes=5,
        active_update_interval_minutes=1,
        error_backoff_interval_minutes=20,
        adaptive_error_threshold=DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
        max_verification_size_gb=100,
        max_expanded_size_gb=500,
        verification_timeout_minutes=45,
        database_timeout_minutes=10,
        manual_verification_cooldown_minutes=10,
    ),
    RUNTIME_PROFILE_SERVER: RuntimePreset(
        update_interval_minutes=2,
        active_update_interval_minutes=1,
        error_backoff_interval_minutes=10,
        adaptive_error_threshold=DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
        max_verification_size_gb=250,
        max_expanded_size_gb=1000,
        verification_timeout_minutes=30,
        database_timeout_minutes=10,
        manual_verification_cooldown_minutes=5,
    ),
}

MONITORING_PRESETS: dict[str, dict[str, Any]] = {
    MONITORING_POLICY_BALANCED: {
        CONF_MAX_AGE_DAYS: 4,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: 50,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 1,
        CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
        CONF_REPAIR_ISSUES_ENABLED: True,
        CONF_ANALYTICS_WINDOW_DAYS: 30,
    },
    MONITORING_POLICY_STRICT: {
        CONF_MAX_AGE_DAYS: 2,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: 35,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 2,
        CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
        CONF_REPAIR_ISSUES_ENABLED: True,
        CONF_ANALYTICS_WINDOW_DAYS: 30,
    },
}

VERIFICATION_PRESETS: dict[str, dict[str, bool]] = {
    VERIFICATION_POLICY_MANUAL: {
        CONF_AUTO_VERIFY_NEW_BACKUPS: False,
        CONF_DATABASE_INTEGRITY_CHECK: False,
    },
    VERIFICATION_POLICY_AUTOMATIC: {
        CONF_AUTO_VERIFY_NEW_BACKUPS: True,
        CONF_DATABASE_INTEGRITY_CHECK: False,
    },
    VERIFICATION_POLICY_DEEP: {
        CONF_AUTO_VERIFY_NEW_BACKUPS: True,
        CONF_DATABASE_INTEGRITY_CHECK: True,
    },
}


def runtime_values(profile: str, *, adaptive_polling: bool = True) -> dict[str, Any]:
    """Return a fresh dictionary for a known runtime profile."""
    preset = RUNTIME_PRESETS.get(profile)
    return preset.as_dict(adaptive_polling=adaptive_polling) if preset else {}


def monitoring_values(policy: str) -> dict[str, Any]:
    """Return a fresh dictionary for a known monitoring policy."""
    return dict(MONITORING_PRESETS.get(policy, {}))


def verification_values(policy: str) -> dict[str, Any]:
    """Return a fresh dictionary for a known verification policy."""
    return dict(VERIFICATION_PRESETS.get(policy, {}))
