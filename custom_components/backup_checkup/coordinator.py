"""Data coordinator for BackupCheckup."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any, cast

from homeassistant.components.backup import async_get_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .activity import (
    ACTIVITY_OUTCOME_CANCELLED,
    ACTIVITY_OUTCOME_CHANGED,
    ACTIVITY_OUTCOME_COMPLETED,
    ACTIVITY_OUTCOME_FAILED,
    ACTIVITY_OUTCOME_SKIPPED,
    ACTIVITY_OUTCOME_STARTED,
    BackupCheckupActivityLog,
)
from .adaptive_policy import AdaptiveRecoveryPolicy, resolve_adaptive_policy
from .age import completed_age_days, precise_age_days
from .analytics import (
    HealthScore,
    calculate_health_score,
    calculate_inventory_analytics,
)
from .backup_normalizer import BackupRecordNormalizer, ThirdPartyBoundary
from .classification import (
    automatic_backup_failed as evaluate_automatic_backup_failed,
)
from .classification import (
    automatic_size_drop_is_suspicious,
    comparable_size_backups,
    monitoring_backups,
)
from .configuration import BackupCheckupSettings
from .const import (
    BACKUP_RESULT_COMPLETE,
    BACKUP_RESULT_PARTIAL,
    BACKUP_RESULT_UNKNOWN,
    CONF_RUNTIME_RUNNER,
    DOMAIN,
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_ABORTED,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_PASSWORD_REQUIRED,
    INTEGRITY_STATUS_UNREADABLE,
    INTEGRITY_STATUS_VALID,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
    NOTIFICATION_CONFIRM_RECHECK_SECONDS,
    RUNNER_CHECK_SOURCE_INTERVAL,
    RUNNER_CHECK_SOURCE_PRE_RUN,
    SIZE_CHECK_AUTO,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OFF,
    STARTUP_SETTLE_SECONDS,
    progress_signal,
    runner_signal,
)
from .history import BackupCheckupHistory
from .integrity import BackupIntegrityVerifier
from .models import (
    BackupAgentSummary,
    BackupCheckupData,
    BackupIntegrityResult,
    BackupRecord,
)
from .native_backup import (
    NativeBackupState,
    native_backup_activity_entity_ids,
    native_backup_manager_busy,
    native_backup_manager_state_busy,
    read_native_backup_state,
)
from .notifications import BackupCheckupNotificationManager
from .problem_state import evaluate_problem_state
from .progress import (
    JOB_ABORTED,
    JOB_FAILED,
    JOB_IDLE,
    JOB_INCONCLUSIVE,
    JOB_NOT_STARTED,
    JOB_PASSED,
    JOB_RUNNING,
    JOB_RUNTIME_TEST,
    JOB_VERIFICATION,
    JobProgress,
    ProgressReporter,
    runtime_status_for_error,
)
from .recovery import (
    RecoveryAssessmentContext,
    RecoveryReadiness,
    assess_recovery_readiness,
)
from .recovery_preparedness import (
    RecoveryPreparednessStore,
    detect_recovery_dependencies,
)
from .recovery_restore import RecoveryRestoreTestStore
from .recovery_runtime import (
    RUNTIME_STATUS_NOT_STARTED,
    RunnerHealth,
    RuntimeRunnerClient,
    RuntimeRunnerConnection,
    RuntimeRunnerError,
    RuntimeTestSnapshot,
    RuntimeTestStore,
)
from .recovery_simulation import simulate_restore
from .repairs import async_set_runner_issues
from .security import (
    anonymous_agent_reference,
    classify_exception,
    resolve_staging_root,
    safe_display_name,
    safe_error_type,
)
from .task_control import release_current_task_reference

_LOGGER = logging.getLogger(__name__)

_AUTOMATIC_RETRY_BASE = timedelta(minutes=30)
_AUTOMATIC_RETRY_MAX = timedelta(hours=6)
_AUTOMATIC_RETRY_LIMIT = 3
_MAX_AGENT_ID_LENGTH = 512
_CREDENTIAL_MARKER_CONTEXT = "backup-checkup-credential-marker"
_SIZE_BASELINE_RECORDS = 5
_RUNNER_HEALTH_WARNING_THRESHOLD = 3

#: While a runtime test runs, the previous proof is no longer valid evidence.
_RUNNING_RUNTIME_EVIDENCE = {
    "passed": None,
    "ready": False,
    "isolation_verified": False,
    "home_assistant_version": None,
    "checked_at": None,
    "error_code": None,
    "backup_sha256": None,
    "runner_id": None,
    "duration_seconds": None,
}

#: Activity actions that keep the established translation keys for the two
#: measured verification steps.
_VERIFICATION_PROGRESS_ACTIONS = {
    "download": "backup_download",
    "archive_scan": "backup_extract",
}

_RUNTIME_ACTIVITY_OUTCOMES = {
    JOB_PASSED: ACTIVITY_OUTCOME_COMPLETED,
    JOB_NOT_STARTED: ACTIVITY_OUTCOME_SKIPPED,
    JOB_ABORTED: ACTIVITY_OUTCOME_CANCELLED,
}

_VERIFICATION_JOB_STATUS = {
    INTEGRITY_STATUS_VALID: JOB_PASSED,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS: JOB_PASSED,
    INTEGRITY_STATUS_ABORTED: JOB_ABORTED,
    INTEGRITY_STATUS_INTERNAL_ERROR: JOB_INCONCLUSIVE,
}


def _verification_job_status(status: str) -> str:
    """Map one integrity status to the shared job status."""
    return _VERIFICATION_JOB_STATUS.get(status, JOB_FAILED)


@dataclass(frozen=True, slots=True)
class SizeChangeAnalysis:
    """Named size-comparison result for the latest comparable backup."""

    previous_percent: float | None
    baseline_percent: float | None
    comparable_count: int


@dataclass(frozen=True, slots=True)
class FreshnessState:
    """Calculated age and freshness state for global backup categories."""

    latest_precise: float | None
    latest_days: int | None
    automatic_precise: float | None
    automatic_days: int | None
    manual_precise: float | None
    manual_days: int | None
    backup_stale: bool
    automatic_backup_overdue: bool


@dataclass(frozen=True, slots=True)
class IntegrityFlags:
    """Integrity-derived problem flags for the latest monitored backup."""

    failed: bool
    checksum_changed: bool
    warning: bool


@dataclass(frozen=True, slots=True)
class StorageState:
    """Normalized storage errors, names, summaries, and problem flags."""

    public_errors: dict[str, str]
    summaries: tuple[BackupAgentSummary, ...]
    storage_error: bool
    required_location_missing: bool


@dataclass(frozen=True, slots=True)
class InventoryState:
    """Partitioned normalized inventory and its latest category records."""

    records: tuple[BackupRecord, ...]
    monitored: tuple[BackupRecord, ...]
    automatic: tuple[BackupRecord, ...]
    manual: tuple[BackupRecord, ...]
    latest: BackupRecord | None
    latest_automatic: BackupRecord | None
    latest_manual: BackupRecord | None
    ignored_update_count: int


def _assessment_fields(
    health: HealthScore,
    recovery: RecoveryReadiness,
    *,
    runtime_test: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return shared health and recovery fields for coordinator snapshots.

    ``runtime_test`` replaces the assessed runtime result with the merged live
    view; passing it as a separate keyword would duplicate the argument.
    """
    return {
        "health_score": health.score,
        "health_rating": health.rating,
        "health_score_deductions": health.deductions,
        "health_score_components": health.component_deductions,
        "health_score_raw_deductions": health.raw_deductions,
        "health_score_suppressed_deductions": health.suppressed_deductions,
        "recovery_readiness_score": recovery.score,
        "recovery_status": recovery.status,
        "recovery_recommendation": recovery.recommendation,
        "recovery_deductions": recovery.deductions,
        "recovery_checks": recovery.checks,
        "recovery_content_inventory": recovery.content_inventory,
        "recovery_content_comparison": recovery.content_comparison,
        "recovery_storage_resilience": recovery.storage_resilience,
        "recovery_preparedness": recovery.preparedness,
        "recovery_restore_simulation": recovery.restore_simulation,
        "recovery_runtime_test": (
            recovery.runtime_test if runtime_test is None else runtime_test
        ),
        "recovery_restore_test": recovery.restore_test,
        "recovery_plan": recovery.recovery_plan,
    }


class BackupCheckupCoordinator(DataUpdateCoordinator[BackupCheckupData]):
    """Fetch and evaluate the actual Home Assistant backup inventory."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from one canonical settings object."""
        self.config_entry = entry
        self.settings = BackupCheckupSettings.from_sources(entry.data, entry.options)
        self._apply_settings_compatibility_attributes()
        runner_data = entry.options.get(CONF_RUNTIME_RUNNER) or entry.data.get(
            CONF_RUNTIME_RUNNER
        )
        self.runtime_runner_connection = RuntimeRunnerConnection.from_mapping(
            runner_data
        )
        self.recovery_policy = self._resolve_recovery_policy()

        self.activity = BackupCheckupActivityLog(
            hass,
            entry.entry_id,
            enabled=self.activity_logging_enabled,
            persistent=self.settings.activity_log_persistence,
            retention_days=self.settings.activity_log_retention_days,
        )
        self.history = BackupCheckupHistory(hass, entry.entry_id)
        self.integrity_verifier = BackupIntegrityVerifier(
            hass, entry.entry_id, activity=self.activity
        )
        self.notification_manager = BackupCheckupNotificationManager(
            hass, entry.entry_id, activity=self.activity
        )
        self.recovery_preparedness = RecoveryPreparednessStore(hass, entry.entry_id)
        self.recovery_restore_tests = RecoveryRestoreTestStore(hass, entry.entry_id)
        self.runtime_tests = RuntimeTestStore(hass, entry.entry_id)
        self.verification_progress = JobProgress.create(JOB_VERIFICATION)
        self.runtime_progress = JobProgress.create(JOB_RUNTIME_TEST)
        self._verification_reporter = ProgressReporter(
            self.verification_progress,
            lambda: self._publish_progress(JOB_VERIFICATION),
            loop=hass.loop,
            activity=lambda key, outcome, details: self._record_step_activity(
                JOB_VERIFICATION, key, outcome, details
            ),
        )
        self._runtime_reporter = ProgressReporter(
            self.runtime_progress,
            lambda: self._publish_progress(JOB_RUNTIME_TEST),
            loop=hass.loop,
            activity=lambda key, outcome, details: self._record_step_activity(
                JOB_RUNTIME_TEST, key, outcome, details
            ),
        )
        self._progress_record: BackupRecord | None = None
        self._runner_health = (
            # A configured runner starts as "configured but not checked yet",
            # never as "not configured".
            RunnerHealth(configured=True)
            if self.runtime_runner_connection is not None
            else RunnerHealth.not_configured()
        )
        self._runner_health_lock = asyncio.Lock()
        self._runner_health_failures = 0
        self._runner_health_unsubscribe: Callable[[], None] | None = None
        self._normalizer = BackupRecordNormalizer(entry.entry_id)

        self.integrity_result = BackupIntegrityResult.not_checked()
        self.integrity_check_running = False
        self._integrity_state_loaded = False
        self._integrity_task: asyncio.Task[None] | None = None
        self._integrity_retry_not_before: datetime | None = None
        self._integrity_retry_key: tuple[str, str] | None = None
        self._integrity_retry_attempts = 0
        self._backup_password_marker: str | None = None
        self._backup_password_marker_initialized = False
        self._last_manual_verification_at: datetime | None = None
        self._invalid_backup_count = 0
        self._invalid_agent_copy_count = 0
        self._last_inventory_success_at: datetime | None = None
        self._inventory_error_count = 0
        self._manager_backup_active = False
        self._manager_state_seen = STATE_UNKNOWN
        self._adaptive_refresh_task: asyncio.Task[None] | None = None
        self._adaptive_refresh_pending = False
        self._adaptive_unsubscribers: list[Callable[[], None]] = []
        self._adaptive_manager_entity_id: str | None = None
        # Backup agents of other integrations are registered while Home
        # Assistant starts, so the first snapshots of a restart report
        # problems that do not exist. A setup in a running instance
        # (installation, reload, options change) needs no hold at all.
        self._startup_settled = hass.state is CoreState.running
        self._startup_grace_logged = False
        self._started_unsubscribe: Callable[[], None] | None = None
        self._settle_unsubscribe: Callable[[], None] | None = None
        self._confirmation_unsubscribe: Callable[[], None] | None = None

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=self.settings.update_interval_minutes),
        )
        self._async_arm_startup_settle()

    @property
    def startup_settled(self) -> bool:
        """Return whether the Home Assistant start phase is over."""
        return self._startup_settled

    @callback
    def async_mark_startup_settled(self) -> None:
        """Release the hold on notifications and health repair issues."""
        self._startup_settled = True

    @callback
    def _async_arm_startup_settle(self) -> None:
        """Wait for the started event plus the settle window when starting."""
        if self._startup_settled:
            return
        self._started_unsubscribe = async_at_started(
            self.hass, self._async_home_assistant_started
        )

    @callback
    def _async_home_assistant_started(self, _hass: HomeAssistant) -> None:
        """Give late storage agents the settle window before reporting."""
        self._started_unsubscribe = None
        self._settle_unsubscribe = async_call_later(
            self.hass, STARTUP_SETTLE_SECONDS, self._async_startup_settled
        )

    async def _async_startup_settled(self, _now: datetime) -> None:
        """Evaluate the first snapshot that is allowed to report problems."""
        self._settle_unsubscribe = None
        self.async_mark_startup_settled()
        await self.async_request_refresh()

    @callback
    def _async_cancel_startup_settle(self) -> None:
        """Make sure an unload during the hold cannot refresh afterwards."""
        if self._started_unsubscribe is not None:
            self._started_unsubscribe()
            self._started_unsubscribe = None
        if self._settle_unsubscribe is not None:
            self._settle_unsubscribe()
            self._settle_unsubscribe = None

    @callback
    def _async_schedule_notification_confirmation(self) -> None:
        """Schedule the one refresh that confirms a newly seen problem.

        The base interval can be up to 60 minutes, so waiting for the next
        regular refresh would delay every problem message. Only one timer is
        armed at a time; a pending problem that is still present when it fires
        reschedules it from the refresh it triggered.
        """
        if self._confirmation_unsubscribe is not None:
            return
        self._confirmation_unsubscribe = async_call_later(
            self.hass,
            NOTIFICATION_CONFIRM_RECHECK_SECONDS,
            self._async_confirm_notifications,
        )

    async def _async_confirm_notifications(self, _now: datetime) -> None:
        """Re-evaluate the snapshot once the confirmation window is over."""
        self._confirmation_unsubscribe = None
        await self.async_request_refresh()

    @callback
    def _async_cancel_notification_confirmation(self) -> None:
        """Drop a pending confirmation refresh on shutdown."""
        if self._confirmation_unsubscribe is not None:
            self._confirmation_unsubscribe()
            self._confirmation_unsubscribe = None

    def _resolve_recovery_policy(self) -> AdaptiveRecoveryPolicy:
        """Resolve adaptive policy against the current runner availability."""
        return resolve_adaptive_policy(
            runtime_profile=self.settings.runtime.profile,
            update_interval_minutes=self.settings.runtime.update_interval_minutes,
            auto_verify_new_backups=self.settings.verification.auto_verify_new_backups,
            database_integrity_check=(
                self.settings.verification.database_integrity_check
            ),
            ephemeral_runner_available=self.runtime_runner_connection is not None,
        )

    def attach_runtime_runner(self, connection: RuntimeRunnerConnection) -> None:
        """Attach a runner discovered after the coordinator was initialized."""
        self.runtime_runner_connection = connection
        self.recovery_policy = self._resolve_recovery_policy()
        self._runner_health_failures = 0
        # The interval check is skipped while no runner exists, so it has to be
        # started once one appears.
        self.async_start_runner_health_monitor()

    @property
    def staging_root(self) -> Path:
        """Return the directory that receives private verification copies."""
        return resolve_staging_root(
            self.hass.config.config_dir,
            self.settings.verification_staging_directory,
        )

    def _backup_manager_busy(self) -> tuple[bool, str]:
        """Return whether the native backup manager is busy, and its state.

        The state is recorded with a skipped verification so the activity log
        shows which manager state caused it.
        """
        try:
            manager = async_get_manager(self.hass)
        except Exception:  # noqa: BLE001 - manager lookup boundary
            return self._manager_backup_active, self._manager_state_seen
        return native_backup_manager_busy(self.hass, manager)

    def _apply_settings_compatibility_attributes(self) -> None:
        """Expose stable attributes used by entities and existing tests."""
        settings = self.settings
        self.entity_mode = settings.entity_mode
        self.activity_logging_enabled = settings.activity_logging_enabled
        self.activity_log_persistence = settings.activity_log_persistence
        self.activity_log_retention_days = settings.activity_log_retention_days
        self.max_age_days = settings.max_age_days
        self.minimum_backup_size_bytes = settings.minimum_backup_size_mb * 1_000_000
        self.maximum_size_drop_percent = settings.maximum_size_drop_percent
        self.size_check_mode = settings.size_check_mode
        self.minimum_redundant_locations = settings.minimum_redundant_locations
        self.repair_issues_enabled = settings.repair_issues_enabled
        self.analytics_window_days = settings.analytics_window_days
        self.auto_verify_new_backups = settings.auto_verify_new_backups
        self.database_integrity_check = settings.database_integrity_check
        self.max_verification_size_gb = settings.max_verification_size_gb
        self.max_expanded_size_gb = settings.max_expanded_size_gb
        self.verification_timeout_minutes = settings.verification_timeout_minutes
        self.database_timeout_minutes = settings.database_timeout_minutes
        self.manual_verification_cooldown_minutes = (
            settings.manual_verification_cooldown_minutes
        )
        self.runner_maximum_archive_gb = settings.runner_maximum_archive_gb
        self.runner_maximum_expanded_gb = settings.runner_maximum_expanded_gb
        self.runner_timeout_minutes = settings.runner_timeout_minutes
        self.runner_health_interval_minutes = settings.runner_health_interval_minutes
        self.expose_backup_metadata = settings.expose_backup_metadata
        self.notifications_enabled = settings.notifications_enabled
        self.notification_targets = settings.notification_targets
        self.notify_on_recovery = settings.notify_on_recovery
        self.runtime_profile = settings.runtime_profile
        self.monitoring_policy = settings.monitoring_policy
        self.verification_policy = settings.verification_policy
        self.adaptive_polling = settings.adaptive_polling
        self.active_update_interval_minutes = settings.active_update_interval_minutes
        self.error_backoff_interval_minutes = settings.error_backoff_interval_minutes
        self.adaptive_error_threshold = settings.adaptive_error_threshold

    def _record_activity(
        self,
        action: str,
        outcome: str,
        *,
        level: int = logging.INFO,
        activity_visible: bool = True,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Record activity when the runtime journal is available."""
        activity = getattr(self, "activity", None)
        if isinstance(activity, BackupCheckupActivityLog):
            activity.record(
                action,
                outcome,
                level=level,
                activity_visible=activity_visible,
                details=details,
            )

    def async_start_adaptive_polling(self) -> None:
        """Subscribe to native backup state changes when adaptive polling is enabled."""
        if not self.adaptive_polling or self._adaptive_unsubscribers:
            return
        entity_ids = native_backup_activity_entity_ids(self.hass)
        self._adaptive_manager_entity_id = entity_ids[0]
        for entity_id in entity_ids:
            unsubscribe = async_track_state_change_event(
                self.hass, [entity_id], self._handle_native_backup_state_change
            )
            self._adaptive_unsubscribers.append(unsubscribe)

    @callback
    def _handle_native_backup_state_change(self, event: Any) -> None:
        """React to backup-manager and automatic-backup state changes."""
        data = getattr(event, "data", {})
        entity_id = data.get("entity_id") if isinstance(data, Mapping) else None
        new_state = data.get("new_state") if isinstance(data, Mapping) else None
        state = str(getattr(new_state, "state", "unknown")).casefold()
        if entity_id == self._adaptive_manager_entity_id:
            self._manager_state_seen = state
            self._manager_backup_active = native_backup_manager_state_busy(state)
            self._set_adaptive_interval()
        self._schedule_adaptive_refresh()

    def _schedule_adaptive_refresh(self) -> None:
        """Coalesce native backup events into one immediate refresh task."""
        if (
            self._adaptive_refresh_task is not None
            and not self._adaptive_refresh_task.done()
        ):
            self._adaptive_refresh_pending = True
            return
        self._adaptive_refresh_task = self.hass.async_create_task(
            self._async_adaptive_refresh(), name=f"{DOMAIN}_adaptive_refresh"
        )

    async def _async_adaptive_refresh(self) -> None:
        """Refresh after native transitions without losing an event mid-refresh."""
        try:
            while True:
                self._adaptive_refresh_pending = False
                await self.async_request_refresh()
                if not self._adaptive_refresh_pending:
                    break
        finally:
            self._adaptive_refresh_pending = False
            self._adaptive_refresh_task = None

    def _set_adaptive_interval(self) -> None:
        """Select base, active, or error-backoff polling interval."""
        if not self.adaptive_polling:
            return
        minutes = self.settings.update_interval_minutes
        if self._inventory_error_count >= self.adaptive_error_threshold:
            minutes = self.error_backoff_interval_minutes
        elif self._manager_backup_active:
            minutes = self.active_update_interval_minutes
        self.update_interval = timedelta(minutes=minutes)

    def _record_inventory_success(self, manager_state: object) -> None:
        """Reset adaptive error backoff and reflect the manager state."""
        self._inventory_error_count = 0
        state = str(manager_state).casefold()
        self._manager_state_seen = state
        self._manager_backup_active = native_backup_manager_state_busy(state)
        self._set_adaptive_interval()

    async def async_shutdown(self) -> None:
        """Cancel a running integrity check and shut down the coordinator."""
        self._record_activity("coordinator_shutdown", ACTIVITY_OUTCOME_STARTED)
        if self._integrity_task is not None and not self._integrity_task.done():
            self._integrity_task.cancel()
            await asyncio.gather(self._integrity_task, return_exceptions=True)
        self._verification_reporter.cancel()
        self._runtime_reporter.cancel()
        self.integrity_verifier.set_progress_reporter(None)
        self.async_stop_runner_health_monitor()
        self._async_cancel_startup_settle()
        self._async_cancel_notification_confirmation()
        if (
            self._adaptive_refresh_task is not None
            and not self._adaptive_refresh_task.done()
        ):
            self._adaptive_refresh_task.cancel()
            await asyncio.gather(self._adaptive_refresh_task, return_exceptions=True)
        for unsubscribe in self._adaptive_unsubscribers:
            unsubscribe()
        self._adaptive_unsubscribers.clear()
        self._adaptive_manager_entity_id = None
        self._adaptive_refresh_pending = False
        await super().async_shutdown()
        self._record_activity("coordinator_shutdown", ACTIVITY_OUTCOME_COMPLETED)
        await self.activity.async_shutdown()

    async def _async_fetch_inventory(
        self,
    ) -> tuple[Any, Mapping[str, Any], Mapping[Any, Any]] | BackupCheckupData:
        """Fetch inventory or return a marked previous snapshot after API failure."""
        try:
            manager = async_get_manager(self.hass)
            backups, agent_errors = await manager.async_get_backups()
        except HomeAssistantError as err:
            return await self._async_manager_error_result(
                err,
                "Home Assistant backup manager is not ready",
            )
        except Exception as err:  # noqa: BLE001 - Home Assistant/agent API boundary
            return await self._async_manager_error_result(
                err,
                "Unable to read Home Assistant backups",
            )

        if not isinstance(backups, Mapping):
            raise UpdateFailed("Backup manager returned an invalid inventory")
        if not isinstance(agent_errors, Mapping):
            agent_errors = {}
        return manager, backups, agent_errors

    async def _async_manager_error_result(
        self,
        err: BaseException,
        message: str,
    ) -> BackupCheckupData:
        """Return a marked previous snapshot or raise on the initial refresh."""
        error_code = classify_exception(err)
        self._inventory_error_count += 1
        self._set_adaptive_interval()
        _LOGGER.warning(
            "%s: error_type=%s error_code=%s",
            message,
            safe_error_type(err),
            error_code,
        )
        self._record_activity(
            "backup_manager_read",
            ACTIVITY_OUTCOME_FAILED,
            level=logging.WARNING,
            details={"error_code": error_code, "error_type": safe_error_type(err)},
        )
        if self.data is None:
            raise UpdateFailed(f"{message} ({error_code})") from None
        snapshot = self._manager_error_snapshot(error_code)
        await self._async_process_notifications(snapshot)
        return snapshot

    async def _async_update_data(self) -> BackupCheckupData:
        """Read and evaluate the backup inventory."""
        started = time.monotonic()
        self._record_activity(
            "inventory_refresh",
            ACTIVITY_OUTCOME_STARTED,
            activity_visible=False,
        )
        fetched = await self._async_fetch_inventory()
        if isinstance(fetched, BackupCheckupData):
            self._record_activity(
                "inventory_refresh",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
                details={
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "status": fetched.status,
                },
            )
            return fetched
        manager, backups, agent_errors = fetched

        now = dt_util.utcnow()
        await self._async_load_integrity_state()
        password_changed = await self._async_update_backup_password_marker(manager)
        data = await self._async_build_snapshot(
            manager=manager,
            backups=backups,
            agent_errors_raw=agent_errors,
            now=now,
        )
        await self._async_process_notifications(data)
        self._schedule_automatic_verification(
            data.latest_monitored_backup_record,
            now=now,
            password_changed=password_changed,
        )
        self._record_activity(
            "inventory_refresh",
            ACTIVITY_OUTCOME_COMPLETED,
            details={
                "backup_count": getattr(data, "inventory_backup_count", len(backups)),
                "duration_seconds": round(time.monotonic() - started, 3),
                "problem_count": getattr(data, "problem_count", 0),
                "status": getattr(data, "status", "unknown"),
            },
        )
        self._record_inventory_success(getattr(data, "manager_state", "unknown"))
        previous = self.data
        previous_status = getattr(previous, "status", None)
        current_status = getattr(data, "status", None)
        previous_problems = getattr(previous, "active_problems", None)
        current_problems = getattr(data, "active_problems", None)
        if previous is not None and (
            previous_status != current_status or previous_problems != current_problems
        ):
            self._record_activity(
                "health_state",
                ACTIVITY_OUTCOME_CHANGED,
                details={
                    "from_status": previous_status,
                    "problem_count": getattr(data, "problem_count", 0),
                    "to_status": current_status,
                },
            )
        return data

    async def _async_load_integrity_state(self) -> None:
        """Hydrate persisted verification result, retry state, and cooldown once."""
        if self._integrity_state_loaded:
            return
        state = await self.integrity_verifier.store.async_load_state()
        self.integrity_result = state.result
        self._integrity_retry_key = state.retry_key
        self._integrity_retry_attempts = state.retry_attempts
        self._integrity_retry_not_before = state.retry_not_before
        self._backup_password_marker = state.password_marker
        self._backup_password_marker_initialized = state.password_marker is not None
        self._last_manual_verification_at = state.last_manual_verification_at
        self._integrity_state_loaded = True
        self._record_activity(
            "integrity_state_load",
            ACTIVITY_OUTCOME_COMPLETED,
            activity_visible=False,
            details={
                "retry_attempts": self._integrity_retry_attempts,
                "status": self.integrity_result.status,
            },
        )

    def _inventory_state(self, backups: Mapping[str, Any]) -> InventoryState:
        """Normalize and partition one backup-manager inventory."""
        normalization = self._normalizer.normalize(backups)
        self._invalid_backup_count = normalization.invalid_backups
        self._invalid_agent_copy_count = normalization.invalid_agent_copies
        monitored = monitoring_backups(normalization.records)
        automatic = tuple(record for record in monitored if record.automatic)
        manual = tuple(record for record in monitored if not record.automatic)
        return InventoryState(
            records=normalization.records,
            monitored=monitored,
            automatic=automatic,
            manual=manual,
            latest=monitored[0] if monitored else None,
            latest_automatic=automatic[0] if automatic else None,
            latest_manual=manual[0] if manual else None,
            ignored_update_count=len(normalization.records) - len(monitored),
        )

    async def _async_build_snapshot(
        self,
        *,
        manager: Any,
        backups: Mapping[str, Any],
        agent_errors_raw: Mapping[Any, Any],
        now: datetime,
    ) -> BackupCheckupData:
        """Build one complete immutable coordinator snapshot."""
        inventory = self._inventory_state(backups)
        records = inventory.records
        monitoring_records = inventory.monitored
        automatic_records = inventory.automatic
        manual_records = inventory.manual
        latest = inventory.latest
        latest_automatic_record = inventory.latest_automatic
        latest_manual_record = inventory.latest_manual

        freshness = self._evaluate_freshness(
            now=now,
            latest=latest,
            latest_automatic=latest_automatic_record,
            latest_manual=latest_manual_record,
        )
        size_analysis = self._size_changes(latest, monitoring_records)
        size_suspicious = self._is_size_suspicious(latest, size_analysis)
        latest_result = self._latest_backup_result(latest)
        latest_locations = latest.agents if latest else ()
        backup_not_redundant = bool(
            latest and len(latest_locations) < self.minimum_redundant_locations
        )

        native = read_native_backup_state(self.hass, manager, now=now)
        history = await self.history.async_observe(
            last_attempt=native.last_attempt,
            last_success=native.last_success,
            now=now,
            window_days=self.analytics_window_days,
            in_progress=native.in_progress,
        )
        inventory_analytics = calculate_inventory_analytics(
            monitoring_records,
            now=now,
            window_days=self.analytics_window_days,
        )
        storage = self._evaluate_storage(
            manager=manager,
            records=records,
            monitoring_records=monitoring_records,
            agent_errors_raw=agent_errors_raw,
            latest_location_ids=latest_locations,
            now=now,
        )
        integrity = self._evaluate_integrity(latest)
        flags = self._problem_flags(
            no_backup=not monitoring_records,
            freshness=freshness,
            native=native,
            storage=storage,
            latest=latest,
            size_suspicious=size_suspicious,
            backup_not_redundant=backup_not_redundant,
            integrity=integrity,
            now=now,
        )
        problem_state = evaluate_problem_state(flags)
        health = calculate_health_score(
            flags,
            automatic_success_rate=history.success_rate,
            consecutive_automatic_failures=history.consecutive_failures,
            resolved_attempts=history.resolved_attempts,
            latest_backup_age_days=freshness.latest_precise,
            max_age_days=self.max_age_days,
            latest_backup_locations=len(latest_locations),
            minimum_redundant_locations=self.minimum_redundant_locations,
        )
        preparedness = self.recovery_preparedness.snapshot(
            now=now,
            detected_dependencies=detect_recovery_dependencies(
                self.hass, latest, storage.summaries
            ),
        )
        restore_test = self.recovery_restore_tests.snapshot(now=now)
        recovery = assess_recovery_readiness(
            latest,
            self.integrity_result,
            backup_stale=freshness.backup_stale,
            required_locations=self.minimum_redundant_locations,
            database_check_enabled=self.database_integrity_check,
            backups=monitoring_records,
            agent_summaries=storage.summaries,
            preparedness=preparedness,
            restore_test=restore_test,
            context=RecoveryAssessmentContext(
                generated_at=now,
                installation_type=self.settings.runtime.hardware_detection.get(
                    "installation_type"
                ),
                language=getattr(
                    getattr(self.hass, "config", None), "language", "en"
                ),
            ),
            simulation_progress=self._verification_reporter.snapshot(),
            adaptive_policy=self.recovery_policy,
            runtime_test=self.runtime_tests.snapshot(),
            runner_reachable=self._runner_health.usable,
        )

        public_locations = self._public_location_ids(latest_locations)
        self._last_inventory_success_at = now
        return BackupCheckupData(
            checked_at=now,
            max_age_days=self.max_age_days,
            minimum_backup_size_bytes=self.minimum_backup_size_bytes,
            maximum_size_drop_percent=self.maximum_size_drop_percent,
            minimum_redundant_locations=self.minimum_redundant_locations,
            total_backups=len(monitoring_records),
            inventory_backup_count=len(records),
            ignored_update_backup_count=inventory.ignored_update_count,
            automatic_backups=len(automatic_records),
            manual_backups=len(manual_records),
            latest_backup=latest.date if latest else None,
            latest_automatic_backup=(
                latest_automatic_record.date if latest_automatic_record else None
            ),
            latest_manual_backup=(
                latest_manual_record.date if latest_manual_record else None
            ),
            latest_backup_age_days=freshness.latest_days,
            latest_backup_age_days_precise=freshness.latest_precise,
            automatic_backup_age_days=freshness.automatic_days,
            automatic_backup_age_days_precise=freshness.automatic_precise,
            manual_backup_age_days=freshness.manual_days,
            manual_backup_age_days_precise=freshness.manual_precise,
            latest_backup_size=latest.size if latest else None,
            latest_automatic_backup_size=(
                latest_automatic_record.size if latest_automatic_record else None
            ),
            latest_backup_size_change_percent=size_analysis.previous_percent,
            comparable_backup_count=size_analysis.comparable_count,
            latest_backup_result=latest_result,
            latest_backup_locations=len(latest_locations),
            latest_backup_location_ids=public_locations,
            last_automatic_attempt=native.last_attempt,
            last_successful_automatic_event=native.last_success,
            next_automatic_backup=native.next_scheduled,
            manager_state=native.manager_state,
            agent_errors=storage.public_errors,
            agent_summaries=storage.summaries,
            backups=records,
            monitored_backups=monitoring_records,
            no_backup=flags["no_backup"],
            backup_stale=flags["backup_stale"],
            automatic_backup_overdue=flags["automatic_backup_overdue"],
            automatic_backup_failed=flags["automatic_backup_failed"],
            automatic_schedule_missing=flags["automatic_schedule_missing"],
            automatic_schedule_overdue=flags["automatic_schedule_overdue"],
            manager_unavailable=False,
            storage_error=flags["storage_error"],
            backup_size_suspicious=flags["backup_size_suspicious"],
            latest_backup_incomplete=flags["latest_backup_incomplete"],
            backup_not_redundant=flags["backup_not_redundant"],
            required_location_missing=flags["required_location_missing"],
            backup_checksum_changed=flags["backup_checksum_changed"],
            backup_integrity_warning=flags["backup_integrity_warning"],
            problem=bool(problem_state.active),
            status=problem_state.status,
            recommendation=problem_state.recommendation,
            problem_count=len(problem_state.active),
            active_problems=problem_state.active,
            size_check_mode=self.size_check_mode,
            analytics_window_days=self.analytics_window_days,
            **_assessment_fields(
                health, recovery, runtime_test=self._runtime_view(latest)
            ),
            recovery_evidence=recovery.evidence,
            recovery_adaptive_policy=recovery.adaptive_policy,
            recovery_open_risks=recovery.open_risks,
            last_restore_test=restore_test.tested_at,
            restore_test_result=restore_test.result,
            restore_test_scope=restore_test.scope,
            restore_test_overdue=False,
            recovery_plan_incomplete=bool(recovery.recovery_plan.get("warnings")),
            recovery_checklist_incomplete=False,
            external_dependency_unprotected=(
                recovery.checks.get("external_dependencies_protected") is False
            ),
            backup_content_changed=recovery.backup_content_changed,
            external_copy_missing=recovery.external_copy_missing,
            average_backup_size=inventory_analytics.average_backup_size,
            longest_backup_gap_days=inventory_analytics.longest_backup_gap_days,
            size_trend=inventory_analytics.size_trend,
            size_trend_percent=inventory_analytics.size_trend_percent,
            analyzed_backup_count=inventory_analytics.analyzed_backup_count,
            analyzed_backup_scope=inventory_analytics.analyzed_backup_scope,
            analyzed_backup_origin=inventory_analytics.analyzed_backup_origin,
            automatic_success_rate=history.success_rate,
            automatic_attempts_observed=history.resolved_attempts,
            automatic_successes_observed=history.successful_attempts,
            automatic_failures_observed=history.failed_attempts,
            consecutive_automatic_failures=history.consecutive_failures,
            history_tracking_started_at=history.tracking_started_at,
            integrity=self.integrity_result,
            integrity_check_running=self.integrity_check_running,
            expose_backup_metadata=self.expose_backup_metadata,
            invalid_backup_count=self._invalid_backup_count,
            invalid_agent_copy_count=self._invalid_agent_copy_count,
            copy_size_mismatch_count=sum(
                record.copy_size_mismatch for record in records
            ),
            last_inventory_success_at=self._last_inventory_success_at,
        )

    def _evaluate_freshness(
        self,
        *,
        now: datetime,
        latest: BackupRecord | None,
        latest_automatic: BackupRecord | None,
        latest_manual: BackupRecord | None,
    ) -> FreshnessState:
        """Calculate age sensors and overdue state from complete usable backups."""
        latest_precise = precise_age_days(now, latest.date if latest else None)
        automatic_precise = precise_age_days(
            now,
            latest_automatic.date if latest_automatic else None,
        )
        manual_precise = precise_age_days(
            now,
            latest_manual.date if latest_manual else None,
        )
        manual_covers_automatic = bool(
            latest_manual
            and not latest_manual.incomplete
            and (latest_automatic is None or latest_manual.date > latest_automatic.date)
        )
        if latest_automatic is None:
            automatic_overdue = bool(
                latest_manual is None
                or latest_manual.incomplete
                or manual_precise is None
                or manual_precise > self.max_age_days
            )
        else:
            automatic_overdue = bool(
                automatic_precise is not None
                and automatic_precise > self.max_age_days
                and not manual_covers_automatic
            )
        return FreshnessState(
            latest_precise=latest_precise,
            latest_days=completed_age_days(latest_precise),
            automatic_precise=automatic_precise,
            automatic_days=completed_age_days(automatic_precise),
            manual_precise=manual_precise,
            manual_days=completed_age_days(manual_precise),
            backup_stale=bool(
                latest_precise is not None and latest_precise > self.max_age_days
            ),
            automatic_backup_overdue=automatic_overdue,
        )

    @staticmethod
    def _latest_backup_result(latest: BackupRecord | None) -> str:
        """Return the stable result enum for the latest monitored backup."""
        if latest is None:
            return BACKUP_RESULT_UNKNOWN
        return BACKUP_RESULT_PARTIAL if latest.incomplete else BACKUP_RESULT_COMPLETE

    def _evaluate_integrity(self, latest: BackupRecord | None) -> IntegrityFlags:
        """Map the latest persisted result to problem flags."""
        applies = bool(latest and self.integrity_result.backup_id == latest.backup_id)
        if not applies:
            return IntegrityFlags(False, False, False)
        status = self.integrity_result.status
        return IntegrityFlags(
            failed=status in {"corrupt", "unreadable", "internal_error"},
            checksum_changed=self.integrity_result.checksum_changed,
            warning=status
            in {
                INTEGRITY_STATUS_VALID_WITH_WARNINGS,
                INTEGRITY_STATUS_ABORTED,
                INTEGRITY_STATUS_PASSWORD_REQUIRED,
            },
        )

    def _problem_flags(
        self,
        *,
        no_backup: bool,
        freshness: FreshnessState,
        native: NativeBackupState,
        storage: StorageState,
        latest: BackupRecord | None,
        size_suspicious: bool,
        backup_not_redundant: bool,
        integrity: IntegrityFlags,
        now: datetime,
    ) -> dict[str, bool]:
        """Build the one canonical problem-flag mapping."""
        return {
            "no_backup": no_backup,
            "backup_integrity_failed": integrity.failed,
            "backup_checksum_changed": integrity.checksum_changed,
            "backup_integrity_warning": integrity.warning,
            "backup_stale": freshness.backup_stale,
            "automatic_backup_overdue": freshness.automatic_backup_overdue,
            "automatic_backup_failed": evaluate_automatic_backup_failed(
                event_type=native.event_type,
                in_progress=native.in_progress,
                last_attempt=native.last_attempt,
                last_success=native.last_success,
            ),
            "automatic_schedule_missing": native.next_scheduled is None,
            "automatic_schedule_overdue": bool(
                native.next_scheduled
                and native.next_scheduled < now - timedelta(hours=6)
            ),
            "manager_unavailable": False,
            "storage_error": storage.storage_error,
            "backup_size_suspicious": size_suspicious,
            "latest_backup_incomplete": bool(latest and latest.incomplete),
            "backup_not_redundant": backup_not_redundant,
            "required_location_missing": storage.required_location_missing,
        }

    def _normalize_agent_errors(self, raw: Mapping[Any, Any]) -> dict[str, str]:
        """Return stable codes for safely materialized storage-agent errors."""
        errors: dict[str, str] = {}
        for agent_id, error in ThirdPartyBoundary.mapping_items(raw):
            normalized = ThirdPartyBoundary.text(agent_id, maximum=_MAX_AGENT_ID_LENGTH)
            if normalized:
                errors[normalized] = classify_exception(error)
        return errors

    def _agent_metadata(self, manager: Any) -> tuple[set[str], dict[str, str]]:
        """Return configured agent IDs and privacy-safe friendly names."""
        configured: set[str] = set()
        names: dict[str, str] = {}
        manager_agents = ThirdPartyBoundary.attribute(manager, "backup_agents", {})
        for agent_id, agent in ThirdPartyBoundary.mapping_items(manager_agents):
            normalized = ThirdPartyBoundary.text(agent_id, maximum=_MAX_AGENT_ID_LENGTH)
            if normalized is None:
                continue
            configured.add(normalized)
            reference = anonymous_agent_reference(
                self.config_entry.entry_id, normalized
            )
            names[normalized] = safe_display_name(
                ThirdPartyBoundary.attribute(agent, "name", None),
                fallback=f"Backup storage {reference}",
            )
        return configured, names

    def _evaluate_storage(
        self,
        *,
        manager: Any,
        records: tuple[BackupRecord, ...],
        monitoring_records: tuple[BackupRecord, ...],
        agent_errors_raw: Mapping[Any, Any],
        latest_location_ids: tuple[str, ...],
        now: datetime,
    ) -> StorageState:
        """Build all storage summaries and required-location state."""
        errors = self._normalize_agent_errors(agent_errors_raw)
        configured, names = self._agent_metadata(manager)
        summaries = self._build_agent_summaries(
            records,
            monitoring_records,
            errors,
            configured,
            names,
            now,
        )
        required_missing = bool(
            latest_location_ids
            and any(
                summary.error
                for summary in summaries
                if summary.agent_id in latest_location_ids
            )
        )
        public_errors = (
            errors
            if self.expose_backup_metadata
            else {
                anonymous_agent_reference(self.config_entry.entry_id, agent_id): code
                for agent_id, code in errors.items()
            }
        )
        return StorageState(
            public_errors=public_errors,
            summaries=summaries,
            storage_error=bool(errors),
            required_location_missing=required_missing,
        )

    @staticmethod
    def _index_agent_records(
        inventory_records: tuple[BackupRecord, ...],
        monitoring_records: tuple[BackupRecord, ...],
    ) -> tuple[
        dict[str, list[BackupRecord]],
        dict[str, list[BackupRecord]],
        dict[str, list[int]],
    ]:
        """Index inventory records, monitored records, and sizes by agent ID."""
        inventory_by_agent: dict[str, list[BackupRecord]] = defaultdict(list)
        monitoring_by_agent: dict[str, list[BackupRecord]] = defaultdict(list)
        sizes_by_agent: dict[str, list[int]] = defaultdict(list)

        for record in inventory_records:
            for copy in record.agent_copies:
                inventory_by_agent[copy.agent_id].append(record)
                if copy.size is not None:
                    sizes_by_agent[copy.agent_id].append(copy.size)
        for record in monitoring_records:
            for agent_id in record.agents:
                monitoring_by_agent[agent_id].append(record)
        return inventory_by_agent, monitoring_by_agent, sizes_by_agent

    @staticmethod
    def _latest_copy_size(record: BackupRecord | None, agent_id: str) -> int | None:
        """Return the reported size of one agent's newest monitored copy."""
        if record is None:
            return None
        return next(
            (copy.size for copy in record.agent_copies if copy.agent_id == agent_id),
            None,
        )

    def _agent_summary(
        self,
        *,
        agent_id: str,
        inventory: list[BackupRecord],
        monitored: list[BackupRecord],
        sizes: list[int],
        error: str | None,
        storage_name: str | None,
        now: datetime,
    ) -> BackupAgentSummary:
        """Build one storage summary from pre-indexed agent data."""
        newest = monitored[0] if monitored else None
        age = precise_age_days(now, newest.date if newest else None)
        stale = age is None or age > self.max_age_days
        reference = anonymous_agent_reference(self.config_entry.entry_id, agent_id)
        return BackupAgentSummary(
            agent_id=agent_id,
            agent_reference=reference,
            storage_name=storage_name or f"Backup storage {reference}",
            backup_count=len(monitored),
            inventory_backup_count=len(inventory),
            ignored_update_backup_count=len(inventory) - len(monitored),
            latest_backup=newest.date if newest else None,
            latest_backup_age_days=age,
            latest_backup_size=self._latest_copy_size(newest, agent_id),
            stored_bytes=sum(sizes) if sizes else None,
            error=error,
            stale=stale,
            problem=bool(error or stale),
        )

    def _build_agent_summaries(
        self,
        inventory_records: tuple[BackupRecord, ...],
        monitoring_records: tuple[BackupRecord, ...],
        agent_errors: Mapping[str, str],
        configured_agent_ids: set[str],
        agent_names: Mapping[str, str],
        now: datetime,
    ) -> tuple[BackupAgentSummary, ...]:
        """Aggregate one health summary per storage agent in linear passes."""
        inventory_by_agent, monitoring_by_agent, sizes_by_agent = (
            self._index_agent_records(inventory_records, monitoring_records)
        )
        all_ids = sorted(
            set(inventory_by_agent)
            | set(monitoring_by_agent)
            | set(agent_errors)
            | configured_agent_ids
        )
        return tuple(
            self._agent_summary(
                agent_id=agent_id,
                inventory=inventory_by_agent.get(agent_id, []),
                monitored=monitoring_by_agent.get(agent_id, []),
                sizes=sizes_by_agent.get(agent_id, []),
                error=agent_errors.get(agent_id),
                storage_name=agent_names.get(agent_id),
                now=now,
            )
            for agent_id in all_ids
        )

    def _public_location_ids(self, locations: tuple[str, ...]) -> tuple[str, ...]:
        """Return raw or installation-local storage identifiers."""
        if self.expose_backup_metadata:
            return locations
        return tuple(
            anonymous_agent_reference(self.config_entry.entry_id, agent_id)
            for agent_id in locations
        )

    def _size_changes(
        self,
        latest: BackupRecord | None,
        records: tuple[BackupRecord, ...],
    ) -> SizeChangeAnalysis:
        """Return comparable previous and median-baseline size changes."""
        if latest is None or latest.size is None:
            return SizeChangeAnalysis(None, None, 0)
        comparable = list(comparable_size_backups(latest, records))
        previous = comparable[0] if comparable else None
        previous_percent = (
            round(((latest.size - previous.size) / previous.size) * 100, 1)
            if previous is not None and previous.size
            else None
        )
        baseline_sizes = [
            record.size for record in comparable[:_SIZE_BASELINE_RECORDS] if record.size
        ]
        baseline = median(baseline_sizes) if baseline_sizes else None
        baseline_percent = (
            round(((latest.size - baseline) / baseline) * 100, 1) if baseline else None
        )
        return SizeChangeAnalysis(previous_percent, baseline_percent, len(comparable))

    def _is_size_suspicious(
        self,
        latest: BackupRecord | None,
        analysis: SizeChangeAnalysis,
    ) -> bool:
        """Evaluate the configured backup-size rule."""
        if self.size_check_mode == SIZE_CHECK_OFF or latest is None:
            return False
        if latest.size is not None and latest.size <= 0:
            return True
        if self.size_check_mode == SIZE_CHECK_FIXED:
            return bool(
                latest.size is not None
                and self.minimum_backup_size_bytes > 0
                and latest.size < self.minimum_backup_size_bytes
            )
        if self.size_check_mode != SIZE_CHECK_AUTO:
            return False
        return automatic_size_drop_is_suspicious(
            maximum_drop_percent=self.maximum_size_drop_percent,
            previous_change_percent=analysis.previous_percent,
            baseline_change_percent=analysis.baseline_percent,
            comparable_backup_count=analysis.comparable_count,
        )

    @staticmethod
    def _integrity_result_is_retryable(result: BackupIntegrityResult) -> bool:
        """Return whether an automatic check may retry a controlled result."""
        if result.status in {
            INTEGRITY_STATUS_INTERNAL_ERROR,
            INTEGRITY_STATUS_UNREADABLE,
        }:
            return True
        return result.status == INTEGRITY_STATUS_ABORTED and result.error_code in {
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

    def _password_marker(self, manager: Any) -> str | None:
        """Return a non-reversible entry-local marker for the current password."""
        password = BackupIntegrityVerifier._backup_password(manager)
        if password is None:
            return None
        entry_id = getattr(getattr(self, "config_entry", None), "entry_id", "unknown")
        material = f"{_CREDENTIAL_MARKER_CONTEXT}:{entry_id}:{password}"
        return hashlib.sha256(material.encode()).hexdigest()

    def _update_backup_password_marker(self, manager: Any) -> bool:
        """Update the in-memory password marker; first observation is not a change."""
        marker = self._password_marker(manager)
        if not self._backup_password_marker_initialized:
            self._backup_password_marker = marker
            self._backup_password_marker_initialized = True
            return False
        changed = marker != self._backup_password_marker
        self._backup_password_marker = marker
        return changed

    async def _async_update_backup_password_marker(self, manager: Any) -> bool:
        """Update and persist the password marker when its value changes."""
        previous = self._backup_password_marker
        initialized = self._backup_password_marker_initialized
        changed = self._update_backup_password_marker(manager)
        if not initialized or previous != self._backup_password_marker:
            await self._async_persist_runtime_state()
        return changed

    def _update_integrity_retry_state(self, result: BackupIntegrityResult) -> None:
        """Apply bounded exponential backoff for repeatable automatic failures."""
        if not self._integrity_result_is_retryable(result) or result.backup_id is None:
            self._integrity_retry_key = None
            self._integrity_retry_attempts = 0
            self._integrity_retry_not_before = None
            return
        key = (result.backup_id, result.error_code or result.status)
        self._integrity_retry_attempts = (
            self._integrity_retry_attempts + 1
            if key == self._integrity_retry_key
            else 1
        )
        self._integrity_retry_key = key
        multiplier = 2 ** max(0, self._integrity_retry_attempts - 1)
        delay = min(_AUTOMATIC_RETRY_BASE * multiplier, _AUTOMATIC_RETRY_MAX)
        self._integrity_retry_not_before = (
            result.checked_at or dt_util.utcnow()
        ) + delay

    async def _async_persist_runtime_state(self) -> None:
        """Persist retry, password, and manual-cooldown state."""
        try:
            await self.integrity_verifier.store.async_update_runtime(
                password_marker=self._backup_password_marker,
                retry_key=self._integrity_retry_key,
                retry_attempts=self._integrity_retry_attempts,
                retry_not_before=self._integrity_retry_not_before,
                last_manual_verification_at=self._last_manual_verification_at,
            )
        except Exception as err:  # noqa: BLE001 - Home Assistant Store boundary
            _LOGGER.warning(
                "Unable to persist verification control state: error_type=%s",
                safe_error_type(err),
            )

    async def _async_save_integrity_result(self, result: BackupIntegrityResult) -> None:
        """Persist one result together with all bounded runtime state."""
        await self.integrity_verifier.store.async_save(
            result,
            retry_key=self._integrity_retry_key,
            retry_attempts=self._integrity_retry_attempts,
            retry_not_before=self._integrity_retry_not_before,
            password_marker=self._backup_password_marker,
            last_manual_verification_at=self._last_manual_verification_at,
        )

    def _record_startup_grace_skip(self) -> None:
        """Record the single entry that explains the hold after a restart."""
        if self._startup_grace_logged:
            return
        self._startup_grace_logged = True
        self._record_activity(
            "notification_processing",
            ACTIVITY_OUTCOME_SKIPPED,
            activity_visible=False,
            details={"reason": "startup_grace"},
        )

    async def _async_process_notifications(self, data: BackupCheckupData) -> None:
        """Process notifications without allowing service failures to escape."""
        if not self._startup_settled:
            # The stored signature stays untouched, so a problem that was
            # already reported before the restart is not pushed again and a
            # change during the start phase is still detected afterwards.
            self._record_startup_grace_skip()
            return
        try:
            confirmation_pending = await self.notification_manager.async_process(
                data,
                enabled=self.notifications_enabled,
                targets=self.notification_targets,
                notify_on_recovery=self.notify_on_recovery,
            )
        except Exception:
            _LOGGER.exception("Unexpected error while processing notifications")
            return
        if confirmation_pending:
            self._async_schedule_notification_confirmation()

    def _manager_error_snapshot(self, error_code: str) -> BackupCheckupData:
        """Return the last snapshot with dynamically aged unavailable state."""
        now = dt_util.utcnow()
        latest = self.data.latest_monitored_backup_record
        automatic = next(
            (record for record in self.data.monitored_backups if record.automatic),
            None,
        )
        manual = next(
            (record for record in self.data.monitored_backups if not record.automatic),
            None,
        )
        freshness = self._evaluate_freshness(
            now=now,
            latest=latest,
            latest_automatic=automatic,
            latest_manual=manual,
        )
        summaries = tuple(
            self._age_agent_summary(summary, now)
            for summary in self.data.agent_summaries
        )
        required_missing = bool(
            latest
            and any(
                summary.error
                for summary in summaries
                if summary.agent_id in latest.agents
            )
        )
        flags = {
            "no_backup": self.data.no_backup,
            "backup_integrity_failed": (
                "backup_integrity_failed" in self.data.active_problems
            ),
            "backup_checksum_changed": self.data.backup_checksum_changed,
            "backup_integrity_warning": self.data.backup_integrity_warning,
            "backup_stale": freshness.backup_stale,
            "automatic_backup_overdue": freshness.automatic_backup_overdue,
            "automatic_backup_failed": self.data.automatic_backup_failed,
            "automatic_schedule_missing": self.data.automatic_schedule_missing,
            "automatic_schedule_overdue": self.data.automatic_schedule_overdue,
            "manager_unavailable": True,
            "storage_error": self.data.storage_error,
            "backup_size_suspicious": self.data.backup_size_suspicious,
            "latest_backup_incomplete": self.data.latest_backup_incomplete,
            "backup_not_redundant": self.data.backup_not_redundant,
            "required_location_missing": required_missing,
        }
        state = evaluate_problem_state(flags)
        health = calculate_health_score(
            flags,
            automatic_success_rate=self.data.automatic_success_rate,
            consecutive_automatic_failures=self.data.consecutive_automatic_failures,
            resolved_attempts=self.data.automatic_attempts_observed,
            latest_backup_age_days=freshness.latest_precise,
            max_age_days=self.max_age_days,
            latest_backup_locations=self.data.latest_backup_locations,
            minimum_redundant_locations=getattr(
                self,
                "minimum_redundant_locations",
                self.data.minimum_redundant_locations,
            ),
        )
        preparedness = self.recovery_preparedness.snapshot(
            now=now,
            detected_dependencies=detect_recovery_dependencies(
                self.hass, self.data.latest_monitored_backup_record, summaries
            ),
        )
        restore_test = self.recovery_restore_tests.snapshot(now=now)
        recovery = assess_recovery_readiness(
            self.data.latest_monitored_backup_record,
            self.data.integrity,
            backup_stale=freshness.backup_stale,
            required_locations=getattr(
                self,
                "minimum_redundant_locations",
                self.data.minimum_redundant_locations,
            ),
            database_check_enabled=getattr(self, "database_integrity_check", False),
            backups=self.data.monitored_backups,
            agent_summaries=summaries,
            preparedness=preparedness,
            restore_test=restore_test,
            context=RecoveryAssessmentContext(
                generated_at=now,
                installation_type=self.settings.runtime.hardware_detection.get(
                    "installation_type"
                ),
                language=getattr(
                    getattr(self.hass, "config", None), "language", "en"
                ),
            ),
            simulation_progress=self._verification_reporter.snapshot(),
            adaptive_policy=self.recovery_policy,
            runtime_test=self.runtime_tests.snapshot(),
            runner_reachable=self._runner_health.usable,
        )
        return cast(
            BackupCheckupData,
            replace(
                self.data,
                checked_at=now,
                latest_backup_age_days=freshness.latest_days,
                latest_backup_age_days_precise=freshness.latest_precise,
                automatic_backup_age_days=freshness.automatic_days,
                automatic_backup_age_days_precise=freshness.automatic_precise,
                manual_backup_age_days=freshness.manual_days,
                manual_backup_age_days_precise=freshness.manual_precise,
                agent_summaries=summaries,
                backup_stale=freshness.backup_stale,
                automatic_backup_overdue=freshness.automatic_backup_overdue,
                required_location_missing=required_missing,
                manager_state=STATE_UNAVAILABLE,
                manager_unavailable=True,
                problem=True,
                status=state.status,
                recommendation=state.recommendation,
                problem_count=len(state.active),
                active_problems=state.active,
                **_assessment_fields(
                    health,
                    recovery,
                    runtime_test=self._runtime_view(
                        self.data.latest_monitored_backup_record
                    ),
                ),
                last_restore_test=restore_test.tested_at,
                restore_test_result=restore_test.result,
                restore_test_scope=restore_test.scope,
                restore_test_overdue=(
                    restore_test.passed is not True
                    and self.data.latest_monitored_backup_record is not None
                ),
                recovery_plan_incomplete=bool(
                    recovery.recovery_plan.get("warnings")
                ),
                recovery_checklist_incomplete=(
                    recovery.checks.get("preparedness_checklist_complete") is not True
                    and self.data.latest_monitored_backup_record is not None
                ),
                external_dependency_unprotected=(
                    recovery.checks.get("external_dependencies_protected") is False
                ),
                backup_content_changed=recovery.backup_content_changed,
                external_copy_missing=recovery.external_copy_missing,
                agent_errors={**self.data.agent_errors, "manager": error_code},
            ),
        )

    def _age_agent_summary(
        self, summary: BackupAgentSummary, now: datetime
    ) -> BackupAgentSummary:
        """Return one storage summary aged to the current failed refresh."""
        age = precise_age_days(now, summary.latest_backup)
        stale = age is None or age > self.max_age_days
        return cast(
            BackupAgentSummary,
            replace(
                summary,
                latest_backup_age_days=age,
                stale=stale,
                problem=bool(summary.error or stale),
            ),
        )

    def _schedule_automatic_verification(
        self,
        latest: BackupRecord | None,
        *,
        now: datetime,
        password_changed: bool,
    ) -> None:
        """Schedule a due automatic verification without overlapping another task."""
        if (
            not self.auto_verify_new_backups
            or not self._automatic_verification_due(
                latest,
                now=now,
                password_changed=password_changed,
            )
            or self.integrity_check_running
            or (self._integrity_task is not None and not self._integrity_task.done())
        ):
            return
        if latest is None:
            return
        manager_busy, manager_state = self._backup_manager_busy()
        if manager_busy:
            # Retry on the next refresh instead of staging data while the manager
            # is creating, receiving or restoring a backup.
            self._record_activity(
                "integrity_check_schedule",
                ACTIVITY_OUTCOME_SKIPPED,
                details={
                    "source": "automatic",
                    "reason": "backup_in_progress",
                    "manager_state": manager_state,
                },
            )
            return
        self._record_activity(
            "integrity_check_schedule",
            ACTIVITY_OUTCOME_COMPLETED,
            details={"source": "automatic"},
        )
        self._set_integrity_task(
            self.hass.async_create_task(
                self._async_run_integrity_check(latest, source="automatic"),
                name=f"{DOMAIN}_automatic_integrity_check",
            )
        )

    def _set_integrity_task(self, task: asyncio.Task[None]) -> None:
        """Track a verification task and always retrieve its final exception."""
        self._integrity_task = task
        task.add_done_callback(self._consume_integrity_task_result)

    def _consume_integrity_task_result(self, task: asyncio.Task[None]) -> None:
        """Consume and log a background result so failures cannot be hidden."""
        try:
            error = task.exception()
        except asyncio.CancelledError:
            error = None
        if error is not None:
            self.integrity_check_running = False
            self._record_activity(
                "integrity_background_task",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.ERROR,
                details={"error_type": safe_error_type(error)},
            )
            _LOGGER.error(
                "Unhandled backup verification task failure: error_type=%s",
                safe_error_type(error),
            )
        if self._integrity_task is task and task.done():
            self._integrity_task = None

    @property
    def integrity_check_pending_or_running(self) -> bool:
        """Return whether a verification task is queued or executing."""
        return self.integrity_check_running or bool(
            self._integrity_task is not None and not self._integrity_task.done()
        )

    @property
    def manual_verification_cooldown_active(self) -> bool:
        """Return whether a manual verification is currently rate-limited."""
        if self.manual_verification_cooldown_minutes <= 0:
            return False
        if self._last_manual_verification_at is None:
            return False
        return dt_util.utcnow() < self._last_manual_verification_at + timedelta(
            minutes=self.manual_verification_cooldown_minutes
        )

    async def async_start_integrity_check(self, *, source: str = "manual") -> bool:
        """Start an integrity check of the latest monitored backup."""
        if self.integrity_check_pending_or_running:
            self._record_activity(
                "integrity_check_request",
                ACTIVITY_OUTCOME_SKIPPED,
                level=logging.WARNING,
                details={"reason": "already_running", "source": source},
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_already_running",
            )
        latest = self.data.latest_monitored_backup_record
        if latest is None:
            self._record_activity(
                "integrity_check_request",
                ACTIVITY_OUTCOME_SKIPPED,
                level=logging.WARNING,
                details={"reason": "no_backup", "source": source},
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_no_backup",
            )
        if (
            source in {"manual", "simulation"}
            and self.manual_verification_cooldown_active
        ):
            self._record_activity(
                "integrity_check_request",
                ACTIVITY_OUTCOME_SKIPPED,
                level=logging.WARNING,
                details={"reason": "cooldown", "source": source},
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_cooldown",
                translation_placeholders={
                    "minutes": str(self.manual_verification_cooldown_minutes)
                },
            )
        manager_busy, manager_state = self._backup_manager_busy()
        if manager_busy:
            self._record_activity(
                "integrity_check_request",
                ACTIVITY_OUTCOME_SKIPPED,
                level=logging.WARNING,
                details={
                    "reason": "backup_in_progress",
                    "source": source,
                    "manager_state": manager_state,
                },
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="verification_backup_in_progress",
            )
        self._record_activity(
            "integrity_check_request",
            ACTIVITY_OUTCOME_COMPLETED,
            details={"source": source},
        )
        self._set_integrity_task(
            self.hass.async_create_task(
                self._async_run_integrity_check(latest, source=source),
                name=f"{DOMAIN}_{source}_integrity_check",
            )
        )
        return True

    def _runtime_archive_callback(
        self, record: BackupRecord, *, simulation_run: bool
    ) -> Callable[..., object] | None:
        """Return the optional callback that hands an archive to the runner."""
        if not simulation_run or self.runtime_runner_connection is None:
            return None
        return lambda path, password, verified: self._async_run_runtime_test(
            record, path, password, verified
        )

    def _record_step_activity(
        self, job: str, key: str, outcome: str, details: Mapping[str, Any]
    ) -> None:
        """Write one bounded journal record for measured step progress.

        Only completed tenths reach the journal; the live percentage itself is
        published on the progress channel and never through the activity log.
        """
        if outcome != ACTIVITY_OUTCOME_CHANGED:
            return
        if job == JOB_RUNTIME_TEST:
            action = "runtime_test"
            payload: dict[str, Any] = {"step": key, **dict(details)}
        else:
            action = _VERIFICATION_PROGRESS_ACTIONS.get(key)
            if action is None:
                return
            payload = dict(details)
        self._record_activity(action, ACTIVITY_OUTCOME_CHANGED, details=payload)

    @callback
    def _publish_progress(self, job: str) -> None:
        """Notify only the progress entities and the panel subscription."""
        async_dispatcher_send(
            self.hass, progress_signal(self.config_entry.entry_id), job
        )

    def _refresh_progress_data(self) -> None:
        """Fold the current progress views into the shared coordinator data.

        This runs on job transitions only; a percentage tick never refreshes
        every entity.
        """
        if self.data is None:
            return
        self.async_set_updated_data(
            replace(
                self.data,
                integrity_check_running=self.integrity_check_running,
                recovery_restore_simulation=self.progress_view(JOB_VERIFICATION),
                recovery_runtime_test=self.progress_view(JOB_RUNTIME_TEST),
            )
        )

    def progress_view(
        self, job: str, latest: BackupRecord | None = None
    ) -> dict[str, Any]:
        """Return the merged stored and live view of one job."""
        if job == JOB_RUNTIME_TEST:
            return self._runtime_view(latest)
        return self._simulation_view(latest)

    def _progress_backup_record(
        self, latest: BackupRecord | None = None
    ) -> BackupRecord | None:
        """Return the backup the progress views describe.

        A running job owns the view; otherwise the current latest backup does,
        so a newer backup is never shown with the result of an older one. While
        a snapshot is being built the caller passes the latest record it just
        read, because ``self.data`` still holds the previous one.
        """
        running = JOB_RUNNING in {
            self.verification_progress.status,
            self.runtime_progress.status,
        }
        if running and self._progress_record is not None:
            return self._progress_record
        if latest is None and self.data is not None:
            latest = self.data.latest_monitored_backup_record
        return latest if latest is not None else self._progress_record

    def _simulation_view(
        self, latest: BackupRecord | None = None
    ) -> dict[str, Any]:
        """Return the restore simulation including any live measurement."""
        return simulate_restore(
            self._progress_backup_record(latest),
            self.integrity_result,
            database_check_enabled=self.database_integrity_check,
            live_progress=self._verification_reporter.snapshot(),
        ).as_dict()

    def _runtime_view(self, latest: BackupRecord | None = None) -> dict[str, Any]:
        """Combine stored proof details with the current live pipeline."""
        state = self.runtime_tests.snapshot().as_dict()
        progress = self._runtime_reporter.snapshot()
        record = self._progress_backup_record(latest)
        reference = record.backup_reference if record else None
        belongs = progress["status"] != JOB_IDLE and (
            reference is None or progress.get("backup_reference") == reference
        )
        if not belongs:
            # The live pipeline belongs to another backup, so this view shows an
            # untouched one instead of finished steps without a percentage.
            empty = JobProgress.create(JOB_RUNTIME_TEST).as_dict()
            state.update(
                {
                    "running": False,
                    "steps": empty["steps"],
                    "stages": empty["stages"],
                    "overall_percent": 0,
                    "progress_percent": 0,
                    "current_step": None,
                    "determinate": False,
                    "heartbeat_at": None,
                    "events": [],
                    "source": empty["source"],
                    **self._runner_fields(),
                }
            )
            return state
        live = {key: value for key, value in progress.items() if key != "job"}
        for key in ("duration_seconds", "runner_version"):
            if live.get(key) is None:
                # Keep the stored value instead of erasing it with a live None.
                live.pop(key)
        if progress["status"] == JOB_RUNNING:
            # A running test must not keep presenting the previous proof.
            state.update(_RUNNING_RUNTIME_EVIDENCE)
        state.update(live)
        state.update(self._runner_fields())
        return state

    def _runner_fields(self) -> dict[str, Any]:
        """Return the runner facts every runtime-test view carries."""
        return {
            "runner_reachable": self._runner_health.usable,
            "runner_configured": self._runner_health.configured,
            "runner_update_recommended": self._runner_health.update_recommended,
            "runner_checked_at": (
                self._runner_health.checked_at.isoformat()
                if self._runner_health.checked_at
                else None
            ),
        }

    def _publish_integrity_result(
        self,
        record: BackupRecord,
        result: BackupIntegrityResult,
        *,
        simulation_run: bool,
    ) -> None:
        """Publish one verifier result to all in-memory consumers."""
        del simulation_run
        self.integrity_result = result
        self._progress_record = record
        self._verification_reporter.finish(
            _verification_job_status(result.status),
            error_code=result.error_code,
        )
        self._refresh_progress_data()
        self._update_integrity_retry_state(result)

    async def _async_complete_integrity_check(
        self,
        record: BackupRecord,
        result: BackupIntegrityResult,
        *,
        source: str,
        simulation_run: bool,
    ) -> None:
        """Persist and record a successful verifier invocation."""
        self._publish_integrity_result(
            record, result, simulation_run=simulation_run
        )
        if source in {"manual", "simulation"}:
            self._last_manual_verification_at = result.checked_at or dt_util.utcnow()
        await self._try_persist_integrity_result(result, source, record)
        self._record_activity(
            "integrity_check",
            ACTIVITY_OUTCOME_COMPLETED,
            details={
                "duration_seconds": result.duration_seconds,
                "source": source,
                "status": result.status,
                "warning_count": len(result.warnings),
            },
        )

    async def _async_fail_integrity_check(
        self,
        record: BackupRecord,
        err: Exception,
        *,
        source: str,
        simulation_run: bool,
    ) -> None:
        """Convert an unexpected verifier exception into bounded state."""
        result = self._internal_error_result(record)
        self._publish_integrity_result(
            record, result, simulation_run=simulation_run
        )
        if source in {"manual", "simulation"}:
            self._last_manual_verification_at = result.checked_at
        self._record_activity(
            "integrity_check",
            ACTIVITY_OUTCOME_FAILED,
            level=logging.ERROR,
            details={"error_type": safe_error_type(err), "source": source},
        )
        await self._try_persist_integrity_result(result, source, record)

    def _cancel_integrity_check(
        self, record: BackupRecord, *, source: str, simulation_run: bool
    ) -> None:
        """Publish a cancelled verifier invocation."""
        del simulation_run
        self._progress_record = record
        self._verification_reporter.cancel()
        self._refresh_progress_data()
        self._record_activity(
            "integrity_check",
            ACTIVITY_OUTCOME_CANCELLED,
            details={"source": source},
        )

    async def _async_finish_integrity_task(
        self, *, simulation_run: bool, cancelled: bool
    ) -> None:
        """Release verifier state and refresh the inventory when appropriate."""
        del simulation_run
        self.integrity_verifier.set_progress_reporter(None)
        self.integrity_check_running = False
        self._integrity_task = release_current_task_reference(self._integrity_task)
        if cancelled:
            return
        try:
            await self.async_request_refresh()
        except Exception as err:  # noqa: BLE001 - coordinator boundary
            self._record_activity(
                "post_verification_refresh",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
                details={"error_type": safe_error_type(err)},
            )

    async def _async_run_integrity_check(
        self,
        record: BackupRecord,
        *,
        source: str,
    ) -> None:
        """Run, persist, and publish one full integrity check safely."""
        if self.integrity_check_running:
            return
        cancelled = False
        self.integrity_check_running = True
        simulation_run = source == "simulation"
        self._progress_record = record
        self._verification_reporter.start(reference=record.backup_reference)
        self.integrity_verifier.set_progress_reporter(self._verification_reporter)
        try:
            self._record_activity(
                "integrity_check",
                ACTIVITY_OUTCOME_STARTED,
                details={
                    "source": source,
                },
            )
            self._refresh_progress_data()
            result = await self.integrity_verifier.async_verify(
                record,
                database_check=self.database_integrity_check,
                max_download_gb=self.max_verification_size_gb,
                max_expanded_gb=self.max_expanded_size_gb,
                timeout_minutes=self.verification_timeout_minutes,
                database_timeout_minutes=self.database_timeout_minutes,
                repair_issues_enabled=self.repair_issues_enabled,
                staging_root=self.staging_root,
                verified_archive_callback=self._runtime_archive_callback(
                    record, simulation_run=simulation_run
                ),
            )
            await self._async_complete_integrity_check(
                record,
                result,
                source=source,
                simulation_run=simulation_run,
            )
        except asyncio.CancelledError:
            cancelled = True
            self._cancel_integrity_check(
                record, source=source, simulation_run=simulation_run
            )
            raise
        except Exception as err:  # noqa: BLE001 - full verification task boundary
            await self._async_fail_integrity_check(
                record,
                err,
                source=source,
                simulation_run=simulation_run,
            )
        finally:
            await self._async_finish_integrity_task(
                simulation_run=simulation_run, cancelled=cancelled
            )

    async def _async_run_runtime_test(
        self,
        record: BackupRecord,
        archive_path: Path,
        password: str | None,
        verified: BackupIntegrityResult,
    ) -> None:
        """Run the optional isolated phase while verified data still exists."""
        connection = self.runtime_runner_connection
        if connection is None or not verified.sha256:
            return

        self.integrity_result = verified
        self._progress_record = record
        # The verification keeps running: its cleanup step only starts once this
        # callback returns, so its result is published by the verifier itself.
        self._runtime_reporter.start(reference=record.backup_reference)
        self._record_activity("runtime_test", ACTIVITY_OUTCOME_STARTED)
        self._refresh_progress_data()
        started = time.monotonic()

        health = await self.async_check_runner(
            source=RUNNER_CHECK_SOURCE_PRE_RUN, maximum_age_seconds=60
        )
        if not health.usable:
            # An unreachable runner means the isolated test never ran. Reporting
            # it as an inconclusive result would contradict the empty pipeline.
            await self._async_finish_runtime_test(
                RuntimeTestSnapshot(
                    status=RUNTIME_STATUS_NOT_STARTED,
                    backup_reference=record.backup_reference,
                    backup_sha256=verified.sha256,
                    checked_at=dt_util.utcnow(),
                    duration_seconds=0.0,
                    runner_id=connection.runner_id,
                    runner_version=health.runner_version,
                    error_code=health.error_code or "runner_unavailable",
                ),
                outcome=ACTIVITY_OUTCOME_SKIPPED,
            )
            return

        try:
            client = RuntimeRunnerClient(
                async_get_clientsession(self.hass), connection
            )
            snapshot = await client.async_run(
                archive_path,
                backup_reference=record.backup_reference,
                backup_sha256=verified.sha256,
                password=password,
                maximum_archive_gb=self.runner_maximum_archive_gb,
                maximum_expanded_gb=self.runner_maximum_expanded_gb,
                timeout_minutes=self.runner_timeout_minutes,
                reporter=self._runtime_reporter,
            )
        except asyncio.CancelledError:
            self._runtime_reporter.cancel()
            self._refresh_progress_data()
            raise
        except RuntimeRunnerError as err:
            snapshot = self._runtime_failure_snapshot(
                record,
                verified,
                connection,
                started=started,
                error_code=err.code,
                status=runtime_status_for_error(err.code, phase=err.phase),
            )
        except Exception as err:  # noqa: BLE001 - optional runner boundary
            snapshot = self._runtime_failure_snapshot(
                record,
                verified,
                connection,
                started=started,
                error_code="runner_internal_error",
                status=JOB_INCONCLUSIVE,
            )
            _LOGGER.warning(
                "Runtime runner failed unexpectedly: error_type=%s",
                safe_error_type(err),
            )

        await self._async_finish_runtime_test(snapshot)

    def _runtime_failure_snapshot(
        self,
        record: BackupRecord,
        verified: BackupIntegrityResult,
        connection: RuntimeRunnerConnection,
        *,
        started: float,
        error_code: str,
        status: str,
    ) -> RuntimeTestSnapshot:
        """Build one bounded failure snapshot for a runner error."""
        return RuntimeTestSnapshot(
            status=status,
            backup_reference=record.backup_reference,
            backup_sha256=verified.sha256,
            checked_at=dt_util.utcnow(),
            duration_seconds=round(time.monotonic() - started, 2),
            runner_id=connection.runner_id,
            runner_version=self._runner_health.runner_version,
            error_code=error_code,
        )

    async def _async_finish_runtime_test(
        self, snapshot: RuntimeTestSnapshot, *, outcome: str | None = None
    ) -> None:
        """Persist, publish and journal one finished runtime test."""
        try:
            await self.runtime_tests.async_save(snapshot)
        except Exception as err:  # noqa: BLE001 - private store boundary
            _LOGGER.warning(
                "Unable to persist runtime-test result: error_type=%s",
                safe_error_type(err),
            )
        self._runtime_reporter.finish(
            snapshot.status, error_code=snapshot.error_code
        )
        self._record_activity(
            "runtime_test",
            outcome or _RUNTIME_ACTIVITY_OUTCOMES.get(
                snapshot.status, ACTIVITY_OUTCOME_FAILED
            ),
            level=logging.INFO if snapshot.passed is True else logging.WARNING,
            details={
                "status": snapshot.status,
                "error_code": snapshot.error_code or "none",
            },
        )
        self._refresh_progress_data()

    # -- companion runner health ------------------------------------------

    @property
    def runner_health(self) -> RunnerHealth:
        """Return the last known companion-runner state."""
        return self._runner_health

    async def async_check_runner(
        self,
        *,
        source: str,
        maximum_age_seconds: float | None = None,
    ) -> RunnerHealth:
        """Check the companion runner and publish one bounded result."""
        if self._runner_health_is_fresh(maximum_age_seconds):
            return self._runner_health
        async with self._runner_health_lock:
            if self._runner_health_is_fresh(maximum_age_seconds):
                return self._runner_health
            health = await self._async_request_runner_health(source)
            self._apply_runner_health(health)
            return health

    def _runner_health_is_fresh(self, maximum_age_seconds: float | None) -> bool:
        """Return whether the stored health is young enough to be reused."""
        if maximum_age_seconds is None:
            return False
        checked_at = self._runner_health.checked_at
        if checked_at is None:
            return False
        age = (dt_util.utcnow() - checked_at).total_seconds()
        return 0 <= age <= maximum_age_seconds

    async def _async_request_runner_health(self, source: str) -> RunnerHealth:
        """Ask the configured runner for its state without leaking its address."""
        connection = self.runtime_runner_connection
        if connection is None:
            return RunnerHealth.not_configured(check_source=source)
        try:
            client = RuntimeRunnerClient(
                async_get_clientsession(self.hass), connection
            )
        except RuntimeRunnerError as err:
            return RunnerHealth.unreachable(err.code, check_source=source)
        return await client.async_health(check_source=source)

    @callback
    def _apply_runner_health(self, health: RunnerHealth) -> None:
        """Store one health result and report repeated failures once."""
        self._runner_health = health
        if health.usable or not health.configured:
            # An installation without the optional add-on is not a failure.
            self._runner_health_failures = 0
        else:
            self._runner_health_failures += 1
            if self._runner_health_failures == _RUNNER_HEALTH_WARNING_THRESHOLD:
                _LOGGER.warning(
                    "Runtime runner unreachable: error_code=%s attempts=%d",
                    health.error_code or "unknown",
                    self._runner_health_failures,
                )
            else:
                _LOGGER.debug(
                    "Runtime runner check failed: error_code=%s",
                    health.error_code or "unknown",
                )
        async_dispatcher_send(
            self.hass, runner_signal(self.config_entry.entry_id)
        )
        if self.repair_issues_enabled:
            async_set_runner_issues(self.hass, health)

    @callback
    def async_start_runner_health_monitor(self) -> None:
        """Start the configurable background check for the companion runner."""
        self.async_stop_runner_health_monitor()
        minutes = self.runner_health_interval_minutes
        if minutes <= 0 or self.runtime_runner_connection is None:
            return
        self._runner_health_unsubscribe = async_track_time_interval(
            self.hass,
            self._async_scheduled_runner_check,
            timedelta(minutes=minutes),
        )

    @callback
    def async_stop_runner_health_monitor(self) -> None:
        """Stop the background runner check."""
        if self._runner_health_unsubscribe is not None:
            self._runner_health_unsubscribe()
            self._runner_health_unsubscribe = None

    async def _async_scheduled_runner_check(self, _now: datetime) -> None:
        """Run one interval check without destabilizing the event loop."""
        try:
            await self.async_check_runner(source=RUNNER_CHECK_SOURCE_INTERVAL)
        except Exception as err:  # noqa: BLE001 - optional runner boundary
            _LOGGER.debug(
                "Scheduled runtime-runner check failed: error_type=%s",
                safe_error_type(err),
            )

    async def _try_persist_integrity_result(
        self,
        result: BackupIntegrityResult,
        source: str,
        record: BackupRecord,
    ) -> None:
        """Persist a result without destabilizing the verification task."""
        try:
            await self._async_save_integrity_result(result)
        except Exception as err:  # noqa: BLE001 - Home Assistant Store boundary
            persist_retry = dt_util.utcnow() + _AUTOMATIC_RETRY_BASE
            if (
                self._integrity_retry_not_before is None
                or self._integrity_retry_not_before < persist_retry
            ):
                self._integrity_retry_not_before = persist_retry
            self._record_activity(
                "integrity_result_persist",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.ERROR,
                details={
                    "error_type": safe_error_type(err),
                    "source": source,
                },
            )

    @staticmethod
    def _internal_error_result(record: BackupRecord) -> BackupIntegrityResult:
        """Return one privacy-safe internal-error result."""
        return BackupIntegrityResult(
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

    # Compatibility wrappers retained for focused unit tests and downstream code.
    def _normalize_backups(
        self, backups: Mapping[str, Any]
    ) -> tuple[BackupRecord, ...]:
        """Normalize inventory through the dedicated defensive normalizer."""
        normalizer = getattr(self, "_normalizer", None)
        if normalizer is None:
            entry_id = getattr(
                getattr(self, "config_entry", None), "entry_id", "unknown"
            )
            normalizer = BackupRecordNormalizer(entry_id)
        result = normalizer.normalize(backups)
        self._invalid_backup_count = result.invalid_backups
        self._invalid_agent_copy_count = result.invalid_agent_copies
        return result.records

    @staticmethod
    def _status(**flags: bool) -> str:
        """Return the highest-priority status from the central problem table."""
        return evaluate_problem_state(flags).status
