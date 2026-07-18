"""Storage-copy fallback tests for BackupCheckup integrity verification."""

from __future__ import annotations

import asyncio
import io
import json
import tarfile
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from custom_components.backup_checkup import integrity
from custom_components.backup_checkup.const import (
    INTEGRITY_STATUS_INTERNAL_ERROR,
    INTEGRITY_STATUS_VALID_WITH_WARNINGS,
)
from custom_components.backup_checkup.integrity import BackupIntegrityVerifier
from custom_components.backup_checkup.models import (
    BackupAgentRecord,
    BackupIntegrityResult,
    BackupRecord,
)


class _ExecutorHass:
    """Provide the executor behavior used by the verifier."""

    def async_add_executor_job(self, target: Any, *args: Any):
        return asyncio.get_running_loop().run_in_executor(None, target, *args)


class _BytesAgent:
    """Download one in-memory backup copy."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def async_download_backup(self, _backup_id: str):
        async def _stream():
            yield self._payload

        return _stream()


def _tar_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()


def _valid_backup() -> bytes:
    inner = _tar_bytes({"data/configuration.yaml": b"homeassistant:"})
    metadata = json.dumps(
        {
            "protected": False,
            "homeassistant": {},
            "addons": [],
            "folders": [],
        }
    ).encode()
    return _tar_bytes({"backup.json": metadata, "homeassistant.tar": inner})


def _record(copy_sizes: dict[str, int]) -> BackupRecord:
    copies = tuple(
        BackupAgentRecord(
            agent_id=agent_id,
            agent_reference=f"ref-{index}",
            size=size,
            protected=False,
        )
        for index, (agent_id, size) in enumerate(copy_sizes.items())
    )
    return BackupRecord(
        backup_id="backup-id",
        backup_reference="backup-ref",
        name="Backup",
        date=datetime.now(UTC),
        automatic=True,
        purpose="automatic",
        included_addons=(),
        included_folders=(),
        scope_fingerprint="scope",
        agents=tuple(copy_sizes),
        agent_copies=copies,
        failed_agents=(),
        failed_addons=(),
        failed_folders=(),
        database_included=None,
        homeassistant_included=True,
        size=max(copy_sizes.values()),
        incomplete=False,
    )


def test_corrupt_preferred_copy_falls_back_to_valid_copy(monkeypatch) -> None:
    """A corrupt local copy does not hide a valid redundant remote copy."""
    corrupt = b"not a tar archive"
    valid = _valid_backup()
    agents = {
        "backup.local": _BytesAgent(corrupt),
        "backup.remote": _BytesAgent(valid),
    }
    manager = SimpleNamespace(backup_agents=agents)
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)

    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    result = asyncio.run(
        verifier.async_verify(
            _record(
                {
                    "backup.local": len(corrupt),
                    "backup.remote": len(valid),
                }
            ),
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS
    assert result.agent_id == "backup.remote"
    assert "alternate_storage_copy_used" in result.warnings
    assert "storage_copy_verification_failed" in result.warnings


def test_all_corrupt_copies_report_failure(monkeypatch) -> None:
    """All failed copies produce one explicit aggregate failure result."""
    first = b"not a tar archive"
    second = b"also not a tar archive"
    agents = {
        "backup.local": _BytesAgent(first),
        "backup.remote": _BytesAgent(second),
    }
    manager = SimpleNamespace(backup_agents=agents)
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)

    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    result = asyncio.run(
        verifier.async_verify(
            _record(
                {
                    "backup.local": len(first),
                    "backup.remote": len(second),
                }
            ),
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == "corrupt"
    assert result.error_code == "archive_invalid"
    assert "all_storage_copies_failed" in result.warnings


def test_copy_local_size_limit_falls_back_to_valid_copy(monkeypatch) -> None:
    """One oversized reported copy does not block a valid redundant copy."""
    valid = _valid_backup()
    agents = {
        "backup.local": _BytesAgent(b"unused"),
        "backup.remote": _BytesAgent(valid),
    }
    manager = SimpleNamespace(backup_agents=agents)
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)
    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    result = asyncio.run(
        verifier.async_verify(
            _record(
                {
                    "backup.local": 1_000_000_001,
                    "backup.remote": len(valid),
                }
            ),
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS
    assert result.agent_id == "backup.remote"
    assert "alternate_storage_copy_used" in result.warnings


def test_all_copy_local_size_limits_return_aggregate_abort(monkeypatch) -> None:
    """All oversized copies result in one bounded aggregate failure."""
    agents = {
        "backup.local": _BytesAgent(b"unused"),
        "backup.remote": _BytesAgent(b"unused"),
    }
    manager = SimpleNamespace(backup_agents=agents)
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)
    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    result = asyncio.run(
        verifier.async_verify(
            _record(
                {
                    "backup.local": 1_000_000_001,
                    "backup.remote": 1_000_000_002,
                }
            ),
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == "aborted"
    assert result.error_code == "download_size_limit"
    assert "all_storage_copies_failed" in result.warnings


def test_reported_cross_copy_size_mismatch_becomes_integrity_warning(
    monkeypatch,
) -> None:
    """A material size disagreement is visible in the verification result."""
    valid = _valid_backup()
    agents = {"backup.local": _BytesAgent(valid)}
    manager = SimpleNamespace(backup_agents=agents)
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)
    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    record = replace(
        _record({"backup.local": len(valid)}),
        copy_size_mismatch=True,
        copy_size_spread_bytes=2_000_000,
    )
    result = asyncio.run(
        verifier.async_verify(
            record,
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == INTEGRITY_STATUS_VALID_WITH_WARNINGS
    assert "storage_copy_size_mismatch" in result.warnings


def test_invalid_final_candidate_state_returns_internal_error(
    monkeypatch, tmp_path
) -> None:
    """An impossible final candidate state fails safely without an assert."""
    manager = SimpleNamespace(
        backup_agents={"backup.local": object()},
        config=SimpleNamespace(
            data=SimpleNamespace(create_backup=SimpleNamespace(password=None))
        ),
    )
    monkeypatch.setattr(integrity, "async_get_manager", lambda _hass: manager)
    verifier = BackupIntegrityVerifier(_ExecutorHass(), "entry")

    async def _load_previous() -> BackupIntegrityResult:
        return BackupIntegrityResult.not_checked()

    async def _temp_directory(*_args, **_kwargs):
        return tmp_path

    async def _invalid_candidate(**_kwargs):
        return integrity._CandidateOutcome(None, final=True)

    async def _cleanup(*_args, **_kwargs):
        return None

    monkeypatch.setattr(verifier.store, "async_load", _load_previous)
    monkeypatch.setattr(verifier, "_async_create_temp_directory", _temp_directory)
    monkeypatch.setattr(verifier, "_async_verify_candidate", _invalid_candidate)
    monkeypatch.setattr(verifier, "_async_cleanup_verification_data", _cleanup)

    result = asyncio.run(
        verifier.async_verify(
            _record({"backup.local": 1}),
            database_check=False,
            max_download_gb=1,
            max_expanded_gb=1,
            timeout_minutes=1,
            database_timeout_minutes=1,
            repair_issues_enabled=False,
        )
    )

    assert result.status == INTEGRITY_STATUS_INTERNAL_ERROR
    assert result.error_code == "candidate_result_missing"
