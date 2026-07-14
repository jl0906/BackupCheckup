"""Config flow for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ANALYTICS_WINDOW_DAYS,
    CONF_AUTO_VERIFY_NEW_BACKUPS,
    CONF_DATABASE_INTEGRITY_CHECK,
    CONF_MAX_AGE_DAYS,
    CONF_MAXIMUM_SIZE_DROP_PERCENT,
    CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS,
    CONF_MONITORING_PROFILE,
    CONF_REPAIR_ISSUES_ENABLED,
    CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_ANALYTICS_WINDOW_DAYS,
    DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
    DEFAULT_DATABASE_INTEGRITY_CHECK,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB,
    DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_MONITORING_PROFILE,
    DEFAULT_REPAIR_ISSUES_ENABLED,
    DEFAULT_SIZE_CHECK_MODE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_ANALYTICS_WINDOW_DAYS,
    MAX_MAX_AGE_DAYS,
    MAX_MAXIMUM_SIZE_DROP_PERCENT,
    MAX_MINIMUM_BACKUP_SIZE_MB,
    MAX_REDUNDANT_LOCATIONS,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_ANALYTICS_WINDOW_DAYS,
    MIN_MAX_AGE_DAYS,
    MIN_MAXIMUM_SIZE_DROP_PERCENT,
    MIN_MINIMUM_BACKUP_SIZE_MB,
    MIN_REDUNDANT_LOCATIONS,
    MIN_UPDATE_INTERVAL_MINUTES,
    NAME,
    PROFILE_CUSTOM,
    PROFILE_OPTIONS,
    PROFILE_SECURE,
    PROFILE_STANDARD,
    SIZE_CHECK_AUTO,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OPTIONS,
)

PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    PROFILE_STANDARD: {
        CONF_MAX_AGE_DAYS: 4,
        CONF_UPDATE_INTERVAL_MINUTES: 5,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: 50,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 1,
        CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
        CONF_REPAIR_ISSUES_ENABLED: True,
        CONF_ANALYTICS_WINDOW_DAYS: 30,
        CONF_AUTO_VERIFY_NEW_BACKUPS: False,
        CONF_DATABASE_INTEGRITY_CHECK: False,
    },
    PROFILE_SECURE: {
        CONF_MAX_AGE_DAYS: 2,
        CONF_UPDATE_INTERVAL_MINUTES: 2,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: 35,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 2,
        CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
        CONF_REPAIR_ISSUES_ENABLED: True,
        CONF_ANALYTICS_WINDOW_DAYS: 30,
        CONF_AUTO_VERIFY_NEW_BACKUPS: False,
        CONF_DATABASE_INTEGRITY_CHECK: False,
    },
}


def _profile_schema(default: str) -> vol.Schema:
    """Return the monitoring profile selector."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MONITORING_PROFILE,
                default=default,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=PROFILE_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="monitoring_profile",
                )
            )
        }
    )


def _integer_selector(minimum: int, maximum: int) -> NumberSelector:
    """Return a whole-number selector."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )


def _advanced_schema(values: dict[str, Any]) -> vol.Schema:
    """Return the custom monitoring schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MAX_AGE_DAYS,
                default=values[CONF_MAX_AGE_DAYS],
            ): _integer_selector(MIN_MAX_AGE_DAYS, MAX_MAX_AGE_DAYS),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=values[CONF_UPDATE_INTERVAL_MINUTES],
            ): _integer_selector(
                MIN_UPDATE_INTERVAL_MINUTES,
                MAX_UPDATE_INTERVAL_MINUTES,
            ),
            vol.Required(
                CONF_SIZE_CHECK_MODE,
                default=values[CONF_SIZE_CHECK_MODE],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=SIZE_CHECK_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="size_check_mode",
                )
            ),
            vol.Required(
                CONF_MINIMUM_BACKUP_SIZE_MB,
                default=values[CONF_MINIMUM_BACKUP_SIZE_MB],
            ): _integer_selector(
                MIN_MINIMUM_BACKUP_SIZE_MB,
                MAX_MINIMUM_BACKUP_SIZE_MB,
            ),
            vol.Required(
                CONF_MAXIMUM_SIZE_DROP_PERCENT,
                default=values[CONF_MAXIMUM_SIZE_DROP_PERCENT],
            ): _integer_selector(
                MIN_MAXIMUM_SIZE_DROP_PERCENT,
                MAX_MAXIMUM_SIZE_DROP_PERCENT,
            ),
            vol.Required(
                CONF_MINIMUM_REDUNDANT_LOCATIONS,
                default=values[CONF_MINIMUM_REDUNDANT_LOCATIONS],
            ): _integer_selector(
                MIN_REDUNDANT_LOCATIONS,
                MAX_REDUNDANT_LOCATIONS,
            ),
            vol.Required(
                CONF_REPAIR_ISSUES_ENABLED,
                default=values[CONF_REPAIR_ISSUES_ENABLED],
            ): BooleanSelector(),
            vol.Required(
                CONF_ANALYTICS_WINDOW_DAYS,
                default=values[CONF_ANALYTICS_WINDOW_DAYS],
            ): _integer_selector(
                MIN_ANALYTICS_WINDOW_DAYS,
                MAX_ANALYTICS_WINDOW_DAYS,
            ),
            vol.Required(
                CONF_AUTO_VERIFY_NEW_BACKUPS,
                default=values[CONF_AUTO_VERIFY_NEW_BACKUPS],
            ): BooleanSelector(),
            vol.Required(
                CONF_DATABASE_INTEGRITY_CHECK,
                default=values[CONF_DATABASE_INTEGRITY_CHECK],
            ): BooleanSelector(),
        }
    )


def _defaults() -> dict[str, Any]:
    """Return all configurable defaults."""
    return {
        CONF_MAX_AGE_DAYS: DEFAULT_MAX_AGE_DAYS,
        CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
        CONF_MINIMUM_BACKUP_SIZE_MB: DEFAULT_MINIMUM_BACKUP_SIZE_MB,
        CONF_MAXIMUM_SIZE_DROP_PERCENT: DEFAULT_MAXIMUM_SIZE_DROP_PERCENT,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
        CONF_SIZE_CHECK_MODE: DEFAULT_SIZE_CHECK_MODE,
        CONF_REPAIR_ISSUES_ENABLED: DEFAULT_REPAIR_ISSUES_ENABLED,
        CONF_ANALYTICS_WINDOW_DAYS: DEFAULT_ANALYTICS_WINDOW_DAYS,
        CONF_AUTO_VERIFY_NEW_BACKUPS: DEFAULT_AUTO_VERIFY_NEW_BACKUPS,
        CONF_DATABASE_INTEGRITY_CHECK: DEFAULT_DATABASE_INTEGRITY_CHECK,
    }


def _validate_advanced_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate combinations that cannot be expressed in the schema."""
    if (
        user_input[CONF_SIZE_CHECK_MODE] == SIZE_CHECK_FIXED
        and int(user_input[CONF_MINIMUM_BACKUP_SIZE_MB]) == 0
    ):
        return {"base": "fixed_size_required"}
    return {}


class BackupCheckupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the BackupCheckup configuration flow."""

    VERSION = 3

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._profile = DEFAULT_MONITORING_PROFILE

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose a ready-to-use profile."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self._profile = str(user_input[CONF_MONITORING_PROFILE])
            if self._profile in PROFILE_PRESETS:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_MONITORING_PROFILE: self._profile,
                        **PROFILE_PRESETS[self._profile],
                    },
                )
            return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user",
            data_schema=_profile_schema(DEFAULT_MONITORING_PROFILE),
        )

    async def async_step_advanced(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure all monitoring thresholds."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_advanced_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_MONITORING_PROFILE: PROFILE_CUSTOM,
                        **user_input,
                    },
                )

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(user_input or _defaults()),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BackupCheckupOptionsFlow()


class BackupCheckupOptionsFlow(config_entries.OptionsFlow):
    """Handle BackupCheckup options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose a profile or open custom settings."""
        if user_input is not None:
            profile = str(user_input[CONF_MONITORING_PROFILE])
            if profile in PROFILE_PRESETS:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_MONITORING_PROFILE: profile,
                        **PROFILE_PRESETS[profile],
                    },
                )
            return await self.async_step_advanced()

        profile = str(
            self.config_entry.options.get(
                CONF_MONITORING_PROFILE,
                self.config_entry.data.get(
                    CONF_MONITORING_PROFILE,
                    PROFILE_CUSTOM,
                ),
            )
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_profile_schema(profile),
        )

    async def async_step_advanced(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Edit every monitoring threshold."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_advanced_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_MONITORING_PROFILE: PROFILE_CUSTOM,
                        **user_input,
                    },
                )

        values = {
            key: self.config_entry.options.get(
                key,
                self.config_entry.data.get(key, default),
            )
            for key, default in _defaults().items()
        }
        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(user_input or values),
            errors=errors,
        )
