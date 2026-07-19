"""Regression tests for BackupCheckup 2.2.4 reliability fixes."""

from __future__ import annotations

import asyncio
import importlib
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.backup_checkup import coordinator as coordinator_module
from custom_components.backup_checkup import security
from custom_components.backup_checkup.analytics import (
    SIZE_TREND_INSUFFICIENT_DATA,
    calculate_health_score,
    calculate_inventory_analytics,
)
from custom_components.backup_checkup.backup_normalizer import BackupRecordNormalizer
from custom_components.backup_checkup.configuration import (
    BackupCheckupSettings,
    _bounded_int,
)
from custom_components.backup_checkup.const import (
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_INTERNAL_ERROR,
    STATUS_STORAGE_ERROR,
)
from custom_components.backup_checkup.coordinator import BackupCheckupCoordinator
from custom_components.backup_checkup.integrity import BackupIntegrityStore
from custom_components.backup_checkup.models import (
    BackupAgentRecord,
    BackupIntegrityResult,
    BackupRecord,
)
from custom_components.backup_checkup.security import (
    VerificationBudget,
    VerificationLimitError,
)


def _record(
    *,
    backup_id: str = "backup",
    date: datetime | None = None,
    automatic: bool = True,
    incomplete: bool = False,
    scope: str = "scope",
    size: int | None = 10_000_000,
) -> BackupRecord:
    return BackupRecord(
        backup_id=backup_id,
        backup_reference=f"ref-{backup_id}",
        name="Backup",
        date=date or datetime.now(UTC),
        automatic=automatic,
        purpose="automatic" if automatic else "manual",
        included_addons=(),
        included_folders=(),
        scope_fingerprint=scope,
        agents=("backup.local",),
        agent_copies=(BackupAgentRecord("backup.local", "storage-ref", size, False),),
        failed_agents=("backup.local",) if incomplete else (),
        failed_addons=(),
        failed_folders=(),
        database_included=True,
        homeassistant_included=True,
        size=size,
        incomplete=incomplete,
    )


def _result(*, checked_at: datetime | None = None) -> BackupIntegrityResult:
    return BackupIntegrityResult(
        status=INTEGRITY_STATUS_INTERNAL_ERROR,
        checked_at=checked_at or datetime.now(UTC),
        backup_id="backup",
        backup_reference="ref-backup",
        backup_date=datetime.now(UTC),
        agent_id=None,
        sha256=None,
        verified_size=None,
        duration_seconds=None,
        archive_count=0,
        file_count=0,
        protected=None,
        database_status=INTEGRITY_DATABASE_NOT_CHECKED,
        warnings=(),
        error_code="internal_error",
        checksum_changed=False,
    )


def test_required_location_missing_never_reports_ok() -> None:
    assert (
        BackupCheckupCoordinator._status(required_location_missing=True)
        == STATUS_STORAGE_ERROR
    )


def test_integrity_running_flag_resets_when_initial_state_publish_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.integrity_check_running = False
    coordinator._integrity_task = None
    coordinator.data = object()
    coordinator._integrity_retry_key = None
    coordinator._integrity_retry_attempts = 0
    coordinator._integrity_retry_not_before = None
    coordinator._last_manual_verification_at = None
    coordinator._backup_password_marker = None
    coordinator.database_integrity_check = False
    coordinator.max_verification_size_gb = 50
    coordinator.max_expanded_size_gb = 250
    coordinator.verification_timeout_minutes = 30
    coordinator.database_timeout_minutes = 10
    coordinator.repair_issues_enabled = True
    coordinator.async_request_refresh = lambda: asyncio.sleep(0)

    saved: list[BackupIntegrityResult] = []

    async def save(result: BackupIntegrityResult) -> None:
        saved.append(result)

    coordinator._async_save_integrity_result = save
    monkeypatch.setattr(
        coordinator_module,
        "replace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("publish")),
    )

    asyncio.run(coordinator._async_run_integrity_check(_record(), source="manual"))

    assert coordinator.integrity_check_running is False
    assert saved[-1].status == INTEGRITY_STATUS_INTERNAL_ERROR


def test_password_marker_first_observation_is_not_a_change() -> None:
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.config_entry = SimpleNamespace(entry_id="entry")
    coordinator._backup_password_marker = None
    coordinator._backup_password_marker_initialized = False
    manager = SimpleNamespace(
        config=SimpleNamespace(
            data=SimpleNamespace(create_backup=SimpleNamespace(password="secret"))
        )
    )

    assert coordinator._update_backup_password_marker(manager) is False
    assert coordinator._update_backup_password_marker(manager) is False
    manager.config.data.create_backup.password = "changed"
    assert coordinator._update_backup_password_marker(manager) is True


class _FakeStore:
    def __init__(self, data: Any = None) -> None:
        self.data = data

    async def async_load(self) -> Any:
        return self.data

    async def async_save(self, data: Any) -> None:
        self.data = data

    async def async_remove(self) -> None:
        self.data = None


def test_retry_and_manual_cooldown_state_survive_store_reload() -> None:
    first = BackupIntegrityStore(object(), "entry")
    backend = _FakeStore()
    first._store = backend
    now = datetime.now(UTC)
    asyncio.run(
        first.async_save(
            _result(checked_at=now),
            retry_key=("backup", "internal_error"),
            retry_attempts=2,
            retry_not_before=now + timedelta(hours=1),
            password_marker="marker",
            last_manual_verification_at=now,
        )
    )

    second = BackupIntegrityStore(object(), "entry")
    second._store = backend
    state = asyncio.run(second.async_load_state())

    assert state.retry_key == ("backup", "internal_error")
    assert state.retry_attempts == 2
    assert state.password_marker == "marker"
    assert state.last_manual_verification_at == now


def test_automatic_result_does_not_trigger_manual_cooldown() -> None:
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.manual_verification_cooldown_minutes = 10
    coordinator.integrity_result = _result()
    coordinator._last_manual_verification_at = None
    assert coordinator.manual_verification_cooldown_active is False

    coordinator._last_manual_verification_at = datetime.now(UTC)
    assert coordinator.manual_verification_cooldown_active is True


def test_incomplete_manual_backup_does_not_cover_overdue_automatic() -> None:
    now = datetime.now(UTC)
    coordinator = object.__new__(BackupCheckupCoordinator)
    coordinator.max_age_days = 2
    freshness = coordinator._evaluate_freshness(
        now=now,
        latest=_record(date=now, automatic=False, incomplete=True),
        latest_automatic=_record(date=now - timedelta(days=3), automatic=True),
        latest_manual=_record(date=now, automatic=False, incomplete=True),
    )
    assert freshness.automatic_backup_overdue is True


def test_invalid_duplicate_cannot_hide_later_valid_backup() -> None:
    invalid = SimpleNamespace(backup_id="duplicate", date="invalid")
    valid = SimpleNamespace(
        backup_id="duplicate",
        name="Valid",
        date=datetime.now(UTC),
        agents={},
        failed_agent_ids=(),
        failed_addons=(),
        failed_folders=(),
        with_automatic_settings=False,
        extra_metadata={},
        addons=(),
        folders=(),
        database_included=True,
        homeassistant_included=True,
        size=100,
    )
    result = BackupRecordNormalizer("entry").normalize(
        {"invalid": invalid, "valid": valid}
    )
    assert [record.backup_id for record in result.records] == ["duplicate"]
    assert result.invalid_backups == 1


@pytest.mark.parametrize("value", [1.5, float("nan"), float("inf"), "1.0"])
def test_fractional_or_nonfinite_integer_options_use_default(value: object) -> None:
    assert _bounded_int(value, 5, 1, 10) == 5


def test_integral_float_is_accepted_without_truncation() -> None:
    assert _bounded_int(2.0, 5, 1, 10) == 2
    assert BackupRecordNormalizer.as_nonnegative_int(2.5) is None


def test_analytics_sorts_records_and_ignores_future_entries() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    records = (
        _record(backup_id="old", date=now - timedelta(days=2), scope="old"),
        _record(backup_id="future", date=now + timedelta(days=1), scope="future"),
        _record(backup_id="new", date=now, scope="new"),
    )
    result = calculate_inventory_analytics(records, now=now, window_days=30)
    assert result.analyzed_backup_scope == "new"
    assert result.analyzed_backup_count == 1
    assert result.size_trend == SIZE_TREND_INSUFFICIENT_DATA


@pytest.mark.parametrize(
    "operation",
    [
        lambda budget: budget.validate_expected_download(-1),
        lambda budget: budget.add_downloaded(-1),
        lambda budget: budget.add_expanded(-1),
        lambda budget: budget.check_free_space(Path("."), -1),
    ],
)
def test_negative_security_accounting_is_rejected(operation) -> None:
    budget = VerificationBudget(
        deadline=10**12,
        max_download_bytes=100,
        max_expanded_bytes=100,
    )
    with pytest.raises(VerificationLimitError):
        operation(budget)


def test_invalid_budget_options_are_rejected() -> None:
    with pytest.raises(VerificationLimitError, match="invalid_verification_budget"):
        VerificationBudget.from_options(
            max_download_gb=0,
            max_expanded_gb=1,
            timeout_minutes=1,
        )


def test_open_writer_preserves_original_fdopen_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(security.os, "open", lambda *_args, **_kwargs: 7)
    monkeypatch.setattr(
        security.os,
        "fdopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("original")),
    )
    monkeypatch.setattr(
        security.os,
        "close",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("cleanup")),
    )
    with pytest.raises(ValueError, match="original"):
        security.open_private_binary_writer(tmp_path / "file")


def test_orphan_cleanup_failure_does_not_block_setup() -> None:
    integration = importlib.import_module("custom_components.backup_checkup.__init__")

    class ConfigEntries:
        @staticmethod
        def async_entries(_domain: str):
            return []

    class Hass:
        config_entries = ConfigEntries()
        config = SimpleNamespace(path=lambda _name: "/tmp/.storage")

        @staticmethod
        async def async_add_executor_job(*_args, **_kwargs):
            raise OSError("filesystem unavailable")

    assert asyncio.run(integration.async_setup(Hass(), {})) is True


def test_migration_updates_once_without_entity_registry_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    integration = importlib.import_module("custom_components.backup_checkup.__init__")
    updates: list[dict[str, Any]] = []
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=lambda _entry, **kwargs: updates.append(kwargs)
        )
    )
    entry = SimpleNamespace(version=5, data={}, options={})
    monkeypatch.setattr(
        integration,
        "async_apply_entity_mode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("migration must not touch registry")
        ),
    )

    assert asyncio.run(integration.async_migrate_entry(hass, entry)) is True
    assert len(updates) == 1
    assert updates[0]["version"] == 10


def test_health_score_ignores_invalid_history_metrics() -> None:
    result = calculate_health_score(
        {},
        automatic_success_rate=math.nan,
        consecutive_automatic_failures=-5,
        resolved_attempts=-3,
    )
    assert result.score == 100
    assert result.deductions == {}


def test_fallback_display_name_is_also_sanitized() -> None:
    value = security.safe_display_name(None, fallback="fallback\nname" + "x" * 200)
    assert "\n" not in value
    assert len(value) <= 128


def test_settings_object_is_canonical_and_immutable() -> None:
    settings = BackupCheckupSettings.from_sources(
        {"max_age_days": "3", "notification_targets": "notify.phone"}
    )
    assert settings.max_age_days == 3
    assert settings.notification_targets == ("notify.phone",)
    with pytest.raises(AttributeError):
        settings.max_age_days = 4  # type: ignore[misc]
