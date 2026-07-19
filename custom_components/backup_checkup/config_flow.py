"""Guided config and options flows for BackupCheckup."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .configuration import normalize_configuration
from .const import (
    CONF_ADAPTIVE_POLLING,
    CONF_ENTITY_MODE,
    CONF_EXPOSE_BACKUP_METADATA,
    CONF_HARDWARE_DETECTION,
    CONF_MAX_EXPANDED_SIZE_GB,
    CONF_MAX_VERIFICATION_SIZE_GB,
    CONF_MONITORING_POLICY,
    CONF_NOTIFICATION_TARGETS,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_ON_RECOVERY,
    CONF_PRESET_REVISION,
    CONF_RUNTIME_PROFILE,
    CONF_SIZE_CHECK_MODE,
    CONF_VERIFICATION_POLICY,
    DEFAULT_ENTITY_MODE,
    DEFAULT_EXPOSE_BACKUP_METADATA,
    DEFAULT_MONITORING_POLICY,
    DEFAULT_NOTIFICATION_TARGETS,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFY_ON_RECOVERY,
    DEFAULT_VERIFICATION_POLICY,
    DOMAIN,
    MAX_MAX_EXPANDED_SIZE_GB,
    MONITORING_POLICY_CUSTOM,
    NAME,
    PRESET_REVISION,
    RUNTIME_PROFILE_CUSTOM,
    RUNTIME_PROFILE_LEGACY,
    SIZE_CHECK_FIXED,
    VERIFICATION_POLICY_CUSTOM,
)
from .flow_schemas import (
    CONF_CONFIRM,
    monitoring_custom_schema,
    monitoring_policy_schema,
    presentation_schema,
    runtime_custom_schema,
    runtime_profile_schema,
    summary_schema,
    verification_policy_schema,
)
from .hardware_profile import HardwareSnapshot, async_detect_hardware
from .notification_selection import normalize_notification_targets
from .presets import monitoring_values, runtime_values, verification_values
from .setup_recommendation import async_recommended_verification_size_gb

_OPTIONS_MENU = (
    "runtime",
    "monitoring",
    "verification",
    "presentation",
    "setup_assistant",
)


def _notification_values(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize selected notification settings."""
    return {
        CONF_NOTIFICATIONS_ENABLED: bool(user_input[CONF_NOTIFICATIONS_ENABLED]),
        CONF_NOTIFICATION_TARGETS: normalize_notification_targets(
            user_input.get(CONF_NOTIFICATION_TARGETS)
        ),
        CONF_NOTIFY_ON_RECOVERY: bool(user_input[CONF_NOTIFY_ON_RECOVERY]),
    }


def _validate_notifications(user_input: dict[str, Any]) -> dict[str, str]:
    """Require a target whenever mobile notifications are enabled."""
    if bool(user_input[CONF_NOTIFICATIONS_ENABLED]) and not user_input.get(
        CONF_NOTIFICATION_TARGETS
    ):
        return {CONF_NOTIFICATION_TARGETS: "notification_target_required"}
    return {}


def _validate_monitoring(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate combinations not expressible by selectors alone."""
    if (
        user_input[CONF_SIZE_CHECK_MODE] == SIZE_CHECK_FIXED
        and int(user_input.get("minimum_backup_size_mb", 0)) == 0
    ):
        return {"base": "fixed_size_required"}
    return {}


def _validate_runtime(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate custom adaptive polling intervals."""
    if int(user_input["active_update_interval_minutes"]) > int(
        user_input["update_interval_minutes"]
    ):
        return {"base": "active_interval_too_slow"}
    if int(user_input["error_backoff_interval_minutes"]) < int(
        user_input["update_interval_minutes"]
    ):
        return {"base": "backoff_interval_too_fast"}
    return {}


def _new_configuration(snapshot: HardwareSnapshot) -> dict[str, Any]:
    """Return resolved defaults for a new installation."""
    runtime_profile = snapshot.recommended_profile
    return normalize_configuration(
        {
            CONF_RUNTIME_PROFILE: runtime_profile,
            CONF_MONITORING_POLICY: DEFAULT_MONITORING_POLICY,
            CONF_VERIFICATION_POLICY: DEFAULT_VERIFICATION_POLICY,
            CONF_PRESET_REVISION: PRESET_REVISION,
            CONF_HARDWARE_DETECTION: snapshot.as_dict(),
            CONF_ENTITY_MODE: DEFAULT_ENTITY_MODE,
            CONF_NOTIFICATIONS_ENABLED: DEFAULT_NOTIFICATIONS_ENABLED,
            CONF_NOTIFICATION_TARGETS: list(DEFAULT_NOTIFICATION_TARGETS),
            CONF_NOTIFY_ON_RECOVERY: DEFAULT_NOTIFY_ON_RECOVERY,
            CONF_EXPOSE_BACKUP_METADATA: DEFAULT_EXPOSE_BACKUP_METADATA,
            **runtime_values(runtime_profile),
            **monitoring_values(DEFAULT_MONITORING_POLICY),
            **verification_values(DEFAULT_VERIFICATION_POLICY),
        }
    )


def _summary_placeholders(values: dict[str, Any]) -> dict[str, str]:
    """Return localized summary values without exposing sensitive identifiers."""
    hardware = values.get(CONF_HARDWARE_DETECTION, {})
    board = hardware.get("board")
    architecture = hardware.get("architecture")
    hardware_name = (
        board
        if isinstance(board, str) and board != "unknown"
        else architecture
        if isinstance(architecture, str) and architecture != "unknown"
        else "unknown"
    )
    verification = values[CONF_VERIFICATION_POLICY]
    if verification == VERIFICATION_POLICY_CUSTOM:
        verification = "custom"
    return {
        "hardware": str(hardware_name),
        "runtime_profile": str(values[CONF_RUNTIME_PROFILE]),
        "update_interval": str(values["update_interval_minutes"]),
        "download_limit": str(values[CONF_MAX_VERIFICATION_SIZE_GB]),
        "adaptive_polling": "enabled" if values[CONF_ADAPTIVE_POLLING] else "disabled",
        "monitoring_policy": str(values[CONF_MONITORING_POLICY]),
        "verification_policy": str(verification),
        "entity_mode": str(values[CONF_ENTITY_MODE]),
        "notification_count": str(len(values[CONF_NOTIFICATION_TARGETS])),
    }


class _GuidedFlowState:
    """Shared state helpers for initial setup and the options setup assistant."""

    _draft: dict[str, Any]
    _hardware: HardwareSnapshot | None
    _recommended_verification_size_gb: int | None

    def _apply_inventory_size_recommendation(self) -> None:
        """Ensure profile limits can hold the largest currently known backup."""
        minimum = self._recommended_verification_size_gb
        if minimum is None:
            return
        self._draft[CONF_MAX_VERIFICATION_SIZE_GB] = max(
            self._draft[CONF_MAX_VERIFICATION_SIZE_GB], minimum
        )
        self._draft[CONF_MAX_EXPANDED_SIZE_GB] = min(
            MAX_MAX_EXPANDED_SIZE_GB,
            max(self._draft[CONF_MAX_EXPANDED_SIZE_GB], minimum * 5),
        )

    def _apply_runtime_profile(self, profile: str, adaptive: bool) -> None:
        self._draft[CONF_RUNTIME_PROFILE] = profile
        self._draft[CONF_ADAPTIVE_POLLING] = adaptive
        if profile != RUNTIME_PROFILE_CUSTOM:
            self._draft.update(runtime_values(profile, adaptive_polling=adaptive))
            self._apply_inventory_size_recommendation()

    def _apply_monitoring_policy(self, policy: str) -> None:
        self._draft[CONF_MONITORING_POLICY] = policy
        if policy != MONITORING_POLICY_CUSTOM:
            self._draft.update(monitoring_values(policy))

    def _apply_verification_policy(self, policy: str) -> None:
        self._draft[CONF_VERIFICATION_POLICY] = policy
        self._draft.update(verification_values(policy))

    def _apply_presentation(self, user_input: dict[str, Any]) -> None:
        self._draft[CONF_ENTITY_MODE] = str(user_input[CONF_ENTITY_MODE])
        self._draft[CONF_EXPOSE_BACKUP_METADATA] = bool(
            user_input[CONF_EXPOSE_BACKUP_METADATA]
        )
        self._draft.update(_notification_values(user_input))


class BackupCheckupConfigFlow(
    _GuidedFlowState, config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle the guided BackupCheckup installation flow."""

    VERSION = 10

    def __init__(self) -> None:
        """Initialize an empty guided flow."""
        self._draft = {}
        self._hardware = None
        self._recommended_verification_size_gb = None

    async def _async_prepare(self) -> None:
        """Detect hardware once and prepare resolved defaults."""
        if self._hardware is not None:
            return
        self._hardware = await async_detect_hardware(self.hass)
        self._recommended_verification_size_gb = (
            await async_recommended_verification_size_gb(self.hass)
        )
        self._draft = _new_configuration(self._hardware)
        self._apply_inventory_size_recommendation()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a recommended or custom runtime profile."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        await self._async_prepare()
        if user_input is not None:
            profile = str(user_input[CONF_RUNTIME_PROFILE])
            self._apply_runtime_profile(
                profile, bool(user_input[CONF_ADAPTIVE_POLLING])
            )
            if profile == RUNTIME_PROFILE_CUSTOM:
                return await self.async_step_runtime_custom()
            return await self.async_step_monitoring()

        hardware = self._hardware
        if hardware is None:
            raise RuntimeError("Hardware detection did not complete")
        return self.async_show_form(
            step_id="user",
            data_schema=runtime_profile_schema(self._draft),
            description_placeholders={
                "installation_type": hardware.installation_type,
                "architecture": hardware.architecture,
                "board": hardware.board,
                "recommended_profile": hardware.recommended_profile,
                "confidence": hardware.confidence,
            },
        )

    async def async_step_runtime_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure custom polling and verification budgets."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_runtime(user_input)
            if not errors:
                self._draft.update(user_input)
                return await self.async_step_monitoring()
        return self.async_show_form(
            step_id="runtime_custom",
            data_schema=runtime_custom_schema(user_input or self._draft),
            errors=errors,
        )

    async def async_step_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose a backup-health monitoring policy."""
        if user_input is not None:
            policy = str(user_input[CONF_MONITORING_POLICY])
            self._apply_monitoring_policy(policy)
            if policy == MONITORING_POLICY_CUSTOM:
                return await self.async_step_monitoring_custom()
            return await self.async_step_verification()
        return self.async_show_form(
            step_id="monitoring",
            data_schema=monitoring_policy_schema(self._draft),
        )

    async def async_step_monitoring_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure custom backup-health thresholds."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_monitoring(user_input)
            if not errors:
                self._draft.update(user_input)
                return await self.async_step_verification()
        return self.async_show_form(
            step_id="monitoring_custom",
            data_schema=monitoring_custom_schema(user_input or self._draft),
            errors=errors,
        )

    async def async_step_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose how new backups are verified."""
        if user_input is not None:
            self._apply_verification_policy(str(user_input[CONF_VERIFICATION_POLICY]))
            return await self.async_step_presentation()
        return self.async_show_form(
            step_id="verification",
            data_schema=verification_policy_schema(self._draft),
        )

    async def async_step_presentation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure entities, privacy, and mobile notifications."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_notifications(user_input)
            if not errors:
                self._apply_presentation(user_input)
                return await self.async_step_summary()
        values = dict(self._draft)
        if user_input is not None:
            values.update(user_input)
            values[CONF_NOTIFICATION_TARGETS] = normalize_notification_targets(
                user_input.get(CONF_NOTIFICATION_TARGETS)
            )
        return self.async_show_form(
            step_id="presentation",
            data_schema=presentation_schema(self.hass, values),
            errors=errors,
        )

    async def async_step_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the resolved setup before persisting it."""
        if user_input is not None:
            if not user_input.get(CONF_CONFIRM):
                return self.async_show_form(
                    step_id="summary",
                    data_schema=summary_schema(),
                    errors={"base": "confirmation_required"},
                    description_placeholders=_summary_placeholders(self._draft),
                )
            data = normalize_configuration(self._draft)
            return self.async_create_entry(title=NAME, data=data)
        return self.async_show_form(
            step_id="summary",
            data_schema=summary_schema(),
            description_placeholders=_summary_placeholders(self._draft),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the menu-based options flow."""
        return BackupCheckupOptionsFlow()


class BackupCheckupOptionsFlow(_GuidedFlowState, config_entries.OptionsFlowWithReload):
    """Edit independent setting groups or rerun the complete assistant."""

    def __init__(self) -> None:
        """Initialize options state."""
        self._draft = {}
        self._hardware = None
        self._recommended_verification_size_gb = None
        self._assistant_mode = False

    def _current(self) -> dict[str, Any]:
        """Return one normalized snapshot of data and options."""
        return normalize_configuration(
            self.config_entry.data, self.config_entry.options
        )

    def _save(self, patch: dict[str, Any]) -> FlowResult:
        """Persist one complete options snapshot and let Home Assistant reload."""
        return self.async_create_entry(
            title="", data=normalize_configuration(self._current(), patch)
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a focused settings menu."""
        del user_input
        return self.async_show_menu(step_id="init", menu_options=list(_OPTIONS_MENU))

    async def async_step_runtime(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the runtime profile and adaptive polling."""
        values = self._current()
        if user_input is not None:
            profile = str(user_input[CONF_RUNTIME_PROFILE])
            patch = {
                CONF_RUNTIME_PROFILE: profile,
                CONF_ADAPTIVE_POLLING: bool(user_input[CONF_ADAPTIVE_POLLING]),
                CONF_PRESET_REVISION: PRESET_REVISION,
            }
            patch.update(
                runtime_values(
                    profile,
                    adaptive_polling=bool(user_input[CONF_ADAPTIVE_POLLING]),
                )
            )
            if profile == RUNTIME_PROFILE_CUSTOM:
                self._draft = normalize_configuration(values, patch)
                return await self.async_step_runtime_custom()
            return self._save(patch)
        if values[CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_LEGACY:
            values[CONF_RUNTIME_PROFILE] = RUNTIME_PROFILE_CUSTOM
        return self.async_show_form(
            step_id="runtime", data_schema=runtime_profile_schema(values)
        )

    async def async_step_runtime_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit custom runtime values."""
        values = self._draft or self._current()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_runtime(user_input)
            if not errors:
                patch = {
                    CONF_RUNTIME_PROFILE: RUNTIME_PROFILE_CUSTOM,
                    CONF_PRESET_REVISION: PRESET_REVISION,
                    **user_input,
                }
                if self._assistant_mode:
                    self._draft.update(patch)
                    return await self.async_step_setup_monitoring()
                return self._save(patch)
        return self.async_show_form(
            step_id="runtime_custom",
            data_schema=runtime_custom_schema(user_input or values),
            errors=errors,
        )

    async def async_step_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the monitoring policy."""
        values = self._current()
        if user_input is not None:
            policy = str(user_input[CONF_MONITORING_POLICY])
            patch = {CONF_MONITORING_POLICY: policy, **monitoring_values(policy)}
            if policy == MONITORING_POLICY_CUSTOM:
                self._draft = normalize_configuration(values, patch)
                return await self.async_step_monitoring_custom()
            return self._save(patch)
        return self.async_show_form(
            step_id="monitoring", data_schema=monitoring_policy_schema(values)
        )

    async def async_step_monitoring_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit custom monitoring thresholds."""
        values = self._draft or self._current()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_monitoring(user_input)
            if not errors:
                patch = {CONF_MONITORING_POLICY: MONITORING_POLICY_CUSTOM, **user_input}
                if self._assistant_mode:
                    self._draft.update(patch)
                    return await self.async_step_setup_verification()
                return self._save(patch)
        return self.async_show_form(
            step_id="monitoring_custom",
            data_schema=monitoring_custom_schema(user_input or values),
            errors=errors,
        )

    async def async_step_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the automatic verification strategy."""
        values = self._current()
        if user_input is not None:
            policy = str(user_input[CONF_VERIFICATION_POLICY])
            return self._save(
                {CONF_VERIFICATION_POLICY: policy, **verification_values(policy)}
            )
        return self.async_show_form(
            step_id="verification", data_schema=verification_policy_schema(values)
        )

    async def async_step_presentation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit entity, privacy, and notification settings."""
        values = self._current()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_notifications(user_input)
            if not errors:
                patch = {
                    CONF_ENTITY_MODE: str(user_input[CONF_ENTITY_MODE]),
                    CONF_EXPOSE_BACKUP_METADATA: bool(
                        user_input[CONF_EXPOSE_BACKUP_METADATA]
                    ),
                    **_notification_values(user_input),
                }
                return self._save(patch)
            values.update(user_input)
            values[CONF_NOTIFICATION_TARGETS] = normalize_notification_targets(
                user_input.get(CONF_NOTIFICATION_TARGETS)
            )
        return self.async_show_form(
            step_id="presentation",
            data_schema=presentation_schema(self.hass, values),
            errors=errors,
        )

    async def async_step_setup_assistant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Rerun the complete guided assistant from the options menu."""
        if self._hardware is None:
            self._hardware = await async_detect_hardware(self.hass)
            self._recommended_verification_size_gb = (
                await async_recommended_verification_size_gb(self.hass)
            )
            self._draft = self._current()
            self._draft[CONF_HARDWARE_DETECTION] = self._hardware.as_dict()
        self._assistant_mode = True
        if user_input is not None:
            profile = str(user_input[CONF_RUNTIME_PROFILE])
            self._apply_runtime_profile(
                profile, bool(user_input[CONF_ADAPTIVE_POLLING])
            )
            self._draft[CONF_PRESET_REVISION] = PRESET_REVISION
            if profile == RUNTIME_PROFILE_CUSTOM:
                return await self.async_step_runtime_custom()
            return await self.async_step_setup_monitoring()
        hardware = self._hardware
        if hardware is None:
            raise RuntimeError("Hardware detection did not complete")
        values = dict(self._draft)
        if values[CONF_RUNTIME_PROFILE] == RUNTIME_PROFILE_LEGACY:
            values[CONF_RUNTIME_PROFILE] = hardware.recommended_profile
        return self.async_show_form(
            step_id="setup_assistant",
            data_schema=runtime_profile_schema(values),
            description_placeholders={
                "installation_type": hardware.installation_type,
                "architecture": hardware.architecture,
                "board": hardware.board,
                "recommended_profile": hardware.recommended_profile,
                "confidence": hardware.confidence,
            },
        )

    async def async_step_setup_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose monitoring while rerunning the setup assistant."""
        if user_input is not None:
            policy = str(user_input[CONF_MONITORING_POLICY])
            self._apply_monitoring_policy(policy)
            if policy == MONITORING_POLICY_CUSTOM:
                return await self.async_step_monitoring_custom()
            return await self.async_step_setup_verification()
        return self.async_show_form(
            step_id="setup_monitoring",
            data_schema=monitoring_policy_schema(self._draft),
        )

    async def async_step_setup_verification(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose verification while rerunning the setup assistant."""
        if user_input is not None:
            self._apply_verification_policy(str(user_input[CONF_VERIFICATION_POLICY]))
            return await self.async_step_setup_presentation()
        return self.async_show_form(
            step_id="setup_verification",
            data_schema=verification_policy_schema(self._draft),
        )

    async def async_step_setup_presentation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose presentation while rerunning the setup assistant."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_notifications(user_input)
            if not errors:
                self._apply_presentation(user_input)
                return await self.async_step_setup_summary()
        values = dict(self._draft)
        if user_input is not None:
            values.update(user_input)
            values[CONF_NOTIFICATION_TARGETS] = normalize_notification_targets(
                user_input.get(CONF_NOTIFICATION_TARGETS)
            )
        return self.async_show_form(
            step_id="setup_presentation",
            data_schema=presentation_schema(self.hass, values),
            errors=errors,
        )

    async def async_step_setup_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm and save the complete options assistant."""
        if user_input is not None and user_input.get(CONF_CONFIRM):
            return self.async_create_entry(
                title="", data=normalize_configuration(self._draft)
            )
        errors = {"base": "confirmation_required"} if user_input is not None else {}
        return self.async_show_form(
            step_id="setup_summary",
            data_schema=summary_schema(),
            errors=errors,
            description_placeholders=_summary_placeholders(self._draft),
        )
