"""Verify Home Assistant async event helpers receive event-loop callbacks."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COORDINATOR = ROOT / "custom_components" / "backup_checkup" / "coordinator.py"


def _name(node: ast.expr) -> str | None:
    """Return the terminal name for a simple name or attribute expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def main() -> None:
    """Ensure each tracked state callback is decorated for the event loop."""
    tree = ast.parse(COORDINATOR.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    tracked_callbacks: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _name(node.func) != "async_track_state_change_event":
            continue
        if len(node.args) < 3:
            raise SystemExit("Tracked state callback must be a positional function")
        callback_name = _name(node.args[2])
        if callback_name is None:
            raise SystemExit("Unable to resolve tracked state callback")
        tracked_callbacks.add(callback_name)

    if not tracked_callbacks:
        raise SystemExit("No tracked state callbacks found")
    for callback_name in tracked_callbacks:
        function = functions.get(callback_name)
        if function is None:
            raise SystemExit(f"Tracked callback not found: {callback_name}")
        decorators = {_name(decorator) for decorator in function.decorator_list}
        if "callback" not in decorators:
            raise SystemExit(
                f"Tracked callback runs outside the event loop: {callback_name}"
            )

    print("Async state callbacks are event-loop safe")


if __name__ == "__main__":
    main()
