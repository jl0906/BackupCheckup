"""Central problem metadata and state evaluation for BackupCheckup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .const import (
    RECOMMENDATION_ADD_STORAGE_LOCATION,
    RECOMMENDATION_CHECK_BACKUP_CONTENTS,
    RECOMMENDATION_CHECK_BACKUP_SIZE,
    RECOMMENDATION_CHECK_BACKUP_SYSTEM,
    RECOMMENDATION_CHECK_SCHEDULE,
    RECOMMENDATION_CHECK_STORAGE,
    RECOMMENDATION_CREATE_BACKUP,
    RECOMMENDATION_NONE,
    RECOMMENDATION_REPLACE_BACKUP,
    STATUS_AUTOMATIC_BACKUP_FAILED,
    STATUS_AUTOMATIC_BACKUP_OVERDUE,
    STATUS_BACKUP_CHECKSUM_CHANGED,
    STATUS_BACKUP_INCOMPLETE,
    STATUS_BACKUP_INTEGRITY_FAILED,
    STATUS_BACKUP_INTEGRITY_WARNING,
    STATUS_BACKUP_NOT_REDUNDANT,
    STATUS_BACKUP_SIZE_SUSPICIOUS,
    STATUS_BACKUP_STALE,
    STATUS_MANAGER_UNAVAILABLE,
    STATUS_NO_BACKUPS,
    STATUS_OK,
    STATUS_SCHEDULE_MISSING,
    STATUS_SCHEDULE_OVERDUE,
    STATUS_STORAGE_ERROR,
)


@dataclass(frozen=True, slots=True)
class ProblemDefinition:
    """Describe one problem consistently across status, score, and guidance."""

    key: str
    status: str
    recommendation: str
    deduction: int
    priority: int


PROBLEM_DEFINITIONS: tuple[ProblemDefinition, ...] = (
    ProblemDefinition(
        "backup_integrity_failed",
        STATUS_BACKUP_INTEGRITY_FAILED,
        RECOMMENDATION_REPLACE_BACKUP,
        60,
        10,
    ),
    ProblemDefinition(
        "backup_checksum_changed",
        STATUS_BACKUP_CHECKSUM_CHANGED,
        RECOMMENDATION_CHECK_STORAGE,
        40,
        20,
    ),
    ProblemDefinition(
        "backup_integrity_warning",
        STATUS_BACKUP_INTEGRITY_WARNING,
        RECOMMENDATION_CHECK_BACKUP_CONTENTS,
        11,
        30,
    ),
    ProblemDefinition(
        "no_backup",
        STATUS_NO_BACKUPS,
        RECOMMENDATION_CREATE_BACKUP,
        100,
        40,
    ),
    ProblemDefinition(
        "manager_unavailable",
        STATUS_MANAGER_UNAVAILABLE,
        RECOMMENDATION_CHECK_BACKUP_SYSTEM,
        50,
        50,
    ),
    ProblemDefinition(
        "storage_error",
        STATUS_STORAGE_ERROR,
        RECOMMENDATION_CHECK_STORAGE,
        20,
        60,
    ),
    # A required copy that is absent is a storage fault, not an OK state. Keeping
    # the existing storage status avoids introducing a new translated enum state.
    ProblemDefinition(
        "required_location_missing",
        STATUS_STORAGE_ERROR,
        RECOMMENDATION_CHECK_STORAGE,
        10,
        65,
    ),
    ProblemDefinition(
        "latest_backup_incomplete",
        STATUS_BACKUP_INCOMPLETE,
        RECOMMENDATION_CHECK_BACKUP_CONTENTS,
        25,
        70,
    ),
    ProblemDefinition(
        "automatic_backup_failed",
        STATUS_AUTOMATIC_BACKUP_FAILED,
        RECOMMENDATION_CHECK_SCHEDULE,
        20,
        80,
    ),
    ProblemDefinition(
        "automatic_backup_overdue",
        STATUS_AUTOMATIC_BACKUP_OVERDUE,
        RECOMMENDATION_CHECK_SCHEDULE,
        15,
        90,
    ),
    ProblemDefinition(
        "backup_stale",
        STATUS_BACKUP_STALE,
        RECOMMENDATION_CREATE_BACKUP,
        25,
        100,
    ),
    ProblemDefinition(
        "backup_not_redundant",
        STATUS_BACKUP_NOT_REDUNDANT,
        RECOMMENDATION_ADD_STORAGE_LOCATION,
        15,
        110,
    ),
    ProblemDefinition(
        "backup_size_suspicious",
        STATUS_BACKUP_SIZE_SUSPICIOUS,
        RECOMMENDATION_CHECK_BACKUP_SIZE,
        15,
        120,
    ),
    ProblemDefinition(
        "automatic_schedule_missing",
        STATUS_SCHEDULE_MISSING,
        RECOMMENDATION_CHECK_SCHEDULE,
        10,
        130,
    ),
    ProblemDefinition(
        "automatic_schedule_overdue",
        STATUS_SCHEDULE_OVERDUE,
        RECOMMENDATION_CHECK_SCHEDULE,
        10,
        140,
    ),
)

PROBLEM_BY_KEY = {definition.key: definition for definition in PROBLEM_DEFINITIONS}
CURRENT_PROBLEM_DEDUCTIONS = {
    definition.key: definition.deduction for definition in PROBLEM_DEFINITIONS
}


@dataclass(frozen=True, slots=True)
class ProblemState:
    """Evaluated active problem state."""

    active: tuple[str, ...]
    status: str
    recommendation: str


def evaluate_problem_state(flags: Mapping[str, bool]) -> ProblemState:
    """Return one consistent active list, status, and recommendation."""
    active = tuple(
        definition.key
        for definition in PROBLEM_DEFINITIONS
        if flags.get(definition.key, False)
    )
    if not active:
        return ProblemState((), STATUS_OK, RECOMMENDATION_NONE)
    primary = min(
        (PROBLEM_BY_KEY[key] for key in active),
        key=lambda definition: definition.priority,
    )
    return ProblemState(active, primary.status, primary.recommendation)
