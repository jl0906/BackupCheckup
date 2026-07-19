"""Minimal test doubles for unit tests that do not require a Home Assistant runtime."""

from __future__ import annotations

import contextlib
import sys
import tarfile
import types
from dataclasses import dataclass
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

voluptuous = types.ModuleType("voluptuous")


class _VolMarker:
    def __init__(self, key: str, *, default: Any = None) -> None:
        self.key = key
        self.default = default

    def __hash__(self) -> int:
        return hash((type(self), self.key))

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and getattr(other, "key", None) == self.key


class Schema:
    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def __call__(self, value: Any) -> Any:
        return value


class Required(_VolMarker):
    pass


class Optional(_VolMarker):
    pass


voluptuous.Schema = Schema
voluptuous.Required = Required
voluptuous.Optional = Optional
sys.modules.setdefault("voluptuous", voluptuous)

homeassistant = types.ModuleType("homeassistant")
components = types.ModuleType("homeassistant.components")
backup = types.ModuleType("homeassistant.components.backup")
binary_sensor = types.ModuleType("homeassistant.components.binary_sensor")
button = types.ModuleType("homeassistant.components.button")
logbook = types.ModuleType("homeassistant.components.logbook")
sensor = types.ModuleType("homeassistant.components.sensor")
config_entries = types.ModuleType("homeassistant.config_entries")
data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
const = types.ModuleType("homeassistant.const")
core = types.ModuleType("homeassistant.core")
exceptions = types.ModuleType("homeassistant.exceptions")
helpers = types.ModuleType("homeassistant.helpers")
device_registry = types.ModuleType("homeassistant.helpers.device_registry")
entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
entity = types.ModuleType("homeassistant.helpers.entity")
entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
selector = types.ModuleType("homeassistant.helpers.selector")
system_info = types.ModuleType("homeassistant.helpers.system_info")
event = types.ModuleType("homeassistant.helpers.event")
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
    """Config-entry test double used by platform and flow tests."""

    def __init__(
        self,
        *,
        entry_id: str = "entry",
        data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        version: int = 9,
    ) -> None:
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}
        self.version = version
        self.runtime_data: Any = None
        self._unloads: list[Any] = []

    def async_on_unload(self, callback_value: Any) -> None:
        self._unloads.append(callback_value)

    def add_update_listener(self, listener: Any) -> Any:
        return listener


class ConfigFlow:
    """Minimal flow base returning dictionary flow results."""

    hass: Any = None

    def __init_subclass__(cls, *, domain: str | None = None, **kwargs: Any) -> None:
        del domain
        super().__init_subclass__(**kwargs)

    def _async_current_entries(self) -> list[Any]:
        return []

    def async_abort(self, *, reason: str) -> dict[str, Any]:
        return {"type": "abort", "reason": reason}

    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "form", **kwargs}

    def async_show_menu(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "menu", **kwargs}


class OptionsFlow(ConfigFlow):
    """Minimal options-flow base."""

    config_entry: ConfigEntry


class OptionsFlowWithReload(OptionsFlow):
    """Minimal auto-reloading options-flow base."""


@dataclass(frozen=True, kw_only=True)
class EntityDescription:
    """Shared subset of Home Assistant entity-description fields."""

    key: str
    translation_key: str | None = None
    icon: str | None = None
    device_class: Any = None
    state_class: Any = None
    native_unit_of_measurement: Any = None
    suggested_display_precision: int | None = None
    entity_category: Any = None
    entity_registry_enabled_default: bool = True
    options: tuple[str, ...] | list[str] | None = None


class Entity:
    """Minimal Home Assistant entity test double."""

    hass: Any = None
    _context: Any = None

    @property
    def unique_id(self) -> str | None:
        return getattr(self, "_attr_unique_id", None)

    async def async_remove(self) -> None:
        return None


class CoordinatorEntity(Entity):
    """Minimal coordinator-backed entity."""

    def __class_getitem__(cls, _item: Any) -> type[CoordinatorEntity]:
        return cls

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)

    @property
    def available(self) -> bool:
        return bool(getattr(self.coordinator, "last_update_success", True))


class SensorEntity(Entity):
    """Sensor entity test double."""


class BinarySensorEntity(Entity):
    """Binary-sensor entity test double."""


class ButtonEntity(Entity):
    """Button entity test double."""


class SensorDeviceClass(StrEnum):
    ENUM = "enum"
    TIMESTAMP = "timestamp"
    DURATION = "duration"
    DATA_SIZE = "data_size"


class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"


class BinarySensorDeviceClass(StrEnum):
    PROBLEM = "problem"


class EntityCategory(StrEnum):
    DIAGNOSTIC = "diagnostic"
    CONFIG = "config"


class UnitOfInformation(StrEnum):
    BYTES = "B"
    MEGABYTES = "MB"


class UnitOfTime(StrEnum):
    DAYS = "d"
    SECONDS = "s"


class DeviceInfo(dict):
    """Dictionary-compatible DeviceInfo test double."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(kwargs)
        self.__dict__.update(kwargs)


@dataclass(frozen=True)
class NumberSelectorConfig:
    min: int
    max: int
    step: int
    mode: Any
    read_only: bool = False


@dataclass(frozen=True)
class SelectSelectorConfig:
    options: Any
    mode: Any
    translation_key: str | None = None
    multiple: bool = False
    custom_value: bool = False
    sort: bool = False
    read_only: bool = False


@dataclass(frozen=True)
class TextSelectorConfig:
    read_only: bool = False


class _Selector:
    def __init__(self, config: Any = None) -> None:
        self.config = config

    def __call__(self, value: Any) -> Any:
        return value


class BooleanSelector(_Selector):
    pass


class NumberSelector(_Selector):
    pass


class SelectSelector(_Selector):
    pass


class TextSelector(_Selector):
    pass


class NumberSelectorMode(StrEnum):
    BOX = "box"


class SelectSelectorMode(StrEnum):
    DROPDOWN = "dropdown"


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

    async def async_config_entry_first_refresh(self) -> None:
        self.data = await self._async_update_data()

    def async_add_listener(self, listener: Any) -> Any:
        return listener

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
binary_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
binary_sensor.BinarySensorEntity = BinarySensorEntity
binary_sensor.BinarySensorEntityDescription = EntityDescription
button.ButtonEntity = ButtonEntity
logbook.async_log_entry = lambda *_args, **_kwargs: None
sensor.SensorDeviceClass = SensorDeviceClass
sensor.SensorEntity = SensorEntity
sensor.SensorEntityDescription = EntityDescription
sensor.SensorStateClass = SensorStateClass
config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
config_entries.OptionsFlowWithReload = OptionsFlowWithReload
data_entry_flow.FlowResult = dict
const.Platform = Platform
const.EntityCategory = EntityCategory
const.UnitOfInformation = UnitOfInformation
const.UnitOfTime = UnitOfTime
const.CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
const.PERCENTAGE = "%"
const.STATE_UNAVAILABLE = "unavailable"
const.STATE_UNKNOWN = "unknown"
const.__version__ = "2026.7.2"
core.HomeAssistant = HomeAssistant
core.ServiceCall = ServiceCall
core.callback = lambda function: function
exceptions.HomeAssistantError = HomeAssistantError
device_registry.DeviceEntry = DeviceEntry
helpers.device_registry = device_registry
device_registry.DeviceInfo = DeviceInfo
entity.Entity = Entity
entity_platform.AddEntitiesCallback = Any
entity_registry.EntityRegistry = object
entity_registry.RegistryEntryDisabler = RegistryEntryDisabler
entity_registry.async_get = lambda _hass: None
helpers.entity = entity
helpers.entity_registry = entity_registry
issue_registry.IssueSeverity = IssueSeverity
issue_registry.async_create_issue = lambda *_args, **_kwargs: None
issue_registry.async_delete_issue = lambda *_args, **_kwargs: None
helpers.issue_registry = issue_registry
service.async_register_admin_service = lambda *_args, **_kwargs: None
typing_module.ConfigType = dict
storage.Store = Store
selector.BooleanSelector = BooleanSelector
selector.NumberSelector = NumberSelector
selector.NumberSelectorConfig = NumberSelectorConfig
selector.NumberSelectorMode = NumberSelectorMode
selector.SelectSelector = SelectSelector
selector.SelectSelectorConfig = SelectSelectorConfig
selector.SelectSelectorMode = SelectSelectorMode
selector.TextSelector = TextSelector
selector.TextSelectorConfig = TextSelectorConfig
system_info.async_get_system_info = lambda _hass: {}
event.async_track_state_change_event = lambda *_args, **_kwargs: lambda: None
translation.async_get_translations = lambda *_args, **_kwargs: {}
update_coordinator.CoordinatorEntity = CoordinatorEntity
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
util.slugify = lambda value: "".join(
    character if character.isalnum() else "_" for character in str(value).lower()
).strip("_")

sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault("homeassistant.components.backup", backup)
sys.modules.setdefault("homeassistant.components.binary_sensor", binary_sensor)
sys.modules.setdefault("homeassistant.components.button", button)
sys.modules.setdefault("homeassistant.components.logbook", logbook)
sys.modules.setdefault("homeassistant.components.sensor", sensor)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.data_entry_flow", data_entry_flow)
sys.modules.setdefault("homeassistant.const", const)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.exceptions", exceptions)
sys.modules.setdefault("homeassistant.helpers", helpers)
sys.modules.setdefault("homeassistant.helpers.device_registry", device_registry)
sys.modules.setdefault("homeassistant.helpers.entity", entity)
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)
sys.modules.setdefault("homeassistant.helpers.entity_registry", entity_registry)
sys.modules.setdefault("homeassistant.helpers.issue_registry", issue_registry)
sys.modules.setdefault("homeassistant.helpers.selector", selector)
sys.modules.setdefault("homeassistant.helpers.system_info", system_info)
sys.modules.setdefault("homeassistant.helpers.event", event)
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
