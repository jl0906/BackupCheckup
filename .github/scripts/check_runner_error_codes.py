"""Verify that every runner failure code is translated and classified.

The Runtime Runner reports failures as stable codes. A code that the panel does
not know used to be rendered as one generic message, which hid the real cause.
This check extracts every ``RunnerFailure("...")`` code from ``server.py`` and
fails unless

* the English panel texts translate it as ``runnerErrors.runner_<code>`` and
* ``progress.py`` lists ``runner_<code>`` in exactly one of the four code sets.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "backup_checkup"
SERVER = (
    ROOT / "runtime_runner" / "rootfs" / "opt" / "backup-checkup-runner" / "server.py"
)
PANEL = INTEGRATION / "frontend" / "backup-checkup-panel.js"
PROGRESS = INTEGRATION / "progress.py"
CODE_SETS = (
    "RUNNER_NOT_STARTED_CODES",
    "RUNNER_ABORTED_CODES",
    "RUNNER_INCONCLUSIVE_CODES",
    "RUNNER_FAILED_CODES",
)
# Codes that only an older, still compatible runner raises.
LEGACY_CODES = frozenset({"unsupported_archive_member"})
_SEPARATOR = "\x1f"


def _runner_codes() -> set[str]:
    """Return every code the shipped runner can raise."""
    source = SERVER.read_text(encoding="utf-8")
    codes = set(re.findall(r'RunnerFailure\("([a-z_]+)"\)', source))
    if not codes:
        raise SystemExit("No RunnerFailure codes found in server.py")
    return codes


def _panel_runner_errors() -> set[str]:
    """Return the runnerErrors keys of the packed English panel texts."""
    source = PANEL.read_text(encoding="utf-8")
    keys: set[str] = set()
    for match in re.finditer(
        r'^const \w+_TEXT_PATHS\w* = Object\.freeze\(("(?:[^"\\]|\\.)*")\.split',
        source,
        re.MULTILINE,
    ):
        # The packed lists are JSON string literals; \x1f is the only escape
        # JSON does not know.
        literal = match.group(1).replace("\\x1f", "\\u001f")
        for path in json.loads(literal).split(_SEPARATOR):
            if path.startswith("runnerErrors."):
                keys.add(path.removeprefix("runnerErrors."))
    if not keys:
        raise SystemExit("No runnerErrors paths found in the panel")
    return keys


def _progress_code_sets() -> dict[str, set[str]]:
    """Return the literal members of the code sets in progress.py."""
    tree = ast.parse(PROGRESS.read_text(encoding="utf-8"), filename=str(PROGRESS))
    result: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in CODE_SETS:
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and len(call.args) == 1):
            raise SystemExit(f"{target.id} must be a frozenset of string literals")
        result[target.id] = set(ast.literal_eval(call.args[0]))
    missing = [name for name in CODE_SETS if name not in result]
    if missing:
        raise SystemExit(f"progress.py does not define {', '.join(missing)}")
    return result


def main() -> int:
    runner_codes = _runner_codes()
    translated = _panel_runner_errors()
    code_sets = _progress_code_sets()
    problems: list[str] = []

    for code in sorted(runner_codes | LEGACY_CODES):
        key = f"runner_{code}"
        if key not in translated:
            problems.append(f"{key} is not translated in the panel runnerErrors")
        owners = [name for name, members in code_sets.items() if key in members]
        if len(owners) != 1:
            problems.append(
                f"{key} must be in exactly one progress.py code set, found: "
                f"{', '.join(owners) or 'none'}"
            )

    known = {f"runner_{code}" for code in runner_codes | LEGACY_CODES}
    for stale in sorted(code_sets["RUNNER_FAILED_CODES"] - known):
        problems.append(f"RUNNER_FAILED_CODES lists {stale}, which no runner raises")
    if "unsupported_archive_member" in runner_codes:
        problems.append("server.py must not raise unsupported_archive_member anymore")

    if problems:
        print("\n".join(problems))
        return 1
    print(
        f"All {len(runner_codes)} runner failure codes are translated and classified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
