<h1 align="center">BackupCheckup</h1>

<p align="center">
  <strong>Understand whether your Home Assistant backups are current, complete, redundant, readable, and ready for recovery.</strong>
</p>

<p align="center">
  <img alt="Version 3.2.0" src="https://img.shields.io/badge/version-3.2.0-blue.svg">
  <img alt="Home Assistant 2026.3 or newer" src="https://img.shields.io/badge/Home_Assistant-2026.3_or_newer-41BDF5.svg">
  <img alt="AI coded and maintained" src="https://img.shields.io/badge/AI-coded%20%26%20maintained-8A2BE2.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-yellow.svg">
</p>

BackupCheckup is a local Home Assistant custom integration. It monitors the native
backup inventory, explains problems through a transparent Health Score, checks age,
completeness, size, storage redundancy and automatic-backup history, and can fully
read the newest backup including encrypted and nested archives. Optional database
verification, Repairs, mobile notifications, a sidebar panel, privacy-safe live
logging and Recovery Readiness guidance are included.

Long-running checks report measured live progress: the download and the archive
scan publish the bytes they have really read, and steps that cannot be measured
are shown as indeterminate with their runtime and last sign of life instead of an
invented percentage.

BackupCheckup never restores or changes the production system. The optional
**BackupCheckup Runtime Runner** for Home Assistant OS can additionally start an
already verified backup in a temporary, network-isolated Home Assistant instance.
Its reachability is monitored, and **Runtime Runner 3** adds live step progress
and boot events. The runner has its own version line; runner 2 keeps working
without the live detail.

## Installation

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

Install BackupCheckup through HACS, restart Home Assistant, then add the integration
under **Settings → Devices & services**. Home Assistant 2026.3.0 or newer is required.

## Documentation

The complete installation, configuration, feature, entity, automation, security,
Runtime Runner and troubleshooting guide is maintained in the
**[BackupCheckup Wiki](https://github.com/jl0906/BackupCheckup/wiki)**.

## License

MIT License
