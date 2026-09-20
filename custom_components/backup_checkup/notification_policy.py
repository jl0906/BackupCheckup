"""Confirmation policy for BackupCheckup problem notifications.

Backup agents of other integrations can be unreachable for a single refresh,
for example while a network share reconnects or a cloud token is renewed.
Pushing a problem on the first snapshot that reports it therefore produces a
"problem detected" message that is followed by an "all problems resolved"
message a few minutes later.

A newly seen problem set is held back until a later refresh still reports the
same set. A problem that disappears before it was confirmed was never
reported, so it must not produce a recovery message either. Recovery from a
confirmed problem stays immediate.

The module is free of Home Assistant imports on purpose so the decision table
can be validated standalone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

NOTIFICATION_ACTION_SEND_PROBLEM: Final = "send_problem"
NOTIFICATION_ACTION_SEND_RECOVERY: Final = "send_recovery"
NOTIFICATION_ACTION_WAIT_CONFIRM: Final = "wait_confirm"
NOTIFICATION_ACTION_CLEAR_PENDING: Final = "clear_pending"
NOTIFICATION_ACTION_NOOP: Final = "noop"

#: Fixed activity reasons for the two decisions that hold a message back.
NOTIFICATION_SKIP_REASONS: Final[dict[str, str]] = {
    NOTIFICATION_ACTION_WAIT_CONFIRM: "awaiting_confirmation",
    NOTIFICATION_ACTION_CLEAR_PENDING: "problem_not_confirmed",
}


@dataclass(frozen=True, slots=True)
class NotificationDecision:
    """One decision together with the confirmation state it leaves behind."""

    action: str
    pending_signature: str = ""
    pending_since: datetime | None = None

    @property
    def confirmation_pending(self) -> bool:
        """Return whether a later refresh still has to confirm a problem."""
        return bool(self.pending_signature)

    @property
    def skip_reason(self) -> str | None:
        """Return the activity reason when no message is sent."""
        return NOTIFICATION_SKIP_REASONS.get(self.action)


def evaluate_notification_change(
    *,
    signature: str,
    last_signature: str,
    pending_signature: str,
    pending_since: datetime | None,
    now: datetime,
    confirm_seconds: float,
) -> NotificationDecision:
    """Return what to do with the currently active problem signature."""
    if signature == last_signature:
        # The reported state is unchanged. A problem that was waiting for its
        # confirmation disappeared, so nothing was ever sent for it and
        # nothing has to be resolved.
        if pending_signature:
            return NotificationDecision(NOTIFICATION_ACTION_CLEAR_PENDING)
        return NotificationDecision(NOTIFICATION_ACTION_NOOP)
    if not signature:
        # Recovery from a reported problem is never delayed.
        return NotificationDecision(NOTIFICATION_ACTION_SEND_RECOVERY)
    if signature != pending_signature or pending_since is None:
        # A new or changed problem set restarts the confirmation window.
        return NotificationDecision(
            NOTIFICATION_ACTION_WAIT_CONFIRM,
            pending_signature=signature,
            pending_since=now,
        )
    if (now - pending_since).total_seconds() >= confirm_seconds:
        return NotificationDecision(NOTIFICATION_ACTION_SEND_PROBLEM)
    return NotificationDecision(
        NOTIFICATION_ACTION_NOOP,
        pending_signature=pending_signature,
        pending_since=pending_since,
    )
