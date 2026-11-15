"""Fail when a large state attribute set would be written to the recorder.

Home Assistant stores the attributes of a state as one shared JSON row that is
limited to 16384 bytes. The recorder drops the complete row and logs "State
attributes ... exceed maximum size of 16384 bytes" for every state write once
that limit is reached. BackupCheckup transports whole panel sections as state
attributes on purpose, because the panel reads them from ``hass.states``.

Those attributes therefore have to be excluded from recording with
``_unrecorded_attributes``: the recorder removes the listed keys before it
measures the row, while the state machine, the websocket API and the panel are
unaffected. ``_unrecorded_attributes`` is a class attribute that Home Assistant
merges in ``Entity.__init_subclass__``, so it cannot be set per instance and a
subclass is required.

The check is AST based so it runs without a Home Assistant installation.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "backup_checkup"

#: Attribute callbacks that hand a whole recovery block or a whole snapshot
#: object to the state machine must not be recorded. The receiver name is not
#: part of the rule, so renaming the lambda parameter cannot hide a block.
_LARGE_FIELD_PREFIX = "recovery_"
_SNAPSHOT_CALL = "as_dict"

#: ``stored_backups`` calls ``as_dict()`` per storage location, but that
#: summary is a flat dict of thirteen scalars and the number of configured
#: backup agents is small, so the row stays far below the limit. It is listed
#: here instead of being excluded, so its attribute history is kept.
_FLAT_SNAPSHOT_KEYS = frozenset({"stored_backups"})

_PLATFORMS: tuple[tuple[str, str], ...] = (
    ("sensor.py", "BackupCheckupSensorDescription"),
    ("binary_sensor.py", "BackupCheckupBinarySensorDescription"),
)

_UNRECORDED_SUBCLASSES: tuple[tuple[str, str, str], ...] = (
    (
        "sensor.py",
        "BackupCheckupUnrecordedAttributesSensor",
        "BackupCheckupSensor",
    ),
    (
        "binary_sensor.py",
        "BackupCheckupUnrecordedAttributesBinarySensor",
        "BackupCheckupBinarySensor",
    ),
)


def _call_name(node: ast.expr) -> str | None:
    """Return the terminal name of a call target."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _class_def(tree: ast.Module, name: str) -> ast.ClassDef | None:
    """Return one module level class definition."""
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == name
        ),
        None,
    )


def _setup_entry(tree: ast.Module) -> ast.AsyncFunctionDef | None:
    """Return the entity platform setup hook of one module."""
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_setup_entry"
        ),
        None,
    )


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Return every module level helper that an attribute callback may call."""
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def _unrecorded_source(class_def: ast.ClassDef, source: str) -> str | None:
    """Return the source of the ``_unrecorded_attributes`` assignment."""
    for node in class_def.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "_unrecorded_attributes":
                return ast.get_source_segment(source, node) or ""
    return None


def _is_large(
    node: ast.AST,
    helpers: dict[str, ast.FunctionDef],
    seen: frozenset[str] = frozenset(),
) -> bool:
    """Return whether an expression exposes a whole detail block.

    Module level helpers are followed once, so moving a recovery block behind
    ``attributes_fn=_recovery_details`` cannot hide it from this check.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr.startswith(
            _LARGE_FIELD_PREFIX
        ):
            return True
        if not isinstance(child, ast.Call):
            continue
        name = _call_name(child.func)
        if name == _SNAPSHOT_CALL:
            return True
        if name is None or name in seen:
            continue
        helper = helpers.get(name)
        if helper is not None and _is_large(helper, helpers, seen | {name}):
            return True
    return False


def _description_keywords(call: ast.Call) -> dict[str, ast.keyword]:
    """Return the keyword arguments of one entity description."""
    return {kw.arg: kw for kw in call.keywords if kw.arg is not None}


def _check_descriptions(
    tree: ast.Module,
    filename: str,
    description_name: str,
    problems: list[str],
) -> int:
    """Require ``record_attributes=False`` for every large description."""
    helpers = _module_functions(tree)
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) != description_name:
            continue
        keywords = _description_keywords(node)
        key_node = keywords.get("key")
        if key_node is None or not isinstance(key_node.value, ast.Constant):
            problems.append(f"{filename}: entity description without a literal key")
            continue
        key = str(key_node.value.value)
        checked += 1
        attributes = keywords.get("attributes_fn")
        if attributes is None or not _is_large(attributes.value, helpers):
            continue
        if key in _FLAT_SNAPSHOT_KEYS:
            continue
        record = keywords.get("record_attributes")
        if record is None or not isinstance(record.value, ast.Constant):
            problems.append(
                f"{filename}: {key} exposes detail attributes without a literal "
                "record_attributes=False"
            )
            continue
        if record.value.value is not False:
            problems.append(
                f"{filename}: {key} exposes detail attributes but sets "
                "record_attributes to a recorded value"
            )
    return checked


def _check_setup_selection(
    tree: ast.Module,
    filename: str,
    class_name: str,
    problems: list[str],
) -> None:
    """Require the platform setup to pick the class from the description."""
    setup = _setup_entry(tree)
    if setup is None:
        problems.append(f"{filename}: no async_setup_entry")
        return
    loaded = {
        node.id
        for node in ast.walk(setup)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    if class_name not in loaded:
        problems.append(
            f"{filename}: async_setup_entry never selects {class_name}, so "
            "record_attributes has no effect"
        )
    attributes = {
        node.attr for node in ast.walk(setup) if isinstance(node, ast.Attribute)
    }
    if "record_attributes" not in attributes:
        problems.append(
            f"{filename}: async_setup_entry does not read record_attributes"
        )


def _check_unrecorded_subclass(
    tree: ast.Module,
    source: str,
    filename: str,
    class_name: str,
    base_name: str,
    problems: list[str],
) -> None:
    """Require a subclass that keeps every attribute out of the recorder."""
    class_def = _class_def(tree, class_name)
    if class_def is None:
        problems.append(f"{filename}: missing class {class_name}")
        return
    bases = {_call_name(base) for base in class_def.bases}
    if base_name not in bases:
        problems.append(f"{filename}: {class_name} does not extend {base_name}")
    assignment = _unrecorded_source(class_def, source)
    if assignment is None:
        problems.append(f"{filename}: {class_name} has no _unrecorded_attributes")
    elif "MATCH_ALL" not in assignment:
        problems.append(f"{filename}: {class_name} does not exclude MATCH_ALL")
    _check_setup_selection(tree, filename, class_name, problems)


def _check_activity_sensor(
    tree: ast.Module,
    source: str,
    problems: list[str],
) -> None:
    """Require the bounded journal entries to stay out of the recorder."""
    class_def = _class_def(tree, "BackupCheckupActivitySensor")
    if class_def is None:
        problems.append("sensor.py: missing class BackupCheckupActivitySensor")
        return
    assignment = _unrecorded_source(class_def, source)
    if assignment is None:
        problems.append(
            "sensor.py: BackupCheckupActivitySensor has no _unrecorded_attributes"
        )
        return
    if '"entries"' not in assignment:
        problems.append(
            "sensor.py: BackupCheckupActivitySensor does not exclude entries"
        )


def main() -> None:
    """Fail when a large attribute set could reach the recorder."""
    problems: list[str] = []
    checked = 0
    sources: dict[str, tuple[ast.Module, str]] = {}
    for filename, description_name in _PLATFORMS:
        source = (PACKAGE / filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        sources[filename] = (tree, source)
        checked += _check_descriptions(tree, filename, description_name, problems)

    for filename, class_name, base_name in _UNRECORDED_SUBCLASSES:
        tree, source = sources[filename]
        _check_unrecorded_subclass(
            tree, source, filename, class_name, base_name, problems
        )

    sensor_tree, sensor_source = sources["sensor.py"]
    _check_activity_sensor(sensor_tree, sensor_source, problems)

    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit("Large state attributes would be written to the recorder")
    print(f"Recorder attribute limits respected: {checked} entity descriptions")


if __name__ == "__main__":
    main()
