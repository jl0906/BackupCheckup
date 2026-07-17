"""Config flow for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
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

from .configuration import normalize_configuration
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
    DOMAIN,
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
    NAME,
    PROFILE_CUSTOM,
    PROFILE_OPTIONS,
    PROFILE_SECURE,
    PROFILE_STANDARD,
    SIZE_CHECK_AUTO,
    SIZE_CHECK_FIXED,
    SIZE_CHECK_OPTIONS,
)
from .entity_mode import async_apply_entity_mode
from .notification_selection import (
    mobile_notification_options,
    normalize_notification_targets,
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
        CONF_MAX_VERIFICATION_SIZE_GB: DEFAULT_MAX_VERIFICATION_SIZE_GB,
        CONF_MAX_EXPANDED_SIZE_GB: DEFAULT_MAX_EXPANDED_SIZE_GB,
        CONF_VERIFICATION_TIMEOUT_MINUTES: DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
        CONF_DATABASE_TIMEOUT_MINUTES: DEFAULT_DATABASE_TIMEOUT_MINUTES,
        CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
            DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES
        ),
        CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
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
        CONF_MAX_VERIFICATION_SIZE_GB: DEFAULT_MAX_VERIFICATION_SIZE_GB,
        CONF_MAX_EXPANDED_SIZE_GB: DEFAULT_MAX_EXPANDED_SIZE_GB,
        CONF_VERIFICATION_TIMEOUT_MINUTES: DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
        CONF_DATABASE_TIMEOUT_MINUTES: DEFAULT_DATABASE_TIMEOUT_MINUTES,
        CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
            DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES
        ),
        CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
    },
}


def _profile_schema(
    hass: HomeAssistant,
    default: str,
    entity_mode: str,
    notifications: dict[str, Any],
) -> vol.Schema:
    """Return monitoring, entity-mode, and mobile-notification selectors."""
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
            ),
            vol.Required(
                CONF_ENTITY_MODE,
                default=entity_mode,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=ENTITY_MODE_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="entity_mode",
                )
            ),
            vol.Required(
                CONF_NOTIFICATIONS_ENABLED,
                default=bool(notifications[CONF_NOTIFICATIONS_ENABLED]),
            ): BooleanSelector(),
            vol.Optional(
                CONF_NOTIFICATION_TARGETS,
                default=list(notifications[CONF_NOTIFICATION_TARGETS]),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=mobile_notification_options(
                        hass, notifications[CONF_NOTIFICATION_TARGETS]
                    ),
                    multiple=True,
                    custom_value=False,
                    mode=SelectSelectorMode.LIST,
                    sort=True,
                )
            ),
            vol.Required(
                CONF_NOTIFY_ON_RECOVERY,
                default=bool(notifications[CONF_NOTIFY_ON_RECOVERY]),
            ): BooleanSelector(),
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
            vol.Required(
                CONF_MAX_VERIFICATION_SIZE_GB,
                default=values[CONF_MAX_VERIFICATION_SIZE_GB],
            ): _integer_selector(
                MIN_MAX_VERIFICATION_SIZE_GB,
                MAX_MAX_VERIFICATION_SIZE_GB,
            ),
            vol.Required(
                CONF_MAX_EXPANDED_SIZE_GB,
                default=values[CONF_MAX_EXPANDED_SIZE_GB],
            ): _integer_selector(
                MIN_MAX_EXPANDED_SIZE_GB,
                MAX_MAX_EXPANDED_SIZE_GB,
            ),
            vol.Required(
                CONF_VERIFICATION_TIMEOUT_MINUTES,
                default=values[CONF_VERIFICATION_TIMEOUT_MINUTES],
            ): _integer_selector(
                MIN_VERIFICATION_TIMEOUT_MINUTES,
                MAX_VERIFICATION_TIMEOUT_MINUTES,
            ),
            vol.Required(
                CONF_DATABASE_TIMEOUT_MINUTES,
                default=values[CONF_DATABASE_TIMEOUT_MINUTES],
            ): _integer_selector(
                MIN_DATABASE_TIMEOUT_MINUTES,
                MAX_DATABASE_TIMEOUT_MINUTES,
            ),
            vol.Required(
                CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
                default=values[CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES],
            ): _integer_selector(
                MIN_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
                MAX_MANUAL_VERIFICATION_COOLDOWN_MINUTES,
            ),
            vol.Required(
                CONF_EXPOSE_BACKUP_METADATA,
                default=values[CONF_EXPOSE_BACKUP_METADATA],
            ): BooleanSelector(),
        }
    )


def _monitoring_defaults() -> dict[str, Any]:
    """Return all monitoring defaults."""
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
        CONF_MAX_VERIFICATION_SIZE_GB: DEFAULT_MAX_VERIFICATION_SIZE_GB,
        CONF_MAX_EXPANDED_SIZE_GB: DEFAULT_MAX_EXPANDED_SIZE_GB,
        CONF_VERIFICATION_TIMEOUT_MINUTES: DEFAULT_VERIFICATION_TIMEOUT_MINUTES,
        CONF_DATABASE_TIMEOUT_MINUTES: DEFAULT_DATABASE_TIMEOUT_MINUTES,
        CONF_MANUAL_VERIFICATION_COOLDOWN_MINUTES: (
            DEFAULT_MANUAL_VERIFICATION_COOLDOWN_MINUTES
        ),
        CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
    }


def _notification_defaults() -> dict[str, Any]:
    """Return mobile-notification defaults."""
    return {
        CONF_NOTIFICATIONS_ENABLED: DEFAULT_NOTIFICATIONS_ENABLED,
        CONF_NOTIFICATION_TARGETS: list(DEFAULT_NOTIFICATION_TARGETS),
        CONF_NOTIFY_ON_RECOVERY: DEFAULT_NOTIFY_ON_RECOVERY,
    }


def _notification_values(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize selected notification settings."""
    return {
        CONF_NOTIFICATIONS_ENABLED: bool(user_input[CONF_NOTIFICATIONS_ENABLED]),
        CONF_NOTIFICATION_TARGETS: normalize_notification_targets(
            user_input.get(CONF_NOTIFICATION_TARGETS)
        ),
        CONF_NOTIFY_ON_RECOVERY: bool(user_input[CONF_NOTIFY_ON_RECOVERY]),
    }


def _validate_profile_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate notification settings from the profile step."""
    if bool(user_input[CONF_NOTIFICATIONS_ENABLED]) and not user_input.get(
        CONF_NOTIFICATION_TARGETS
    ):
        return {CONF_NOTIFICATION_TARGETS: "notification_target_required"}
    return {}


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

    VERSION = 9

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._profile = DEFAULT_MONITORING_PROFILE
        self._entity_mode = DEFAULT_ENTITY_MODE
        self._notifications = _notification_defaults()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose a profile and optional mobile notifications."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_profile_input(user_input)
            if not errors:
                self._profile = str(user_input[CONF_MONITORING_PROFILE])
                self._entity_mode = str(user_input[CONF_ENTITY_MODE])
                self._notifications = _notification_values(user_input)
                if self._profile in PROFILE_PRESETS:
                    return self.async_create_entry(
                        title=NAME,
                        data={
                            CONF_MONITORING_PROFILE: self._profile,
                            CONF_ENTITY_MODE: self._entity_mode,
                            **PROFILE_PRESETS[self._profile],
                            **self._notifications,
                        },
                    )
                return await self.async_step_advanced()

        values = _notification_defaults()
        if user_input is not None:
            values.update(_notification_values(user_input))
        return self.async_show_form(
            step_id="user",
            data_schema=_profile_schema(
                self.hass,
                str(
                    user_input.get(CONF_MONITORING_PROFILE, DEFAULT_MONITORING_PROFILE)
                    if user_input
                    else DEFAULT_MONITORING_PROFILE
                ),
                str(
                    user_input.get(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)
                    if user_input
                    else DEFAULT_ENTITY_MODE
                ),
                values,
            ),
            errors=errors,
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
                        CONF_ENTITY_MODE: self._entity_mode,
                        **user_input,
                        **self._notifications,
                    },
                )

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(user_input or _monitoring_defaults()),
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

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._notifications = _notification_defaults()
        self._entity_mode = DEFAULT_ENTITY_MODE
        self._previous_entity_mode = DEFAULT_ENTITY_MODE

    def _current_snapshot(self) -> dict[str, Any]:
        """Return a fully normalized snapshot for the first and later form opens."""
        return normalize_configuration(
            self.config_entry.data,
            self.config_entry.options,
        )

    def _current(self, key: str, default: Any) -> Any:
        """Return one normalized option with a defensive fallback."""
        return self._current_snapshot().get(key, default)

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose monitoring, entity, and mobile-notification options."""
        errors: dict[str, str] = {}
        self._previous_entity_mode = str(
            self._current(CONF_ENTITY_MODE, DEFAULT_ENTITY_MODE)
        )
        if user_input is not None:
            errors = _validate_profile_input(user_input)
            if not errors:
                profile = str(user_input[CONF_MONITORING_PROFILE])
                self._entity_mode = str(user_input[CONF_ENTITY_MODE])
                self._notifications = _notification_values(user_input)
                if profile in PROFILE_PRESETS:
                    if self._entity_mode != self._previous_entity_mode:
                        async_apply_entity_mode(
                            self.hass,
                            self.config_entry,
                            self._entity_mode,
                        )
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_MONITORING_PROFILE: profile,
                            CONF_ENTITY_MODE: self._entity_mode,
                            **PROFILE_PRESETS[profile],
                            **self._notifications,
                        },
                    )
                return await self.async_step_advanced()

        profile = str(self._current(CONF_MONITORING_PROFILE, PROFILE_CUSTOM))
        entity_mode = self._previous_entity_mode
        notifications = {
            CONF_NOTIFICATIONS_ENABLED: self._current(
                CONF_NOTIFICATIONS_ENABLED,
                DEFAULT_NOTIFICATIONS_ENABLED,
            ),
            CONF_NOTIFICATION_TARGETS: normalize_notification_targets(
                self._current(
                    CONF_NOTIFICATION_TARGETS,
                    DEFAULT_NOTIFICATION_TARGETS,
                )
            ),
            CONF_NOTIFY_ON_RECOVERY: self._current(
                CONF_NOTIFY_ON_RECOVERY,
                DEFAULT_NOTIFY_ON_RECOVERY,
            ),
        }
        if user_input is not None:
            profile = str(user_input[CONF_MONITORING_PROFILE])
            entity_mode = str(user_input[CONF_ENTITY_MODE])
            notifications.update(_notification_values(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=_profile_schema(self.hass, profile, entity_mode, notifications),
            errors=errors,
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
                if self._entity_mode != self._previous_entity_mode:
                    async_apply_entity_mode(
                        self.hass,
                        self.config_entry,
                        self._entity_mode,
                    )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_MONITORING_PROFILE: PROFILE_CUSTOM,
                        CONF_ENTITY_MODE: self._entity_mode,
                        **user_input,
                        **self._notifications,
                    },
                )

        values = {
            key: self._current(key, default)
            for key, default in _monitoring_defaults().items()
        }
        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(user_input or values),
            errors=errors,
        )
