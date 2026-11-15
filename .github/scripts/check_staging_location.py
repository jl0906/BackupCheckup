"""Fail when verification data could be staged in the process temporary directory.

On Home Assistant OS the Core container mounts ``/tmp`` as a RAM-backed tmpfs, so
any ``tempfile`` call without an explicit ``dir=`` argument would place multi-GB
verification copies in memory and abort with ``insufficient_free_space``. Every
temporary file or directory must therefore be created below the configured
staging root, and ``tempfile.gettempdir()`` may only be used by the explicitly
named legacy cleanup helper.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
_FACTORIES = {"mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile"}
_LEGACY_FUNCTION = "legacy_temp_root"


def _call_name(node: ast.Call) -> str | None:
    """Return ``tempfile.<name>`` style call targets."""
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "tempfile":
            return func.attr
        return None
    if isinstance(func, ast.Name) and func.id in _FACTORIES | {"gettempdir"}:
        return func.id
    return None


def _enclosing_function(tree: ast.AST, target: ast.AST) -> str | None:
    """Return the name of the function that contains ``target``."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if child is target:
                    return node.name
    return None


def _check_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in _FACTORIES:
            if not any(keyword.arg == "dir" for keyword in node.keywords):
                problems.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: tempfile.{name}() "
                    "without dir= would use the process temporary directory"
                )
        elif name == "gettempdir":
            function = _enclosing_function(tree, node)
            if function != _LEGACY_FUNCTION:
                problems.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: tempfile.gettempdir() "
                    f"is only allowed inside {_LEGACY_FUNCTION}()"
                )
    return problems


def main() -> int:
    problems: list[str] = []
    for path in sorted(INTEGRATION.rglob("*.py")):
        problems.extend(_check_file(path))
    if problems:
        print("\n".join(problems))
        return 1
    print("Verification staging never falls back to the process temporary directory")
    return 0


if __name__ == "__main__":
    sys.exit(main())
