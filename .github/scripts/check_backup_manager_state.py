"""Validate which backup-manager states block verification, without Home Assistant.

Home Assistant's backup manager reports ``blocked`` from its creation until Home
Assistant has finished starting. Only creating, receiving, or restoring a backup
may stop a verification; treating every non-idle state as busy skipped checks
for minutes after each restart.
"""

from __future__ import annotations

import ast
import enum
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
PACKAGE = "backup_checkup_manager_state_check"
MANAGER_ENTITY_ID = "sensor.backup_backup_manager_state"


class BackupManagerState(enum.StrEnum):
    """Mirror of ``homeassistant.components.backup.manager.BackupManagerState``."""

    IDLE = "idle"
    BLOCKED = "blocked"
    CREATE_BACKUP = "create_backup"
    RECEIVE_BACKUP = "receive_backup"
    RESTORE_BACKUP = "restore_backup"


def _module(name: str, **attributes: object) -> ModuleType:
    """Register one stub module and return it."""
    module = ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module
    return module


def _install_home_assistant_stubs() -> None:
    """Provide the few Home Assistant names the module imports."""

    class Platform(enum.StrEnum):
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        BUTTON = "button"

    def async_get(hass: object) -> object:
        return hass.registry  # type: ignore[attr-defined]

    def parse_datetime(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    root = _module("homeassistant")
    root.__path__ = []
    _module(
        "homeassistant.const",
        STATE_UNAVAILABLE="unavailable",
        STATE_UNKNOWN="unknown",
        Platform=Platform,
    )
    _module("homeassistant.core", HomeAssistant=object)
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    helpers.entity_registry = _module(
        "homeassistant.helpers.entity_registry", async_get=async_get
    )
    util = _module("homeassistant.util")
    util.__path__ = []
    util.dt = _module(
        "homeassistant.util.dt",
        parse_datetime=parse_datetime,
        as_utc=lambda value: value.astimezone(UTC),
    )


def _load_native_backup() -> ModuleType:
    """Import native_backup.py and its real constants as a private package."""
    _install_home_assistant_stubs()
    package = _module(PACKAGE)
    package.__path__ = [str(INTEGRATION)]
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.native_backup", INTEGRATION / "native_backup.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load the native backup module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


def _hass(entity_state: str | None = None, *, registry: bool = True) -> object:
    """Return a minimal hass with an optional backup-manager sensor state."""
    states: dict[str, object] = {}
    if entity_state is not None:
        states[MANAGER_ENTITY_ID] = SimpleNamespace(
            state=entity_state, attributes={}, last_changed=None, last_updated=None
        )
    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    if registry:
        hass.registry = SimpleNamespace(
            entities={
                "manager": SimpleNamespace(
                    platform="backup",
                    unique_id="backup_manager_state",
                    entity_id=MANAGER_ENTITY_ID,
                )
            }
        )
    return hass


def _check_manager_states(native) -> None:
    """Every native manager state maps to the documented busy decision."""
    expected = {
        BackupManagerState.IDLE: False,
        BackupManagerState.BLOCKED: False,
        BackupManagerState.CREATE_BACKUP: True,
        BackupManagerState.RECEIVE_BACKUP: True,
        BackupManagerState.RESTORE_BACKUP: True,
    }
    _require(
        set(expected) == set(BackupManagerState), "Not every manager state is covered"
    )
    for state, busy in expected.items():
        for value in (state, str(state.value)):
            result = native.native_backup_manager_busy(
                _hass(), SimpleNamespace(state=value)
            )
            _require(
                result == (busy, state.value),
                f"Manager state {value!r} returned {result}, expected "
                f"{(busy, state.value)}",
            )
        _require(
            native.native_backup_manager_state_busy(state) is busy,
            f"State predicate disagrees for {state.value}",
        )


def _check_unreadable_states(native) -> None:
    """Unknown and unavailable manager data never blocks verification."""
    for entity_state in ("unknown", "unavailable"):
        result = native.native_backup_manager_busy(
            _hass(entity_state), SimpleNamespace(state=None)
        )
        _require(
            result == (False, entity_state),
            f"Entity state {entity_state!r} returned {result}",
        )
        result = native.native_backup_manager_busy(
            _hass(), SimpleNamespace(state=entity_state)
        )
        _require(
            result == (False, entity_state),
            f"Manager state {entity_state!r} returned {result}",
        )
    result = native.native_backup_manager_busy(_hass(), SimpleNamespace())
    _require(result == (False, "unknown"), f"Missing manager state returned {result}")
    result = native.native_backup_manager_busy(
        _hass(registry=False), SimpleNamespace(state="")
    )
    _require(result == (False, "unknown"), f"Unreadable registry returned {result}")
    for value in (None, "", "none", "   "):
        _require(
            native.native_backup_manager_state_busy(value) is False,
            f"State predicate treated {value!r} as busy",
        )


def _check_entity_fallback(native) -> None:
    """Spelled-out states read through the entity fallback keep their decision."""
    expected = {
        "Idle": False,
        "Blocked": False,
        "Creating a backup": True,
        "creating_a_backup": True,
        "Receiving a backup": True,
        "receiving_a_backup": True,
        "Restoring a backup": True,
        "restoring_a_backup": True,
    }
    for entity_state, busy in expected.items():
        result = native.native_backup_manager_busy(
            _hass(entity_state), SimpleNamespace(state=None)
        )
        _require(
            result == (busy, entity_state.casefold()),
            f"Sensor state {entity_state!r} returned {result}",
        )
    _require(
        native.native_backup_manager_state_busy("  Restore_Backup ") is True,
        "State predicate does not normalize whitespace and case",
    )


def _check_constants(native) -> None:
    """One source of truth: writing states are a subset of busy states."""
    _require(
        not hasattr(native, "_MANAGER_IDLE_STATES"),
        "_MANAGER_IDLE_STATES must not come back",
    )
    writing = native._MANAGER_WRITING_STATES
    busy = native._MANAGER_BUSY_STATES
    _require(writing < busy, "Writing states must be a strict subset of busy states")
    _require(
        busy - writing == {"restore_backup", "restoring_a_backup", "restoring a backup"},
        f"Only restore states may extend the writing states: {sorted(busy - writing)}",
    )
    _require("blocked" not in busy, "blocked must not block verification")


def _check_in_progress(native) -> None:
    """A restore blocks verification but is not reported as a running backup."""
    now = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    expected = {
        BackupManagerState.IDLE: False,
        BackupManagerState.BLOCKED: False,
        BackupManagerState.CREATE_BACKUP: True,
        BackupManagerState.RECEIVE_BACKUP: True,
        BackupManagerState.RESTORE_BACKUP: False,
    }
    for state, in_progress in expected.items():
        result = native.read_native_backup_state(
            _hass(), SimpleNamespace(state=state), now=now
        )
        _require(
            result.in_progress is in_progress and result.manager_state == state.value,
            f"read_native_backup_state({state.value}) reported "
            f"in_progress={result.in_progress}, manager_state={result.manager_state}",
        )


def _details_keys(call: ast.Call) -> dict[str, object] | None:
    """Return the literal ``details`` mapping of one ``_record_activity`` call."""
    for keyword in call.keywords:
        if keyword.arg == "details" and isinstance(keyword.value, ast.Dict):
            return {
                key.value: value.value if isinstance(value, ast.Constant) else value
                for key, value in zip(keyword.value.keys, keyword.value.values)
                if isinstance(key, ast.Constant)
            }
    return None


def _check_adaptive_polling(tree: ast.Module) -> None:
    """The adaptive-polling flag uses the shared busy predicate everywhere."""
    derived = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Attribute)
            and target.attr == "_manager_backup_active"
            for target in targets
        ):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, bool):
            continue
        _require(
            isinstance(node, ast.Assign)
            and isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "native_backup_manager_state_busy",
            f"coordinator.py:{node.lineno}: _manager_backup_active must be derived "
            "from native_backup_manager_state_busy()",
        )
        derived += 1
    _require(
        derived == 2,
        f"Expected two derived _manager_backup_active assignments, found {derived}",
    )


def _check_coordinator() -> None:
    """Skips name the manager state, the tuple is unpacked, polling shares the rule."""
    path = INTEGRATION / "coordinator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    _check_adaptive_polling(tree)
    skips = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp, ast.While, ast.Assert)):
            for child in ast.walk(node.test):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "_backup_manager_busy"
                ):
                    _require(
                        False,
                        f"coordinator.py:{child.lineno}: _backup_manager_busy() "
                        "returns a tuple and must be unpacked before testing it",
                    )
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_record_activity"
        ):
            continue
        details = _details_keys(node)
        if details is None or details.get("reason") != "backup_in_progress":
            continue
        skips += 1
        _require(
            "manager_state" in details,
            f"coordinator.py:{node.lineno}: backup_in_progress skip does not record "
            "manager_state",
        )
    _require(skips == 2, f"Expected two backup_in_progress skip records, found {skips}")


def main() -> None:
    """Run every backup-manager state assertion."""
    native = _load_native_backup()
    _check_manager_states(native)
    _check_unreadable_states(native)
    _check_entity_fallback(native)
    _check_constants(native)
    _check_in_progress(native)
    _check_coordinator()
    print("Only creating, receiving, or restoring a backup blocks verification")


if __name__ == "__main__":
    main()
