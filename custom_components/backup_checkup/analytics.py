"""Pure analytics helpers for BackupCheckup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from statistics import mean, median

from .models import BackupRecord

HEALTH_RATING_EXCELLENT = "excellent"
HEALTH_RATING_GOOD = "good"
HEALTH_RATING_WARNING = "warning"
HEALTH_RATING_CRITICAL = "critical"

SIZE_TREND_INCREASING = "increasing"
SIZE_TREND_STABLE = "stable"
SIZE_TREND_DECREASING = "decreasing"
SIZE_TREND_INSUFFICIENT_DATA = "insufficient_data"

CURRENT_PROBLEM_DEDUCTIONS: dict[str, int] = {
    "no_backup": 100,
    "backup_integrity_failed": 60,
    "backup_integrity_warning": 11,
    "backup_checksum_changed": 40,
    "manager_unavailable": 50,
    "backup_stale": 25,
    "automatic_backup_overdue": 15,
    "automatic_backup_failed": 20,
    "automatic_schedule_missing": 10,
    "automatic_schedule_overdue": 10,
    "storage_error": 20,
    "backup_size_suspicious": 15,
    "latest_backup_incomplete": 25,
    "backup_not_redundant": 15,
    "required_location_missing": 10,
}


@dataclass(frozen=True, slots=True)
class InventoryAnalytics:
    """Analytics calculated from the currently retained backup inventory."""

    average_backup_size: int | None
    longest_backup_gap_days: float | None
    size_trend: str
    size_trend_percent: float | None
    analyzed_backup_count: int
    analyzed_backup_scope: str | None
    analyzed_backup_origin: str | None


@dataclass(frozen=True, slots=True)
class HealthScore:
    """Transparent health-score result."""

    score: int
    rating: str
    deductions: dict[str, int]


def calculate_inventory_analytics(
    records: tuple[BackupRecord, ...],
    *,
    now: datetime,
    window_days: int,
    stable_threshold_percent: float = 5.0,
) -> InventoryAnalytics:
    """Calculate size and interval analytics strictly inside the selected window."""
    window_start = now - timedelta(days=window_days)
    window_records = tuple(record for record in records if record.date >= window_start)
    if not window_records:
        return InventoryAnalytics(
            average_backup_size=None,
            longest_backup_gap_days=None,
            size_trend=SIZE_TREND_INSUFFICIENT_DATA,
            size_trend_percent=None,
            analyzed_backup_count=0,
            analyzed_backup_scope=None,
            analyzed_backup_origin=None,
        )

    newest = window_records[0]
    analyzed_scope = newest.scope_fingerprint
    analyzed_automatic = newest.automatic
    analyzed_origin = "automatic" if analyzed_automatic else "manual"
    size_analysis_records = tuple(
        record
        for record in window_records
        if record.scope_fingerprint == analyzed_scope
        and record.automatic == analyzed_automatic
    )

    known_sizes = [
        record.size for record in size_analysis_records if record.size is not None
    ]
    average_size = round(mean(known_sizes)) if known_sizes else None

    chronological = sorted(record.date for record in window_records)
    gaps = [
        (newer - older).total_seconds() / 86400
        for older, newer in pairwise(chronological)
    ]
    longest_gap = round(max(gaps), 2) if gaps else None

    trend_records = [
        record
        for record in size_analysis_records
        if record.size is not None and record.size > 0
    ][:6]

    if len(trend_records) < 4:
        trend = SIZE_TREND_INSUFFICIENT_DATA
        trend_percent = None
    else:
        split = len(trend_records) // 2
        recent_baseline = median(
            record.size for record in trend_records[:split] if record.size is not None
        )
        older_baseline = median(
            record.size for record in trend_records[split:] if record.size is not None
        )
        trend_percent = (
            round(((recent_baseline - older_baseline) / older_baseline) * 100, 1)
            if older_baseline
            else None
        )
        if trend_percent is None:
            trend = SIZE_TREND_INSUFFICIENT_DATA
        elif trend_percent > stable_threshold_percent:
            trend = SIZE_TREND_INCREASING
        elif trend_percent < -stable_threshold_percent:
            trend = SIZE_TREND_DECREASING
        else:
            trend = SIZE_TREND_STABLE

    return InventoryAnalytics(
        average_backup_size=average_size,
        longest_backup_gap_days=longest_gap,
        size_trend=trend,
        size_trend_percent=trend_percent,
        analyzed_backup_count=len(size_analysis_records),
        analyzed_backup_scope=analyzed_scope,
        analyzed_backup_origin=analyzed_origin,
    )


def calculate_health_score(
    flags: Mapping[str, bool],
    *,
    automatic_success_rate: float | None,
    consecutive_automatic_failures: int,
    resolved_attempts: int,
) -> HealthScore:
    """Calculate a transparent 0-100 backup health score."""
    deductions = {
        key: deduction
        for key, deduction in CURRENT_PROBLEM_DEDUCTIONS.items()
        if flags.get(key, False)
    }

    if resolved_attempts >= 3 and automatic_success_rate is not None:
        if automatic_success_rate < 60:
            deductions["low_automatic_success_rate"] = 20
        elif automatic_success_rate < 80:
            deductions["reduced_automatic_success_rate"] = 12
        elif automatic_success_rate < 95:
            deductions["imperfect_automatic_success_rate"] = 5

    if consecutive_automatic_failures > 0:
        deductions["consecutive_automatic_failures"] = min(
            15, consecutive_automatic_failures * 5
        )

    score = max(0, 100 - sum(deductions.values()))
    if score >= 90:
        rating = HEALTH_RATING_EXCELLENT
    elif score >= 75:
        rating = HEALTH_RATING_GOOD
    elif score >= 50:
        rating = HEALTH_RATING_WARNING
    else:
        rating = HEALTH_RATING_CRITICAL

    return HealthScore(score=score, rating=rating, deductions=deductions)
