"""Config flow for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MAX_AGE_DAYS,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_MAXIMUM_SIZE_DROP_PERCENT,
    MAX_MAX_AGE_DAYS,
    MAX_MINIMUM_BACKUP_SIZE_MB,
    MAX_REDUNDANT_LOCATIONS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_MAXIMUM_SIZE_DROP_PERCENT,
    MIN_MAX_AGE_DAYS,
    MIN_MINIMUM_BACKUP_SIZE_MB,
    MIN_REDUNDANT_LOCATIONS,
    MIN_UPDATE_INTERVAL_MINUTES,
    NAME,
)


def _schema(values: dict[str, int]) -> vol.Schema:
    """Return the configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_MAX_AGE_DAYS, default=values[CONF_MAX_AGE_DAYS]): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_MAX_AGE_DAYS, max=MAX_MAX_AGE_DAYS)
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=values[CONF_UPDATE_INTERVAL_MINUTES],
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_UPDATE_INTERVAL_MINUTES, max=MAX_UPDATE_INTERVAL_MINUTES),
            ),
            vol.Required(
                CONF_MINIMUM_BACKUP_SIZE_MB,
                default=values[CONF_MINIMUM_BACKUP_SIZE_MB],
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_MINIMUM_BACKUP_SIZE_MB, max=MAX_MINIMUM_BACKUP_SIZE_MB),
            ),
            vol.Required(
                CONF_MAXIMUM_SIZE_DROP_PERCENT,
                default=values[CONF_MAXIMUM_SIZE_DROP_PERCENT],
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_MAXIMUM_SIZE_DROP_PERCENT, max=MAX_MAXIMUM_SIZE_DROP_PERCENT),
            ),
            vol.Required(
                CONF_MINIMUM_REDUNDANT_LOCATIONS,
                default=values[CONF_MINIMUM_REDUNDANT_LOCATIONS],
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_REDUNDANT_LOCATIONS, max=MAX_REDUNDANT_LOCATIONS),
            ),
        }
    )


def _defaults() -> dict[str, int]:
    return {
        CONF_MAX_AGE_DAYS: DEFAULT_MAX_AGE_DAYS,
        CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
        CONF_MINIMUM_BACKUP_SIZE_MB: DEFAULT_MINIMUM_BACKUP_SIZE_MB,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    }


class BackupCheckupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BackupCheckup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(_defaults()))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return BackupCheckupOptionsFlow(config_entry)


class BackupCheckupOptionsFlow(config_entries.OptionsFlow):
    """Handle BackupCheckup options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage BackupCheckup options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        values = {
            key: int(self.config_entry.options.get(key, self.config_entry.data.get(key, default)))
            for key, default in _defaults().items()
        }
        return self.async_show_form(step_id="init", data_schema=_schema(values))
