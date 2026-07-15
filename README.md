# BackupCheckup

> **Backup health, integrity, and mobile alerting for Home Assistant**
>
> BackupCheckup checks whether Home Assistant backups are available, recent,
> complete, plausible in size, redundant, and structurally readable.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-2.1.2-blue.svg)
![License](https://img.shields.io/github/license/jl0906/BackupCheckup)

Version: **2.1.2**

**Requirements:** Home Assistant **2026.3.0 or newer**. Full encrypted-backup
verification depends on the SecureTar archive API bundled with Home Assistant 2026.3+.

BackupCheckup reads the **actual backup inventory** from Home Assistant's native
backup manager. It can download the newest backup, verify its complete archive
structure, and notify selected Companion App devices when backup problems change.

Everything runs locally inside Home Assistant. BackupCheckup does not modify, delete,
restore, rebuild, or upload backup files.

## Why BackupCheckup?

Creating a backup does not automatically mean that its file is recent, complete, or
still readable. A backup may be missing, unexpectedly small, available on only one
location, or damaged after creation.

BackupCheckup can detect:

- No backup is available.
- The newest backup is too old.
- An automatic backup failed or is overdue.
- A backup is incomplete or unexpectedly small.
- A storage location is unavailable.
- The newest backup is not stored on enough locations.
- A backup cannot be downloaded or fully read.
- An encrypted backup cannot be decrypted with Home Assistant's configured password.
- An included SQLite database fails its optional expert integrity check.

## Main features

### Backup monitoring and analytics

- Actual backup inventory, ages, sizes, and storage locations
- Automatic and manual backup distinction
- Empty, stale, failed, overdue, and incomplete backup detection
- Automatic or fixed backup-size plausibility checks
- Redundancy checks across multiple storage locations
- Deterministic health score from `0` to `100`
- Size trend, average size, longest gap, observed success rate, and consecutive failures
- Backup-size sensors displayed in megabytes instead of raw bytes

### Full backup integrity verification

Use **Verify latest backup** to start a complete, non-destructive verification.
BackupCheckup then:

1. Downloads one available copy through Home Assistant's native backup agent.
2. Calculates and stores a SHA-256 checksum.
3. Opens and reads the complete outer backup archive.
4. Validates `backup.json` and the expected contained archives.
5. Reads every file in every inner archive to the end.
6. Decrypts protected archives using Home Assistant's configured backup password.
7. Optionally runs SQLite `PRAGMA integrity_check` on the included database.
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

### Mobile notifications

Version 2.1 can send alerts directly to one or more mobile devices registered through
the Home Assistant Companion App.

The setup and options flows list only `notify` entities provided by the `mobile_app`
integration, which keeps unrelated notification services out of the selection.

Notifications are available for:

- A newly detected backup problem
- A changed set of active backup problems
- Recovery after all previously reported problems are resolved, when enabled

The same unchanged problem is not sent again at every polling interval. Use the
**Send test notification** button to verify the selected devices.

Mobile notifications are optional and disabled by default. Native Home Assistant
Repair issues and all sensors continue to work without them.

### Selectable entity mode

The setup assistant separates the **monitoring profile** from the number of enabled
entities. This means that Standard, Secure, and Custom monitoring can each be combined
with either entity mode:

| Entity mode | Enabled entities |
| --- | --- |
| **Standard mode** | Enables the useful status, health, backup, integrity, analytics, and global problem entities used by most dashboards and automations. Detailed raw diagnostics and per-storage entities remain disabled. |
| **Expert mode** | Enables every BackupCheckup entity, including schedule diagnostics, checksums, database results, manual-backup values, and every storage-location entity. |

The selection is available during initial setup and later under **Settings → Devices
& services → BackupCheckup → Configure**. Changing the mode applies the corresponding
preset to entities managed by BackupCheckup. Entities explicitly disabled by the user
remain disabled.

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
6. Search for **BackupCheckup**.
7. Choose a monitoring profile and, independently, Standard or Expert entity mode.

### Manual installation

Copy `custom_components/backup_checkup` to
`/config/custom_components/backup_checkup`, restart Home Assistant, and add the
integration through **Settings → Devices & services**.

## Configuration

BackupCheckup offers three monitoring profiles. The profile controls the backup
rules; the separate entity mode controls how many entities are enabled.

| Monitoring profile | Intended use |
| --- | --- |
| **Standard** | Recommended for most installations. Automatic size comparison and one required storage location. |
| **Secure** | Stricter age and size limits and at least two required storage locations. |
| **Custom** | Exposes every monitoring, analytics, Repair, and integrity option. |

| Entity mode | Intended use |
| --- | --- |
| **Standard** | Recommended for most users. Enables the main monitoring, analytics, integrity, and problem entities. |
| **Expert** | Enables all entities, including detailed diagnostics and per-storage metrics. |

Monitoring profile and entity mode are independent. For example, **Secure +
Standard mode** applies strict backup rules without enabling every diagnostic entity.

### Mobile notification setup

During initial setup or later under **Settings → Devices & services → BackupCheckup
→ Configure**:

1. Enable **Mobile notifications**.
2. Select one or more displayed smartphones or tablets.
3. Choose whether a recovery message should be sent.
4. Save the options and press **Send test notification** on the BackupCheckup device.

Only mobile devices with an enabled Home Assistant Companion App `notify` entity are
listed. See the [troubleshooting guide](docs/troubleshooting.md) when a phone is
missing from the selector.

### Custom options

| Option | Description |
| --- | --- |
| Maximum backup age | Creates a problem after the configured number of days. |
| Update interval | Controls how often the lightweight backup inventory is read. |
| Size check mode | Automatic comparison, fixed minimum size, or disabled. |
| Maximum size drop | Allowed reduction compared with comparable backups. |
| Required backup locations | Minimum number of locations containing the newest backup. |
| Repair issues | Shows active backup problems in Home Assistant Repairs. |
| Analysis period | Window used for analytics and observed automatic outcomes. |
| Automatically verify new backups | Starts one full check when a new newest backup is detected. |
| Database integrity check | Expert option that runs SQLite `PRAGMA integrity_check`. |
| Mobile notifications | Sends deduplicated alerts to selected Companion App devices. |
| Notify on recovery | Sends one message after all reported problems are resolved. |

The database check is disabled by default. It requires additional temporary storage
roughly equal to the included database size and can take considerably longer.

## Integrity states

| State | Meaning |
| --- | --- |
| Not checked | No full check has completed yet. |
| Checking | The backup is currently being downloaded and read. |
| Valid | The complete archive was read without errors. |
| Valid with warnings | The archive is readable, but a non-fatal inconsistency was detected. |
| Corrupt | The archive structure or optional database integrity check failed. |
| Unreadable | The backup could not be downloaded or read. |
| Password required | The protected archive could not be decrypted with the available password. |

The normal Home Assistant UI displays these enum states in the selected interface
language. Developer Tools may still show the stable raw values such as `valid`, which
is expected for automations and templates.

The last completed result and checksum are stored locally in Home Assistant. Backup
names, passwords, backup contents, and selected notification entity IDs are not
included in exported diagnostics.

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
  - entity: button.backup_checkup_test_notification
  - entity: button.backup_checkup_refresh
```

## Automation example

Built-in mobile notifications are the easiest choice for most users. A separate
automation remains useful for advanced messages, channels, or escalation rules.

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
Repair links open the dedicated troubleshooting guide.

The diagnostics download includes health, integrity, storage, and sanitized
notification information. It reports only the number of selected notification
targets and the latest privacy-safe error; entity IDs are excluded.

## Documentation

- [Entity reference](docs/entities.md)
- [Integrity verification details](docs/integrity.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Safe 2.0 integrity test plan](docs/testing-2.0.md)
- [FAQ](docs/faq.md)
- [Dashboard example](docs/examples/dashboard.yaml)
- [Automation example](docs/examples/automation.yaml)
- [Changelog](CHANGELOG.md)

## Troubleshooting

Installation, notification, size-unit, integrity, storage, log, diagnostics, and
rollback guidance is maintained on the dedicated
**[Troubleshooting page](docs/troubleshooting.md)**.

## Updating and removal

Install updates through HACS or replace the integration folder manually, then restart
Home Assistant. Removing the config entry also removes BackupCheckup's locally stored
automatic-outcome history, integrity result, and notification deduplication state. It
does not delete any Home Assistant backups.

## License

MIT License
