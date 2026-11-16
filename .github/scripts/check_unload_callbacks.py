"""Verify config-entry unload callbacks cannot return a truthy non-coroutine.

Home Assistant treats every truthy result of an ``async_on_unload`` callback
as a coroutine and schedules it. A bound ``Task.cancel`` or
``TimerHandle.cancel`` returns ``True`` while the task is running, which
aborts the unload with ``TypeError: a coroutine was expected, got True``.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"


def _name(node: ast.expr) -> str | None:
    """Return the terminal name for a simple name or attribute expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_cancel(node: ast.expr) -> bool:
    """Return whether the expression is an attribute access named ``cancel``."""
    return isinstance(node, ast.Attribute) and node.attr == "cancel"


def _problem(call: ast.Call) -> str | None:
    """Return why one ``async_on_unload`` call is unsafe, if it is."""
    if not call.args:
        return "the callback must be passed as a positional argument"
    callback = call.args[0]
    if _is_cancel(callback):
        return "a bound cancel method returns a bool, not None or a coroutine"
    if (
        isinstance(callback, ast.Lambda)
        and isinstance(callback.body, ast.Call)
        and _is_cancel(callback.body.func)
    ):
        return "a lambda that calls cancel() returns a bool"
    return None


def main() -> None:
    """Check every ``async_on_unload`` call of the integration."""
    found = 0
    problems: list[str] = []
    for path in sorted(INTEGRATION.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _name(node.func) != "async_on_unload":
                continue
            found += 1
            reason = _problem(node)
            if reason is not None:
                location = path.relative_to(ROOT).as_posix()
                problems.append(f"{location}:{node.lineno}: {reason}")

    if not found:
        raise SystemExit("No async_on_unload calls found")
    if problems:
        raise SystemExit("Unsafe unload callbacks:\n" + "\n".join(problems))

    print(f"Unload callbacks are safe: {found} checked")


if __name__ == "__main__":
    main()
