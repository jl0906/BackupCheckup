"""Branch tests for integrity persistence and small archive helpers."""

from __future__ import annotations

import asyncio
import io
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from custom_components.backup_checkup import integrity
from custom_components.backup_checkup.const import (
    INTEGRITY_DATABASE_NOT_CHECKED,
    INTEGRITY_STATUS_VALID,
)
from custom_components.backup_checkup.integrity import (
    BackupIntegrityStore,
    BackupIntegrityVerifier,
)
from custom_components.backup_checkup.models import BackupIntegrityResult
from custom_components.backup_checkup.security import VerificationBudget


class FakeStore:
    def __init__(self, data: Any) -> None:
        self.data = data
        self.saved: dict[str, Any] | None = None
        self.removed = False
        self.loads = 0

    async def async_load(self) -> Any:
        self.loads += 1
        if isinstance(self.data, BaseException):
            raise self.data
        return self.data

    async def async_save(self, data: dict[str, Any]) -> None:
        self.saved = data

    async def async_remove(self) -> None:
        self.removed = True


def _result() -> BackupIntegrityResult:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    return BackupIntegrityResult(
        status=INTEGRITY_STATUS_VALID,
        checked_at=now,
        backup_id="backup-id",
        backup_reference="reference",
        backup_date=now,
        agent_id="agent",
        sha256="a" * 64,
        verified_size=123,
        duration_seconds=1.2,
        archive_count=2,
        file_count=3,
        protected=True,
        database_status=INTEGRITY_DATABASE_NOT_CHECKED,
        warnings=(),
        error_code=None,
        checksum_changed=False,
    )


def test_integrity_store_load_none_and_cached_result() -> None:
    store = BackupIntegrityStore(object(), "entry")
    fake = FakeStore(None)
    store._store = fake

    first = asyncio.run(store.async_load())
    second = asyncio.run(store.async_load())

    assert first.status == "not_checked"
    assert second is first
    assert fake.loads == 1


@pytest.mark.parametrize(
    "stored",
    [
        [],
        {"status": "future-status"},
        ValueError("load failed"),
    ],
)
def test_integrity_store_resets_invalid_data(stored: Any) -> None:
    store = BackupIntegrityStore(object(), "entry")
    store._store = FakeStore(stored)

    result = asyncio.run(store.async_load())

    assert result.status == "not_checked"


def test_integrity_store_loads_saves_and_removes_valid_result() -> None:
    expected = _result()
    store = BackupIntegrityStore(object(), "entry")
    fake = FakeStore(expected.as_dict())
    store._store = fake

    loaded = asyncio.run(store.async_load())
    assert loaded.status == INTEGRITY_STATUS_VALID
    assert loaded.backup_id == "backup-id"

    replacement = BackupIntegrityResult.not_checked()
    asyncio.run(store.async_save(replacement))
    assert fake.saved is not None
    assert fake.saved["result"] == replacement.as_dict()
    assert fake.saved["retry"]["attempts"] == 0
    assert store._result is replacement

    asyncio.run(store.async_remove())
    assert fake.removed is True


def test_archive_prefix_expected_archives_and_database_expectation() -> None:
    assert BackupIntegrityVerifier._archive_prefix("addon.tar.gz") == "addon"
    assert BackupIntegrityVerifier._archive_prefix("addon.tgz") == "addon"
    assert BackupIntegrityVerifier._archive_prefix("addon.tar") == "addon"
    assert BackupIntegrityVerifier._archive_prefix("plain-name") == "plain-name"

    assert (
        BackupIntegrityVerifier._expected_archives(
            {
                "homeassistant": "invalid",
                "addons": "invalid",
                "folders": "invalid",
            }
        )
        == set()
    )
    assert BackupIntegrityVerifier._expected_archives(
        {
            "homeassistant": {},
            "addons": [None, {}, {"slug": 1}, {"slug": "addon"}],
            "folders": ["homeassistant", "share"],
        }
    ) == {"homeassistant", "addon", "share"}

    assert not BackupIntegrityVerifier._database_expected({})
    assert not BackupIntegrityVerifier._database_expected(
        {"homeassistant": {"exclude_database": True}}
    )
    assert BackupIntegrityVerifier._database_expected(
        {"homeassistant": {"exclude_database": False}}
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        123,
        "bad\\path",
        "bad\x00path",
        "/absolute",
        "../escape",
        "folder/../../escape",
    ],
)
def test_member_path_validation_rejects_unsafe_names(name: Any) -> None:
    with pytest.raises(tarfile.ReadError, match="unsafe_archive_member_path"):
        BackupIntegrityVerifier._validate_member_path(name)


def test_member_path_validation_accepts_safe_relative_name() -> None:
    BackupIntegrityVerifier._validate_member_path("folder/file.txt")


def test_consume_and_copy_helpers_cover_optional_accounting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=100,
        max_expanded_bytes=100,
    )
    consumed = BackupIntegrityVerifier._consume_all(
        io.BytesIO(b"abc"),
        budget=budget,
        count_expanded=False,
    )
    assert consumed == 3
    assert budget.expanded_bytes == 0

    checks: list[Path] = []
    monkeypatch.setattr(integrity, "_FREE_SPACE_CHECK_INTERVAL", 1)
    monkeypatch.setattr(
        VerificationBudget,
        "check_free_space",
        lambda self, path, required_bytes=0: checks.append(Path(path)),
    )
    writer = io.BytesIO()
    copied = BackupIntegrityVerifier._copy_all(
        io.BytesIO(b"abcdef"),
        writer,
        budget=budget,
        free_space_path=tmp_path,
    )
    assert copied == 6
    assert writer.getvalue() == b"abcdef"
    assert checks == [tmp_path]
