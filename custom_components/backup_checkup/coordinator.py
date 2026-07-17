"""Data coordinator for BackupCheckup."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from homeassistant.components.backup import async_get_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .age import completed_age_days, precise_age_days
from .analytics import calculate_health_score, calculate_inventory_analytics
from .classification import (
    automatic_backup_failed as evaluate_automatic_backup_failed,
)
from .classification import (
    automatic_size_drop_is_suspicious,
    classify_backup_purpose,
    comparable_size_backups,
    monitoring_backups,
)
from .configuration import normalize_configuration
from .const import (
    BACKUP_RESULT_COMPLETE,
    BACKUP_RESULT_PARTIAL,
    BACKUP_RESULT_UNKNOWN,
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
    DEFAULT_NOTIFICATION_TARGETS,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFY_ON_RECOVERY,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_SIZE_CHECK_MODE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
    DOMAIN,
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
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
    RECOMMENDATION_ADD_STORAGE_LOCATION,
    RECOMMENDATION_CHECK_BACKUP_CONTENTS,
    RECOMMENDATION_CHECK_BACKUP_SIZE,
    RECOMMENDATION_CHECK_BACKUP_SYSTEM,
    RECOMMENDATION_CHECK_SCHEDULE,
    RECOMMENDATION_CHECK_STORAGE,
    RECOMMENDATION_CREATE_BACKUP,
    RECOMMENDATION_NONE,
    RECOMMENDATION_REPLACE_BACKUP,
    SIZE_CHECK_AUTO,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OFF,
    STATUS_AUTOMATIC_BACKUP_FAILED,
    STATUS_AUTOMATIC_BACKUP_OVERDUE,
    STATUS_BACKUP_CHECKSUM_CHANGED,
    STATUS_BACKUP_INCOMPLETE,
    STATUS_BACKUP_INTEGRITY_FAILED,
    STATUS_BACKUP_INTEGRITY_WARNING,
    STATUS_BACKUP_NOT_REDUNDANT,
    STATUS_BACKUP_SIZE_SUSPICIOUS,
    STATUS_BACKUP_STALE,
    STATUS_MANAGER_UNAVAILABLE,
    STATUS_NO_BACKUPS,
    STATUS_OK,
    STATUS_SCHEDULE_MISSING,
    STATUS_SCHEDULE_OVERDUE,
    STATUS_STORAGE_ERROR,
)
from .history import BackupCheckupHistory
from .integrity import BackupIntegrityVerifier
from .models import (
    BackupAgentRecord,
    BackupAgentSummary,
    BackupCheckupData,
    BackupIntegrityResult,
    BackupRecord,
)
from .native_backup import read_native_backup_state
from .notifications import BackupCheckupNotificationManager
from .security import (
    anonymous_agent_reference,
    anonymous_backup_reference,
    backup_scope_fingerprint,
    classify_exception,
    safe_display_name,
    safe_error_type,
)
from .task_control import release_current_task_reference

_LOGGER = logging.getLogger(__name__)

_AUTOMATIC_RETRY_BASE = timedelta(minutes=30)
_AUTOMATIC_RETRY_MAX = timedelta(hours=6)
_AUTOMATIC_RETRY_LIMIT = 3
_COPY_SIZE_MISMATCH_MIN_BYTES = 1_000_000
_COPY_SIZE_MISMATCH_RATIO = 0.01


def _bounded_int_option(
    options: Mapping[str, Any],
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Return one validated integer option or its safe default."""
    value = options.get(key, default)
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if minimum <= parsed <= maximum else default


def _boolean_option(options: Mapping[str, Any], key: str, default: bool) -> bool:
    """Return one strict boolean option or its safe default."""
    value = options.get(key, default)
    return value if isinstance(value, bool) else default


class BackupCheckupCoordinator(DataUpdateCoordinator[BackupCheckupData]):
    """Fetch and evaluate the actual Home Assistant backup inventory."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        options = normalize_configuration(entry.data, entry.options)

        entity_mode = options.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)
        self.entity_mode = (
            entity_mode
            if entity_mode in {"standard", "expert"}
            else DEFAULT_ENTITY_MODE
        )
        self.max_age_days = _bounded_int_option(
            options,
            CONF_MAX_AGE_DAYS,
            DEFAULT_MAX_AGE_DAYS,
            MIN_MAX_AGE_DAYS,
            MAX_MAX_AGE_DAYS,
        )
        self.minimum_backup_size_bytes = (
            _bounded_int_option(
                options,
                CONF_MINIMUM_BACKUP_SIZE_MB,
                DEFAULT_MINIMUM_BACKUP_SIZE_MB,
                MIN_MINIMUM_BACKUP_SIZE_MB,
                MAX_MINIMUM_BACKUP_SIZE_MB,
            )
            * 1_000_000
        )
        self.maximum_size_drop_percent = _bounded_int_option(
            options,
            CONF_MAXIMUM_SIZE_DROP_PERCENT,
            DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
            MIN_MAXIMUM_SIZE_DROP_PERCENT,
            MAX_MAXIMUM_SIZE_DROP_PERCENT,
        )
        size_check_mode = options.get(CONF_SIZE_CHECK_MODE, DEFAULT_SIZE_CHECK_MODE)
        self.size_check_mode = (
            size_check_mode
            if size_check_mode in {SIZE_CHECK_AUTO, SIZE_CHECK_FIXED, SIZE_CHECK_OFF}
            else DEFAULT_SIZE_CHECK_MODE
        )
        self.minimum_redundant_locations = _bounded_int_option(
            options,
            CONF_MINIMUM_REDUNDANT_LOCATIONS,
            DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
            MIN_REDUNDANT_LOCATIONS,
            MAX_REDUNDANT_LOCATIONS,
        )
        self.repair_issues_enabled = _boolean_option(
            options, CONF_REPAIR_ISSUES_ENABLED, DEFAULT_REPAIR_ISSUES_ENABLED
        )
        self.analytics_window_days = _bounded_int_option(
            options,
            CONF_ANALYTICS_WINDOW_DAYS,
            DEFAULT_ANALYTICS_WINDOW_DAYS,
            MIN_ANALYTICS_WINDOW_DAYS,
            MAX_ANALYTICS_WINDOW_DAYS,
        )
        self.auto_verify_new_backups = _boolean_option(
            options, CONF_AUTO_VERIFY_NEW_BACKUPS, DEFAULT_AUTO_VERIFY_NEW_BACKUPS
        )
        self.database_integrity_check = _boolean_option(
            options,
            CONF_DATABASE_INTEGRITY_CHECK,
            DEFAULT_DATABASE_INTEGRITY_CHECK,
        )
        self.max_verification_size_gb = _bounded_int_option(
            options,
            CONF_MAX_VERIFICATION_SIZE_GB,
            DEFAULT_MAX_VERIFICATION_SIZE_GB,
            MIN_MAX_VERIFICATION_SIZE_GB,
            MAX_MAX_VERIFICATION_SIZE_GB,
        )
        self.max_expanded_size_gb = _bounded_int_option(
            options,
            CONF_MAX_EXPANDED_SIZE_GB,
            DEFAULT_MAX_EXPANDED_SIZE_GB,
            MIN_MAX_EXPANDED_SIZE_GB,
            MAX_MAX_EXPANDED_SIZE_GB,
        )
        self.verification_timeout_minutes = _bounded_int_option(
            options,
            CONF_VERIFICATION_TIMEOUT_MINUTES,
            DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
            MIN_VERIFICATION_TIMEOUT_MINUTES,
            MAX_VERIFICATION_TIMEOUT_MINUTES,
        )
        self.database_timeout_minutes = _bounded_int_option(
            options,
            CONF_DATABASE_TIMEOUT_MINUTES,
            DEFAULT_DATABASE_TIMEOUT_MINUTES,
            MIN_DATABASE_TIMEOUT_MINUTES,
            MAX_DATABASE_TIMEOUT_MINUTES,
        )
        self.manual_verification_cooldown_minutes = _bounded_int_option(
            options,
            CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
        )
        self.expose_backup_metadata = _boolean_option(
            options, CONF_EXPOSE_BACKUP_METADATA, DEFAULT_EXPOSE_BACKUP_METADATA
        )
        self.notifications_enabled = _boolean_option(
            options, CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED
        )
        notification_targets = options.get(
            CONF_NOTIFICATION_TARGETS,
            DEFAULT_NOTIFICATION_TARGETS,
        )
        if isinstance(notification_targets, str):
            notification_targets = [notification_targets]
        if not isinstance(notification_targets, (list, tuple, set, frozenset)):
            notification_targets = []
        self.notification_targets = tuple(
            entity_id
            for entity_id in notification_targets
            if isinstance(entity_id, str)
            and entity_id.startswith("notify.")
            and len(entity_id) <= 255
        )
        self.notify_on_recovery = _boolean_option(
            options, CONF_NOTIFY_ON_RECOVERY, DEFAULT_NOTIFY_ON_RECOVERY
        )
        self.history = BackupCheckupHistory(hass, entry.entry_id)
        self.integrity_verifier = BackupIntegrityVerifier(hass, entry.entry_id)
        self.notification_manager = BackupCheckupNotificationManager(
            hass, entry.entry_id
        )
        self.integrity_result = BackupIntegrityResult.not_checked()
        self.integrity_check_running = False
        self._integrity_loaded = False
        self._integrity_task: asyncio.Task[None] | None = None
        self._integrity_retry_not_before: datetime | None = None
        self._integrity_retry_key: tuple[str, str] | None = None
        self._integrity_retry_attempts = 0
        self._backup_password_marker: str | None = None
        self._backup_password_marker_initialized = False
        self._invalid_backup_count = 0
        self._invalid_agent_copy_count = 0
        self._last_inventory_success_at: datetime | None = None
        update_minutes = _bounded_int_option(
            options,
            CONF_UPDATE_INTERVAL_MINUTES,
            DEFAULT_UPDATE_INTERVAL_MINUTES,
            MIN_UPDATE_INTERVAL_MINUTES,
            MAX_UPDATE_INTERVAL_MINUTES,
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_minutes),
        )

    async def async_shutdown(self) -> None:
        """Cancel a running integrity check and shut down the coordinator."""
        if self._integrity_task is not None and not self._integrity_task.done():
            self._integrity_task.cancel()
            await asyncio.gather(self._integrity_task, return_exceptions=True)
        await super().async_shutdown()

    @staticmethod
    def _safe_getattr(value: Any, name: str, default: Any = None) -> Any:
        """Read one third-party property without allowing it to break refresh."""
        try:
            return getattr(value, name, default)
        except Exception:  # noqa: BLE001
            return default

    @staticmethod
    def _safe_text(
        value: Any,
        *,
        maximum: int,
        strip: bool = True,
    ) -> str | None:
        """Return bounded text or None when conversion itself is unsafe."""
        try:
            text = str(value)
        except Exception:  # noqa: BLE001
            return None
        if strip:
            text = text.strip()
        return text[:maximum] if text else None

    @staticmethod
    def _safe_mapping_items(value: Any) -> tuple[tuple[Any, Any], ...]:
        """Return mapping items without trusting a third-party iterator."""
        if not isinstance(value, Mapping):
            return ()
        try:
            return tuple(value.items())
        except Exception:  # noqa: BLE001
            return ()

    @staticmethod
    def _copy_sizes_mismatch(sizes: list[int]) -> tuple[bool, int | None]:
        """Return whether reported redundant-copy sizes differ materially."""
        if len(sizes) < 2:
            return False, None
        smallest = min(sizes)
        largest = max(sizes)
        spread = largest - smallest
        tolerance = max(
            _COPY_SIZE_MISMATCH_MIN_BYTES,
            int(largest * _COPY_SIZE_MISMATCH_RATIO),
        )
        return spread > tolerance, spread

    @staticmethod
    def _as_datetime(value: Any) -> datetime | None:
        """Convert a value to an aware UTC datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = dt_util.parse_datetime(str(value))
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return dt_util.as_utc(parsed)

    def _entity_datetime(self, entity_id: str) -> datetime | None:
        """Read an ISO datetime from a Home Assistant entity state."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "",
            "none",
        }:
            return None
        return self._as_datetime(state.state)

    def _entity_state(self, entity_id: str) -> str:
        """Read a normalized entity state."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return STATE_UNKNOWN
        return state.state.lower()

    @staticmethod
    def _as_bool(value: Any) -> bool | None:
        """Return a boolean value when one is available."""
        return value if isinstance(value, bool) else None

    @staticmethod
    def _as_string_tuple(value: Any) -> tuple[str, ...]:
        """Normalize an iterable or mapping to a sorted string tuple."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            try:
                value = value.keys()
            except Exception:  # noqa: BLE001
                return ()
        if isinstance(value, str):
            return (value,)
        try:
            normalized: set[str] = set()
            for item in value:
                text = BackupCheckupCoordinator._safe_text(item, maximum=512)
                if text:
                    normalized.add(text)
            return tuple(sorted(normalized))
        except Exception:  # noqa: BLE001
            return ()

    @staticmethod
    def _addon_slugs(value: Any) -> tuple[str, ...]:
        """Normalize Home Assistant add-on metadata to sorted slugs."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            try:
                value = value.values()
            except Exception:  # noqa: BLE001
                return ()
        if isinstance(value, str):
            return (value,)
        slugs: set[str] = set()
        try:
            for addon in value:
                slug = BackupCheckupCoordinator._safe_getattr(addon, "slug", None)
                if slug is None and isinstance(addon, Mapping):
                    try:
                        slug = addon.get("slug")
                    except Exception:  # noqa: BLE001
                        slug = None
                if isinstance(slug, str) and slug:
                    slugs.add(slug)
        except Exception:  # noqa: BLE001
            return ()
        return tuple(sorted(slugs))

    @staticmethod
    def _as_nonnegative_int(value: Any) -> int | None:
        """Return a finite non-negative integer or None for invalid agent data."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        try:
            normalized = int(value)
        except (OverflowError, ValueError):
            return None
        return normalized if normalized >= 0 else None

    def _agent_copy(self, agent_id: Any, details: Any) -> BackupAgentRecord | None:
        """Normalize one backup-agent copy record across HA model versions."""
        normalized_agent_id = self._safe_text(agent_id, maximum=512)
        if normalized_agent_id is None:
            return None
        size_raw = self._safe_getattr(details, "size", None)
        if size_raw is None and isinstance(details, Mapping):
            try:
                size_raw = details.get("size")
            except Exception:  # noqa: BLE001
                return None
        size = BackupCheckupCoordinator._as_nonnegative_int(size_raw)

        protected_raw = self._safe_getattr(details, "protected", None)
        if protected_raw is None:
            protected_raw = self._safe_getattr(details, "is_protected", None)
        if protected_raw is None and isinstance(details, Mapping):
            try:
                protected_raw = details.get("protected", details.get("is_protected"))
            except Exception:  # noqa: BLE001
                return None
        protected = protected_raw if isinstance(protected_raw, bool) else None
        return BackupAgentRecord(
            normalized_agent_id,
            anonymous_agent_reference(self.config_entry.entry_id, normalized_agent_id),
            size,
            protected,
        )

    async def _async_update_data(self) -> BackupCheckupData:
        """Read and evaluate the backup inventory."""
        try:
            manager = async_get_manager(self.hass)
            backups, agent_errors_raw = await manager.async_get_backups()
        except HomeAssistantError as err:
            error_code = classify_exception(err)
            _LOGGER.warning(
                "Home Assistant backup manager is not ready: "
                "error_type=%s error_code=%s",
                safe_error_type(err),
                error_code,
            )
            if self.data is not None:
                snapshot = self._manager_error_snapshot(error_code)
                await self._async_process_notifications(snapshot)
                return snapshot
            raise UpdateFailed(
                f"Home Assistant backup manager is not ready ({error_code})"
            ) from None
        except Exception as err:  # noqa: BLE001
            error_code = classify_exception(err)
            _LOGGER.error(
                "Unable to read Home Assistant backups: error_type=%s error_code=%s",
                safe_error_type(err),
                error_code,
            )
            if self.data is not None:
                snapshot = self._manager_error_snapshot(error_code)
                await self._async_process_notifications(snapshot)
                return snapshot
            raise UpdateFailed(
                f"Unable to read Home Assistant backups ({error_code})"
            ) from None

        if not isinstance(backups, Mapping):
            raise UpdateFailed("Backup manager returned an invalid inventory")
        if not isinstance(agent_errors_raw, Mapping):
            agent_errors_raw = {}

        now = dt_util.utcnow()
        password_changed = self._update_backup_password_marker(manager)
        if not self._integrity_loaded:
            self.integrity_result = await self.integrity_verifier.store.async_load()
            self._integrity_loaded = True
        records = self._normalize_backups(backups)
        monitoring_records = monitoring_backups(records)
        ignored_update_backup_count = len(records) - len(monitoring_records)
        automatic_records = [item for item in monitoring_records if item.automatic]
        manual_records = [item for item in monitoring_records if not item.automatic]
        latest_record = monitoring_records[0] if monitoring_records else None
        latest_automatic_record = automatic_records[0] if automatic_records else None

        latest_backup = latest_record.date if latest_record else None
        latest_automatic = (
            latest_automatic_record.date if latest_automatic_record else None
        )
        latest_manual = manual_records[0].date if manual_records else None

        latest_age_precise = precise_age_days(now, latest_backup)
        latest_age = completed_age_days(latest_age_precise)
        automatic_age_precise = precise_age_days(now, latest_automatic)
        automatic_age = completed_age_days(automatic_age_precise)
        manual_age_precise = precise_age_days(now, latest_manual)
        manual_age = completed_age_days(manual_age_precise)

        (
            size_change_percent,
            automatic_drop_percent,
            comparable_backup_count,
        ) = self._size_changes(
            latest_record,
            monitoring_records,
        )
        backup_size_suspicious = self._is_size_suspicious(
            latest_record,
            size_change_percent,
            automatic_drop_percent,
            comparable_backup_count,
        )

        latest_backup_incomplete = bool(latest_record and latest_record.incomplete)
        if latest_record is None:
            latest_backup_result = BACKUP_RESULT_UNKNOWN
        elif latest_record.incomplete:
            latest_backup_result = BACKUP_RESULT_PARTIAL
        else:
            latest_backup_result = BACKUP_RESULT_COMPLETE

        latest_location_ids = latest_record.agents if latest_record else ()
        latest_locations = len(latest_location_ids)
        backup_not_redundant = bool(
            latest_record and latest_locations < self.minimum_redundant_locations
        )

        native_backup = read_native_backup_state(self.hass, manager, now=now)
        last_automatic_attempt = native_backup.last_attempt
        last_successful_automatic_event = native_backup.last_success
        next_automatic = native_backup.next_scheduled
        manager_state = native_backup.manager_state
        automatic_event_type = native_backup.event_type
        automatic_backup_in_progress = native_backup.in_progress
        history_metrics = await self.history.async_observe(
            last_attempt=last_automatic_attempt,
            last_success=last_successful_automatic_event,
            now=now,
            window_days=self.analytics_window_days,
            in_progress=automatic_backup_in_progress,
        )
        inventory_analytics = calculate_inventory_analytics(
            monitoring_records,
            now=now,
            window_days=self.analytics_window_days,
        )

        no_backup = not monitoring_records
        backup_stale = (
            latest_age_precise is not None and latest_age_precise > self.max_age_days
        )
        manual_covers_automatic = latest_manual is not None and (
            latest_automatic is None or latest_manual > latest_automatic
        )
        if latest_automatic is None:
            automatic_backup_overdue = (
                latest_manual is None
                or manual_age is None
                or manual_age_precise > self.max_age_days
            )
        else:
            automatic_backup_overdue = (
                automatic_age_precise is not None
                and automatic_age_precise > self.max_age_days
                and not manual_covers_automatic
            )

        automatic_backup_failed = evaluate_automatic_backup_failed(
            event_type=automatic_event_type,
            in_progress=automatic_backup_in_progress,
            last_attempt=last_automatic_attempt,
            last_success=last_successful_automatic_event,
        )
        automatic_schedule_missing = next_automatic is None
        automatic_schedule_overdue = (
            next_automatic is not None and next_automatic < now - timedelta(hours=6)
        )
        # A successful manager API response proves availability. The optional
        # state entity is supplemental and may be disabled or not loaded yet.
        manager_unavailable = False
        agent_errors: dict[str, str] = {}
        for agent_id, error in self._safe_mapping_items(agent_errors_raw):
            normalized_agent_id = self._safe_text(agent_id, maximum=512)
            if normalized_agent_id:
                agent_errors[normalized_agent_id] = classify_exception(error)
        storage_error = bool(agent_errors)

        manager_agents = self._safe_getattr(manager, "backup_agents", {})
        manager_agent_items = self._safe_mapping_items(manager_agents)
        configured_agent_ids: set[str] = set()
        agent_names: dict[str, str] = {}
        for agent_id, agent in manager_agent_items:
            normalized_agent_id = self._safe_text(agent_id, maximum=512)
            if normalized_agent_id is None:
                continue
            configured_agent_ids.add(normalized_agent_id)
            agent_reference = anonymous_agent_reference(
                self.config_entry.entry_id,
                normalized_agent_id,
            )
            agent_names[normalized_agent_id] = safe_display_name(
                self._safe_getattr(agent, "name", None),
                fallback=f"Backup storage {agent_reference}",
            )
        agent_summaries = self._build_agent_summaries(
            records,
            monitoring_records,
            agent_errors,
            configured_agent_ids,
            agent_names,
            now,
        )
        required_location_missing = bool(
            latest_record
            and any(
                summary.problem
                for summary in agent_summaries
                if summary.agent_id in latest_location_ids
            )
        )
        backup_integrity_failed = bool(
            latest_record
            and self.integrity_result.backup_id == latest_record.backup_id
            and self.integrity_result.status
            in {"corrupt", "unreadable", "internal_error"}
        )
        backup_checksum_changed = bool(
            latest_record
            and self.integrity_result.backup_id == latest_record.backup_id
            and self.integrity_result.checksum_changed
        )
        backup_integrity_warning = bool(
            latest_record
            and self.integrity_result.backup_id == latest_record.backup_id
            and self.integrity_result.status
            in {
                INTEGRITY_STATUS_VALID_WITH_WARNINGS,
                "aborted",
                "password_required",
            }
        )

        status = self._status(
            no_backup=no_backup,
            backup_integrity_failed=backup_integrity_failed,
            backup_checksum_changed=backup_checksum_changed,
            backup_integrity_warning=backup_integrity_warning,
            manager_unavailable=manager_unavailable,
            automatic_schedule_missing=automatic_schedule_missing,
            storage_error=storage_error,
            latest_backup_incomplete=latest_backup_incomplete,
            backup_size_suspicious=backup_size_suspicious,
            backup_not_redundant=backup_not_redundant,
            automatic_backup_failed=automatic_backup_failed,
            automatic_backup_overdue=automatic_backup_overdue,
            backup_stale=backup_stale,
            automatic_schedule_overdue=automatic_schedule_overdue,
        )

        active_problems = tuple(
            key
            for key, active in (
                ("no_backup", no_backup),
                ("backup_integrity_failed", backup_integrity_failed),
                ("backup_checksum_changed", backup_checksum_changed),
                ("backup_integrity_warning", backup_integrity_warning),
                ("backup_stale", backup_stale),
                ("automatic_backup_overdue", automatic_backup_overdue),
                ("automatic_backup_failed", automatic_backup_failed),
                ("automatic_schedule_missing", automatic_schedule_missing),
                ("automatic_schedule_overdue", automatic_schedule_overdue),
                ("manager_unavailable", manager_unavailable),
                ("storage_error", storage_error),
                ("backup_size_suspicious", backup_size_suspicious),
                ("latest_backup_incomplete", latest_backup_incomplete),
                ("backup_not_redundant", backup_not_redundant),
                ("required_location_missing", required_location_missing),
            )
            if active
        )

        score_flags = {
            "no_backup": no_backup,
            "backup_integrity_failed": backup_integrity_failed,
            "backup_checksum_changed": backup_checksum_changed,
            "backup_integrity_warning": backup_integrity_warning,
            "backup_stale": backup_stale,
            "automatic_backup_overdue": automatic_backup_overdue,
            "automatic_backup_failed": automatic_backup_failed,
            "automatic_schedule_missing": automatic_schedule_missing,
            "automatic_schedule_overdue": automatic_schedule_overdue,
            "manager_unavailable": manager_unavailable,
            "storage_error": storage_error,
            "backup_size_suspicious": backup_size_suspicious,
            "latest_backup_incomplete": latest_backup_incomplete,
            "backup_not_redundant": backup_not_redundant,
            "required_location_missing": required_location_missing,
        }
        health = calculate_health_score(
            score_flags,
            automatic_success_rate=history_metrics.success_rate,
            consecutive_automatic_failures=history_metrics.consecutive_failures,
            resolved_attempts=history_metrics.resolved_attempts,
        )

        recommendation = {
            STATUS_OK: RECOMMENDATION_NONE,
            STATUS_NO_BACKUPS: RECOMMENDATION_CREATE_BACKUP,
            STATUS_BACKUP_INTEGRITY_FAILED: RECOMMENDATION_REPLACE_BACKUP,
            STATUS_BACKUP_CHECKSUM_CHANGED: RECOMMENDATION_CHECK_STORAGE,
            STATUS_BACKUP_INTEGRITY_WARNING: RECOMMENDATION_CHECK_BACKUP_CONTENTS,
            STATUS_BACKUP_STALE: RECOMMENDATION_CREATE_BACKUP,
            STATUS_AUTOMATIC_BACKUP_OVERDUE: RECOMMENDATION_CHECK_SCHEDULE,
            STATUS_AUTOMATIC_BACKUP_FAILED: RECOMMENDATION_CHECK_SCHEDULE,
            STATUS_SCHEDULE_MISSING: RECOMMENDATION_CHECK_SCHEDULE,
            STATUS_SCHEDULE_OVERDUE: RECOMMENDATION_CHECK_SCHEDULE,
            STATUS_MANAGER_UNAVAILABLE: RECOMMENDATION_CHECK_BACKUP_SYSTEM,
            STATUS_STORAGE_ERROR: RECOMMENDATION_CHECK_STORAGE,
            STATUS_BACKUP_INCOMPLETE: RECOMMENDATION_CHECK_BACKUP_CONTENTS,
            STATUS_BACKUP_SIZE_SUSPICIOUS: RECOMMENDATION_CHECK_BACKUP_SIZE,
            STATUS_BACKUP_NOT_REDUNDANT: RECOMMENDATION_ADD_STORAGE_LOCATION,
        }.get(status, RECOMMENDATION_CHECK_BACKUP_SYSTEM)

        public_agent_errors = (
            agent_errors
            if self.expose_backup_metadata
            else {
                anonymous_agent_reference(self.config_entry.entry_id, agent_id): code
                for agent_id, code in agent_errors.items()
            }
        )
        public_location_ids = (
            latest_location_ids
            if self.expose_backup_metadata
            else tuple(
                anonymous_agent_reference(self.config_entry.entry_id, agent_id)
                for agent_id in latest_location_ids
            )
        )

        self._last_inventory_success_at = now
        data = BackupCheckupData(
            checked_at=now,
            max_age_days=self.max_age_days,
            minimum_backup_size_bytes=self.minimum_backup_size_bytes,
            maximum_size_drop_percent=self.maximum_size_drop_percent,
            minimum_redundant_locations=self.minimum_redundant_locations,
            total_backups=len(monitoring_records),
            inventory_backup_count=len(records),
            ignored_update_backup_count=ignored_update_backup_count,
            automatic_backups=len(automatic_records),
            manual_backups=len(manual_records),
            latest_backup=latest_backup,
            latest_automatic_backup=latest_automatic,
            latest_manual_backup=latest_manual,
            latest_backup_age_days=latest_age,
            latest_backup_age_days_precise=latest_age_precise,
            automatic_backup_age_days=automatic_age,
            automatic_backup_age_days_precise=automatic_age_precise,
            manual_backup_age_days=manual_age,
            manual_backup_age_days_precise=manual_age_precise,
            latest_backup_size=latest_record.size if latest_record else None,
            latest_automatic_backup_size=(
                latest_automatic_record.size if latest_automatic_record else None
            ),
            latest_backup_size_change_percent=size_change_percent,
            comparable_backup_count=comparable_backup_count,
            latest_backup_result=latest_backup_result,
            latest_backup_locations=latest_locations,
            latest_backup_location_ids=public_location_ids,
            last_automatic_attempt=last_automatic_attempt,
            last_successful_automatic_event=last_successful_automatic_event,
            next_automatic_backup=next_automatic,
            manager_state=manager_state,
            agent_errors=public_agent_errors,
            agent_summaries=agent_summaries,
            backups=records,
            monitored_backups=monitoring_records,
            no_backup=no_backup,
            backup_stale=backup_stale,
            automatic_backup_overdue=automatic_backup_overdue,
            automatic_backup_failed=automatic_backup_failed,
            automatic_schedule_missing=automatic_schedule_missing,
            automatic_schedule_overdue=automatic_schedule_overdue,
            manager_unavailable=manager_unavailable,
            storage_error=storage_error,
            backup_size_suspicious=backup_size_suspicious,
            latest_backup_incomplete=latest_backup_incomplete,
            backup_not_redundant=backup_not_redundant,
            required_location_missing=required_location_missing,
            backup_checksum_changed=backup_checksum_changed,
            backup_integrity_warning=backup_integrity_warning,
            problem=bool(active_problems),
            status=status,
            recommendation=recommendation,
            problem_count=len(active_problems),
            active_problems=active_problems,
            size_check_mode=self.size_check_mode,
            analytics_window_days=self.analytics_window_days,
            health_score=health.score,
            health_rating=health.rating,
            health_score_deductions=health.deductions,
            average_backup_size=inventory_analytics.average_backup_size,
            longest_backup_gap_days=inventory_analytics.longest_backup_gap_days,
            size_trend=inventory_analytics.size_trend,
            size_trend_percent=inventory_analytics.size_trend_percent,
            analyzed_backup_count=inventory_analytics.analyzed_backup_count,
            analyzed_backup_scope=inventory_analytics.analyzed_backup_scope,
            analyzed_backup_origin=inventory_analytics.analyzed_backup_origin,
            automatic_success_rate=history_metrics.success_rate,
            automatic_attempts_observed=history_metrics.resolved_attempts,
            automatic_successes_observed=history_metrics.successful_attempts,
            automatic_failures_observed=history_metrics.failed_attempts,
            consecutive_automatic_failures=history_metrics.consecutive_failures,
            history_tracking_started_at=history_metrics.tracking_started_at,
            integrity=self.integrity_result,
            integrity_check_running=self.integrity_check_running,
            expose_backup_metadata=self.expose_backup_metadata,
            invalid_backup_count=self._invalid_backup_count,
            invalid_agent_copy_count=self._invalid_agent_copy_count,
            copy_size_mismatch_count=sum(
                1 for record in records if record.copy_size_mismatch
            ),
            last_inventory_success_at=self._last_inventory_success_at,
        )

        await self._async_process_notifications(data)

        if (
            self.auto_verify_new_backups
            and self._automatic_verification_due(
                latest_record,
                now=now,
                password_changed=password_changed,
            )
            and not self.integrity_check_running
            and (self._integrity_task is None or self._integrity_task.done())
        ):
            self._set_integrity_task(
                self.hass.async_create_task(
                    self._async_run_integrity_check(latest_record, source="automatic"),
                    name=f"{DOMAIN}_automatic_integrity_check",
                )
            )
        return data

    @staticmethod
    def _integrity_result_is_retryable(result: BackupIntegrityResult) -> bool:
        """Return whether an automatic check may retry a controlled result."""
        if result.status in {
            INTEGRITY_STATUS_INTERNAL_ERROR,
            INTEGRITY_STATUS_UNREADABLE,
        }:
            return True
        if result.status != INTEGRITY_STATUS_ABORTED:
            return False
        return result.error_code in {
            "verification_timeout",
            "database_timeout",
            "insufficient_free_space",
        }

    def _automatic_verification_due(
        self,
        latest_record: BackupRecord | None,
        *,
        now: datetime,
        password_changed: bool = False,
    ) -> bool:
        """Return whether the newest backup should be checked automatically."""
        if latest_record is None:
            return False
        result = self.integrity_result
        if result.backup_id != latest_record.backup_id:
            return True
        if result.status == INTEGRITY_STATUS_PASSWORD_REQUIRED:
            return password_changed and self._backup_password_marker is not None
        if not self._integrity_result_is_retryable(result):
            return False
        if self._integrity_retry_attempts >= _AUTOMATIC_RETRY_LIMIT:
            return False
        not_before = self._integrity_retry_not_before
        if not_before is None and result.checked_at is not None:
            not_before = result.checked_at + _AUTOMATIC_RETRY_BASE
        return not_before is None or now >= not_before

    def _update_backup_password_marker(self, manager: Any) -> bool:
        """Return whether the native backup password changed since last refresh."""
        password = BackupIntegrityVerifier._backup_password(manager)
        marker = (
            hashlib.sha256(password.encode()).hexdigest()
            if password is not None
            else None
        )
        changed = (
            self._backup_password_marker_initialized
            and marker != self._backup_password_marker
        )
        if not self._backup_password_marker_initialized:
            changed = marker is not None
        self._backup_password_marker = marker
        self._backup_password_marker_initialized = True
        return changed

    def _update_integrity_retry_state(
        self,
        result: BackupIntegrityResult,
    ) -> None:
        """Apply bounded exponential backoff for repeatable automatic failures."""
        if not self._integrity_result_is_retryable(result) or result.backup_id is None:
            self._integrity_retry_key = None
            self._integrity_retry_attempts = 0
            self._integrity_retry_not_before = None
            return
        key = (result.backup_id, result.error_code or result.status)
        if key == self._integrity_retry_key:
            self._integrity_retry_attempts += 1
        else:
            self._integrity_retry_key = key
            self._integrity_retry_attempts = 1
        multiplier = 2 ** max(0, self._integrity_retry_attempts - 1)
        delay = min(_AUTOMATIC_RETRY_BASE * multiplier, _AUTOMATIC_RETRY_MAX)
        checked_at = result.checked_at or dt_util.utcnow()
        self._integrity_retry_not_before = checked_at + delay

    async def _async_process_notifications(self, data: BackupCheckupData) -> None:
        """Process notifications without allowing third-party failures to escape."""
        try:
            await self.notification_manager.async_process(
                data,
                enabled=self.notifications_enabled,
                targets=self.notification_targets,
                notify_on_recovery=self.notify_on_recovery,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Unexpected error while processing BackupCheckup notifications: "
                "error_type=%s",
                safe_error_type(err),
            )

    def _manager_error_snapshot(self, error_code: str) -> BackupCheckupData:
        """Return the last snapshot marked unavailable after a manager API error."""
        now = dt_util.utcnow()
        latest_age_precise = precise_age_days(now, self.data.latest_backup)
        automatic_age_precise = precise_age_days(now, self.data.latest_automatic_backup)
        manual_age_precise = precise_age_days(now, self.data.latest_manual_backup)
        backup_stale = bool(
            latest_age_precise is not None and latest_age_precise > self.max_age_days
        )
        manual_covers_automatic = self.data.latest_manual_backup is not None and (
            self.data.latest_automatic_backup is None
            or self.data.latest_manual_backup > self.data.latest_automatic_backup
        )
        if self.data.latest_automatic_backup is None:
            automatic_backup_overdue = (
                self.data.latest_manual_backup is None
                or manual_age_precise is None
                or manual_age_precise > self.max_age_days
            )
        else:
            automatic_backup_overdue = bool(
                automatic_age_precise is not None
                and automatic_age_precise > self.max_age_days
                and not manual_covers_automatic
            )
        agent_summaries = tuple(
            replace(
                summary,
                latest_backup_age_days=(
                    age := precise_age_days(now, summary.latest_backup)
                ),
                stale=age is None or age > self.max_age_days,
                problem=bool(summary.error or age is None or age > self.max_age_days),
            )
            for summary in self.data.agent_summaries
        )
        latest = self.data.latest_monitored_backup_record
        required_location_missing = bool(
            latest
            and any(
                summary.problem
                for summary in agent_summaries
                if summary.agent_id in latest.agents
            )
        )
        dynamic_problem_keys = {
            "backup_stale",
            "automatic_backup_overdue",
            "required_location_missing",
            "manager_unavailable",
        }
        active_items = [
            item
            for item in self.data.active_problems
            if item not in dynamic_problem_keys
        ]
        for key, is_active in (
            ("backup_stale", backup_stale),
            ("automatic_backup_overdue", automatic_backup_overdue),
            ("required_location_missing", required_location_missing),
            ("manager_unavailable", True),
        ):
            if is_active:
                active_items.append(key)
        active = tuple(dict.fromkeys(active_items))
        score_flags = {
            "no_backup": self.data.no_backup,
            "backup_integrity_failed": "backup_integrity_failed" in active,
            "backup_checksum_changed": self.data.backup_checksum_changed,
            "backup_integrity_warning": self.data.backup_integrity_warning,
            "backup_stale": backup_stale,
            "automatic_backup_overdue": automatic_backup_overdue,
            "automatic_backup_failed": self.data.automatic_backup_failed,
            "automatic_schedule_missing": self.data.automatic_schedule_missing,
            "automatic_schedule_overdue": self.data.automatic_schedule_overdue,
            "manager_unavailable": True,
            "storage_error": self.data.storage_error,
            "backup_size_suspicious": self.data.backup_size_suspicious,
            "latest_backup_incomplete": self.data.latest_backup_incomplete,
            "backup_not_redundant": self.data.backup_not_redundant,
            "required_location_missing": required_location_missing,
        }
        health = calculate_health_score(
            score_flags,
            automatic_success_rate=self.data.automatic_success_rate,
            consecutive_automatic_failures=self.data.consecutive_automatic_failures,
            resolved_attempts=self.data.automatic_attempts_observed,
        )
        return replace(
            self.data,
            checked_at=now,
            latest_backup_age_days=completed_age_days(latest_age_precise),
            latest_backup_age_days_precise=latest_age_precise,
            automatic_backup_age_days=completed_age_days(automatic_age_precise),
            automatic_backup_age_days_precise=automatic_age_precise,
            manual_backup_age_days=completed_age_days(manual_age_precise),
            manual_backup_age_days_precise=manual_age_precise,
            agent_summaries=agent_summaries,
            backup_stale=backup_stale,
            automatic_backup_overdue=automatic_backup_overdue,
            required_location_missing=required_location_missing,
            manager_state=STATE_UNAVAILABLE,
            manager_unavailable=True,
            problem=True,
            status=STATUS_MANAGER_UNAVAILABLE,
            recommendation=RECOMMENDATION_CHECK_BACKUP_SYSTEM,
            problem_count=len(active),
            active_problems=active,
            health_score=health.score,
            health_rating=health.rating,
            health_score_deductions=health.deductions,
            agent_errors={**self.data.agent_errors, "manager": error_code},
        )

    def _set_integrity_task(self, task: asyncio.Task[None]) -> None:
        """Track a verification task and always retrieve its final exception."""
        self._integrity_task = task
        task.add_done_callback(self._consume_integrity_task_result)

    @staticmethod
    def _consume_integrity_task_result(task: asyncio.Task[None]) -> None:
        """Consume a background task result so asyncio never reports it unhandled."""
        try:
            task.exception()
        except asyncio.CancelledError:
            return

    @property
    def integrity_check_pending_or_running(self) -> bool:
        """Return whether a verification task is queued or currently executing."""
        return self.integrity_check_running or bool(
            self._integrity_task is not None and not self._integrity_task.done()
        )

    @property
    def manual_verification_cooldown_active(self) -> bool:
        """Return whether a manual verification is currently rate-limited."""
        if self.manual_verification_cooldown_minutes <= 0:
            return False
        checked_at = self.integrity_result.checked_at
        if checked_at is None:
            return False
        return dt_util.utcnow() < checked_at + timedelta(
            minutes=self.manual_verification_cooldown_minutes
        )

    async def async_start_integrity_check(self, *, source: str = "manual") -> bool:
        """Start an integrity check of the latest monitored backup."""
        if self.integrity_check_pending_or_running:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_already_running",
            )
        latest_record = self.data.latest_monitored_backup_record
        if latest_record is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_no_backup",
            )
        if source == "manual" and self.manual_verification_cooldown_active:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_cooldown",
                translation_placeholders={
                    "minutes": str(self.manual_verification_cooldown_minutes)
                },
            )
        self._set_integrity_task(
            self.hass.async_create_task(
                self._async_run_integrity_check(latest_record, source=source),
                name=f"{DOMAIN}_{source}_integrity_check",
            )
        )
        return True

    async def _async_run_integrity_check(
        self,
        record: BackupRecord,
        *,
        source: str,
    ) -> None:
        """Run and persist one full integrity check without leaking task errors."""
        if self.integrity_check_running:
            return
        cancelled = False
        self.integrity_check_running = True
        _LOGGER.info(
            "Backup verification started: source=%s backup_reference=%s",
            source,
            record.backup_reference,
        )
        if self.data is not None:
            self.async_set_updated_data(
                replace(self.data, integrity_check_running=True)
            )
        try:
            result = await self.integrity_verifier.async_verify(
                record,
                database_check=self.database_integrity_check,
                max_download_gb=self.max_verification_size_gb,
                max_expanded_gb=self.max_expanded_size_gb,
                timeout_minutes=self.verification_timeout_minutes,
                database_timeout_minutes=self.database_timeout_minutes,
                repair_issues_enabled=self.repair_issues_enabled,
            )
            self.integrity_result = result
            self._update_integrity_retry_state(result)
            try:
                await self.integrity_verifier.store.async_save(result)
            except Exception as err:  # noqa: BLE001
                persist_retry = dt_util.utcnow() + _AUTOMATIC_RETRY_BASE
                if (
                    self._integrity_retry_not_before is None
                    or self._integrity_retry_not_before < persist_retry
                ):
                    self._integrity_retry_not_before = persist_retry
                _LOGGER.error(
                    "Unable to persist backup verification result: source=%s "
                    "error_type=%s backup_reference=%s",
                    source,
                    safe_error_type(err),
                    record.backup_reference,
                )
            _LOGGER.info(
                "Backup verification completed: source=%s status=%s "
                "duration_seconds=%s warnings=%s backup_reference=%s",
                source,
                result.status,
                result.duration_seconds,
                len(result.warnings),
                record.backup_reference,
            )
        except asyncio.CancelledError:
            cancelled = True
            _LOGGER.info(
                "Backup verification cancelled: source=%s backup_reference=%s",
                source,
                record.backup_reference,
            )
            raise
        except Exception as err:  # noqa: BLE001
            self._integrity_retry_not_before = dt_util.utcnow() + timedelta(minutes=30)
            result = BackupIntegrityResult(
                status=INTEGRITY_STATUS_INTERNAL_ERROR,
                checked_at=dt_util.utcnow(),
                backup_id=record.backup_id,
                backup_reference=record.backup_reference,
                backup_date=record.date,
                agent_id=None,
                sha256=None,
                verified_size=None,
                duration_seconds=None,
                archive_count=0,
                file_count=0,
                protected=None,
                database_status=INTEGRITY_DATABASE_NOT_CHECKED,
                warnings=(),
                error_code="internal_error",
                checksum_changed=False,
            )
            self.integrity_result = result
            self._update_integrity_retry_state(result)
            _LOGGER.error(
                "Backup verification failed internally: source=%s "
                "error_type=%s backup_reference=%s",
                source,
                safe_error_type(err),
                record.backup_reference,
            )
            try:
                await self.integrity_verifier.store.async_save(result)
            except Exception as save_err:  # noqa: BLE001
                _LOGGER.error(
                    "Unable to persist internal verification failure: error_type=%s",
                    safe_error_type(save_err),
                )
        finally:
            self.integrity_check_running = False
            self._integrity_task = release_current_task_reference(self._integrity_task)
            if not cancelled:
                try:
                    await self.async_request_refresh()
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning(
                        "Unable to refresh BackupCheckup after verification: "
                        "error_type=%s",
                        safe_error_type(err),
                    )

    def _normalize_backups(
        self, backups: Mapping[str, Any]
    ) -> tuple[BackupRecord, ...]:
        """Normalize Home Assistant backup models into stable local records."""
        records: list[BackupRecord] = []
        invalid_backup_count = 0
        invalid_agent_copy_count = 0
        seen_backup_ids: set[str] = set()

        backup_items = self._safe_mapping_items(backups)

        for _inventory_key, backup in backup_items:
            try:
                backup_id_raw = self._safe_getattr(backup, "backup_id", None)
                if not isinstance(backup_id_raw, str):
                    raise ValueError("invalid_backup_id")
                backup_id = backup_id_raw.strip()
                if not backup_id or len(backup_id) > 1024:
                    raise ValueError("invalid_backup_id")
                if backup_id in seen_backup_ids:
                    raise ValueError("duplicate_backup_id")

                backup_date = self._as_datetime(
                    self._safe_getattr(backup, "date", None)
                )
                if backup_date is None:
                    raise ValueError("invalid_backup_date")
                seen_backup_ids.add(backup_id)

                agents_raw = self._safe_getattr(backup, "agents", {}) or {}
                copies: list[BackupAgentRecord] = []
                if isinstance(agents_raw, Mapping):
                    agent_items = self._safe_mapping_items(agents_raw)
                    if agents_raw and not agent_items:
                        invalid_agent_copy_count += 1
                    for agent_id, details in agent_items:
                        copy = self._agent_copy(agent_id, details)
                        if copy is None:
                            invalid_agent_copy_count += 1
                            continue
                        copies.append(copy)
                elif isinstance(agents_raw, (list, tuple, set, frozenset)):
                    try:
                        for agent_id in agents_raw:
                            normalized_agent_id = self._safe_text(agent_id, maximum=512)
                            if normalized_agent_id is None:
                                invalid_agent_copy_count += 1
                                continue
                            copies.append(
                                BackupAgentRecord(
                                    normalized_agent_id,
                                    anonymous_agent_reference(
                                        self.config_entry.entry_id,
                                        normalized_agent_id,
                                    ),
                                    None,
                                    None,
                                )
                            )
                    except Exception:  # noqa: BLE001
                        invalid_agent_copy_count += 1
                else:
                    invalid_agent_copy_count += 1

                agent_copies = tuple(
                    sorted(
                        {copy.agent_id: copy for copy in copies}.values(),
                        key=lambda item: item.agent_id,
                    )
                )
                agents = tuple(copy.agent_id for copy in agent_copies)

                failed_agents = self._as_string_tuple(
                    self._safe_getattr(backup, "failed_agent_ids", None)
                    or self._safe_getattr(backup, "failed_agents", None)
                )
                failed_addons = self._as_string_tuple(
                    self._safe_getattr(backup, "failed_addons", None)
                    or self._safe_getattr(backup, "failed_addon_ids", None)
                )
                failed_folders = self._as_string_tuple(
                    self._safe_getattr(backup, "failed_folders", None)
                    or self._safe_getattr(backup, "failed_folder_ids", None)
                )
                known_sizes = [
                    copy.size for copy in agent_copies if copy.size is not None
                ]
                legacy_size = self._safe_getattr(backup, "size", None)
                size = (
                    max(known_sizes)
                    if known_sizes
                    else self._as_nonnegative_int(legacy_size)
                )
                copy_size_mismatch, copy_size_spread = self._copy_sizes_mismatch(
                    known_sizes
                )
                incomplete = bool(failed_agents or failed_addons or failed_folders)
                automatic = (
                    self._safe_getattr(backup, "with_automatic_settings", None) is True
                )
                extra_metadata = self._safe_getattr(backup, "extra_metadata", None)
                included_addons = self._addon_slugs(
                    self._safe_getattr(backup, "addons", None)
                )
                included_folders = self._as_string_tuple(
                    self._safe_getattr(backup, "folders", None)
                )
                database_included = self._as_bool(
                    self._safe_getattr(backup, "database_included", None)
                )
                homeassistant_included = self._as_bool(
                    self._safe_getattr(backup, "homeassistant_included", None)
                )
                purpose = classify_backup_purpose(
                    automatic=automatic,
                    extra_metadata=extra_metadata,
                )
                name = (
                    self._safe_text(
                        self._safe_getattr(backup, "name", ""),
                        maximum=512,
                        strip=False,
                    )
                    or ""
                )

                records.append(
                    BackupRecord(
                        backup_id=backup_id,
                        backup_reference=anonymous_backup_reference(
                            self.config_entry.entry_id, backup_id
                        ),
                        name=name,
                        date=backup_date,
                        automatic=automatic,
                        purpose=purpose,
                        included_addons=included_addons,
                        included_folders=included_folders,
                        scope_fingerprint=backup_scope_fingerprint(
                            entry_id=self.config_entry.entry_id,
                            homeassistant_included=homeassistant_included,
                            database_included=database_included,
                            addons=included_addons,
                            folders=included_folders,
                        ),
                        agents=agents,
                        agent_copies=agent_copies,
                        failed_agents=failed_agents,
                        failed_addons=failed_addons,
                        failed_folders=failed_folders,
                        database_included=database_included,
                        homeassistant_included=homeassistant_included,
                        size=size,
                        incomplete=incomplete,
                        copy_size_mismatch=copy_size_mismatch,
                        copy_size_spread_bytes=copy_size_spread,
                    )
                )
            except Exception as err:  # noqa: BLE001
                invalid_backup_count += 1
                _LOGGER.warning(
                    "Ignoring one invalid backup inventory record: error_type=%s",
                    safe_error_type(err),
                )

        records.sort(key=lambda item: item.date, reverse=True)
        self._invalid_backup_count = invalid_backup_count
        self._invalid_agent_copy_count = invalid_agent_copy_count
        return tuple(records)

    def _size_changes(
        self,
        latest_record: BackupRecord | None,
        records: tuple[BackupRecord, ...],
    ) -> tuple[float | None, float | None, int]:
        """Return comparable previous and baseline size changes."""
        if latest_record is None or latest_record.size is None:
            return None, None, 0

        comparable = list(comparable_size_backups(latest_record, records))
        previous = comparable[0] if comparable else None
        size_change_percent = None
        if previous is not None and previous.size:
            size_change_percent = round(
                ((latest_record.size - previous.size) / previous.size) * 100,
                1,
            )

        baseline_sizes = [item.size for item in comparable[:5] if item.size]
        baseline = median(baseline_sizes) if baseline_sizes else None
        baseline_change = (
            round(((latest_record.size - baseline) / baseline) * 100, 1)
            if baseline
            else None
        )
        return size_change_percent, baseline_change, len(comparable)

    def _is_size_suspicious(
        self,
        latest_record: BackupRecord | None,
        size_change_percent: float | None,
        baseline_change_percent: float | None,
        comparable_backup_count: int,
    ) -> bool:
        """Evaluate the configured backup-size rule."""
        if self.size_check_mode == SIZE_CHECK_OFF or latest_record is None:
            return False
        if latest_record.size is not None and latest_record.size <= 0:
            return True
        if self.size_check_mode == SIZE_CHECK_FIXED:
            return bool(
                latest_record.size is not None
                and self.minimum_backup_size_bytes > 0
                and latest_record.size < self.minimum_backup_size_bytes
            )
        if self.size_check_mode != SIZE_CHECK_AUTO:
            return False

        return automatic_size_drop_is_suspicious(
            maximum_drop_percent=self.maximum_size_drop_percent,
            previous_change_percent=size_change_percent,
            baseline_change_percent=baseline_change_percent,
            comparable_backup_count=comparable_backup_count,
        )

    def _build_agent_summaries(
        self,
        inventory_records: tuple[BackupRecord, ...],
        monitoring_records: tuple[BackupRecord, ...],
        agent_errors: dict[str, str],
        configured_agent_ids: set[str],
        agent_names: Mapping[str, str],
        now: datetime,
    ) -> tuple[BackupAgentSummary, ...]:
        """Build one health summary per detected backup storage agent."""
        all_agent_ids = sorted(
            {agent for item in inventory_records for agent in item.agents}
            | set(agent_errors)
            | configured_agent_ids
        )
        summaries: list[BackupAgentSummary] = []

        for agent_id in all_agent_ids:
            inventory_agent_records = [
                item for item in inventory_records if agent_id in item.agents
            ]
            agent_records = [
                item for item in monitoring_records if agent_id in item.agents
            ]
            newest = agent_records[0] if agent_records else None
            sizes = [
                copy.size
                for item in inventory_agent_records
                for copy in item.agent_copies
                if copy.agent_id == agent_id and copy.size is not None
            ]
            newest_size = next(
                (
                    copy.size
                    for copy in (newest.agent_copies if newest else ())
                    if copy.agent_id == agent_id
                ),
                None,
            )
            age = precise_age_days(now, newest.date if newest else None)
            stale = age is None or age > self.max_age_days
            error = agent_errors.get(agent_id)
            summaries.append(
                BackupAgentSummary(
                    agent_id=agent_id,
                    agent_reference=anonymous_agent_reference(
                        self.config_entry.entry_id, agent_id
                    ),
                    storage_name=agent_names.get(
                        agent_id,
                        (
                            "Backup storage "
                            f"{
                                anonymous_agent_reference(
                                    self.config_entry.entry_id, agent_id
                                )
                            }"
                        ),
                    ),
                    backup_count=len(agent_records),
                    inventory_backup_count=len(inventory_agent_records),
                    ignored_update_backup_count=(
                        len(inventory_agent_records) - len(agent_records)
                    ),
                    latest_backup=newest.date if newest else None,
                    latest_backup_age_days=age,
                    latest_backup_size=newest_size,
                    stored_bytes=sum(sizes) if sizes else None,
                    error=error,
                    stale=stale,
                    problem=bool(error or stale),
                )
            )

        return tuple(summaries)

    @staticmethod
    def _status(**flags: bool) -> str:
        """Return the highest-priority status from the active flags."""
        priority = (
            ("backup_integrity_failed", STATUS_BACKUP_INTEGRITY_FAILED),
            ("backup_checksum_changed", STATUS_BACKUP_CHECKSUM_CHANGED),
            ("backup_integrity_warning", STATUS_BACKUP_INTEGRITY_WARNING),
            ("no_backup", STATUS_NO_BACKUPS),
            ("manager_unavailable", STATUS_MANAGER_UNAVAILABLE),
            ("storage_error", STATUS_STORAGE_ERROR),
            ("latest_backup_incomplete", STATUS_BACKUP_INCOMPLETE),
            ("automatic_backup_failed", STATUS_AUTOMATIC_BACKUP_FAILED),
            ("automatic_backup_overdue", STATUS_AUTOMATIC_BACKUP_OVERDUE),
            ("backup_stale", STATUS_BACKUP_STALE),
            ("backup_not_redundant", STATUS_BACKUP_NOT_REDUNDANT),
            ("backup_size_suspicious", STATUS_BACKUP_SIZE_SUSPICIOUS),
            ("automatic_schedule_missing", STATUS_SCHEDULE_MISSING),
            ("automatic_schedule_overdue", STATUS_SCHEDULE_OVERDUE),
        )
        return next((status for key, status in priority if flags[key]), STATUS_OK)
