# BackupCheckup

> **Backup health and integrity monitoring for Home Assistant**
>
> BackupCheckup checks whether Home Assistant backups are available, recent,
> complete, plausible in size, redundant, and structurally readable.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/github/license/jl0906/BackupCheckup)

Version: **2.0.0**

BackupCheckup reads the **actual backup inventory** from Home Assistant's native
backup manager. Version 2.0 can additionally download the newest backup and verify
its complete archive structure without changing the backup.

Everything runs locally inside Home Assistant. BackupCheckup never uploads backup
contents and does not modify, delete, restore, or rebuild backup files.

## Why BackupCheckup?

Creating a backup does not automatically mean that its file can still be read.
A backup may be missing, too old, incomplete, unexpectedly small, available on only
one location, or damaged after it was created.

BackupCheckup can detect:

- No backup is available.
- The newest backup is too old.
- An automatic backup failed or is overdue.
- A backup is incomplete or unexpectedly small.
- A storage location is unavailable.
- The newest backup is not stored on enough locations.
- A backup cannot be downloaded or fully read.
- An encrypted backup cannot be decrypted with Home Assistant's configured backup password.
- An included SQLite database fails its integrity check when expert verification is enabled.

## Features

### Full backup integrity verification

Use **Verify latest backup** to start a complete, non-destructive verification.
BackupCheckup then:

1. Downloads one available copy of the newest backup through Home Assistant's native backup agent.
2. Calculates and stores a SHA-256 checksum.
3. Opens and reads the complete outer backup archive.
4. Validates `backup.json` and the expected contained archives.
5. Reads every file in every inner archive to the end.
6. Decrypts and validates protected archives using Home Assistant's configured backup password.
7. Optionally extracts the included SQLite database to temporary storage and runs `PRAGMA integrity_check`.
8. Deletes all temporary files when the check finishes.

The result is available through `sensor.backup_checkup_integrity_status`. A native
Home Assistant Repair issue is created if the newest backup is corrupt or unreadable.

> [!IMPORTANT]
> A successful integrity check proves that the downloaded backup is structurally
> readable and, where applicable, decryptable. It is not a full restore test and
> cannot guarantee that every integration, add-on, external service, or device will
> work after restoration.

### Optional automatic verification

The Custom profile can automatically verify each newly detected newest backup.
Automatic verification is disabled by default because a full check can transfer and
read several gigabytes and may temporarily increase disk, network, and CPU usage.

### Backup monitoring and analytics

- Actual backup inventory, ages, sizes, and storage locations
- Automatic and manual backup distinction
- Empty, stale, failed, overdue, and incomplete backup detection
- Automatic or fixed backup-size plausibility checks
- Redundancy checks across multiple storage locations
- Deterministic health score from `0` to `100`
- Size trend, average size, longest gap, observed success rate, and consecutive failures
- Native Home Assistant Repairs and privacy-conscious diagnostics

### Streamlined entities

Version 2.0 keeps all existing detail entities for compatibility, but new
installations start with a smaller default set. The main device exposes the values
needed for everyday monitoring. Analytics, schedule details, checksum, database
status, and per-storage metrics remain available as disabled entities and can be
enabled from the entity registry.

Existing installations are not forcibly changed, so current dashboards and
automations continue to work.

### Languages

English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish are
included. Belgian users are covered by Dutch, French, and German.

## Installation

### HACS — recommended

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

1. Open HACS.
2. Add this repository as a custom repository of type **Integration**.
3. Install **BackupCheckup**.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Search for **BackupCheckup** and choose a monitoring profile.

### Manual installation

Copy `custom_components/backup_checkup` to
`/config/custom_components/backup_checkup`, restart Home Assistant, and add the
integration through **Settings → Devices & services**.

## Configuration

BackupCheckup offers three profiles.

| Profile | Intended use |
| --- | --- |
| **Standard** | Recommended for most installations. Automatic size comparison and one required storage location. |
| **Secure** | Stricter age and size limits and at least two required storage locations. |
| **Custom** | Exposes every threshold, analytics, Repair, and integrity option. |

### Custom options

| Option | Description |
| --- | --- |
| Maximum backup age | Creates a problem after the configured number of days. |
| Update interval | Controls how often the actual backup inventory is read. |
| Size check mode | Automatic comparison, fixed minimum size, or disabled. |
| Maximum size drop | Allowed reduction compared with comparable backups. |
| Required backup locations | Minimum number of locations containing the newest backup. |
| Repair notifications | Shows active backup problems in Home Assistant Repairs. |
| Analysis period | Window used for analytics and observed automatic outcomes. |
| Automatically verify new backups | Starts one full check when a new newest backup is detected. |
| Database integrity check | Expert option that runs SQLite `PRAGMA integrity_check` on the included database. |

The database check is disabled by default. It requires additional temporary storage
roughly equal to the size of the included database and can take considerably longer.

## Integrity states

| State | Meaning |
| --- | --- |
| Not checked | No full check has completed yet. |
| Checking | The backup is currently being downloaded and read. |
| Valid | The complete archive was read without errors. |
| Valid with warnings | The archive is readable, but a non-fatal issue such as a size or checksum change was detected. |
| Corrupt | The archive structure or optional database integrity check failed. |
| Unreadable | The backup could not be downloaded or read. |
| Password required | The protected archive could not be decrypted with the available backup password. |

The last completed result and checksum are stored locally in Home Assistant. Backup
names, passwords, and backup contents are never stored by BackupCheckup.

## Recommended dashboard

A ready-to-copy example is available in
[`docs/examples/dashboard.yaml`](docs/examples/dashboard.yaml).

```yaml
type: entities
title: BackupCheckup
entities:
  - entity: sensor.backup_checkup_health_score
  - entity: sensor.backup_checkup_status
  - entity: sensor.backup_checkup_recommendation
  - entity: sensor.backup_checkup_latest_backup
  - entity: sensor.backup_checkup_latest_backup_age
  - entity: sensor.backup_checkup_latest_backup_size
  - entity: sensor.backup_checkup_integrity_status
  - entity: binary_sensor.backup_checkup_problem
  - entity: button.backup_checkup_verify_latest_backup
  - entity: button.backup_checkup_refresh
```

## Automation example

A complete example is available in
[`docs/examples/automation.yaml`](docs/examples/automation.yaml).

```yaml
alias: BackupCheckup problem notification
triggers:
  - trigger: state
    entity_id: binary_sensor.backup_checkup_problem
    to: "on"
actions:
  - action: notify.notify
    data:
      title: BackupCheckup
      message: "{{ states('sensor.backup_checkup_recommendation') }}"
mode: single
```

## Repairs and diagnostics

When enabled, BackupCheckup creates native Repair issues under
**Settings → System → Repairs** and removes them automatically after recovery.
Version 2.0 adds a Repair issue for a corrupt or unreadable newest backup.

The diagnostics download includes the integrity status, verification time, selected
storage location, SHA-256 checksum, verified size, archive/file counts, database
result, warnings, and error code. Backup names and backup IDs are excluded.

## Documentation

- [Entity reference](docs/entities.md)
- [Integrity verification details](docs/integrity.md)
- [Safe 2.0 test plan](docs/testing-2.0.md)
- [FAQ](docs/faq.md)
- [Dashboard example](docs/examples/dashboard.yaml)
- [Automation example](docs/examples/automation.yaml)
- [Changelog](CHANGELOG.md)

## Troubleshooting

### Verification remains on Checking

Large backups may take several minutes. Check free temporary storage and the
connection to the selected backup location. Restarting or reloading the integration
cancels the current check without changing the backup.

### Password required

Open Home Assistant's native backup settings and verify that the configured backup
password can decrypt the selected backup. BackupCheckup does not save or request a
separate password.

### Corrupt or unreadable result

Keep the affected backup for diagnosis, verify another copy or storage location, and
create a new backup. Do not rely on the affected file as the only recovery point.

More answers are available in [`docs/faq.md`](docs/faq.md).

## Updating and removal

Install updates through HACS or replace the integration folder manually, then restart
Home Assistant. Removing the config entry also removes BackupCheckup's locally stored
automatic-outcome history and last integrity result. It does not delete any Home
Assistant backups.

## License

MIT License
