"""Resolve one user-facing recovery evidence level from all available proofs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .recovery_restore import RestoreTestSnapshot

EVIDENCE_NOT_RECOVERABLE = "not_recoverable"
EVIDENCE_LIMITED = "limited"
EVIDENCE_MONITORED = "monitored"
EVIDENCE_STRUCTURAL = "structurally_verified"
EVIDENCE_RUNTIME = "runtime_ready"
EVIDENCE_FULL = "fully_tested"
EVIDENCE_OPTIONS = (
    EVIDENCE_NOT_RECOVERABLE,
    EVIDENCE_LIMITED,
    EVIDENCE_MONITORED,
    EVIDENCE_STRUCTURAL,
    EVIDENCE_RUNTIME,
    EVIDENCE_FULL,
)


@dataclass(frozen=True, slots=True)
class RecoveryEvidence:
    """One honest, non-duplicated recovery proof level."""

    level: str
    structural_verified: bool
    runtime_verified: bool
    external_restore_verified: bool
    optional_next_step: str | None

    def as_dict(self) -> dict[str, Any]:
        """Return frontend-safe evidence data."""
        return {
            "level": self.level,
            "structural_verified": self.structural_verified,
            "runtime_verified": self.runtime_verified,
            "external_restore_verified": self.external_restore_verified,
            "optional_next_step": self.optional_next_step,
        }


def resolve_recovery_evidence(
    *,
    has_backup: bool,
    backup_usable: bool,
    structural_passed: bool | None,
    restore_test: RestoreTestSnapshot,
    runtime_verified: bool = False,
) -> RecoveryEvidence:
    """Choose the strongest proof without making optional evidence a requirement."""
    external = restore_test.passed is True
    structural = structural_passed is True
    if not has_backup:
        level = EVIDENCE_NOT_RECOVERABLE
    elif not backup_usable or structural_passed is False:
        level = EVIDENCE_LIMITED
    elif external:
        level = EVIDENCE_FULL
    elif runtime_verified:
        level = EVIDENCE_RUNTIME
    elif structural:
        level = EVIDENCE_STRUCTURAL
    else:
        level = EVIDENCE_MONITORED

    optional_next_step = None
    if level == EVIDENCE_STRUCTURAL:
        optional_next_step = "ephemeral_runtime_test"
    elif level == EVIDENCE_RUNTIME:
        optional_next_step = "external_restore_test"
    return RecoveryEvidence(
        level=level,
        structural_verified=structural,
        runtime_verified=runtime_verified,
        external_restore_verified=external,
        optional_next_step=optional_next_step,
    )
