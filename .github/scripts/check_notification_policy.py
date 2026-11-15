"""Validate the notification confirmation policy without Home Assistant.

Two effects produced a "problem detected" push that was followed by an "all
problems resolved" push a few minutes later:

* the first refresh runs while Home Assistant is still starting, when the
  backup agents of other integrations are not registered yet, and
* a single failing storage read during normal operation is enough to change
  the active problem set for one refresh.

The first case is handled by the startup hold of the coordinator, the second
by the confirmation window of ``notification_policy``. This check drives the
real decision function through both situations and additionally guards the
structure that makes the decision effective: the hold, the persisted store
format and the timer contract.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "backup_checkup"
POLICY_PATH = PACKAGE / "notification_policy.py"

CONFIRM_SECONDS = 180.0
START = datetime(2026, 1, 1, tzinfo=UTC)

#: The exact payload of the notification store. The confirmation window is
#: runtime state and must not extend the persisted format.
STORE_KEYS = {"last_signature", "was_enabled", "last_targets"}

#: The fixed delays. They are deliberately not configuration options.
EXPECTED_CONSTANTS = {
    "STARTUP_SETTLE_SECONDS": "120",
    "NOTIFICATION_CONFIRM_SECONDS": "180",
    "NOTIFICATION_CONFIRM_RECHECK_SECONDS": "NOTIFICATION_CONFIRM_SECONDS + 5",
}


def _load_policy():
    """Import notification_policy.py directly, without the package."""
    spec = importlib.util.spec_from_file_location(
        "backup_checkup_notification_policy_check", POLICY_PATH
    )
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load the notification policy module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require(condition: bool, message: str) -> None:
    """Fail the check with a readable message."""
    if not condition:
        raise SystemExit(message)


class _Manager:
    """Mirror of the notification manager around the real policy function.

    Only the small persistence rule of
    ``BackupCheckupNotificationManager._async_send_state_change`` is
    reproduced: a problem is pushed when the signature is not empty, a
    recovery is pushed only for a previously reported problem and only when
    the user asked for it, and the stored signature always follows the new
    state. ``_check_store_format`` guards that the real method still works
    that way, so the mirror cannot drift apart unnoticed.
    """

    def __init__(self, policy, last_signature: str = "") -> None:
        """Start from the state a restart would restore from the store."""
        self._policy = policy
        self.last_signature = last_signature
        self.pending_signature = ""
        self.pending_since: datetime | None = None
        self.pushes: list[str] = []
        self.reasons: list[str] = []

    def process(
        self,
        signature: str,
        now: datetime,
        *,
        notify_on_recovery: bool = True,
    ) -> bool:
        """Run one refresh and return whether a confirmation is pending."""
        decision = self._policy.evaluate_notification_change(
            signature=signature,
            last_signature=self.last_signature,
            pending_signature=self.pending_signature,
            pending_since=self.pending_since,
            now=now,
            confirm_seconds=CONFIRM_SECONDS,
        )
        self.pending_signature = decision.pending_signature
        self.pending_since = decision.pending_since
        if (reason := decision.skip_reason) is not None:
            self.reasons.append(reason)
        if decision.action in (
            self._policy.NOTIFICATION_ACTION_SEND_PROBLEM,
            self._policy.NOTIFICATION_ACTION_SEND_RECOVERY,
        ):
            if signature:
                self.pushes.append("problem")
            elif self.last_signature and notify_on_recovery:
                self.pushes.append("recovery")
            self.last_signature = signature
        return decision.confirmation_pending


def _check_startup_flapping(policy) -> None:
    """A problem that only exists during the start phase is never pushed."""
    manager = _Manager(policy)
    _require(
        manager.process("storage_error", START) is True,
        "A newly seen problem must start a confirmation window",
    )
    manager.process("storage_error", START + timedelta(seconds=60))
    manager.process("", START + timedelta(seconds=120))
    _require(
        manager.pushes == [],
        f"Start flapping must not notify, sent {manager.pushes}",
    )
    _require(
        manager.reasons == ["awaiting_confirmation", "problem_not_confirmed"],
        f"Unexpected activity reasons: {manager.reasons}",
    )
    _require(
        manager.last_signature == "" and manager.pending_signature == "",
        "Unconfirmed flapping must leave no state behind",
    )


def _check_real_problem(policy) -> None:
    """A problem that survives the window is pushed exactly once."""
    manager = _Manager(policy)
    manager.process("storage_error", START)
    manager.process("storage_error", START + timedelta(seconds=120))
    _require(manager.pushes == [], "A problem must not be pushed before the window")
    manager.process("storage_error", START + timedelta(seconds=185))
    _require(
        manager.pushes == ["problem"],
        f"The confirmed problem must be pushed once, sent {manager.pushes}",
    )
    _require(
        manager.pending_signature == "",
        "A confirmed problem must not stay pending",
    )
    manager.process("storage_error", START + timedelta(seconds=600))
    _require(
        manager.pushes == ["problem"],
        "An unchanged problem must not be pushed again",
    )
    manager.process("", START + timedelta(seconds=900))
    _require(
        manager.pushes == ["problem", "recovery"],
        f"Recovery must be sent immediately, sent {manager.pushes}",
    )


def _check_restart_with_reported_problem(policy) -> None:
    """A problem that was reported before a restart is not pushed again."""
    manager = _Manager(policy, last_signature="storage_error")
    for offset in (0, 300, 3600):
        manager.process("storage_error", START + timedelta(seconds=offset))
    _require(
        manager.pushes == [],
        f"A restart must not repeat a reported problem, sent {manager.pushes}",
    )
    _require(
        manager.reasons == [],
        f"An unchanged problem needs no activity entry: {manager.reasons}",
    )


def _check_changed_problem_set(policy) -> None:
    """A changed problem set restarts the confirmation window."""
    manager = _Manager(policy)
    manager.process("storage_error", START)
    manager.process(
        "backup_not_redundant|storage_error", START + timedelta(seconds=100)
    )
    _require(
        manager.pending_since == START + timedelta(seconds=100),
        "A changed problem set must restart the window",
    )
    manager.process(
        "backup_not_redundant|storage_error", START + timedelta(seconds=200)
    )
    _require(
        manager.pushes == [],
        "The restarted window must still hold the problem back",
    )
    manager.process(
        "backup_not_redundant|storage_error", START + timedelta(seconds=281)
    )
    _require(
        manager.pushes == ["problem"],
        f"The changed set must be pushed after its own window: {manager.pushes}",
    )


def _check_recovery_notification_disabled(policy) -> None:
    """A disabled recovery message still clears the reported state."""
    manager = _Manager(policy, last_signature="storage_error")
    manager.process("", START, notify_on_recovery=False)
    _require(
        manager.pushes == [],
        f"notify_on_recovery=False must stay silent, sent {manager.pushes}",
    )
    _require(
        manager.last_signature == "",
        "The reported state must be cleared even without a recovery message",
    )
    manager.process("storage_error", START + timedelta(seconds=60))
    manager.process("storage_error", START + timedelta(seconds=300))
    _require(
        manager.pushes == ["problem"],
        f"A later problem must be reported again, sent {manager.pushes}",
    )


def _function(tree: ast.Module, name: str) -> ast.AST:
    """Return one function definition anywhere in a module."""
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise SystemExit(f"Function not found: {name}")


def _assigned_targets(node: ast.AST) -> set[str]:
    """Return every assignment target below one node."""
    return {
        ast.unparse(target)
        for child in ast.walk(node)
        if isinstance(child, ast.Assign)
        for target in child.targets
    }


def _returns(node: ast.AST) -> bool:
    """Return whether a branch leaves its function."""
    return any(isinstance(child, ast.Return) for child in ast.walk(node))


def _first_statement(function: ast.AST) -> ast.stmt | None:
    """Return the first real statement of a function, skipping its docstring."""
    body = list(getattr(function, "body", ()))
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return body[0] if body else None


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Return every module level constant as unparsed source."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = ast.unparse(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            constants[node.target.id] = ast.unparse(node.value)
    return constants


def _check_store_format(problems: list[str]) -> None:
    """The confirmation window must stay out of the persisted store."""
    source = (PACKAGE / "notifications.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    constants = _module_constants(tree)
    if constants.get("_STORAGE_VERSION") != "1":
        problems.append(
            f"notifications.py: _STORAGE_VERSION is {constants.get('_STORAGE_VERSION')}"
        )
    save = _function(tree, "_async_save")
    keys = {
        key.value
        for node in ast.walk(save)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant)
    }
    if keys != STORE_KEYS:
        problems.append(f"notifications.py: store payload changed to {sorted(keys)}")

    send = _function(tree, "_async_send_state_change")
    if "self._last_signature" not in _assigned_targets(send):
        problems.append(
            "notifications.py: _async_send_state_change no longer stores the signature"
        )
    for node in ast.walk(send):
        if not isinstance(node, ast.If):
            continue
        if "notify_on_recovery" not in ast.unparse(node.test):
            continue
        if "self._last_signature" in _assigned_targets(node):
            problems.append(
                "notifications.py: the stored signature now depends on "
                "notify_on_recovery, so a silenced recovery would never clear it"
            )
    if "evaluate_notification_change" not in source:
        problems.append("notifications.py: the confirmation policy is not used")


def _check_startup_hold(problems: list[str]) -> None:
    """Notifications and health repairs must wait for a settled start."""
    coordinator_source = (PACKAGE / "coordinator.py").read_text(encoding="utf-8")
    coordinator = ast.parse(coordinator_source)

    # hass.is_running is also true while Home Assistant is still starting, so
    # only an explicit CoreState.running test gives a restart its grace period.
    settled = [
        ast.unparse(node.value)
        for node in ast.walk(coordinator)
        if isinstance(node, ast.Assign)
        and "self._startup_settled" in _assigned_targets(node)
    ]
    if not any("CoreState.running" in value for value in settled):
        problems.append(
            "coordinator.py: the startup hold does not test for CoreState.running"
        )

    process = _function(coordinator, "_async_process_notifications")
    guard = _first_statement(process)
    if not isinstance(guard, ast.If) or "startup_settled" not in ast.unparse(
        guard.test
    ):
        problems.append(
            "coordinator.py: _async_process_notifications does not start with "
            "the startup hold"
        )
    elif not _returns(guard):
        problems.append(
            "coordinator.py: the startup hold does not return before processing"
        )

    schedule = _function(coordinator, "_async_schedule_notification_confirmation")
    reuse = _first_statement(schedule)
    if (
        not isinstance(reuse, ast.If)
        or "_confirmation_unsubscribe" not in ast.unparse(reuse.test)
        or not _returns(reuse)
    ):
        problems.append(
            "coordinator.py: the confirmation timer is no longer reused, so "
            "refreshes would stack"
        )

    shutdown = _function(coordinator, "async_shutdown")
    shutdown_calls = ast.unparse(shutdown)
    for name in (
        "_async_cancel_startup_settle",
        "_async_cancel_notification_confirmation",
    ):
        if name not in shutdown_calls:
            problems.append(f"coordinator.py: async_shutdown does not call {name}")

    setup = ast.parse((PACKAGE / "__init__.py").read_text(encoding="utf-8"))
    sync = _function(setup, "_sync_repair_issues")
    repair_guard = _first_statement(sync)
    if not isinstance(repair_guard, ast.If) or "startup_settled" not in ast.unparse(
        repair_guard.test
    ):
        problems.append(
            "__init__.py: _sync_repair_issues does not wait for a settled start"
        )
    elif not _returns(repair_guard):
        problems.append(
            "__init__.py: the repair issue hold does not return before syncing"
        )


def _check_constants(problems: list[str]) -> None:
    """The delays are fixed constants and never configuration options."""
    source = (PACKAGE / "const.py").read_text(encoding="utf-8")
    constants = _module_constants(ast.parse(source))
    for name, value in EXPECTED_CONSTANTS.items():
        if constants.get(name) != value:
            problems.append(
                f"const.py: {name} is {constants.get(name)} instead of {value}"
            )
        option_key = f"CONF_{name.removesuffix('_SECONDS')}"
        if option_key in constants:
            problems.append(f"const.py: {name} must not become the option {option_key}")


def main() -> None:
    """Fail when a restart or a short dropout could notify again."""
    policy = _load_policy()
    _check_startup_flapping(policy)
    _check_real_problem(policy)
    _check_restart_with_reported_problem(policy)
    _check_changed_problem_set(policy)
    _check_recovery_notification_disabled(policy)

    problems: list[str] = []
    _check_store_format(problems)
    _check_startup_hold(problems)
    _check_constants(problems)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit("Notification confirmation policy is not wired correctly")
    print("Notification confirmation policy verified: 5 scenarios")


if __name__ == "__main__":
    main()
