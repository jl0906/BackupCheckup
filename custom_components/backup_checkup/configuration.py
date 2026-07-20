"""Canonical configuration model and legacy normalization for BackupCheckup."""

from __future__ import annotations

import math
from collections.abc import Mapping
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
    CONF_MONITORING_PROFILE,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_PRESET_REVISION,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_RUNTIME_PROFILE,
    CONF_SHOW_SIDEBAR_PANEL,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_VERIFICATION_POLICY,
    CONF_VERIFICATION_TIMEOUT_MINUTES,
    DEFAULT_ACTIVE_UPDATE_INTERVAL_MINUTES,
    DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
    DEFAULT_ADAPTIVE_POLLING,
    DEFAULT_ANALYTICS_WINDOW_DAYS,
    DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    DEFAULT_DATABASE_INTEGRITY_CHECK,
    DEFAULT_DATABASE_TIMEOUT_MINUTES,
    DEFAULT_ENTITY_MODE,
    DEFAULT_ERROR_BACKOFF_INTERVAL_MINUTES,
    DEFAULT_EXPOSE_BACKUP_METADATA,
    DEFAULT_HARDWARE_DETECTION,
    DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAX_EXPANDED_SIZE_GB,
    DEFAULT_MAX_VERIFICATION_SIZE_GB,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_MONITORING_POLICY,
    DEFAULT_NOTIFICATION_TARGETS,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFY_ON_RECOVERY,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_RUNTIME_PROFILE,
    DEFAULT_SHOW_SIDEBAR_PANEL,
    DEFAULT_SIZE_CHECK_MODE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_VERIFICATION_POLICY,
    DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
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
    MONITORING_POLICY_BALANCED,
    MONITORING_POLICY_CUSTOM,
    MONITORING_POLICY_OPTIONS,
    MONITORING_POLICY_STRICT,
    PRESET_REVISION,
    PROFILE_CUSTOM,
    PROFILE_SECURE,
    RUNTIME_PROFILE_LEGACY,
    RUNTIME_PROFILE_STORED_OPTIONS,
    SIZE_CHECK_OPTIONS,
    VERIFICATION_POLICY_AUTOMATIC,
    VERIFICATION_POLICY_CUSTOM,
    VERIFICATION_POLICY_DEEP,
    VERIFICATION_POLICY_MANUAL,
    VERIFICATION_POLICY_STORED_OPTIONS,
)
from .notification_selection import normalize_notification_targets

_INTEGER_OPTIONS: dict[str, tuple[int, int, int]] = {
    CONF_MAX_AGE_DAYS: (DEFAULT_MAX_AGE_DAYS, MIN_MAX_AGE_DAYS, MAX_MAX_AGE_DAYS),
    CONF_UPDATE_INTERVAL_MINUTES: (
        DEFAULT_UPDATE_INTERVAL_MINUTES,
        MIN_UPDATE_INTERVAL_MINUTES,
        MAX_UPDATE_INTERVAL_MINUTES,
    ),
    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES: (
        DEFAULT_ACTIVE_UPDATE_INTERVAL_MINUTES,
        MIN_ACTIVE_UPDATE_INTERVAL_MINUTES,
        MAX_ACTIVE_UPDATE_INTERVAL_MINUTES,
    ),
    CONF_ERROR_BACKOFF_INTERVAL_MINUTES: (
        DEFAULT_ERROR_BACKOFF_INTERVAL_MINUTES,
        MIN_ERROR_BACKOFF_INTERVAL_MINUTES,
        MAX_ERROR_BACKOFF_INTERVAL_MINUTES,
    ),
    CONF_ADAPTIVE_ERROR_THRESHOLD: (
        DEFAULT_ADAPTIVE_ERROR_THRESHOLD,
        MIN_ADAPTIVE_ERROR_THRESHOLD,
        MAX_ADAPTIVE_ERROR_THRESHOLD,
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
    CONF_PRESET_REVISION: (PRESET_REVISION, 1, 1000),
}

_BOOLEAN_OPTIONS: dict[str, bool] = {
    CONF_ADAPTIVE_POLLING: DEFAULT_ADAPTIVE_POLLING,
    CONF_REPAIR_ISSUES_ENABLED: DEFAULT_REPAIR_ISSUES_ENABLED,
    CONF_AUTO_VERIFY_NEW_BACKUPS: DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK: DEFAULT_DATABASE_INTEGRITY_CHECK,
    CONF_NOTIFICATIONS_ENABLED: DEFAULT_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY: DEFAULT_NOTIFY_ON_RECOVERY,
    CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
    CONF_SHOW_SIDEBAR_PANEL: DEFAULT_SHOW_SIDEBAR_PANEL,
}

_ENUM_OPTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    CONF_RUNTIME_PROFILE: (
        DEFAULT_RUNTIME_PROFILE,
        tuple(RUNTIME_PROFILE_STORED_OPTIONS),
    ),
    CONF_MONITORING_POLICY: (
        DEFAULT_MONITORING_POLICY,
        tuple(MONITORING_POLICY_OPTIONS),
    ),
    CONF_VERIFICATION_POLICY: (
        DEFAULT_VERIFICATION_POLICY,
        tuple(VERIFICATION_POLICY_STORED_OPTIONS),
    ),
    CONF_ENTITY_MODE: (DEFAULT_ENTITY_MODE, tuple(ENTITY_MODE_OPTIONS)),
    CONF_SIZE_CHECK_MODE: (DEFAULT_SIZE_CHECK_MODE, tuple(SIZE_CHECK_OPTIONS)),
}

KNOWN_CONFIGURATION_KEYS = frozenset(
    {
        *_INTEGER_OPTIONS,
        *_BOOLEAN_OPTIONS,
        *_ENUM_OPTIONS,
        CONF_NOTIFICATION_TARGETS,
        CONF_HARDWARE_DETECTION,
    }
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


def _legacy_monitoring_policy(merged: Mapping[str, Any]) -> str:
    """Map the 2.3.x combined profile to the independent monitoring policy."""
    profile = merged.get(CONF_MONITORING_PROFILE)
    if profile == PROFILE_SECURE:
        return MONITORING_POLICY_STRICT
    if profile == PROFILE_CUSTOM:
        return MONITORING_POLICY_CUSTOM
    return MONITORING_POLICY_BALANCED


def _legacy_verification_policy(merged: Mapping[str, Any]) -> str:
    """Infer the strategy represented by legacy booleans."""
    automatic = _strict_bool(
        merged.get(CONF_AUTO_VERIFY_NEW_BACKUPS), DEFAULT_AUTO_VERIFY_NEW_BACKUPS
    )
    database = _strict_bool(
        merged.get(CONF_DATABASE_INTEGRITY_CHECK), DEFAULT_DATABASE_INTEGRITY_CHECK
    )
    if automatic and database:
        return VERIFICATION_POLICY_DEEP
    if automatic:
        return VERIFICATION_POLICY_AUTOMATIC
    if not database:
        return VERIFICATION_POLICY_MANUAL
    return VERIFICATION_POLICY_CUSTOM


def _hardware_detection(value: Any) -> dict[str, str]:
    """Normalize bounded, string-only hardware metadata."""
    if not isinstance(value, Mapping):
        return dict(DEFAULT_HARDWARE_DETECTION)
    result: dict[str, str] = {}
    for key in (
        "installation_type",
        "architecture",
        "board",
        "recommended_profile",
        "confidence",
        "detection",
    ):
        candidate = value.get(key)
        if isinstance(candidate, str):
            result[key] = candidate[:80]
    return result


def _with_legacy_derivations(merged: dict[str, Any]) -> dict[str, Any]:
    """Fill new schema fields from 2.3.x entries without changing behavior."""
    if CONF_RUNTIME_PROFILE not in merged:
        merged[CONF_RUNTIME_PROFILE] = RUNTIME_PROFILE_LEGACY
        merged.setdefault(CONF_ADAPTIVE_POLLING, False)
    if CONF_MONITORING_POLICY not in merged:
        merged[CONF_MONITORING_POLICY] = _legacy_monitoring_policy(merged)
    if CONF_VERIFICATION_POLICY not in merged:
        merged[CONF_VERIFICATION_POLICY] = _legacy_verification_policy(merged)
    return merged


def normalize_configuration(*sources: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return one complete canonical configuration snapshot."""
    merged: dict[str, Any] = {}
    for source in sources:
        if isinstance(source, Mapping):
            merged.update(source)
    _with_legacy_derivations(merged)

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
    normalized[CONF_HARDWARE_DETECTION] = _hardware_detection(
        merged.get(CONF_HARDWARE_DETECTION)
    )
    return normalized


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Performance-sensitive runtime settings."""

    profile: str
    update_interval_minutes: int
    active_update_interval_minutes: int
    error_backoff_interval_minutes: int
    adaptive_error_threshold: int
    adaptive_polling: bool
    max_verification_size_gb: int
    max_expanded_size_gb: int
    verification_timeout_minutes: int
    database_timeout_minutes: int
    manual_verification_cooldown_minutes: int
    preset_revision: int
    hardware_detection: dict[str, str]


@dataclass(frozen=True, slots=True)
class MonitoringSettings:
    """Backup-health policy and thresholds."""

    policy: str
    max_age_days: int
    minimum_backup_size_mb: int
    maximum_size_drop_percent: int
    minimum_redundant_locations: int
    analytics_window_days: int
    repair_issues_enabled: bool
    size_check_mode: str


@dataclass(frozen=True, slots=True)
class VerificationSettings:
    """Automatic integrity-check policy."""

    policy: str
    auto_verify_new_backups: bool
    database_integrity_check: bool


@dataclass(frozen=True, slots=True)
class PresentationSettings:
    """Entity, privacy, and notification settings."""

    entity_mode: str
    notifications_enabled: bool
    notification_targets: tuple[str, ...]
    notify_on_recovery: bool
    expose_backup_metadata: bool
    show_sidebar_panel: bool


@dataclass(frozen=True)
class BackupCheckupSettings:
    """Canonical immutable settings consumed by the runtime coordinator."""

    runtime: RuntimeSettings
    monitoring: MonitoringSettings
    verification: VerificationSettings
    presentation: PresentationSettings

    @classmethod
    def from_sources(cls, *sources: Mapping[str, Any] | None) -> BackupCheckupSettings:
        """Create settings from config-entry data and options."""
        values = normalize_configuration(*sources)
        return cls(
            runtime=RuntimeSettings(
                profile=values[CONF_RUNTIME_PROFILE],
                update_interval_minutes=values[CONF_UPDATE_INTERVAL_MINUTES],
                active_update_interval_minutes=values[
                    CONF_ACTIVE_UPDATE_INTERVAL_MINUTES
                ],
                error_backoff_interval_minutes=values[
                    CONF_ERROR_BACKOFF_INTERVAL_MINUTES
                ],
                adaptive_error_threshold=values[CONF_ADAPTIVE_ERROR_THRESHOLD],
                adaptive_polling=values[CONF_ADAPTIVE_POLLING],
                max_verification_size_gb=values[CONF_MAX_VERIFICATION_SIZE_GB],
                max_expanded_size_gb=values[CONF_MAX_EXPANDED_SIZE_GB],
                verification_timeout_minutes=values[CONF_VERIFICATION_TIMEOUT_MINUTES],
                database_timeout_minutes=values[CONF_DATABASE_TIMEOUT_MINUTES],
                manual_verification_cooldown_minutes=values[
                    CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES
                ],
                preset_revision=values[CONF_PRESET_REVISION],
                hardware_detection=values[CONF_HARDWARE_DETECTION],
            ),
            monitoring=MonitoringSettings(
                policy=values[CONF_MONITORING_POLICY],
                max_age_days=values[CONF_MAX_AGE_DAYS],
                minimum_backup_size_mb=values[CONF_MINIMUM_BACKUP_SIZE_MB],
                maximum_size_drop_percent=values[CONF_MAXIMUM_SIZE_DROP_PERCENT],
                minimum_redundant_locations=values[CONF_MINIMUM_REDUNDANT_LOCATIONS],
                analytics_window_days=values[CONF_ANALYTICS_WINDOW_DAYS],
                repair_issues_enabled=values[CONF_REPAIR_ISSUES_ENABLED],
                size_check_mode=values[CONF_SIZE_CHECK_MODE],
            ),
            verification=VerificationSettings(
                policy=values[CONF_VERIFICATION_POLICY],
                auto_verify_new_backups=values[CONF_AUTO_VERIFY_NEW_BACKUPS],
                database_integrity_check=values[CONF_DATABASE_INTEGRITY_CHECK],
            ),
            presentation=PresentationSettings(
                entity_mode=values[CONF_ENTITY_MODE],
                notifications_enabled=values[CONF_NOTIFICATIONS_ENABLED],
                notification_targets=tuple(values[CONF_NOTIFICATION_TARGETS]),
                notify_on_recovery=values[CONF_NOTIFY_ON_RECOVERY],
                expose_backup_metadata=values[CONF_EXPOSE_BACKUP_METADATA],
                show_sidebar_panel=values[CONF_SHOW_SIDEBAR_PANEL],
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical config-entry representation."""
        return {
            CONF_RUNTIME_PROFILE: self.runtime.profile,
            CONF_UPDATE_INTERVAL_MINUTES: self.runtime.update_interval_minutes,
            CONF_ACTIVE_UPDATE_INTERVAL_MINUTES: (
                self.runtime.active_update_interval_minutes
            ),
            CONF_ERROR_BACKOFF_INTERVAL_MINUTES: (
                self.runtime.error_backoff_interval_minutes
            ),
            CONF_ADAPTIVE_ERROR_THRESHOLD: self.runtime.adaptive_error_threshold,
            CONF_ADAPTIVE_POLLING: self.runtime.adaptive_polling,
            CONF_MAX_VERIFICATION_SIZE_GB: self.runtime.max_verification_size_gb,
            CONF_MAX_EXPANDED_SIZE_GB: self.runtime.max_expanded_size_gb,
            CONF_VERIFICATION_TIMEOUT_MINUTES: (
                self.runtime.verification_timeout_minutes
            ),
            CONF_DATABASE_TIMEOUT_MINUTES: self.runtime.database_timeout_minutes,
            CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
                self.runtime.manual_verification_cooldown_minutes
            ),
            CONF_PRESET_REVISION: self.runtime.preset_revision,
            CONF_HARDWARE_DETECTION: dict(self.runtime.hardware_detection),
            CONF_MONITORING_POLICY: self.monitoring.policy,
            CONF_MAX_AGE_DAYS: self.monitoring.max_age_days,
            CONF_MINIMUM_BACKUP_SIZE_MB: self.monitoring.minimum_backup_size_mb,
            CONF_MAXIMUM_SIZE_DROP_PERCENT: (self.monitoring.maximum_size_drop_percent),
            CONF_MINIMUM_REDUNDANT_LOCATIONS: (
                self.monitoring.minimum_redundant_locations
            ),
            CONF_ANALYTICS_WINDOW_DAYS: self.monitoring.analytics_window_days,
            CONF_REPAIR_ISSUES_ENABLED: self.monitoring.repair_issues_enabled,
            CONF_SIZE_CHECK_MODE: self.monitoring.size_check_mode,
            CONF_VERIFICATION_POLICY: self.verification.policy,
            CONF_AUTO_VERIFY_NEW_BACKUPS: self.verification.auto_verify_new_backups,
            CONF_DATABASE_INTEGRITY_CHECK: (self.verification.database_integrity_check),
            CONF_ENTITY_MODE: self.presentation.entity_mode,
            CONF_NOTIFICATIONS_ENABLED: self.presentation.notifications_enabled,
            CONF_NOTIFICATION_TARGETS: list(self.presentation.notification_targets),
            CONF_NOTIFY_ON_RECOVERY: self.presentation.notify_on_recovery,
            CONF_EXPOSE_BACKUP_METADATA: self.presentation.expose_backup_metadata,
            CONF_SHOW_SIDEBAR_PANEL: self.presentation.show_sidebar_panel,
        }

    # Compatibility properties keep runtime consumers simple and stable.
    @property
    def runtime_profile(self) -> str:
        return self.runtime.profile

    @property
    def monitoring_policy(self) -> str:
        return self.monitoring.policy

    @property
    def verification_policy(self) -> str:
        return self.verification.policy

    @property
    def update_interval_minutes(self) -> int:
        return self.runtime.update_interval_minutes

    @property
    def active_update_interval_minutes(self) -> int:
        return self.runtime.active_update_interval_minutes

    @property
    def error_backoff_interval_minutes(self) -> int:
        return self.runtime.error_backoff_interval_minutes

    @property
    def adaptive_error_threshold(self) -> int:
        return self.runtime.adaptive_error_threshold

    @property
    def adaptive_polling(self) -> bool:
        return self.runtime.adaptive_polling

    @property
    def max_verification_size_gb(self) -> int:
        return self.runtime.max_verification_size_gb

    @property
    def max_expanded_size_gb(self) -> int:
        return self.runtime.max_expanded_size_gb

    @property
    def verification_timeout_minutes(self) -> int:
        return self.runtime.verification_timeout_minutes

    @property
    def database_timeout_minutes(self) -> int:
        return self.runtime.database_timeout_minutes

    @property
    def manual_verification_cooldown_minutes(self) -> int:
        return self.runtime.manual_verification_cooldown_minutes

    @property
    def max_age_days(self) -> int:
        return self.monitoring.max_age_days

    @property
    def minimum_backup_size_mb(self) -> int:
        return self.monitoring.minimum_backup_size_mb

    @property
    def maximum_size_drop_percent(self) -> int:
        return self.monitoring.maximum_size_drop_percent

    @property
    def minimum_redundant_locations(self) -> int:
        return self.monitoring.minimum_redundant_locations

    @property
    def analytics_window_days(self) -> int:
        return self.monitoring.analytics_window_days

    @property
    def repair_issues_enabled(self) -> bool:
        return self.monitoring.repair_issues_enabled

    @property
    def size_check_mode(self) -> str:
        return self.monitoring.size_check_mode

    @property
    def auto_verify_new_backups(self) -> bool:
        return self.verification.auto_verify_new_backups

    @property
    def database_integrity_check(self) -> bool:
        return self.verification.database_integrity_check

    @property
    def entity_mode(self) -> str:
        return self.presentation.entity_mode

    @property
    def notifications_enabled(self) -> bool:
        return self.presentation.notifications_enabled

    @property
    def notification_targets(self) -> tuple[str, ...]:
        return self.presentation.notification_targets

    @property
    def notify_on_recovery(self) -> bool:
        return self.presentation.notify_on_recovery

    @property
    def expose_backup_metadata(self) -> bool:
        return self.presentation.expose_backup_metadata

    @property
    def show_sidebar_panel(self) -> bool:
        """Return whether the optional frontend panel is enabled."""
        return self.presentation.show_sidebar_panel
