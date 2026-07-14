"""Data coordinator for BackupCheckup."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
import logging
from math import floor
from typing import Any

from homeassistant.components.backup import async_get_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MAX_AGE_DAYS,
    CONF_UPDATE_INTERVAL_MINUTES,
    CORE_BACKUP_MANAGER_STATE,
    CORE_LAST_AUTOMATIC_ATTEMPT,
    CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP,
    CORE_NEXT_AUTOMATIC_BACKUP,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    STATUS_AUTOMATIC_BACKUP_FAILED,
    STATUS_AUTOMATIC_BACKUP_OVERDUE,
    STATUS_BACKUP_STALE,
    STATUS_MANAGER_UNAVAILABLE,
    STATUS_NO_BACKUPS,
    STATUS_OK,
    STATUS_SCHEDULE_MISSING,
    STATUS_SCHEDULE_OVERDUE,
    STATUS_STORAGE_ERROR,
)
from .models import BackupCheckupData, BackupRecord

_LOGGER = logging.getLogger(__name__)


class BackupCheckupCoordinator(DataUpdateCoordinator[BackupCheckupData]):
    """Fetch and evaluate the actual Home Assistant backup inventory."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.max_age_days = int(
            entry.options.get(
                CONF_MAX_AGE_DAYS,
                entry.data.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS),
            )
        )
        update_minutes = int(
            entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            )
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_minutes),
        )

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
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE, "", "none"}:
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

    async def _async_update_data(self) -> BackupCheckupData:
        """Read and evaluate the backup inventory."""
        try:
            manager = async_get_manager(self.hass)
            backups, agent_errors_raw = await manager.async_get_backups()
        except HomeAssistantError as err:
            raise UpdateFailed(f"Home Assistant backup manager is not ready: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unable to read Home Assistant backups: {err}") from err

        now = dt_util.utcnow()
        records: list[BackupRecord] = []

        for backup in backups.values():
            backup_date = self._as_datetime(getattr(backup, "date", None))
            if backup_date is None:
                _LOGGER.warning(
                    "Ignoring backup %s because its date is invalid",
                    getattr(backup, "backup_id", "unknown"),
                )
                continue

            agents_raw = getattr(backup, "agents", {})
            if isinstance(agents_raw, Mapping):
                agents = tuple(sorted(str(agent_id) for agent_id in agents_raw))
            else:
                agents = tuple(sorted(str(agent_id) for agent_id in (agents_raw or [])))

            failed_agents = tuple(
                sorted(
                    str(agent_id)
                    for agent_id in (getattr(backup, "failed_agent_ids", []) or [])
                )
            )
            size_raw = getattr(backup, "size", None)
            size = int(size_raw) if isinstance(size_raw, (int, float)) else None

            records.append(
                BackupRecord(
                    backup_id=str(getattr(backup, "backup_id", "")),
                    name=str(getattr(backup, "name", "")),
                    date=backup_date,
                    automatic=getattr(backup, "with_automatic_settings", None) is True,
                    agents=agents,
                    failed_agents=failed_agents,
                    size=size,
                )
            )

        records.sort(key=lambda item: item.date, reverse=True)
        automatic_records = [item for item in records if item.automatic]
        manual_records = [item for item in records if not item.automatic]

        latest_backup = records[0].date if records else None
        latest_automatic = automatic_records[0].date if automatic_records else None
        latest_manual = manual_records[0].date if manual_records else None

        latest_age = self._age_days(now, latest_backup)
        automatic_age_precise = self._age_days(now, latest_automatic)
        automatic_age = self._completed_days(automatic_age_precise)
        manual_age = self._age_days(now, latest_manual)

        last_automatic_attempt = self._entity_datetime(CORE_LAST_AUTOMATIC_ATTEMPT)
        last_successful_automatic_event = self._entity_datetime(
            CORE_LAST_SUCCESSFUL_AUTOMATIC_BACKUP
        )
        next_automatic = self._entity_datetime(CORE_NEXT_AUTOMATIC_BACKUP)
        manager_state = self._entity_state(CORE_BACKUP_MANAGER_STATE)

        no_backup = len(records) == 0
        backup_stale = latest_age is not None and latest_age > self.max_age_days

        manual_covers_automatic = (
            latest_manual is not None
            and (latest_automatic is None or latest_manual > latest_automatic)
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

        automatic_backup_failed = (
            last_automatic_attempt is not None
            and (
                last_successful_automatic_event is None
                or last_automatic_attempt
                > last_successful_automatic_event + timedelta(seconds=60)
            )
        )
        automatic_schedule_missing = next_automatic is None
        automatic_schedule_overdue = (
            next_automatic is not None
            and next_automatic < now - timedelta(hours=6)
        )
        manager_unavailable = manager_state in {
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
            "none",
            "",
        }
        agent_errors = {
            str(agent_id): f"{type(error).__name__}: {error}"
            for agent_id, error in agent_errors_raw.items()
        }
        storage_error = bool(agent_errors)

        if no_backup:
            status = STATUS_NO_BACKUPS
        elif manager_unavailable:
            status = STATUS_MANAGER_UNAVAILABLE
        elif automatic_schedule_missing:
            status = STATUS_SCHEDULE_MISSING
        elif storage_error:
            status = STATUS_STORAGE_ERROR
        elif automatic_backup_failed:
            status = STATUS_AUTOMATIC_BACKUP_FAILED
        elif automatic_backup_overdue:
            status = STATUS_AUTOMATIC_BACKUP_OVERDUE
        elif backup_stale:
            status = STATUS_BACKUP_STALE
        elif automatic_schedule_overdue:
            status = STATUS_SCHEDULE_OVERDUE
        else:
            status = STATUS_OK

        problem = any(
            (
                no_backup,
                backup_stale,
                automatic_backup_overdue,
                automatic_backup_failed,
                automatic_schedule_missing,
                automatic_schedule_overdue,
                manager_unavailable,
                storage_error,
            )
        )

        return BackupCheckupData(
            checked_at=now,
            max_age_days=self.max_age_days,
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
            last_automatic_attempt=last_automatic_attempt,
            last_successful_automatic_event=last_successful_automatic_event,
            next_automatic_backup=next_automatic,
            manager_state=manager_state,
            agent_errors=agent_errors,
            backups=tuple(records),
            no_backup=no_backup,
            backup_stale=backup_stale,
            automatic_backup_overdue=automatic_backup_overdue,
            automatic_backup_failed=automatic_backup_failed,
            automatic_schedule_missing=automatic_schedule_missing,
            automatic_schedule_overdue=automatic_schedule_overdue,
            manager_unavailable=manager_unavailable,
            storage_error=storage_error,
            problem=problem,
            status=status,
        )
