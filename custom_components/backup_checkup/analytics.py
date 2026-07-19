"""Pure analytics helpers for BackupCheckup."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from statistics import mean, median

from .models import BackupRecord
from .problem_state import CURRENT_PROBLEM_DEDUCTIONS

HEALTH_RATING_EXCELLENT = "excellent"
HEALTH_RATING_GOOD = "good"
HEALTH_RATING_WARNING = "warning"
HEALTH_RATING_CRITICAL = "critical"

SIZE_TREND_INCREASING = "increasing"
SIZE_TREND_STABLE = "stable"
SIZE_TREND_DECREASING = "decreasing"
SIZE_TREND_INSUFFICIENT_DATA = "insufficient_data"

_MIN_TREND_RECORDS = 4
_MAX_TREND_RECORDS = 6
_EXCELLENT_SCORE_MIN = 90
_GOOD_SCORE_MIN = 75
_WARNING_SCORE_MIN = 50
_LOW_SUCCESS_RATE = 60.0
_REDUCED_SUCCESS_RATE = 80.0
_IMPERFECT_SUCCESS_RATE = 95.0


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
    component_deductions: dict[str, int]
    raw_deductions: dict[str, int]
    suppressed_deductions: tuple[str, ...]


def _window_records(
    records: Iterable[BackupRecord], *, now: datetime, window_days: int
) -> tuple[BackupRecord, ...]:
    """Return newest-first records inside the selected window and not in future."""
    window_start = now - timedelta(days=window_days)
    return tuple(
        sorted(
            (record for record in records if window_start <= record.date <= now),
            key=lambda record: record.date,
            reverse=True,
        )
    )


def _size_analysis_records(
    records: tuple[BackupRecord, ...], newest: BackupRecord
) -> tuple[BackupRecord, ...]:
    """Return records comparable to the newest scope and origin."""
    return tuple(
        record
        for record in records
        if record.scope_fingerprint == newest.scope_fingerprint
        and record.automatic == newest.automatic
    )


def _average_known_size(records: Iterable[BackupRecord]) -> int | None:
    """Return the rounded mean of known non-negative sizes."""
    sizes = [record.size for record in records if record.size is not None]
    return round(mean(sizes)) if sizes else None


def _longest_gap_days(records: Iterable[BackupRecord]) -> float | None:
    """Return the longest chronological gap in days."""
    chronological = sorted(record.date for record in records)
    gaps = [
        (newer - older).total_seconds() / 86400
        for older, newer in pairwise(chronological)
    ]
    return round(max(gaps), 2) if gaps else None


def _size_trend(
    records: tuple[BackupRecord, ...], *, stable_threshold_percent: float
) -> tuple[str, float | None]:
    """Return a robust recent-versus-older median size trend."""
    trend_records = [
        record for record in records if record.size is not None and record.size > 0
    ][:_MAX_TREND_RECORDS]
    if len(trend_records) < _MIN_TREND_RECORDS:
        return SIZE_TREND_INSUFFICIENT_DATA, None

    split = len(trend_records) // 2
    recent_baseline = median(record.size for record in trend_records[:split])
    older_baseline = median(record.size for record in trend_records[split:])
    percent = round(((recent_baseline - older_baseline) / older_baseline) * 100, 1)
    if percent > stable_threshold_percent:
        return SIZE_TREND_INCREASING, percent
    if percent < -stable_threshold_percent:
        return SIZE_TREND_DECREASING, percent
    return SIZE_TREND_STABLE, percent


def calculate_inventory_analytics(
    records: tuple[BackupRecord, ...],
    *,
    now: datetime,
    window_days: int,
    stable_threshold_percent: float = 5.0,
) -> InventoryAnalytics:
    """Calculate size and interval analytics strictly inside the selected window."""
    selected = _window_records(records, now=now, window_days=window_days)
    if not selected:
        return InventoryAnalytics(
            average_backup_size=None,
            longest_backup_gap_days=None,
            size_trend=SIZE_TREND_INSUFFICIENT_DATA,
            size_trend_percent=None,
            analyzed_backup_count=0,
            analyzed_backup_scope=None,
            analyzed_backup_origin=None,
        )

    newest = selected[0]
    comparable = _size_analysis_records(selected, newest)
    trend, trend_percent = _size_trend(
        comparable,
        stable_threshold_percent=stable_threshold_percent,
    )
    return InventoryAnalytics(
        average_backup_size=_average_known_size(comparable),
        longest_backup_gap_days=_longest_gap_days(selected),
        size_trend=trend,
        size_trend_percent=trend_percent,
        analyzed_backup_count=len(comparable),
        analyzed_backup_scope=newest.scope_fingerprint,
        analyzed_backup_origin="automatic" if newest.automatic else "manual",
    )


def _valid_success_rate(value: float | None) -> float | None:
    """Return a finite percentage in the supported 0-100 range."""
    if value is None or isinstance(value, bool) or not isinstance(value, int | float):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) and 0.0 <= parsed <= 100.0 else None


def _normalized_history_metrics(
    *,
    automatic_success_rate: float | None,
    consecutive_automatic_failures: int,
    resolved_attempts: int,
) -> tuple[float | None, int, int]:
    """Return internally consistent automatic-backup history metrics."""
    resolved = (
        max(0, resolved_attempts)
        if isinstance(resolved_attempts, int)
        and not isinstance(resolved_attempts, bool)
        else 0
    )
    failures = (
        max(0, consecutive_automatic_failures)
        if isinstance(consecutive_automatic_failures, int)
        and not isinstance(consecutive_automatic_failures, bool)
        else 0
    )
    failures = min(failures, resolved) if resolved else 0
    return _valid_success_rate(automatic_success_rate), failures, resolved


def _history_deductions(
    *,
    automatic_success_rate: float | None,
    consecutive_automatic_failures: int,
    resolved_attempts: int,
) -> dict[str, int]:
    """Return deductions from normalized automatic-backup history metrics."""
    success_rate, failures, resolved = _normalized_history_metrics(
        automatic_success_rate=automatic_success_rate,
        consecutive_automatic_failures=consecutive_automatic_failures,
        resolved_attempts=resolved_attempts,
    )
    deductions: dict[str, int] = {}
    if resolved >= 3 and success_rate is not None:
        if success_rate < _LOW_SUCCESS_RATE:
            deductions["low_automatic_success_rate"] = 20
        elif success_rate < _REDUCED_SUCCESS_RATE:
            deductions["reduced_automatic_success_rate"] = 12
        elif success_rate < _IMPERFECT_SUCCESS_RATE:
            deductions["imperfect_automatic_success_rate"] = 5

    if failures:
        deductions["consecutive_automatic_failures"] = min(15, failures * 5)
    return deductions


def _stale_deduction(
    *, latest_backup_age_days: float | None, max_age_days: int | None
) -> int:
    """Scale stale-backup severity without trusting malformed context values."""
    if (
        latest_backup_age_days is None
        or isinstance(latest_backup_age_days, bool)
        or not isinstance(latest_backup_age_days, int | float)
        or not math.isfinite(float(latest_backup_age_days))
        or max_age_days is None
        or isinstance(max_age_days, bool)
        or not isinstance(max_age_days, int)
        or max_age_days <= 0
    ):
        return CURRENT_PROBLEM_DEDUCTIONS["backup_stale"]
    ratio = max(0.0, float(latest_backup_age_days)) / max_age_days
    if ratio >= 3.0:
        return 35
    if ratio >= 1.5:
        return 25
    return 20


def _redundancy_deduction(
    *, latest_backup_locations: int | None, minimum_redundant_locations: int | None
) -> int:
    """Scale redundancy severity by the number of missing locations."""
    values = (latest_backup_locations, minimum_redundant_locations)
    if any(
        value is None or isinstance(value, bool) or not isinstance(value, int)
        for value in values
    ):
        return CURRENT_PROBLEM_DEDUCTIONS["backup_not_redundant"]
    missing = max(0, minimum_redundant_locations - latest_backup_locations)
    return min(25, 10 + missing * 5)


_HEALTH_DEDUCTION_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("availability", ("no_backup", "manager_unavailable")),
    (
        "integrity",
        (
            "backup_integrity_failed",
            "backup_checksum_changed",
            "backup_integrity_warning",
        ),
    ),
    ("backup_quality", ("latest_backup_incomplete", "backup_size_suspicious")),
    ("freshness", ("backup_stale", "automatic_backup_overdue")),
    (
        "storage",
        ("storage_error", "required_location_missing", "backup_not_redundant"),
    ),
    (
        "automation",
        (
            "automatic_backup_failed",
            "automatic_schedule_missing",
            "automatic_schedule_overdue",
            "low_automatic_success_rate",
            "reduced_automatic_success_rate",
            "imperfect_automatic_success_rate",
            "consecutive_automatic_failures",
        ),
    ),
)


def _grouped_deductions(
    raw_deductions: Mapping[str, int],
) -> tuple[dict[str, int], dict[str, int], tuple[str, ...]]:
    """Apply only the strongest correlated deduction in each cause group."""
    applied: dict[str, int] = {}
    components: dict[str, int] = {}
    suppressed: list[str] = []
    grouped_keys: set[str] = set()

    for component, keys in _HEALTH_DEDUCTION_GROUPS:
        candidates = [
            (key, raw_deductions[key]) for key in keys if key in raw_deductions
        ]
        grouped_keys.update(key for key, _value in candidates)
        if not candidates:
            components[component] = 0
            continue
        selected_key, selected_value = max(candidates, key=lambda item: item[1])
        applied[selected_key] = selected_value
        components[component] = selected_value
        suppressed.extend(key for key, _value in candidates if key != selected_key)

    for key, value in raw_deductions.items():
        if key not in grouped_keys:
            applied[key] = value
    return applied, components, tuple(suppressed)


def _rating_for_score(score: int) -> str:
    """Return the localized enum key for one normalized score."""
    if score >= _EXCELLENT_SCORE_MIN:
        return HEALTH_RATING_EXCELLENT
    if score >= _GOOD_SCORE_MIN:
        return HEALTH_RATING_GOOD
    if score >= _WARNING_SCORE_MIN:
        return HEALTH_RATING_WARNING
    return HEALTH_RATING_CRITICAL


def calculate_health_score(
    flags: Mapping[str, bool],
    *,
    automatic_success_rate: float | None,
    consecutive_automatic_failures: int,
    resolved_attempts: int,
    latest_backup_age_days: float | None = None,
    max_age_days: int | None = None,
    latest_backup_locations: int | None = None,
    minimum_redundant_locations: int | None = None,
) -> HealthScore:
    """Calculate a correlation-aware, transparent 0-100 health score."""
    raw_deductions = {
        key: deduction
        for key, deduction in CURRENT_PROBLEM_DEDUCTIONS.items()
        if flags.get(key, False) is True
    }
    if "backup_stale" in raw_deductions:
        raw_deductions["backup_stale"] = _stale_deduction(
            latest_backup_age_days=latest_backup_age_days, max_age_days=max_age_days
        )
    if "backup_not_redundant" in raw_deductions:
        raw_deductions["backup_not_redundant"] = _redundancy_deduction(
            latest_backup_locations=latest_backup_locations,
            minimum_redundant_locations=minimum_redundant_locations,
        )
    raw_deductions.update(
        _history_deductions(
            automatic_success_rate=automatic_success_rate,
            consecutive_automatic_failures=consecutive_automatic_failures,
            resolved_attempts=resolved_attempts,
        )
    )

    if flags.get("no_backup", False) is True:
        suppressed = tuple(key for key in raw_deductions if key != "no_backup")
        return HealthScore(
            score=0,
            rating=HEALTH_RATING_CRITICAL,
            deductions={"no_backup": CURRENT_PROBLEM_DEDUCTIONS["no_backup"]},
            component_deductions={"availability": 100},
            raw_deductions=raw_deductions,
            suppressed_deductions=suppressed,
        )

    deductions, components, suppressed = _grouped_deductions(raw_deductions)
    score = max(0, 100 - sum(deductions.values()))
    return HealthScore(
        score=score,
        rating=_rating_for_score(score),
        deductions=deductions,
        component_deductions=components,
        raw_deductions=raw_deductions,
        suppressed_deductions=suppressed,
    )
