"""Tests for BackupCheckup security helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from custom_components.backup_checkup import security
from custom_components.backup_checkup.security import (
    VerificationBudget,
    VerificationLimitError,
    anonymous_backup_reference,
    cleanup_stale_temp_directories,
    create_private_temp_directory,
    open_private_binary_writer,
    safe_error_type,
    safe_log_value,
)


def test_download_and_expanded_limits() -> None:
    """Safety budgets stop oversized input."""
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=10,
        max_expanded_bytes=20,
        max_members=2,
    )
    budget.add_downloaded(10)
    with pytest.raises(VerificationLimitError, match="download_size_limit"):
        budget.add_downloaded(1)

    budget.add_expanded(20)
    with pytest.raises(VerificationLimitError, match="expanded_size_limit"):
        budget.add_expanded(1)

    budget.add_member()
    budget.add_member()
    with pytest.raises(VerificationLimitError, match="archive_member_limit"):
        budget.add_member()


def test_budget_cancellation_is_cooperative() -> None:
    """Executor workers stop at their next budget check after cancellation."""
    budget = VerificationBudget(
        deadline=time.monotonic() + 60,
        max_download_bytes=10,
        max_expanded_bytes=20,
    )
    budget.cancel()
    with pytest.raises(VerificationLimitError, match="verification_cancelled"):
        budget.check_deadline()


def test_safe_log_value_is_single_line_and_bounded() -> None:
    """Untrusted values cannot inject log lines or grow without bounds."""
    value = safe_log_value(
        "name\nwith\tcontrols\u2028separator" + "x" * 200, max_length=40
    )
    assert "\n" not in value
    assert "\t" not in value
    assert "\u2028" not in value
    assert len(value) == 40


def test_safe_error_type_sanitizes_dynamic_class_names() -> None:
    """Untrusted exception class names cannot inject diagnostic lines."""
    unsafe_error = type("Unsafe\nError", (Exception,), {})()
    assert safe_error_type(unsafe_error) == "Unsafe?Error"


def test_anonymous_backup_reference_is_stable_and_installation_local() -> None:
    """Backup IDs are replaced by stable local references."""
    first = anonymous_backup_reference("entry-a", "secret-id")
    assert first == anonymous_backup_reference("entry-a", "secret-id")
    assert first != anonymous_backup_reference("entry-b", "secret-id")
    assert first != "secret-id"
    assert len(first) == 12


def test_private_temp_permissions() -> None:
    """Verification directories and files are owner-only on POSIX systems."""
    temp_dir = create_private_temp_directory()
    try:
        file_path = temp_dir / "backup.tar"
        with open_private_binary_writer(file_path) as writer:
            writer.write(b"backup")
        if os.name == "posix":
            assert temp_dir.stat().st_mode & 0o777 == 0o700
            assert file_path.stat().st_mode & 0o777 == 0o600
    finally:
        security.cleanup_temp_directory(temp_dir)


def test_stale_cleanup_only_removes_owned_prefixed_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Startup cleanup ignores unrelated paths and removes stale verification data."""
    stale = tmp_path / "backup_checkup_stale"
    fresh = tmp_path / "backup_checkup_fresh"
    unrelated = tmp_path / "other_component"
    for path in (stale, fresh, unrelated):
        path.mkdir()
    old = time.time() - 48 * 3600
    os.utime(stale, (old, old))
    os.utime(unrelated, (old, old))
    monkeypatch.setattr(security.tempfile, "gettempdir", lambda: str(tmp_path))

    result = cleanup_stale_temp_directories()
    assert result.failures == 0
    assert result.remaining == 1
    assert result.issue_active
    assert not stale.exists()
    assert fresh.exists()
    assert unrelated.exists()
