"""Config flow for BackupCheckup."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    CONF_MAXIMUM_SIZE_DROP_PERCENT, CONF_MAX_AGE_DAYS, CONF_MINIMUM_BACKUP_SIZE_MB,
    CONF_MINIMUM_REDUNDANT_LOCATIONS, CONF_MONITORING_PROFILE, CONF_SIZE_CHECK_MODE,
    CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_MAXIMUM_SIZE_DROP_PERCENT, DEFAULT_MAX_AGE_DAYS,
    DEFAULT_MINIMUM_BACKUP_SIZE_MB, DEFAULT_MINIMUM_REDUNDANT_LOCATIONS,
    DEFAULT_MONITORING_PROFILE, DEFAULT_SIZE_CHECK_MODE, DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN, MAX_MAXIMUM_SIZE_DROP_PERCENT, MAX_MAX_AGE_DAYS, MAX_MINIMUM_BACKUP_SIZE_MB,
    MAX_REDUNDANT_LOCATIONS, MAX_UPDATE_INTERVAL_MINUTES, MIN_MAXIMUM_SIZE_DROP_PERCENT,
    MIN_MAX_AGE_DAYS, MIN_MINIMUM_BACKUP_SIZE_MB, MIN_REDUNDANT_LOCATIONS,
    MIN_UPDATE_INTERVAL_MINUTES, NAME, PROFILE_CUSTOM, PROFILE_SECURE, PROFILE_STANDARD,
    SIZE_CHECK_AUTO, SIZE_CHECK_FIXED, SIZE_CHECK_OFF,
)

PROFILE_PRESETS = {
    PROFILE_STANDARD: {
        CONF_MAX_AGE_DAYS: 4, CONF_UPDATE_INTERVAL_MINUTES: 5,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1, CONF_MAXIMUM_SIZE_DROP_PERCENT: 50,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 1, CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
    },
    PROFILE_SECURE: {
        CONF_MAX_AGE_DAYS: 2, CONF_UPDATE_INTERVAL_MINUTES: 2,
        CONF_MINIMUM_BACKUP_SIZE_MB: 1, CONF_MAXIMUM_SIZE_DROP_PERCENT: 35,
        CONF_MINIMUM_REDUNDANT_LOCATIONS: 2, CONF_SIZE_CHECK_MODE: SIZE_CHECK_AUTO,
    },
}

def _profile_schema(default: str) -> vol.Schema:
    return vol.Schema({vol.Required(CONF_MONITORING_PROFILE, default=default): SelectSelector(
        SelectSelectorConfig(options=[
            SelectOptionDict(value=PROFILE_STANDARD, label="Standard"),
            SelectOptionDict(value=PROFILE_SECURE, label="Secure"),
            SelectOptionDict(value=PROFILE_CUSTOM, label="Custom"),
        ], mode=SelectSelectorMode.DROPDOWN, translation_key="monitoring_profile")
    )})

def _advanced_schema(values: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_MAX_AGE_DAYS, default=values[CONF_MAX_AGE_DAYS]): vol.All(vol.Coerce(int), vol.Range(min=MIN_MAX_AGE_DAYS,max=MAX_MAX_AGE_DAYS)),
        vol.Required(CONF_UPDATE_INTERVAL_MINUTES, default=values[CONF_UPDATE_INTERVAL_MINUTES]): vol.All(vol.Coerce(int),vol.Range(min=MIN_UPDATE_INTERVAL_MINUTES,max=MAX_UPDATE_INTERVAL_MINUTES)),
        vol.Required(CONF_SIZE_CHECK_MODE, default=values[CONF_SIZE_CHECK_MODE]): SelectSelector(SelectSelectorConfig(options=[SIZE_CHECK_AUTO,SIZE_CHECK_FIXED,SIZE_CHECK_OFF], mode=SelectSelectorMode.DROPDOWN, translation_key="size_check_mode")),
        vol.Required(CONF_MINIMUM_BACKUP_SIZE_MB, default=values[CONF_MINIMUM_BACKUP_SIZE_MB]): vol.All(vol.Coerce(int),vol.Range(min=MIN_MINIMUM_BACKUP_SIZE_MB,max=MAX_MINIMUM_BACKUP_SIZE_MB)),
        vol.Required(CONF_MAXIMUM_SIZE_DROP_PERCENT, default=values[CONF_MAXIMUM_SIZE_DROP_PERCENT]): vol.All(vol.Coerce(int),vol.Range(min=MIN_MAXIMUM_SIZE_DROP_PERCENT,max=MAX_MAXIMUM_SIZE_DROP_PERCENT)),
        vol.Required(CONF_MINIMUM_REDUNDANT_LOCATIONS, default=values[CONF_MINIMUM_REDUNDANT_LOCATIONS]): vol.All(vol.Coerce(int),vol.Range(min=MIN_REDUNDANT_LOCATIONS,max=MAX_REDUNDANT_LOCATIONS)),
    })

def _defaults() -> dict[str, Any]:
    return {CONF_MAX_AGE_DAYS:DEFAULT_MAX_AGE_DAYS, CONF_UPDATE_INTERVAL_MINUTES:DEFAULT_UPDATE_INTERVAL_MINUTES, CONF_MINIMUM_BACKUP_SIZE_MB:DEFAULT_MINIMUM_BACKUP_SIZE_MB, CONF_MAXIMUM_SIZE_DROP_PERCENT:DEFAULT_MAXIMUM_SIZE_DROP_PERCENT, CONF_MINIMUM_REDUNDANT_LOCATIONS:DEFAULT_MINIMUM_REDUNDANT_LOCATIONS, CONF_SIZE_CHECK_MODE:DEFAULT_SIZE_CHECK_MODE}

class BackupCheckupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION=2
    def __init__(self) -> None: self._profile=DEFAULT_MONITORING_PROFILE
    async def async_step_user(self,user_input:dict[str,Any]|None=None)->FlowResult:
        if self._async_current_entries(): return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            self._profile=user_input[CONF_MONITORING_PROFILE]
            if self._profile in PROFILE_PRESETS:
                return self.async_create_entry(title=NAME,data={CONF_MONITORING_PROFILE:self._profile,**PROFILE_PRESETS[self._profile]})
            return await self.async_step_advanced()
        return self.async_show_form(step_id="user",data_schema=_profile_schema(DEFAULT_MONITORING_PROFILE))
    async def async_step_advanced(self,user_input:dict[str,Any]|None=None)->FlowResult:
        if user_input is not None: return self.async_create_entry(title=NAME,data={CONF_MONITORING_PROFILE:PROFILE_CUSTOM,**user_input})
        return self.async_show_form(step_id="advanced",data_schema=_advanced_schema(_defaults()))
    @staticmethod
    @callback
    def async_get_options_flow(config_entry:config_entries.ConfigEntry)->config_entries.OptionsFlow:
        return BackupCheckupOptionsFlow(config_entry)

class BackupCheckupOptionsFlow(config_entries.OptionsFlow):
    def __init__(self,config_entry:config_entries.ConfigEntry)->None:
        self.config_entry=config_entry; self._profile=str(config_entry.options.get(CONF_MONITORING_PROFILE,config_entry.data.get(CONF_MONITORING_PROFILE,PROFILE_CUSTOM)))
    async def async_step_init(self,user_input:dict[str,Any]|None=None)->FlowResult:
        if user_input is not None:
            self._profile=user_input[CONF_MONITORING_PROFILE]
            if self._profile in PROFILE_PRESETS: return self.async_create_entry(title="",data={CONF_MONITORING_PROFILE:self._profile,**PROFILE_PRESETS[self._profile]})
            return await self.async_step_advanced()
        return self.async_show_form(step_id="init",data_schema=_profile_schema(self._profile))
    async def async_step_advanced(self,user_input:dict[str,Any]|None=None)->FlowResult:
        if user_input is not None: return self.async_create_entry(title="",data={CONF_MONITORING_PROFILE:PROFILE_CUSTOM,**user_input})
        values={key:self.config_entry.options.get(key,self.config_entry.data.get(key,default)) for key,default in _defaults().items()}
        return self.async_show_form(step_id="advanced",data_schema=_advanced_schema(values))
