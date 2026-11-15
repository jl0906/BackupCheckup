"""Verify that every intra-package import resolves without loading the package.

Home Assistant is not installed in the validation job, so a misspelled helper
in ``from .module import name`` would only surface at runtime. This check
resolves every relative import statically and also rejects import cycles.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "backup_checkup"


def _module_exports(tree: ast.Module) -> set[str]:
    """Return every name a module defines at module level."""
    exported: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exported.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    exported.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            exported.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported.add(alias.asname or alias.name)
    return exported


def _relative_imports(tree: ast.Module) -> list[tuple[str, tuple[str, ...], int]]:
    """Return every ``from .module import ...`` statement of one file."""
    statements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            names = tuple(alias.name for alias in node.names)
            statements.append((node.module, names, node.lineno))
    return statements


def _detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return every import cycle inside the package."""
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for target in sorted(graph.get(node, ())):
            if state.get(target) == 1:
                cycles.append([*stack[stack.index(target) :], target])
            elif state.get(target, 0) == 0 and target in graph:
                visit(target)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def main() -> None:
    """Resolve every relative import and report unknown names or cycles."""
    trees = {
        path.stem: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in sorted(PACKAGE.glob("*.py"))
    }
    exports = {name: _module_exports(tree) for name, tree in trees.items()}
    graph: dict[str, set[str]] = {}
    problems: list[str] = []

    for name, tree in trees.items():
        graph[name] = set()
        for module, imported, lineno in _relative_imports(tree):
            graph[name].add(module)
            if module not in trees:
                problems.append(
                    f"{name}.py:{lineno} imports unknown module .{module}"
                )
                continue
            for imported_name in imported:
                if imported_name not in exports[module]:
                    problems.append(
                        f"{name}.py:{lineno} imports missing name "
                        f"{imported_name!r} from .{module}"
                    )

    for cycle in _detect_cycles(graph):
        problems.append("import cycle: " + " -> ".join(cycle))

    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(f"{len(problems)} unresolved intra-package imports")
    print(f"Internal imports resolved across {len(trees)} modules")


if __name__ == "__main__":
    main()
