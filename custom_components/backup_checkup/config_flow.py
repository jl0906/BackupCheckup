"""Config flow for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MAX_AGE_DAYS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_MAX_AGE_DAYS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_MAX_AGE_DAYS,
    MIN_UPDATE_INTERVAL_MINUTES,
    NAME,
)


def _schema(max_age_days: int, update_interval_minutes: int) -> vol.Schema:
    """Return the configuration schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MAX_AGE_DAYS,
                default=max_age_days,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_MAX_AGE_DAYS, max=MAX_MAX_AGE_DAYS),
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=update_interval_minutes,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_UPDATE_INTERVAL_MINUTES,
                    max=MAX_UPDATE_INTERVAL_MINUTES,
                ),
            ),
        }
    )


class BackupCheckupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BackupCheckup."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                DEFAULT_MAX_AGE_DAYS,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BackupCheckupOptionsFlow(config_entry)


class BackupCheckupOptionsFlow(config_entries.OptionsFlow):
    """Handle BackupCheckup options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage BackupCheckup options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        max_age_days = int(
            self.config_entry.options.get(
                CONF_MAX_AGE_DAYS,
                self.config_entry.data.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS),
            )
        )
        update_interval = int(
            self.config_entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                self.config_entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(max_age_days, update_interval),
        )
