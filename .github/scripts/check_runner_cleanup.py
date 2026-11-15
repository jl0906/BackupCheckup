"""Exercise runner cleanup behavior without requiring a Home Assistant image."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import threading
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = (
    ROOT
    / "runtime_runner"
    / "rootfs"
    / "opt"
    / "backup-checkup-runner"
    / "server.py"
)


def _load_server():
    securetar = ModuleType("securetar")
    securetar.SecureTarArchive = object
    sys.modules.setdefault("securetar", securetar)
    spec = importlib.util.spec_from_file_location("runner_server_cleanup_test", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load runner server module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manager(server):
    manager = server.RunManager.__new__(server.RunManager)
    manager._lock = threading.Lock()
    manager._runs = {}
    return manager


def main() -> None:
    server = _load_server()
    if server.PROTOCOL_VERSION != 2 or server.RUNNER_VERSION != "4":
        raise SystemExit("Unexpected runner protocol or independent version")
    payload = {
        "maximum_archive_gb": 50,
        "maximum_expanded_gb": 250,
        "runtime_timeout_minutes": 20,
    }
    for key, minimum, maximum in (
        ("maximum_archive_gb", 1, 2048),
        ("maximum_expanded_gb", 1, 8192),
        ("runtime_timeout_minutes", 2, 60),
    ):
        if server.RunManager._required_limit(payload, key, minimum, maximum) != payload[key]:
            raise SystemExit(f"Runner rejected valid limit: {key}")
        for invalid in (True, minimum - 1, maximum + 1):
            try:
                server.RunManager._required_limit({key: invalid}, key, minimum, maximum)
            except server.RunnerFailure as error:
                if error.code != "runner_limits_invalid":
                    raise
            else:
                raise SystemExit(f"Runner accepted invalid limit: {key}")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        run_dir = root / "success"
        run_dir.mkdir()
        (run_dir / "backup.tar").write_bytes(b"backup")
        run = server.RunState(
            "success", run_dir, "ref", "0" * 64, 6, None, 60, 250_000_000_000, "id"
        )
        manager = _manager(server)
        manager._runs[run.run_id] = run
        manager.delete(run.run_id)
        if run_dir.exists() or run.run_id in manager._runs:
            raise SystemExit("Successful deletion left runner data behind")

        failed_dir = root / "failed"
        failed_dir.mkdir()
        failed = server.RunState(
            "failed", failed_dir, "ref", "0" * 64, 1, None, 60, 250_000_000_000, "id"
        )
        manager._runs[failed.run_id] = failed
        with patch.object(server.shutil, "rmtree", side_effect=PermissionError):
            try:
                manager.delete(failed.run_id)
            except server.RunnerFailure as error:
                if error.code != "cleanup_failed":
                    raise
            else:
                raise SystemExit("Deletion failure was incorrectly reported as success")
        if failed.run_id not in manager._runs:
            raise SystemExit("Failed cleanup was removed instead of retained for retry")

        cleanup_dir = root / "contents"
        (cleanup_dir / "restored").mkdir(parents=True)
        (cleanup_dir / "restored" / "large-file").write_bytes(b"data")
        (cleanup_dir / "result.json").write_text("{}", encoding="utf-8")
        (cleanup_dir / "progress.json").write_text("{}", encoding="utf-8")
        content_run = server.RunState(
            "contents",
            cleanup_dir,
            "ref",
            "0" * 64,
            4,
            None,
            60,
            250_000_000_000,
            "id",
        )
        manager._cleanup_run(content_run)
        remaining = {path.name for path in cleanup_dir.iterdir()}
        if remaining != {"result.json", "progress.json"}:
            raise SystemExit(f"Unexpected artifacts after runtime cleanup: {remaining}")

    print("Runner cleanup behavior passed")


if __name__ == "__main__":
    main()
