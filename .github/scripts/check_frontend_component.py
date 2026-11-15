"""Verify that every version constant of the release stays synchronized."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_ROOT = ROOT / "custom_components" / "backup_checkup"
RUNNER_ROOT = ROOT / "runtime_runner"
SERVER = RUNNER_ROOT / "rootfs" / "opt" / "backup-checkup-runner" / "server.py"


def _required_match(pattern: str, content: str, source: str) -> str:
    """Return the first capture or fail with a useful validation error."""
    match = re.search(pattern, content, re.MULTILINE)
    if match is None:
        raise SystemExit(f"Unable to read version data from {source}")
    return match.group(1)


def _check_panel(manifest: dict[str, str], problems: list[str]) -> None:
    """Compare the manifest, backend asset revision, and custom element name."""
    backend = (INTEGRATION_ROOT / "frontend.py").read_text(encoding="utf-8")
    panel = (INTEGRATION_ROOT / "frontend" / "backup-checkup-panel.js").read_text(
        encoding="utf-8"
    )
    revision = _required_match(
        r"^PANEL_ASSET_REVISION = (\d+)$", backend, "frontend.py"
    )
    actual = _required_match(
        r'^const PANEL_ELEMENT_NAME = "([^"]+)";$',
        panel,
        "backup-checkup-panel.js",
    )
    expected = (
        f"backup-checkup-panel-v{manifest['version'].replace('.', '-')}-r{revision}"
    )
    if actual != expected:
        problems.append(f"Frontend component mismatch: {actual} != {expected}")


def _check_integration(manifest: dict[str, str], problems: list[str]) -> str:
    """Compare the manifest, constants, readme badge, and changelog."""
    const = (INTEGRATION_ROOT / "const.py").read_text(encoding="utf-8")
    version = _required_match(r'^VERSION = "([^"]+)"$', const, "const.py")
    if version != manifest["version"]:
        problems.append(
            f"const.py VERSION {version} != manifest {manifest['version']}"
        )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"version-{version}-blue" not in readme:
        problems.append(f"README badge does not mention version {version}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version}" not in changelog:
        problems.append(f"CHANGELOG.md has no section for {version}")
    return version


def _check_runner(problems: list[str]) -> str:
    """Compare every runner version constant with the integration policy."""
    const = (INTEGRATION_ROOT / "const.py").read_text(encoding="utf-8")
    server = SERVER.read_text(encoding="utf-8")
    config = (RUNNER_ROOT / "config.yaml").read_text(encoding="utf-8")
    dockerfile = (RUNNER_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = (INTEGRATION_ROOT / "recovery_runtime.py").read_text(encoding="utf-8")

    runner_version = _required_match(
        r'^RUNNER_VERSION = "([^"]+)"$', server, "server.py"
    )
    config_version = _required_match(r'^version: "([^"]+)"$', config, "config.yaml")
    build_version = _required_match(
        r"^ARG BUILD_VERSION=(\S+)$", dockerfile, "Dockerfile"
    )
    minimum = int(
        _required_match(r"^MIN_RUNNER_VERSION = (\d+)$", const, "const.py")
    )
    recommended = int(
        _required_match(r"^RECOMMENDED_RUNNER_VERSION = (\d+)$", const, "const.py")
    )
    server_protocol = int(
        _required_match(r"^PROTOCOL_VERSION = (\d+)$", server, "server.py")
    )
    client_protocol = int(
        _required_match(
            r"^_PROTOCOL_VERSION = (\d+)$", runtime, "recovery_runtime.py"
        )
    )

    if not runner_version == config_version == build_version:
        problems.append(
            "Runner version mismatch: "
            f"server.py {runner_version}, config.yaml {config_version}, "
            f"Dockerfile {build_version}"
        )
    if int(runner_version) != recommended:
        problems.append(
            f"RECOMMENDED_RUNNER_VERSION {recommended} != shipped runner "
            f"{runner_version}"
        )
    if minimum > recommended:
        problems.append(
            f"MIN_RUNNER_VERSION {minimum} is above "
            f"RECOMMENDED_RUNNER_VERSION {recommended}"
        )
    if server_protocol != client_protocol:
        problems.append(
            f"Protocol mismatch: runner {server_protocol}, "
            f"integration {client_protocol}"
        )
    if (banner := f'server_version = "BackupCheckupRuntime/{runner_version}"') not in (
        server
    ):
        problems.append(f"Runner banner does not match: expected {banner}")
    _check_runner_changelog(runner_version, problems)
    return runner_version


def _check_runner_changelog(runner_version: str, problems: list[str]) -> None:
    """Require release notes for the shipped runner in the app update dialog."""
    path = RUNNER_ROOT / "CHANGELOG.md"
    if not path.is_file():
        problems.append("runtime_runner/CHANGELOG.md is missing")
        return
    sections = re.findall(
        r"^## (\S+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if runner_version not in sections:
        problems.append(
            f"runtime_runner/CHANGELOG.md has no section for runner {runner_version}"
        )
    elif sections[0] != runner_version:
        problems.append(
            f"runtime_runner/CHANGELOG.md starts with runner {sections[0]} "
            f"instead of the shipped runner {runner_version}"
        )


def main() -> None:
    """Fail when any released version constant drifts apart."""
    manifest = json.loads(
        (INTEGRATION_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    problems: list[str] = []
    version = _check_integration(manifest, problems)
    _check_panel(manifest, problems)
    runner_version = _check_runner(problems)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit("Version constants are inconsistent")
    print(f"Versions synchronized: integration {version}, runner {runner_version}")


if __name__ == "__main__":
    main()
