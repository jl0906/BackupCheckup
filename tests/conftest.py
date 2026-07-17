"""Minimal test doubles for unit tests that do not require a Home Assistant runtime."""

from __future__ import annotations

import contextlib
import sys
import tarfile
import types
from datetime import UTC, datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_COMPONENTS = _ROOT / "custom_components"
_INTEGRATION = _COMPONENTS / "backup_checkup"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(_COMPONENTS)]
backup_checkup = types.ModuleType("custom_components.backup_checkup")
backup_checkup.__path__ = [str(_INTEGRATION)]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.backup_checkup", backup_checkup)

homeassistant = types.ModuleType("homeassistant")
components = types.ModuleType("homeassistant.components")
backup = types.ModuleType("homeassistant.components.backup")
config_entries = types.ModuleType("homeassistant.config_entries")
const = types.ModuleType("homeassistant.const")
core = types.ModuleType("homeassistant.core")
exceptions = types.ModuleType("homeassistant.exceptions")
helpers = types.ModuleType("homeassistant.helpers")
device_registry = types.ModuleType("homeassistant.helpers.device_registry")
entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")
service = types.ModuleType("homeassistant.helpers.service")
storage = types.ModuleType("homeassistant.helpers.storage")
typing_module = types.ModuleType("homeassistant.helpers.typing")
translation = types.ModuleType("homeassistant.helpers.translation")
update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
util = types.ModuleType("homeassistant.util")
dt = types.ModuleType("homeassistant.util.dt")


def _async_get_manager(_hass: Any) -> Any:
    raise RuntimeError("Not available in isolated unit tests")


class Platform(StrEnum):
    """Subset of Home Assistant platforms used by the integration."""

    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"


class HomeAssistant:
    """Type-only Home Assistant test double."""


class ServiceCall:
    """Type-only service-call test double."""


class DeviceEntry:
    """Type-only device-registry test double."""


class ConfigEntry:
    """Type-only config-entry test double."""


class RegistryEntryDisabler(Enum):
    """Subset of Home Assistant entity-registry disablers."""

    INTEGRATION = "integration"
    USER = "user"
    CONFIG_ENTRY = "config_entry"


class HomeAssistantError(Exception):
    """Minimal Home Assistant service error."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)
        self.translation_domain = kwargs.get("translation_domain")
        self.translation_key = kwargs.get("translation_key")


class UpdateFailed(Exception):
    """Minimal coordinator update error."""


class DataUpdateCoordinator:
    """Small coordinator base used by isolated unit tests."""

    def __class_getitem__(cls, _item: Any) -> type[DataUpdateCoordinator]:
        return cls

    def __init__(self, hass: Any, _logger: Any, **kwargs: Any) -> None:
        self.hass = hass
        self.config_entry = kwargs.get("config_entry")
        self.update_interval = kwargs.get("update_interval")
        self.data = None
        self.last_update_success = True
        self.last_exception = None

    async def async_shutdown(self) -> None:
        return None

    async def async_request_refresh(self) -> None:
        return None

    def async_set_updated_data(self, data: Any) -> None:
        self.data = data


class Store:
    """In-memory private Store test double."""

    def __class_getitem__(cls, _item: Any) -> type[Store]:
        return cls

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.data: Any = None

    async def async_load(self) -> Any:
        return self.data

    async def async_save(self, data: Any) -> None:
        self.data = data

    async def async_remove(self) -> None:
        self.data = None


class IssueSeverity(StrEnum):
    """Subset of repair issue severities."""

    WARNING = "warning"
    ERROR = "error"


backup.async_get_manager = _async_get_manager
config_entries.ConfigEntry = ConfigEntry
const.Platform = Platform
const.STATE_UNAVAILABLE = "unavailable"
const.STATE_UNKNOWN = "unknown"
const.__version__ = "2026.7.2"
core.HomeAssistant = HomeAssistant
core.ServiceCall = ServiceCall
core.callback = lambda function: function
exceptions.HomeAssistantError = HomeAssistantError
device_registry.DeviceEntry = DeviceEntry
helpers.device_registry = device_registry
entity_registry.RegistryEntryDisabler = RegistryEntryDisabler
entity_registry.async_get = lambda _hass: None
helpers.entity_registry = entity_registry
issue_registry.IssueSeverity = IssueSeverity
issue_registry.async_create_issue = lambda *_args, **_kwargs: None
issue_registry.async_delete_issue = lambda *_args, **_kwargs: None
helpers.issue_registry = issue_registry
service.async_register_admin_service = lambda *_args, **_kwargs: None
typing_module.ConfigType = dict
storage.Store = Store
translation.async_get_translations = lambda *_args, **_kwargs: {}
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
dt.utcnow = lambda: datetime.now(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


dt.parse_datetime = _parse_datetime
dt.as_utc = lambda value: (
    value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
)
util.dt = dt

sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault("homeassistant.components.backup", backup)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.const", const)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.exceptions", exceptions)
sys.modules.setdefault("homeassistant.helpers", helpers)
sys.modules.setdefault("homeassistant.helpers.device_registry", device_registry)
sys.modules.setdefault("homeassistant.helpers.entity_registry", entity_registry)
sys.modules.setdefault("homeassistant.helpers.issue_registry", issue_registry)
sys.modules.setdefault("homeassistant.helpers.service", service)
sys.modules.setdefault("homeassistant.helpers.storage", storage)
sys.modules.setdefault("homeassistant.helpers.typing", typing_module)
sys.modules.setdefault("homeassistant.helpers.translation", translation)
sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)
sys.modules.setdefault("homeassistant.util", util)
sys.modules.setdefault("homeassistant.util.dt", dt)

securetar = types.ModuleType("securetar")


class SecureTarError(Exception):
    """SecureTar test-double base exception."""


class InvalidPasswordError(SecureTarError):
    """SecureTar test-double password exception."""


class SecureTarArchive:
    """Open ordinary TAR files with the subset used by these unit tests."""

    def __init__(
        self,
        path: Path,
        mode: str,
        *,
        bufsize: int,
        password: str | None,
    ) -> None:
        del bufsize, password
        self._path = path
        self._mode = mode
        self.tar: tarfile.TarFile

    def __enter__(self) -> SecureTarArchive:
        self.tar = tarfile.open(self._path, self._mode)
        return self

    def __exit__(self, *_args: Any) -> None:
        self.tar.close()

    @contextlib.contextmanager
    def extract_tar(self, member: tarfile.TarInfo):
        """Yield an unencrypted nested TAR stream."""
        reader = self.tar.extractfile(member)
        if reader is None:
            raise tarfile.ReadError("archive_member_unreadable")
        try:
            yield reader
        finally:
            reader.close()


securetar.InvalidPasswordError = InvalidPasswordError
securetar.SecureTarArchive = SecureTarArchive
securetar.SecureTarError = SecureTarError
sys.modules.setdefault("securetar", securetar)
