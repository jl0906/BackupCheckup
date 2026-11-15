"""Reject calls that pass a keyword twice through an unpacked helper dict.

``f(**helper(), key=value)`` raises ``TypeError`` at runtime when ``helper``
also returns ``key``. Neither ruff nor ``compileall`` sees that, because the
conflict only exists once the helper's literal keys are known.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "backup_checkup"


def _returned_keys(function: ast.FunctionDef) -> set[str] | None:
    """Return the literal keys of a helper that always returns one dict."""
    keys: set[str] = set()
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
    if not returns:
        return None
    for node in returns:
        if not isinstance(node.value, ast.Dict):
            return None
        for key in node.value.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                return None
            keys.add(key.value)
    return keys


def _helpers(tree: ast.Module) -> dict[str, set[str]]:
    """Return every module-level function that yields a literal dict."""
    helpers: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and (keys := _returned_keys(node)):
            helpers[node.name] = keys
    return helpers


def _conflicts(tree: ast.Module, helpers: dict[str, set[str]]) -> list[str]:
    """Return one message per call that would raise a duplicate-keyword error."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        explicit = {
            keyword.arg for keyword in node.keywords if keyword.arg is not None
        }
        if not explicit:
            continue
        for keyword in node.keywords:
            if keyword.arg is not None:
                continue
            value = keyword.value
            if not isinstance(value, ast.Call) or not isinstance(
                value.func, ast.Name
            ):
                continue
            unpacked = helpers.get(value.func.id)
            if unpacked is None:
                continue
            if duplicate := sorted(unpacked & explicit):
                problems.append(
                    f"line {node.lineno}: **{value.func.id}() and the explicit "
                    f"keyword(s) {', '.join(duplicate)} collide"
                )
    return problems


def main() -> None:
    """Fail when any call would receive the same keyword twice."""
    problems: list[str] = []
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        helpers = _helpers(tree)
        if not helpers:
            continue
        problems.extend(
            f"{path.name}:{message}" for message in _conflicts(tree, helpers)
        )
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(f"{len(problems)} duplicate keyword arguments")
    print("No duplicate keyword arguments through unpacked helpers")


if __name__ == "__main__":
    main()
