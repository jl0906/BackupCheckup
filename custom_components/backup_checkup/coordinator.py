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
    STATUS_BACKUP_INCOMPLETE,
    STATUS_BACKUP_INTEGRITY_FAILED,
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
    anonymous_backup_reference,
    classify_exception,
    safe_error_type,
)

_LOGGER = logging.getLogger(__name__)


class BackupCheckupCoordinator(DataUpdateCoordinator[BackupCheckupData]):
    """Fetch and evaluate the actual Home Assistant backup inventory."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        options = {**entry.data, **entry.options}

        self.entity_mode = str(options.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE))
        self.max_age_days = int(options.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS))
        self.minimum_backup_size_bytes = (
            int(
                options.get(
                    CONF_MINIMUM_BACKUP_SIZE_MB,
                    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
                )
            )
            * 1_000_000
        )
        self.maximum_size_drop_percent = int(
            options.get(
                CONF_MAXIMUM_SIZE_DROP_PERCENT,
                DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
            )
        )
        self.size_check_mode = str(
            options.get(CONF_SIZE_CHECK_MODE, DEFAULT_SIZE_CHECK_MODE)
        )
        self.minimum_redundant_locations = int(
            options.get(
                CONF_MINIMUM_REDUNDANT_LOCATIONS,
                DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
            )
        )
        self.repair_issues_enabled = bool(
            options.get(
                CONF_REPAIR_ISSUES_ENABLED,
                DEFAULT_REPAIR_ISSUES_ENABLED,
            )
        )
        self.analytics_window_days = int(
            options.get(
                CONF_ANALYTICS_WINDOW_DAYS,
                DEFAULT_ANALYTICS_WINDOW_DAYS,
            )
        )
        self.auto_verify_new_backups = bool(
            options.get(
                CONF_AUTO_VERIFY_NEW_BACKUPS,
                DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
            )
        )
        self.database_integrity_check = bool(
            options.get(
                CONF_DATABASE_INTEGRITY_CHECK,
                DEFAULT_DATABASE_INTEGRITY_CHECK,
            )
        )
        self.max_verification_size_gb = int(
            options.get(
                CONF_MAX_VERIFICATION_SIZE_GB,
                DEFAULT_MAX_VERIFICATION_SIZE_GB,
            )
        )
        self.max_expanded_size_gb = int(
            options.get(
                CONF_MAX_EXPANDED_SIZE_GB,
                DEFAULT_MAX_EXPANDED_SIZE_GB,
            )
        )
        self.verification_timeout_minutes = int(
            options.get(
                CONF_VERIFICATION_TIMEOUT_MINUTES,
                DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
            )
        )
        self.database_timeout_minutes = int(
            options.get(
                CONF_DATABASE_TIMEOUT_MINUTES,
                DEFAULT_DATABASE_TIMEOUT_MINUTES,
            )
        )
        self.manual_verification_cooldown_minutes = int(
            options.get(
                CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
                DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            )
        )
        self.expose_backup_metadata = bool(
            options.get(
                CONF_EXPOSE_BACKUP_METADATA,
                DEFAULT_EXPOSE_BACKUP_METADATA,
            )
        )
        self.notifications_enabled = bool(
            options.get(
                CONF_NOTIFICATIONS_ENABLED,
                DEFAULT_NOTIFICATIONS_ENABLED,
            )
        )
        notification_targets = options.get(
            CONF_NOTIFICATION_TARGETS,
            DEFAULT_NOTIFICATION_TARGETS,
        )
        if isinstance(notification_targets, str):
            notification_targets = [notification_targets]
        self.notification_targets = tuple(
            str(entity_id) for entity_id in notification_targets or []
        )
        self.notify_on_recovery = bool(
            options.get(
                CONF_NOTIFY_ON_RECOVERY,
                DEFAULT_NOTIFY_ON_RECOVERY,
            )
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
        update_minutes = int(
            options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            )
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
    def _as_nonnegative_int(value: Any) -> int | None:
        """Return a finite non-negative integer or None for invalid agent data."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        try:
            normalized = int(value)
        except (OverflowError, ValueError):
            return None
        return normalized if normalized >= 0 else None

    @staticmethod
    def _agent_copy(agent_id: Any, details: Any) -> BackupAgentRecord:
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
        return BackupAgentRecord(str(agent_id), size, protected)

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
            raise UpdateFailed(
                f"Unable to read Home Assistant backups ({error_code})"
            ) from None

        now = dt_util.utcnow()
        if not self._integrity_loaded:
            self.integrity_result = await self.integrity_verifier.store.async_load()
            self._integrity_loaded = True
        records = self._normalize_backups(backups)
        automatic_records = [item for item in records if item.automatic]
        manual_records = [item for item in records if not item.automatic]
        latest_record = records[0] if records else None
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

        size_change_percent, automatic_drop_percent = self._size_changes(
            latest_record,
            records,
        )
        backup_size_suspicious = self._is_size_suspicious(
            latest_record,
            size_change_percent,
            automatic_drop_percent,
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
        history_metrics = await self.history.async_observe(
            last_attempt=last_automatic_attempt,
            last_success=last_successful_automatic_event,
            now=now,
            window_days=self.analytics_window_days,
        )
        inventory_analytics = calculate_inventory_analytics(
            records,
            now=now,
            window_days=self.analytics_window_days,
        )

        no_backup = not records
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

        automatic_backup_failed = last_automatic_attempt is not None and (
            last_successful_automatic_event is None
            or last_automatic_attempt
            > last_successful_automatic_event + timedelta(seconds=60)
        )
        automatic_schedule_missing = next_automatic is None
        automatic_schedule_overdue = (
            next_automatic is not None and next_automatic < now - timedelta(hours=6)
        )
        manager_unavailable = manager_state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "none",
            "",
        }
        agent_errors = {
            str(agent_id): classify_exception(error)
            for agent_id, error in agent_errors_raw.items()
        }
        storage_error = bool(agent_errors)

        agent_summaries = self._build_agent_summaries(
            records,
            agent_errors,
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
            and self.integrity_result.status in {"corrupt", "unreadable"}
        )

        status = self._status(
            no_backup=no_backup,
            backup_integrity_failed=backup_integrity_failed,
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

        data = BackupCheckupData(
            checked_at=now,
            max_age_days=self.max_age_days,
            minimum_backup_size_bytes=self.minimum_backup_size_bytes,
            maximum_size_drop_percent=self.maximum_size_drop_percent,
            minimum_redundant_locations=self.minimum_redundant_locations,
            total_backups=len(records),
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
            latest_backup_result=latest_backup_result,
            latest_backup_locations=latest_locations,
            latest_backup_location_ids=latest_location_ids,
            last_automatic_attempt=last_automatic_attempt,
            last_successful_automatic_event=last_successful_automatic_event,
            next_automatic_backup=next_automatic,
            manager_state=manager_state,
            agent_errors=agent_errors,
            agent_summaries=agent_summaries,
            backups=records,
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
            automatic_success_rate=history_metrics.success_rate,
            automatic_attempts_observed=history_metrics.resolved_attempts,
            automatic_successes_observed=history_metrics.successful_attempts,
            automatic_failures_observed=history_metrics.failed_attempts,
            consecutive_automatic_failures=history_metrics.consecutive_failures,
            history_tracking_started_at=history_metrics.tracking_started_at,
            integrity=self.integrity_result,
            integrity_check_running=self.integrity_check_running,
            expose_backup_metadata=self.expose_backup_metadata,
        )

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

        if (
            self.auto_verify_new_backups
            and latest_record is not None
            and self.integrity_result.backup_id != latest_record.backup_id
            and not self.integrity_check_running
            and (self._integrity_task is None or self._integrity_task.done())
        ):
            self._integrity_task = self.hass.async_create_task(
                self._async_run_integrity_check(latest_record),
                name=f"{DOMAIN}_automatic_integrity_check",
            )
        return data

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
        """Start an integrity check of the latest backup."""
        if self.integrity_check_pending_or_running:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_already_running",
            )
        if not self.data.backups:
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
        self._integrity_task = self.hass.async_create_task(
            self._async_run_integrity_check(self.data.backups[0]),
            name=f"{DOMAIN}_{source}_integrity_check",
        )
        return True

    async def _async_run_integrity_check(self, record: BackupRecord) -> None:
        """Run and persist one full integrity check."""
        if self.integrity_check_running:
            return
        cancelled = False
        self.integrity_check_running = True
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
            await self.integrity_verifier.store.async_save(result)
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            self.integrity_check_running = False
            if not cancelled:
                await self.async_request_refresh()

    def _normalize_backups(
        self, backups: Mapping[str, Any]
    ) -> tuple[BackupRecord, ...]:
        """Normalize Home Assistant backup models into stable local records."""
        records: list[BackupRecord] = []

        for backup in backups.values():
            backup_date = self._as_datetime(getattr(backup, "date", None))
            if backup_date is None:
                _LOGGER.warning("Ignoring one backup because its date is invalid")
                continue

            agents_raw = getattr(backup, "agents", {}) or {}
            if isinstance(agents_raw, Mapping):
                agent_copies = tuple(
                    sorted(
                        (
                            self._agent_copy(agent_id, details)
                            for agent_id, details in agents_raw.items()
                        ),
                        key=lambda item: item.agent_id,
                    )
                )
            else:
                agent_copies = tuple(
                    BackupAgentRecord(str(agent_id), None, None)
                    for agent_id in sorted(agents_raw, key=str)
                )
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

            records.append(
                BackupRecord(
                    backup_id=str(getattr(backup, "backup_id", "")),
                    backup_reference=anonymous_backup_reference(
                        self.config_entry.entry_id,
                        str(getattr(backup, "backup_id", "")),
                    ),
                    name=str(getattr(backup, "name", "")),
                    date=backup_date,
                    automatic=(
                        getattr(backup, "with_automatic_settings", None) is True
                    ),
                    agents=agents,
                    agent_copies=agent_copies,
                    failed_agents=failed_agents,
                    failed_addons=failed_addons,
                    failed_folders=failed_folders,
                    database_included=self._as_bool(
                        getattr(backup, "database_included", None)
                    ),
                    homeassistant_included=self._as_bool(
                        getattr(backup, "homeassistant_included", None)
                    ),
                    size=size,
                    incomplete=incomplete,
                )
            )

        records.sort(key=lambda item: item.date, reverse=True)
        return tuple(records)

    def _size_changes(
        self,
        latest_record: BackupRecord | None,
        records: tuple[BackupRecord, ...],
    ) -> tuple[float | None, float | None]:
        """Return previous-backup and automatic-baseline size changes."""
        if latest_record is None or latest_record.size is None:
            return None, None

        comparable = [
            item
            for item in records[1:]
            if item.automatic == latest_record.automatic
            and item.size is not None
            and item.size > 0
        ]
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
        return size_change_percent, baseline_change

    def _is_size_suspicious(
        self,
        latest_record: BackupRecord | None,
        size_change_percent: float | None,
        baseline_change_percent: float | None,
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

        effective_drop = (
            baseline_change_percent
            if baseline_change_percent is not None
            else size_change_percent
        )
        return bool(
            self.maximum_size_drop_percent > 0
            and effective_drop is not None
            and effective_drop <= -self.maximum_size_drop_percent
        )

    def _build_agent_summaries(
        self,
        records: tuple[BackupRecord, ...],
        agent_errors: dict[str, str],
        now: datetime,
    ) -> tuple[BackupAgentSummary, ...]:
        """Build one health summary per detected backup storage agent."""
        all_agent_ids = sorted(
            {agent for item in records for agent in item.agents} | set(agent_errors)
        )
        summaries: list[BackupAgentSummary] = []

        for agent_id in all_agent_ids:
            agent_records = [item for item in records if agent_id in item.agents]
            newest = agent_records[0] if agent_records else None
            sizes = [
                copy.size
                for item in agent_records
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
                    backup_count=len(agent_records),
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
            ("no_backup", STATUS_NO_BACKUPS),
            ("backup_integrity_failed", STATUS_BACKUP_INTEGRITY_FAILED),
            ("manager_unavailable", STATUS_MANAGER_UNAVAILABLE),
            ("automatic_schedule_missing", STATUS_SCHEDULE_MISSING),
            ("storage_error", STATUS_STORAGE_ERROR),
            ("latest_backup_incomplete", STATUS_BACKUP_INCOMPLETE),
            ("backup_size_suspicious", STATUS_BACKUP_SIZE_SUSPICIOUS),
            ("backup_not_redundant", STATUS_BACKUP_NOT_REDUNDANT),
            ("automatic_backup_failed", STATUS_AUTOMATIC_BACKUP_FAILED),
            ("automatic_backup_overdue", STATUS_AUTOMATIC_BACKUP_OVERDUE),
            ("backup_stale", STATUS_BACKUP_STALE),
            ("automatic_schedule_overdue", STATUS_SCHEDULE_OVERDUE),
        )
        return next((status for key, status in priority if flags[key]), STATUS_OK)
