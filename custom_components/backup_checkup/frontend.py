"""Optional Home Assistant frontend panel for BackupCheckup."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .configuration import normalize_configuration
from .const import CONF_SHOW_SIDEBAR_PANEL, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "backup-checkup"
PANEL_WEB_COMPONENT = "backup-checkup-panel"
PANEL_MODULE_PATH = "/backup_checkup/frontend/backup-checkup-panel.js"
PANEL_MODULE_URL = f"{PANEL_MODULE_PATH}?v={VERSION}"
PANEL_MODULE_FILE = Path(__file__).parent / "frontend" / "backup-checkup-panel.js"

_PANEL_ENTITIES: dict[str, tuple[str, str]] = {
    "status": ("sensor", "status"),
    "health_score": ("sensor", "health_score"),
    "recommendation": ("sensor", "recommendation"),
    "stored_backups": ("sensor", "stored_backups"),
    "latest_backup_age": ("sensor", "latest_backup_age"),
    "latest_backup_size": ("sensor", "latest_backup_size"),
    "integrity_status": ("sensor", "integrity_status"),
    "problem": ("binary_sensor", "problem"),
    "verify": ("button", "verify_latest_backup"),
    "refresh": ("button", "refresh"),
}


def _entity_id(
    hass: HomeAssistant,
    entry: ConfigEntry,
    platform: str,
    key: str,
) -> str:
    """Resolve a possibly renamed entity and retain a stable fallback."""
    registry = er.async_get(hass)
    if registry is not None:
        resolved = registry.async_get_entity_id(
            platform,
            DOMAIN,
            f"{entry.entry_id}_{key}",
        )
        if resolved is not None:
            return resolved
    return f"{platform}.{DOMAIN}_{key}"


def _panel_config(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, object]:
    """Return the privacy-safe configuration passed to the browser panel."""
    return {
        "entry_id": entry.entry_id,
        "entities": {
            name: _entity_id(hass, entry, platform, key)
            for name, (platform, key) in _PANEL_ENTITIES.items()
        },
    }


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the versioned panel module from the integration directory."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_MODULE_PATH,
                str(PANEL_MODULE_FILE),
                cache_headers=True,
            )
        ]
    )


async def async_setup_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the optional sidebar panel for one loaded config entry."""
    configuration = normalize_configuration(entry.data, entry.options)
    if not configuration[CONF_SHOW_SIDEBAR_PANEL]:
        return

    try:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_WEB_COMPONENT,
            sidebar_title="BackupCheckup",
            sidebar_icon="mdi:backup-restore",
            module_url=PANEL_MODULE_URL,
            config=_panel_config(hass, entry),
            require_admin=False,
        )
    except ValueError as err:
        _LOGGER.warning("Unable to register BackupCheckup panel: %s", err)
        return

    entry.async_on_unload(
        lambda: frontend.async_remove_panel(
            hass,
            PANEL_URL_PATH,
            warn_if_unknown=False,
        )
    )
