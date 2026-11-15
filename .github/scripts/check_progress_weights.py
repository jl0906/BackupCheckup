"""Keep the runtime step weights of integration and runner identical."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRESS = ROOT / "custom_components" / "backup_checkup" / "progress.py"
SERVER = (
    ROOT
    / "runtime_runner"
    / "rootfs"
    / "opt"
    / "backup-checkup-runner"
    / "server.py"
)


def _assignment(tree: ast.Module, name: str) -> ast.expr:
    """Return the value assigned to one module-level constant."""
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(item, ast.Name) and item.id == name for item in targets):
            value = node.value
            if value is None:
                break
            return value
    raise SystemExit(f"Constant {name} not found")


def _integration_steps(tree: ast.Module, name: str) -> list[tuple[str, int, bool]]:
    """Read one StepDefinition tuple from progress.py."""
    steps: list[tuple[str, int, bool]] = []
    for call in _assignment(tree, name).elts:
        if not isinstance(call, ast.Call):
            raise SystemExit(f"{name} must only contain StepDefinition calls")
        key = ast.literal_eval(call.args[0])
        weight = ast.literal_eval(call.args[2])
        determinate = True
        for keyword in call.keywords:
            if keyword.arg == "determinate":
                determinate = ast.literal_eval(keyword.value)
        steps.append((key, weight, determinate))
    return steps


def _runner_steps(tree: ast.Module) -> list[tuple[str, int, bool]]:
    """Read the mirrored RUNTIME_STEPS tuple from the runner."""
    return [tuple(ast.literal_eval(item)) for item in _assignment(tree, "RUNTIME_STEPS").elts]


def main() -> None:
    """Fail when the two step lists drift apart or stop summing to 100."""
    progress_tree = ast.parse(PROGRESS.read_text(encoding="utf-8"))
    server_tree = ast.parse(SERVER.read_text(encoding="utf-8"))

    verification = _integration_steps(progress_tree, "VERIFICATION_STEPS")
    runtime = _integration_steps(progress_tree, "RUNTIME_STEPS")
    runner = _runner_steps(server_tree)

    problems: list[str] = []
    for name, steps in (("verification", verification), ("runtime_test", runtime)):
        total = sum(weight for _key, weight, _determinate in steps)
        if total != 100:
            problems.append(f"{name} weights sum to {total} instead of 100")
        keys = [key for key, _weight, _determinate in steps]
        if len(keys) != len(set(keys)):
            problems.append(f"{name} contains duplicate step keys")

    runner_total = sum(weight for _key, weight, _determinate in runner)
    if runner_total != 100:
        problems.append(f"runner weights sum to {runner_total} instead of 100")
    if runtime != runner:
        problems.append(
            "runtime step lists differ:\n"
            f"  progress.py: {runtime}\n"
            f"  server.py:   {runner}"
        )

    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit("Progress weights are inconsistent")
    print(
        "Progress weights consistent: "
        f"{len(verification)} verification steps, {len(runtime)} runtime steps"
    )


if __name__ == "__main__":
    main()
