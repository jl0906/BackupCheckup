"""Data coordinator for BackupCheckup."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from math import floor
from statistics import median
from typing import Any

from homeassistant.components.backup import async_get_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
    CORE_AUTOMATIC_BACKUP_EVENT,
    CORE_BACKUP_MANAGER_STATE,
    CORE_LAST_AUTOMATIC_ATTEMPT,
    CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP,
    CORE_NEXT_AUTOMATIC_BACKUP,
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
    INTEGRITY_STATUS_INTERNAL_ERROR,
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
        options = {**entry.data, **entry.options}

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
        self._invalid_backup_count = 0
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
    def _age_days(now: datetime, value: datetime | None) -> float | None:
        """Return the precise age in days."""
        if value is None:
            return None
        return max(0.0, (now - value).total_seconds() / 86400)

    @staticmethod
    def _completed_days(value: float | None) -> int | None:
        """Return only fully completed days from a precise age value."""
        if value is None:
            return None
        return floor(value)

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
            value = value.keys()
        if isinstance(value, str):
            return (value,)
        try:
            return tuple(sorted(str(item) for item in value))
        except TypeError:
            return ()

    @staticmethod
    def _addon_slugs(value: Any) -> tuple[str, ...]:
        """Normalize Home Assistant add-on metadata to sorted slugs."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            value = value.values()
        if isinstance(value, str):
            return (value,)
        slugs: set[str] = set()
        try:
            for addon in value:
                slug = getattr(addon, "slug", None)
                if slug is None and isinstance(addon, Mapping):
                    slug = addon.get("slug")
                if isinstance(slug, str) and slug:
                    slugs.add(slug)
        except TypeError:
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

    def _agent_copy(self, agent_id: Any, details: Any) -> BackupAgentRecord:
        """Normalize one backup-agent copy record across HA model versions."""
        size_raw = getattr(details, "size", None)
        if size_raw is None and isinstance(details, Mapping):
            size_raw = details.get("size")
        size = BackupCheckupCoordinator._as_nonnegative_int(size_raw)

        protected_raw = getattr(details, "protected", None)
        if protected_raw is None:
            protected_raw = getattr(details, "is_protected", None)
        if protected_raw is None and isinstance(details, Mapping):
            protected_raw = details.get("protected", details.get("is_protected"))
        protected = protected_raw if isinstance(protected_raw, bool) else None
        normalized_agent_id = str(agent_id)
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

        latest_age = self._age_days(now, latest_backup)
        automatic_age_precise = self._age_days(now, latest_automatic)
        automatic_age = self._completed_days(automatic_age_precise)
        manual_age = self._age_days(now, latest_manual)

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

        last_automatic_attempt = self._entity_datetime(CORE_LAST_AUTOMATIC_ATTEMPT)
        last_successful_automatic_event = self._entity_datetime(
            CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP
        )
        next_automatic = self._entity_datetime(CORE_NEXT_AUTOMATIC_BACKUP)
        manager_state = self._entity_state(CORE_BACKUP_MANAGER_STATE)
        automatic_event = self.hass.states.get(CORE_AUTOMATIC_BACKUP_EVENT)
        automatic_event_type = (
            str(automatic_event.attributes.get("event_type", "")).lower()
            if automatic_event is not None
            else ""
        )
        automatic_backup_in_progress = automatic_event_type in {
            "in_progress",
            "in progress",
        } or manager_state in {
            "create_backup",
            "creating_a_backup",
            "creating a backup",
            "receive_backup",
            "receiving_a_backup",
            "receiving a backup",
        }
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
        backup_stale = latest_age is not None and latest_age > self.max_age_days
        manual_covers_automatic = latest_manual is not None and (
            latest_automatic is None or latest_manual > latest_automatic
        )
        if latest_automatic is None:
            automatic_backup_overdue = (
                latest_manual is None
                or manual_age is None
                or manual_age > self.max_age_days
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
        agent_errors = {
            normalized_agent_id: classify_exception(error)
            for agent_id, error in agent_errors_raw.items()
            if (normalized_agent_id := str(agent_id).strip())
            and len(normalized_agent_id) <= 512
        }
        storage_error = bool(agent_errors)

        manager_agents = getattr(manager, "backup_agents", {})
        configured_agent_ids = (
            {str(agent_id) for agent_id in manager_agents}
            if isinstance(manager_agents, Mapping)
            else set()
        )
        agent_names = (
            {
                str(agent_id): safe_display_name(
                    getattr(agent, "name", None),
                    fallback=(
                        "Backup storage "
                        f"{
                            anonymous_agent_reference(
                                self.config_entry.entry_id, str(agent_id)
                            )
                        }"
                    ),
                )
                for agent_id, agent in manager_agents.items()
            }
            if isinstance(manager_agents, Mapping)
            else {}
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
            and self.integrity_result.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS
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
            automatic_backup_age_days=automatic_age,
            automatic_backup_age_days_precise=automatic_age_precise,
            manual_backup_age_days=manual_age,
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
        )

        await self._async_process_notifications(data)

        if (
            self.auto_verify_new_backups
            and latest_record is not None
            and (
                self.integrity_result.backup_id != latest_record.backup_id
                or self.integrity_result.status == INTEGRITY_STATUS_INTERNAL_ERROR
            )
            and not self.integrity_check_running
            and (self._integrity_task is None or self._integrity_task.done())
            and (
                self._integrity_retry_not_before is None
                or now >= self._integrity_retry_not_before
            )
        ):
            self._set_integrity_task(
                self.hass.async_create_task(
                    self._async_run_integrity_check(latest_record, source="automatic"),
                    name=f"{DOMAIN}_automatic_integrity_check",
                )
            )
        return data

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
        active = tuple(
            dict.fromkeys(("manager_unavailable", *self.data.active_problems))
        )
        deductions = dict(self.data.health_score_deductions)
        deductions["manager_unavailable"] = max(
            deductions.get("manager_unavailable", 0), 50
        )
        return replace(
            self.data,
            checked_at=now,
            manager_state=STATE_UNAVAILABLE,
            manager_unavailable=True,
            problem=True,
            status=STATUS_MANAGER_UNAVAILABLE,
            recommendation=RECOMMENDATION_CHECK_BACKUP_SYSTEM,
            problem_count=len(active),
            active_problems=active,
            health_score=min(self.data.health_score, 50),
            health_rating="critical",
            health_score_deductions=deductions,
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
            try:
                await self.integrity_verifier.store.async_save(result)
            except Exception as err:  # noqa: BLE001
                self._integrity_retry_not_before = dt_util.utcnow() + timedelta(
                    minutes=30
                )
                _LOGGER.error(
                    "Unable to persist backup verification result: source=%s "
                    "error_type=%s backup_reference=%s",
                    source,
                    safe_error_type(err),
                    record.backup_reference,
                )
            else:
                self._integrity_retry_not_before = None
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
        seen_backup_ids: set[str] = set()

        for backup in backups.values():
            backup_id_raw = getattr(backup, "backup_id", None)
            if (
                not isinstance(backup_id_raw, str)
                or not backup_id_raw.strip()
                or len(backup_id_raw) > 1024
            ):
                invalid_backup_count += 1
                _LOGGER.warning("Ignoring one backup because its ID is invalid")
                continue
            backup_id = backup_id_raw.strip()
            if backup_id in seen_backup_ids:
                invalid_backup_count += 1
                _LOGGER.warning("Ignoring one backup because its ID is duplicated")
                continue
            backup_date = self._as_datetime(getattr(backup, "date", None))
            if backup_date is None:
                invalid_backup_count += 1
                _LOGGER.warning("Ignoring one backup because its date is invalid")
                continue
            seen_backup_ids.add(backup_id)

            agents_raw = getattr(backup, "agents", {}) or {}
            if isinstance(agents_raw, Mapping):
                normalized_agent_items = [
                    (str(agent_id).strip(), details)
                    for agent_id, details in agents_raw.items()
                    if str(agent_id).strip() and len(str(agent_id)) <= 512
                ]
                agent_copies = tuple(
                    sorted(
                        (
                            self._agent_copy(agent_id, details)
                            for agent_id, details in normalized_agent_items
                        ),
                        key=lambda item: item.agent_id,
                    )
                )
            elif isinstance(agents_raw, (list, tuple, set, frozenset)):
                normalized_agent_ids = sorted(
                    {
                        str(agent_id).strip()
                        for agent_id in agents_raw
                        if str(agent_id).strip() and len(str(agent_id)) <= 512
                    }
                )
                agent_copies = tuple(
                    BackupAgentRecord(
                        agent_id,
                        anonymous_agent_reference(self.config_entry.entry_id, agent_id),
                        None,
                        None,
                    )
                    for agent_id in normalized_agent_ids
                )
            else:
                invalid_backup_count += 1
                agent_copies = ()
            agents = tuple(copy.agent_id for copy in agent_copies)

            failed_agents = self._as_string_tuple(
                getattr(backup, "failed_agent_ids", None)
                or getattr(backup, "failed_agents", None)
            )
            failed_addons = self._as_string_tuple(
                getattr(backup, "failed_addons", None)
                or getattr(backup, "failed_addon_ids", None)
            )
            failed_folders = self._as_string_tuple(
                getattr(backup, "failed_folders", None)
                or getattr(backup, "failed_folder_ids", None)
            )
            known_sizes = [copy.size for copy in agent_copies if copy.size is not None]
            legacy_size = getattr(backup, "size", None)
            size = (
                max(known_sizes)
                if known_sizes
                else (self._as_nonnegative_int(legacy_size))
            )
            incomplete = bool(failed_agents or failed_addons or failed_folders)
            automatic = getattr(backup, "with_automatic_settings", None) is True
            extra_metadata = getattr(backup, "extra_metadata", None)
            included_addons = self._addon_slugs(getattr(backup, "addons", None))
            included_folders = self._as_string_tuple(getattr(backup, "folders", None))
            database_included = self._as_bool(
                getattr(backup, "database_included", None)
            )
            homeassistant_included = self._as_bool(
                getattr(backup, "homeassistant_included", None)
            )
            purpose = classify_backup_purpose(
                automatic=automatic,
                extra_metadata=extra_metadata,
            )

            records.append(
                BackupRecord(
                    backup_id=backup_id,
                    backup_reference=anonymous_backup_reference(
                        self.config_entry.entry_id,
                        backup_id,
                    ),
                    name=str(getattr(backup, "name", ""))[:512],
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
                )
            )

        records.sort(key=lambda item: item.date, reverse=True)
        self._invalid_backup_count = invalid_backup_count
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
            age = self._age_days(now, newest.date if newest else None)
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
