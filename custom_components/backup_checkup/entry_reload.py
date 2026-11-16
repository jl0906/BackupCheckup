"""Reload the config entry from a detached task and report failures."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .security import safe_error_type

_LOGGER = logging.getLogger(__name__)

RELOAD_AFTER_PANEL_SAVE = "after saving the panel settings"
RELOAD_AFTER_RUNNER_DISCOVERY = "after connecting the Runtime Runner"


async def async_reload_entry_logged(
    hass: HomeAssistant, entry_id: str, occasion: str
) -> None:
    """Reload the entry and log a failure nobody is waiting for.

    The caller already answered its request, so a reload that fails or is
    refused must at least leave a clear line in the log.
    """
    try:
        reloaded = await hass.config_entries.async_reload(entry_id)
    except Exception as err:  # noqa: BLE001 - config-entry reload boundary
        _LOGGER.error(
            "BackupCheckup could not be reloaded %s; restart Home Assistant "
            "to apply the change: error_type=%s",
            occasion,
            safe_error_type(err),
        )
        return
    if not reloaded:
        _LOGGER.warning(
            "BackupCheckup was not reloaded %s; restart Home Assistant to "
            "apply the change",
            occasion,
        )
