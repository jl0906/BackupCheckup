<p align="center">
  <img src="custom_components/backup_checkup/brand/icon@2x.png" alt="BackupCheckup icon" width="150">
</p>

<h1 align="center">BackupCheckup</h1>

<p align="center">
  <strong>Understand whether your Home Assistant backups are current, complete, redundant, and readable.</strong>
</p>

<p align="center">
  <img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-orange.svg">
  <img alt="Version 3.0.5" src="https://img.shields.io/badge/version-3.0.5-blue.svg">
  <img alt="Home Assistant 2026.3 or newer" src="https://img.shields.io/badge/Home_Assistant-2026.3_or_newer-41BDF5.svg">
  <img alt="AI coded and maintained" src="https://img.shields.io/badge/AI-coded%20%26%20maintained-8A2BE2.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-yellow.svg">
</p>

BackupCheckup is a local custom integration for Home Assistant. It monitors the
native backup inventory, explains problems, and can verify that the newest backup
is structurally readable. No helpers or automations are required.

## Features

- Monitors backup age, completeness, size changes, storage locations, and failures
- Calculates a transparent Health Score from `0` to `100`
- Verifies complete archives, including encrypted backups and nested archives
- Optionally checks the included Home Assistant SQLite database
- Shows problems through entities, Repairs, and optional notifications
- Provides a responsive sidebar with overview, recovery status, settings, and live log
- Keeps backup names, raw identifiers, paths, passwords, and contents private

## Recovery evidence

The Recovery page presents one evidence level:

| Level | Meaning |
| --- | --- |
| **Monitored** | Backup inventory and health are known. |
| **Structurally verified** | The selected backup was downloaded and completely read. |
| **Runtime-ready** | The optional runner also started that exact backup in an isolated temporary instance. |
| **Fully tested** | A successful external test restore was documented. |

Use **Check backup protection** to run the strongest available verification. The
page shows every stage and the total progress live. BackupCheckup never starts a
restore on the production Home Assistant instance.

## Installation

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **BackupCheckup** and restart Home Assistant.
3. Open **Settings -> Devices & services -> Add integration**.
4. Search for **BackupCheckup** and complete the setup.

Home Assistant **2026.3.0 or newer** is required.

For a manual installation, copy `custom_components/backup_checkup` to
`/config/custom_components/backup_checkup`, restart Home Assistant, and add the
integration from **Settings -> Devices & services**.

## Optional Runtime Runner

Home Assistant OS users can install **BackupCheckup Runtime Runner** from this
repository in the App Store. Once connected, **Check backup protection** continues
from structural verification through these additional stages:

1. Internal upload of the verified archive
2. Extraction into a temporary workspace
3. Isolated Home Assistant Recovery Mode start
4. Readiness probe and signed result
5. Complete cleanup

The runner uses a temporary copy and an isolated network namespace. It does not
call the Supervisor restore API, mount the production configuration, or expose the
temporary instance to the normal network. Communication uses certificate-pinned
TLS. See the [Runtime Runner documentation](runtime_runner/DOCS.md) for installation,
permissions, and limits.

## Configuration and interface

The guided setup separates three decisions:

- **Performance profile:** resource limits and polling frequency
- **Monitoring policy:** acceptable age, size, and storage redundancy
- **Verification strategy:** manual, automatic, or deep archive verification

The optional sidebar contains:

- **Overview** for current health, recent backups, and the next action
- **Recovery** for evidence, risks, live progress, and preparedness tools
- **Settings** for administrator-only configuration
- **Live log** for privacy-safe local activity details

Expert mode adds detailed storage entities and diagnostics. The standard Home
Assistant options dialog remains available when the sidebar is disabled.

## Safety and privacy

The integration runs locally and uses Home Assistant's backup APIs. Structural
verification is read-only and temporary files are removed after each check. The
optional runner receives the selected archive only over Home Assistant's internal
app network and deletes its upload, extracted copy, credentials, and logs after the
run.

A successful structural or runtime check is strong technical evidence, but it is
not a guarantee that every external dependency will work after a real disaster.
For the highest confidence, perform and document a complete restore test on a
separate system.

## Documentation

- [Entity reference](docs/entities.md)
- [Integrity verification](docs/integrity.md)
- [Recovery Readiness](docs/recovery-readiness.md)
- [Activity logging](docs/logging.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)
- [Changelog](CHANGELOG.md)

## Languages

English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish are
included.

## License

MIT License
