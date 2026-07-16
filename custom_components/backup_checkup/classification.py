"""Pure backup classification helpers for BackupCheckup."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    APP_UPDATE_METADATA_KEY,
    BACKUP_PURPOSE_APP_UPDATE,
    BACKUP_PURPOSE_AUTOMATIC,
    BACKUP_PURPOSE_MANUAL,
)
from .models import BackupRecord


def classify_backup_purpose(*, automatic: bool, extra_metadata: Any) -> str:
    """Classify regular backups and Supervisor app-update snapshots."""
    if isinstance(extra_metadata, Mapping):
        app_update = extra_metadata.get(APP_UPDATE_METADATA_KEY)
        if isinstance(app_update, str) and app_update:
            return BACKUP_PURPOSE_APP_UPDATE
    return BACKUP_PURPOSE_AUTOMATIC if automatic else BACKUP_PURPOSE_MANUAL


def monitoring_backups(
    records: tuple[BackupRecord, ...],
) -> tuple[BackupRecord, ...]:
    """Return backups that should influence health and analytics."""
    return tuple(
        record for record in records if record.purpose != BACKUP_PURPOSE_APP_UPDATE
    )


def comparable_size_backups(
    latest: BackupRecord,
    records: tuple[BackupRecord, ...],
) -> tuple[BackupRecord, ...]:
    """Return older backups with the same origin and content scope."""
    return tuple(
        record
        for record in records
        if record.backup_id != latest.backup_id
        and record.automatic == latest.automatic
        and record.scope_fingerprint == latest.scope_fingerprint
        and record.size is not None
        and record.size > 0
    )


def automatic_size_drop_is_suspicious(
    *,
    maximum_drop_percent: int,
    previous_change_percent: float | None,
    baseline_change_percent: float | None,
    comparable_backup_count: int,
) -> bool:
    """Return whether a scope-matched automatic size drop is suspicious."""
    if maximum_drop_percent <= 0 or comparable_backup_count < 2:
        return False
    effective_drop = (
        baseline_change_percent
        if baseline_change_percent is not None
        else previous_change_percent
    )
    return bool(effective_drop is not None and effective_drop <= -maximum_drop_percent)
