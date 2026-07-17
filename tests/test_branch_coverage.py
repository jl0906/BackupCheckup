"""Focused branch tests for pure BackupCheckup helpers."""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.backup_checkup import notification_selection, security
from custom_components.backup_checkup.age import precise_age_days
from custom_components.backup_checkup.analytics import (
    HEALTH_RATING_CRITICAL,
    HEALTH_RATING_EXCELLENT,
    HEALTH_RATING_GOOD,
    HEALTH_RATING_WARNING,
    SIZE_TREND_DECREASING,
    SIZE_TREND_INCREASING,
    SIZE_TREND_STABLE,
    calculate_health_score,
    calculate_inventory_analytics,
)
from custom_components.backup_checkup.classification import classify_backup_purpose
from custom_components.backup_checkup.configuration import (
    _bounded_int,
    _enum,
    _strict_bool,
    normalize_configuration,
)
from custom_components.backup_checkup.const import (
    BACKUP_PURPOSE_AUTOMATIC,
    BACKUP_PURPOSE_MANUAL,
    CONF_ENTITY_MODE,
    CONF_MAX_AGE_DAYS,
    ENTITY_MODE_STANDARD,
)
from custom_components.backup_checkup.models import (
    BackupAgentRecord,
    BackupAgentSummary,
    BackupCheckupData,
    BackupIntegrityResult,
    BackupRecord,
)
from custom_components.backup_checkup.security import (
    VerificationBudget,
    VerificationLimitError,
)
from custom_components.backup_checkup.storage_cleanup import (
    cleanup_entry_store_files,
    cleanup_orphaned_store_files,
)
from custom_components.backup_checkup.task_control import (
    release_current_task_reference,
)


def _record(
    *,
    date: datetime,
    size: int | None,
    automatic: bool = True,
    scope: str = "scope",
) -> BackupRecord:
    return BackupRecord(
        backup_id=f"{date.isoformat()}-{size}-{automatic}",
        backup_reference="reference",
        name="backup",
        date=date,
        automatic=automatic,
        purpose=BACKUP_PURPOSE_AUTOMATIC if automatic else BACKUP_PURPOSE_MANUAL,
        included_addons=(),
        included_folders=(),
        scope_fingerprint=scope,
        agents=(),
        agent_copies=(),
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=size,
        incomplete=False,
    )


@pytest.mark.parametrize(
    ("sizes", "expected_trend"),
    [
        ((160, 150, 100, 90), SIZE_TREND_INCREASING),
        ((90, 100, 150, 160), SIZE_TREND_DECREASING),
        ((101, 99, 100, 100), SIZE_TREND_STABLE),
    ],
)
def test_inventory_trend_branches(sizes: tuple[int, ...], expected_trend: str) -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    records = tuple(
        _record(date=now - timedelta(days=index), size=size)
        for index, size in enumerate(sizes)
    )

    result = calculate_inventory_analytics(records, now=now, window_days=30)

    assert result.size_trend == expected_trend
    assert result.size_trend_percent is not None
    assert result.longest_backup_gap_days == 1.0
    assert result.analyzed_backup_count == 4


def test_inventory_analytics_handles_unknown_sizes_and_single_record() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    result = calculate_inventory_analytics(
        (_record(date=now, size=None, automatic=False),),
        now=now,
        window_days=30,
    )

    assert result.average_backup_size is None
    assert result.longest_backup_gap_days is None
    assert result.analyzed_backup_origin == "manual"


@pytest.mark.parametrize(
    ("success_rate", "resolved", "failures", "expected_key", "expected_value"),
    [
        (59.9, 3, 0, "low_automatic_success_rate", 20),
        (79.9, 3, 0, "reduced_automatic_success_rate", 12),
        (94.9, 3, 0, "imperfect_automatic_success_rate", 5),
        (100.0, 3, 4, "consecutive_automatic_failures", 15),
    ],
)
def test_health_score_history_deductions(
    success_rate: float,
    resolved: int,
    failures: int,
    expected_key: str,
    expected_value: int,
) -> None:
    result = calculate_health_score(
        {},
        automatic_success_rate=success_rate,
        consecutive_automatic_failures=failures,
        resolved_attempts=resolved,
    )

    assert result.deductions[expected_key] == expected_value


@pytest.mark.parametrize(
    ("flags", "expected_rating"),
    [
        ({}, HEALTH_RATING_EXCELLENT),
        ({"backup_integrity_warning": True}, HEALTH_RATING_GOOD),
        ({"backup_stale": True, "storage_error": True}, HEALTH_RATING_WARNING),
        ({"manager_unavailable": True, "backup_stale": True}, HEALTH_RATING_CRITICAL),
    ],
)
def test_health_score_rating_boundaries(
    flags: dict[str, bool], expected_rating: str
) -> None:
    result = calculate_health_score(
        flags,
        automatic_success_rate=None,
        consecutive_automatic_failures=0,
        resolved_attempts=0,
    )
    assert result.rating == expected_rating


@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [
        (True, False, True),
        (0, True, False),
        (1, False, True),
        (" YES ", False, True),
        ("off", True, False),
        ("maybe", True, True),
        (object(), False, False),
    ],
)
def test_strict_bool_all_legacy_representations(
    value: object, default: bool, expected: bool
) -> None:
    assert _strict_bool(value, default) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, 5),
        ("7", 7),
        ("bad", 5),
        (999, 5),
        (None, 5),
    ],
)
def test_bounded_integer_paths(value: object, expected: int) -> None:
    assert _bounded_int(value, 5, 1, 10) == expected


def test_enum_and_configuration_ignore_invalid_sources() -> None:
    assert _enum("expert", "standard", ("standard", "expert")) == "expert"
    assert _enum("future", "standard", ("standard", "expert")) == "standard"

    normalized = normalize_configuration(
        None,
        {CONF_MAX_AGE_DAYS: "3", "removed_legacy_key": "ignored"},
        object(),  # type: ignore[arg-type]
        {CONF_ENTITY_MODE: ENTITY_MODE_STANDARD},
    )
    assert normalized[CONF_MAX_AGE_DAYS] == 3
    assert normalized[CONF_ENTITY_MODE] == ENTITY_MODE_STANDARD
    assert "removed_legacy_key" not in normalized


def test_classification_handles_non_mapping_and_empty_marker() -> None:
    assert (
        classify_backup_purpose(automatic=True, extra_metadata=None)
        == BACKUP_PURPOSE_AUTOMATIC
    )
    assert (
        classify_backup_purpose(
            automatic=False,
            extra_metadata={"supervisor.addon_update": ""},
        )
        == BACKUP_PURPOSE_MANUAL
    )


def test_precise_age_none_branch() -> None:
    assert precise_age_days(datetime.now(UTC), None) is None


def test_notification_normalization_and_disabled_selection(monkeypatch) -> None:
    assert notification_selection.normalize_notification_targets(123) == []

    disabled = SimpleNamespace(
        entity_id="notify.mobile_app_disabled",
        platform="mobile_app",
        disabled_by="user",
        name=None,
        original_name="Disabled phone",
    )
    invalid_id = SimpleNamespace(
        entity_id=123,
        platform="mobile_app",
        disabled_by=None,
        name="Invalid",
        original_name="Invalid",
    )
    registry = SimpleNamespace(entities={"disabled": disabled, "invalid": invalid_id})
    monkeypatch.setattr(notification_selection.er, "async_get", lambda _hass: registry)
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda _entity_id: None))

    assert notification_selection.mobile_notification_options(hass) == []
    assert notification_selection.mobile_notification_options(
        hass, ["notify.mobile_app_disabled"]
    ) == [
        {
            "value": "notify.mobile_app_disabled",
            "label": "Disabled phone",
        }
    ]


def test_security_budget_deadline_expected_size_and_capacities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    budget = VerificationBudget(
        deadline=time.monotonic() + 30,
        max_download_bytes=10,
        max_expanded_bytes=20,
        max_metadata_bytes=5,
        free_space_reserve_bytes=10,
    )
    assert budget.remaining_seconds() > 0
    budget.validate_expected_download(None)
    budget.validate_expected_download(10)
    with pytest.raises(VerificationLimitError, match="download_size_limit"):
        budget.validate_expected_download(11)

    budget.ensure_expanded_capacity(20)
    with pytest.raises(VerificationLimitError, match="expanded_size_limit"):
        budget.ensure_expanded_capacity(-1)
    with pytest.raises(VerificationLimitError, match="expanded_size_limit"):
        budget.ensure_expanded_capacity(21)

    budget.check_metadata_size(5)
    with pytest.raises(VerificationLimitError, match="metadata_size_limit"):
        budget.check_metadata_size(-1)
    with pytest.raises(VerificationLimitError, match="metadata_size_limit"):
        budget.check_metadata_size(6)

    monkeypatch.setattr(
        security.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=10, free=90),
    )
    budget.check_free_space(tmp_path, required_bytes=0)
    with pytest.raises(VerificationLimitError, match="insufficient_free_space"):
        budget.check_free_space(tmp_path, required_bytes=85)

    expired = VerificationBudget(
        deadline=time.monotonic() - 1,
        max_download_bytes=1,
        max_expanded_bytes=1,
    )
    with pytest.raises(VerificationLimitError, match="verification_timeout"):
        expired.remaining_seconds()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), "timeout"),
        (PermissionError(), "permission_denied"),
        (ConnectionError(), "connection_error"),
        (FileNotFoundError(), "not_found"),
        (OSError(), "io_error"),
        (type("AuthenticationFailure", (Exception,), {})(), "authentication_error"),
        (type("CredentialProblem", (Exception,), {})(), "authentication_error"),
        (type("LoginFailure", (Exception,), {})(), "authentication_error"),
        (type("CustomTimeout", (Exception,), {})(), "timeout"),
        (type("NetworkFailure", (Exception,), {})(), "connection_error"),
        (ValueError(), "unknown_error"),
    ],
)
def test_exception_classification(error: BaseException, expected: str) -> None:
    assert security.classify_exception(error) == expected


@pytest.mark.parametrize(
    ("value", "fallback", "expected"),
    [
        (" Friendly name ", "fallback", "Friendly name"),
        ("\n\t", "fallback", "??"),
        ("   ", "fallback", "fallback"),
        (123, "fallback", "fallback"),
    ],
)
def test_safe_display_name_paths(value: object, fallback: str, expected: str) -> None:
    assert security.safe_display_name(value, fallback=fallback) == expected


def test_anonymous_agent_reference_is_stable() -> None:
    first = security.anonymous_agent_reference("entry", "agent")
    assert first == security.anonymous_agent_reference("entry", "agent")
    assert first != security.anonymous_agent_reference("other", "agent")
    assert len(first) == 10


def test_private_directory_chmod_failure_is_cleaned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    created = tmp_path / "backup_checkup_failure"
    created.mkdir()
    original_rmtree = security.shutil.rmtree
    removed: list[Path] = []

    monkeypatch.setattr(security.tempfile, "mkdtemp", lambda **_kwargs: str(created))
    monkeypatch.setattr(
        Path, "chmod", lambda _self, _mode: (_ for _ in ()).throw(OSError())
    )

    def _rmtree(path: Path, *, ignore_errors: bool = False) -> None:
        removed.append(Path(path))
        original_rmtree(path, ignore_errors=ignore_errors)

    monkeypatch.setattr(security.shutil, "rmtree", _rmtree)

    with pytest.raises(OSError):
        security.create_private_temp_directory()
    assert removed == [created]
    assert not created.exists()


def test_private_writer_fdopen_failure_removes_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "private.bin"
    real_fdopen = os.fdopen

    def _raise_fdopen(_descriptor: int, _mode: str):
        raise RuntimeError("fdopen failed")

    monkeypatch.setattr(security.os, "fdopen", _raise_fdopen)
    with pytest.raises(RuntimeError, match="fdopen failed"):
        security.open_private_binary_writer(path)
    monkeypatch.setattr(security.os, "fdopen", real_fdopen)
    assert not path.exists()


def test_cleanup_temp_directory_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    assert security.cleanup_temp_directory(link) is False

    missing = tmp_path / "missing"
    assert security.cleanup_temp_directory(missing) is True

    stubborn = tmp_path / "stubborn"
    stubborn.mkdir()
    monkeypatch.setattr(
        security.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("busy")),
    )
    assert security.cleanup_temp_directory(stubborn) is False


def test_stale_cleanup_reports_root_and_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    broken_root = tmp_path / "broken-root"
    broken_root.mkdir()
    original_iterdir = Path.iterdir

    def _iterdir(self: Path):
        if self == broken_root:
            raise OSError("unreadable")
        return original_iterdir(self)

    monkeypatch.setattr(security.tempfile, "gettempdir", lambda: str(broken_root))
    monkeypatch.setattr(Path, "iterdir", _iterdir)
    assert security.cleanup_stale_temp_directories().failures == 1
    monkeypatch.setattr(Path, "iterdir", original_iterdir)

    stale = tmp_path / "backup_checkup_stale"
    stale.mkdir()
    old = time.time() - 48 * 3600
    os.utime(stale, (old, old))
    monkeypatch.setattr(security.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(security, "cleanup_temp_directory", lambda _path: False)

    result = security.cleanup_stale_temp_directories()
    assert result.failures == 1
    assert result.remaining == 1


def test_store_cleanup_non_directory_and_file_kinds(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert cleanup_orphaned_store_files(missing, set()).removed == 0

    directory = tmp_path / "storage"
    directory.mkdir()
    orphan_dir = directory / "backup_checkup.ORPHAN.history"
    orphan_dir.mkdir()
    orphan_link = directory / "backup_checkup.ORPHAN.integrity"
    target = directory / "target"
    target.write_text("target")
    orphan_link.symlink_to(target)

    result = cleanup_orphaned_store_files(directory, set())
    assert result.removed == 0
    assert result.failed == 0
    assert orphan_dir.exists()
    assert orphan_link.is_symlink()


def test_entry_cleanup_missing_files_and_unlink_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert cleanup_entry_store_files(tmp_path, "ENTRY").removed == 0

    path = tmp_path / "backup_checkup.ENTRY.history"
    path.write_text("data")
    original_unlink = Path.unlink

    def _unlink(self: Path, *args, **kwargs):
        if self == path:
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _unlink)
    result = cleanup_entry_store_files(tmp_path, "ENTRY")
    assert result.failed == 1
    assert path.exists()


def test_task_reference_none_and_missing_event_loop(monkeypatch) -> None:
    assert release_current_task_reference(None) is None
    tracked = object()
    monkeypatch.setattr(
        asyncio,
        "current_task",
        lambda: (_ for _ in ()).throw(RuntimeError("no loop")),
    )
    assert release_current_task_reference(tracked) is tracked  # type: ignore[arg-type]


def test_model_privacy_and_summary_branches() -> None:
    copy = BackupAgentRecord("raw-agent", "safe-agent", 123, True)
    assert "agent_id" not in copy.as_dict()
    assert copy.as_dict(expose_metadata=True)["agent_id"] == "raw-agent"

    when = datetime(2026, 7, 17, tzinfo=UTC)
    summary = BackupAgentSummary(
        agent_id="raw-agent",
        agent_reference="safe-agent",
        storage_name="NAS",
        backup_count=2,
        inventory_backup_count=3,
        ignored_update_backup_count=1,
        latest_backup=when,
        latest_backup_age_days=1.9,
        latest_backup_size=123,
        stored_bytes=456,
        error=None,
        stale=False,
        problem=False,
    )
    public = summary.as_dict()
    assert public["latest_backup"] == when.isoformat()
    assert public["latest_backup_age_days"] == 1
    assert "agent_id" not in public
    assert summary.as_dict(expose_metadata=True)["agent_id"] == "raw-agent"

    empty_summary = BackupAgentSummary(
        agent_id="raw-agent",
        agent_reference="safe-agent",
        storage_name="NAS",
        backup_count=0,
        inventory_backup_count=0,
        ignored_update_backup_count=0,
        latest_backup=None,
        latest_backup_age_days=None,
        latest_backup_size=None,
        stored_bytes=None,
        error="unavailable",
        stale=True,
        problem=True,
    )
    assert empty_summary.as_dict()["latest_backup"] is None


def test_integrity_result_initial_serialization_and_validation() -> None:
    initial = BackupIntegrityResult.not_checked()
    serialized = initial.as_dict()
    assert serialized["checked_at"] is None
    assert serialized["backup_date"] is None
    assert serialized["warnings"] == []

    invalid_cases = [
        [],
        {"database_status": "future"},
        {"backup_id": 123},
        {"archive_count": True},
        {"file_count": -1},
        {"verified_size": "large"},
        {"duration_seconds": True},
        {"duration_seconds": -1},
        {"protected": "yes"},
        {"checksum_changed": 1},
        {"warnings": ["ok", 1]},
        {"warnings": ["x"] * 1001},
    ]
    for case in invalid_cases:
        assert not BackupIntegrityResult.storage_dict_is_valid(case)  # type: ignore[arg-type]
    assert BackupIntegrityResult.storage_dict_is_valid({"warnings": None})


def test_integrity_result_defensive_deserialization() -> None:
    parsed = BackupIntegrityResult.from_dict(
        {
            "status": "future",
            "database_status": "future",
            "checked_at": 123,
            "backup_id": "",
            "backup_reference": "x" * 100,
            "archive_count": True,
            "file_count": float("inf"),
            "verified_size": -1,
            "duration_seconds": 999999999,
            "protected": "yes",
            "warnings": "not-a-list",
            "error_code": "e" * 200,
            "checksum_changed": 1,
        }
    )
    assert parsed.checked_at is None
    assert parsed.backup_id is None
    assert parsed.backup_reference == "x" * 64
    assert parsed.archive_count == 0
    assert parsed.file_count == 0
    assert parsed.verified_size is None
    assert parsed.duration_seconds is None
    assert parsed.protected is None
    assert parsed.warnings == ()
    assert parsed.error_code == "e" * 128
    assert parsed.checksum_changed is False

    valid = BackupIntegrityResult.from_dict(
        {
            "status": "valid",
            "database_status": "passed",
            "checked_at": "2026-07-17T12:00:00+00:00",
            "backup_date": "2026-07-17T11:00:00+00:00",
            "archive_count": 2.9,
            "file_count": 3,
            "verified_size": 4.9,
            "duration_seconds": 1.5,
            "protected": True,
            "warnings": ["w" * 200, 2],
            "checksum_changed": True,
        }
    )
    assert valid.status == "valid"
    assert valid.database_status == "passed"
    assert valid.archive_count == 0
    assert valid.verified_size is None
    assert valid.warnings == ("w" * 128,)
    assert valid.checksum_changed is True


def test_latest_monitored_record_property() -> None:
    descriptor = BackupCheckupData.latest_monitored_backup_record
    now = datetime(2026, 7, 17, tzinfo=UTC)
    record = _record(date=now, size=1)
    assert descriptor.fget(SimpleNamespace(monitored_backups=())) is None
    assert descriptor.fget(SimpleNamespace(monitored_backups=(record,))) is record


def test_stale_cleanup_ignores_unsafe_candidate_types_and_owners(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prefixed_file = tmp_path / "backup_checkup_regular_file"
    prefixed_file.write_text("not a directory")
    wrong_owner_dir = tmp_path / "backup_checkup_wrong_owner"
    wrong_owner_dir.mkdir()
    old = time.time() - 48 * 3600
    os.utime(wrong_owner_dir, (old, old))

    monkeypatch.setattr(security.tempfile, "gettempdir", lambda: str(tmp_path))
    current_uid = os.getuid() if hasattr(os, "getuid") else 0
    monkeypatch.setattr(security.os, "getuid", lambda: current_uid + 1)

    result = security.cleanup_stale_temp_directories()
    assert result.failures == 0
    assert prefixed_file.exists()
    assert wrong_owner_dir.exists()


def test_stale_cleanup_rejects_candidate_outside_resolved_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    old = time.time() - 48 * 3600
    current_uid = os.getuid() if hasattr(os, "getuid") else 0
    fake_stat = SimpleNamespace(
        st_mode=0o040700,
        st_uid=current_uid,
        st_mtime=old,
    )
    candidate = SimpleNamespace(
        name="backup_checkup_outside",
        lstat=lambda: fake_stat,
        parent=SimpleNamespace(resolve=lambda: outside),
    )
    original_iterdir = Path.iterdir

    def _iterdir(self: Path):
        if self == root:
            return iter((candidate,))
        return original_iterdir(self)

    monkeypatch.setattr(security.tempfile, "gettempdir", lambda: str(root))
    monkeypatch.setattr(Path, "iterdir", _iterdir)

    result = security.cleanup_stale_temp_directories()
    assert result.failures == 0
    assert result.remaining == 0
