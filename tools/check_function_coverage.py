#!/usr/bin/env python3
"""Enforce execution of every Python production function at least once."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class FunctionEntry:
    """One executable production function entry point."""

    path: Path
    qualified_name: str
    line: int


def _first_executable_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the first executable body line, excluding a docstring."""
    body = node.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return body[0].lineno if body else node.lineno


class _FunctionVisitor(ast.NodeVisitor):
    """Collect qualified names and executable entry lines."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.scope: list[str] = []
        self.entries: list[FunctionEntry] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = ".".join((*self.scope, node.name))
        self.entries.append(
            FunctionEntry(self.path, name, _first_executable_line(node))
        )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


def _production_functions(source: Path) -> list[FunctionEntry]:
    """Return every function defined below the production source directory."""
    entries: list[FunctionEntry] = []
    for path in sorted(source.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _FunctionVisitor(path)
        visitor.visit(tree)
        entries.extend(visitor.entries)
    return entries


def _executed_lines(report: dict[str, Any], path: Path) -> set[int]:
    """Return executed lines while tolerating relative and absolute report keys."""
    files = report.get("files", {})
    candidates = (path.as_posix(), str(path), str(path.resolve()))
    for candidate in candidates:
        data = files.get(candidate)
        if isinstance(data, dict):
            return set(data.get("executed_lines", ()))
    for report_path, data in files.items():
        if Path(report_path).as_posix().endswith(path.as_posix()):
            return set(data.get("executed_lines", ()))
    return set()


def main() -> int:
    """Validate the coverage JSON report and print a stable summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", default="coverage.json")
    parser.add_argument(
        "--source", default="custom_components/backup_checkup", type=Path
    )
    args = parser.parse_args()

    report_path = Path(args.coverage_json)
    if not report_path.is_file():
        print(f"Function coverage report not found: {report_path}", file=sys.stderr)
        return 2

    report = json.loads(report_path.read_text(encoding="utf-8"))
    functions = _production_functions(args.source)
    uncovered = [
        entry
        for entry in functions
        if entry.line not in _executed_lines(report, entry.path)
    ]
    covered = len(functions) - len(uncovered)
    percentage = 100.0 if not functions else covered / len(functions) * 100
    print(
        "Function coverage: "
        f"{covered}/{len(functions)} ({percentage:.2f}%) production functions entered"
    )
    for entry in uncovered:
        print(f"UNCOVERED {entry.path}:{entry.line} {entry.qualified_name}")
    return 1 if uncovered else 0


if __name__ == "__main__":
    raise SystemExit(main())
