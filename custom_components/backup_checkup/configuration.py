"""Configuration normalization helpers for BackupCheckup."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .const import (
    CONF_ANALYTICS_WINDOW_DAYS,
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_DATABASE_TIMEOUT_MINUTES,
    CONF_ENTITY_MODE,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    CONF_MAX_AGE_DAYS,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_MONITORING_PROFILE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    DEFAULT_ANALYTICS_WINDOW_DAYS,
    DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    DEFAULT_DATABASE_INTEGRITY_CHECK,
    DEFAULT_DATABASE_TIMEOUT_MINUTES,
    DEFAULT_ENTITY_MODE,
    DEFAULT_EXPOSE_BACKUP_METADATA,
    DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_EXPANDED_SIZE_GB,
    DEFAULT_MAX_VERIFICATION_SIZE_GB,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_MONITORING_PROFILE,
    DEFAULT_NOTIFICATION_TARGETS,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFY_ON_RECOVERY,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_SIZE_CHECK_MODE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
    ENTITY_MODE_OPTIONS,
    MAX_ANALYTICS_WINDOW_DAYS,
    MAX_DATABASE_TIMEOUT_MINUTES,
    MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    MAX_MAX_AGE_DAYS,
    MAX_MAX_EXPANDED_SIZE_GB,
    MAX_MAX_VERIFICATION_SIZE_GB,
    MAX_MAXIMUM_SIZE_DROP_PERCENT,
    MAX_MINIMUM_BACKUP_SIZE_MB,
    MAX_REDUNDANT_LOCATIONS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MAX_VERIFICATION_TIMEOUT_MINUTES,
    MIN_ANALYTICS_WINDOW_DAYS,
    MIN_DATABASE_TIMEOUT_MINUTES,
    MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    MIN_MAX_AGE_DAYS,
    MIN_MAX_EXPANDED_SIZE_GB,
    MIN_MAX_VERIFICATION_SIZE_GB,
    MIN_MAXIMUM_SIZE_DROP_PERCENT,
    MIN_MINIMUM_BACKUP_SIZE_MB,
    MIN_REDUNDANT_LOCATIONS,
    MIN_UPDATE_INTERVAL_MINUTES,
    MIN_VERIFICATION_TIMEOUT_MINUTES,
    PROFILE_OPTIONS,
    SIZE_CHECK_OPTIONS,
)
from .notification_selection import normalize_notification_targets

_INTEGER_OPTIONS: dict[str, tuple[int, int, int]] = {
    CONF_MAX_AGE_DAYS: (DEFAULT_MAX_AGE_DAYS, MIN_MAX_AGE_DAYS, MAX_MAX_AGE_DAYS),
    CONF_UPDATE_INTERVAL_MINUTES: (
        DEFAULT_UPDATE_INTERVAL_MINUTES,
        MIN_UPDATE_INTERVAL_MINUTES,
        MAX_UPDATE_INTERVAL_MINUTES,
    ),
    CONF_MINIMUM_BACKUP_SIZE_MB: (
        DEFAULT_MINIMUM_BACKUP_SIZE_MB,
        MIN_MINIMUM_BACKUP_SIZE_MB,
        MAX_MINIMUM_BACKUP_SIZE_MB,
    ),
    CONF_MAXIMUM_SIZE_DROP_PERCENT: (
        DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
        MIN_MAXIMUM_SIZE_DROP_PERCENT,
        MAX_MAXIMUM_SIZE_DROP_PERCENT,
    ),
    CONF_MINIMUM_REDUNDANT_LOCATIONS: (
        DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
        MIN_REDUNDANT_LOCATIONS,
        MAX_REDUNDANT_LOCATIONS,
    ),
    CONF_ANALYTICS_WINDOW_DAYS: (
        DEFAULT_ANALYTICS_WINDOW_DAYS,
        MIN_ANALYTICS_WINDOW_DAYS,
        MAX_ANALYTICS_WINDOW_DAYS,
    ),
    CONF_MAX_VERIFICATION_SIZE_GB: (
        DEFAULT_MAX_VERIFICATION_SIZE_GB,
        MIN_MAX_VERIFICATION_SIZE_GB,
        MAX_MAX_VERIFICATION_SIZE_GB,
    ),
    CONF_MAX_EXPANDED_SIZE_GB: (
        DEFAULT_MAX_EXPANDED_SIZE_GB,
        MIN_MAX_EXPANDED_SIZE_GB,
        MAX_MAX_EXPANDED_SIZE_GB,
    ),
    CONF_VERIFICATION_TIMEOUT_MINUTES: (
        DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
        MIN_VERIFICATION_TIMEOUT_MINUTES,
        MAX_VERIFICATION_TIMEOUT_MINUTES,
    ),
    CONF_DATABASE_TIMEOUT_MINUTES: (
        DEFAULT_DATABASE_TIMEOUT_MINUTES,
        MIN_DATABASE_TIMEOUT_MINUTES,
        MAX_DATABASE_TIMEOUT_MINUTES,
    ),
    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
        DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
        MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
        MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    ),
}

_BOOLEAN_OPTIONS: dict[str, bool] = {
    CONF_REPAIR_ISSUES_ENABLED: DEFAULT_REPAIR_ISSUES_ENABLED,
    CONF_AUTO_VERIFY_NEW_BACKUPS: DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK: DEFAULT_DATABASE_INTEGRITY_CHECK,
    CONF_NOTIFICATIONS_ENABLED: DEFAULT_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY: DEFAULT_NOTIFY_ON_RECOVERY,
    CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
}

_ENUM_OPTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    CONF_MONITORING_PROFILE: (DEFAULT_MONITORING_PROFILE, tuple(PROFILE_OPTIONS)),
    CONF_ENTITY_MODE: (DEFAULT_ENTITY_MODE, tuple(ENTITY_MODE_OPTIONS)),
    CONF_SIZE_CHECK_MODE: (DEFAULT_SIZE_CHECK_MODE, tuple(SIZE_CHECK_OPTIONS)),
}

KNOWN_CONFIGURATION_KEYS = frozenset(
    {*_INTEGER_OPTIONS, *_BOOLEAN_OPTIONS, *_ENUM_OPTIONS, CONF_NOTIFICATION_TARGETS}
)


def _strict_bool(value: Any, default: bool) -> bool:
    """Normalize legacy boolean representations without truthiness surprises."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0"}:
            return False
    return default


def _integer_value(value: Any) -> int | None:
    """Return a strict finite integer without silently truncating fractions."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        signless = stripped[1:] if stripped[:1] in {"+", "-"} else stripped
        if not signless.isdecimal():
            return None
        try:
            return int(stripped, 10)
        except ValueError:
            return None
    return None


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """Normalize one integer and enforce its supported range."""
    parsed = _integer_value(value)
    return parsed if parsed is not None and minimum <= parsed <= maximum else default


def _enum(value: Any, default: str, allowed: tuple[str, ...]) -> str:
    """Normalize one enum option."""
    return value if isinstance(value, str) and value in allowed else default


def normalize_configuration(*sources: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return one complete canonical configuration snapshot.

    Sources are merged from left to right. Persisted options therefore override the
    original config-entry data while every returned value receives a stable type.
    Unknown legacy keys are deliberately discarded.
    """
    merged: dict[str, Any] = {}
    for source in sources:
        if isinstance(source, Mapping):
            merged.update(source)

    normalized: dict[str, Any] = {}
    for key, (default, minimum, maximum) in _INTEGER_OPTIONS.items():
        normalized[key] = _bounded_int(merged.get(key), default, minimum, maximum)
    for key, default in _BOOLEAN_OPTIONS.items():
        normalized[key] = _strict_bool(merged.get(key), default)
    for key, (default, allowed) in _ENUM_OPTIONS.items():
        normalized[key] = _enum(merged.get(key), default, allowed)
    normalized[CONF_NOTIFICATION_TARGETS] = normalize_notification_targets(
        merged.get(CONF_NOTIFICATION_TARGETS, DEFAULT_NOTIFICATION_TARGETS)
    )
    return normalized


@dataclass(frozen=True, slots=True)
class BackupCheckupSettings:
    """Canonical immutable settings consumed by the runtime coordinator."""

    max_age_days: int
    update_interval_minutes: int
    minimum_backup_size_mb: int
    maximum_size_drop_percent: int
    minimum_redundant_locations: int
    analytics_window_days: int
    max_verification_size_gb: int
    max_expanded_size_gb: int
    verification_timeout_minutes: int
    database_timeout_minutes: int
    manual_verification_cooldown_minutes: int
    repair_issues_enabled: bool
    auto_verify_new_backups: bool
    database_integrity_check: bool
    notifications_enabled: bool
    notify_on_recovery: bool
    expose_backup_metadata: bool
    monitoring_profile: str
    entity_mode: str
    size_check_mode: str
    notification_targets: tuple[str, ...]

    @classmethod
    def from_sources(cls, *sources: Mapping[str, Any] | None) -> BackupCheckupSettings:
        """Create settings from config-entry data and options."""
        values = normalize_configuration(*sources)
        return cls(
            max_age_days=values[CONF_MAX_AGE_DAYS],
            update_interval_minutes=values[CONF_UPDATE_INTERVAL_MINUTES],
            minimum_backup_size_mb=values[CONF_MINIMUM_BACKUP_SIZE_MB],
            maximum_size_drop_percent=values[CONF_MAXIMUM_SIZE_DROP_PERCENT],
            minimum_redundant_locations=values[CONF_MINIMUM_REDUNDANT_LOCATIONS],
            analytics_window_days=values[CONF_ANALYTICS_WINDOW_DAYS],
            max_verification_size_gb=values[CONF_MAX_VERIFICATION_SIZE_GB],
            max_expanded_size_gb=values[CONF_MAX_EXPANDED_SIZE_GB],
            verification_timeout_minutes=values[CONF_VERIFICATION_TIMEOUT_MINUTES],
            database_timeout_minutes=values[CONF_DATABASE_TIMEOUT_MINUTES],
            manual_verification_cooldown_minutes=values[
                CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES
            ],
            repair_issues_enabled=values[CONF_REPAIR_ISSUES_ENABLED],
            auto_verify_new_backups=values[CONF_AUTO_VERIFY_NEW_BACKUPS],
            database_integrity_check=values[CONF_DATABASE_INTEGRITY_CHECK],
            notifications_enabled=values[CONF_NOTIFICATIONS_ENABLED],
            notify_on_recovery=values[CONF_NOTIFY_ON_RECOVERY],
            expose_backup_metadata=values[CONF_EXPOSE_BACKUP_METADATA],
            monitoring_profile=values[CONF_MONITORING_PROFILE],
            entity_mode=values[CONF_ENTITY_MODE],
            size_check_mode=values[CONF_SIZE_CHECK_MODE],
            notification_targets=tuple(values[CONF_NOTIFICATION_TARGETS]),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical config-entry representation."""
        result = asdict(self)
        result[CONF_NOTIFICATION_TARGETS] = list(self.notification_targets)
        result[CONF_MAX_AGE_DAYS] = result.pop("max_age_days")
        result[CONF_UPDATE_INTERVAL_MINUTES] = result.pop("update_interval_minutes")
        result[CONF_MINIMUM_BACKUP_SIZE_MB] = result.pop("minimum_backup_size_mb")
        result[CONF_MAXIMUM_SIZE_DROP_PERCENT] = result.pop("maximum_size_drop_percent")
        result[CONF_MINIMUM_REDUNDANT_LOCATIONS] = result.pop(
            "minimum_redundant_locations"
        )
        result[CONF_ANALYTICS_WINDOW_DAYS] = result.pop("analytics_window_days")
        result[CONF_MAX_VERIFICATION_SIZE_GB] = result.pop("max_verification_size_gb")
        result[CONF_MAX_EXPANDED_SIZE_GB] = result.pop("max_expanded_size_gb")
        result[CONF_VERIFICATION_TIMEOUT_MINUTES] = result.pop(
            "verification_timeout_minutes"
        )
        result[CONF_DATABASE_TIMEOUT_MINUTES] = result.pop("database_timeout_minutes")
        result[CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES] = result.pop(
            "manual_verification_cooldown_minutes"
        )
        result[CONF_REPAIR_ISSUES_ENABLED] = result.pop("repair_issues_enabled")
        result[CONF_AUTO_VERIFY_NEW_BACKUPS] = result.pop("auto_verify_new_backups")
        result[CONF_DATABASE_INTEGRITY_CHECK] = result.pop("database_integrity_check")
        result[CONF_NOTIFICATIONS_ENABLED] = result.pop("notifications_enabled")
        result[CONF_NOTIFY_ON_RECOVERY] = result.pop("notify_on_recovery")
        result[CONF_EXPOSE_BACKUP_METADATA] = result.pop("expose_backup_metadata")
        result[CONF_MONITORING_PROFILE] = result.pop("monitoring_profile")
        result[CONF_ENTITY_MODE] = result.pop("entity_mode")
        result[CONF_SIZE_CHECK_MODE] = result.pop("size_check_mode")
        return result
