# BackupCheckup

> **Know whether your Home Assistant backups are truly ready when you need them.**
>
> BackupCheckup monitors backup health, verifies archive integrity, checks storage redundancy, and can alert your mobile devices when something needs attention.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-2.1.2-blue.svg)
![License](https://img.shields.io/github/license/jl0906/BackupCheckup)

> [!IMPORTANT]
> Required Home Assistant Version: **2026.3.0 or newer**

BackupCheckup works directly with Home Assistant's native backup manager. It reads the real backup inventory, evaluates backup quality, and can fully inspect the newest backup without modifying it.

Everything runs locally. BackupCheckup never restores, deletes, rebuilds, uploads, or changes your backup files.

## Why BackupCheckup?

A successful backup task does not always mean that the resulting file is recent, complete, available on enough storage locations, or still readable.

BackupCheckup gives you one clear place to answer the important questions:

- Is a recent backup available?
- Did the automatic backup process work?
- Is the backup size plausible?
- Is the newest backup stored redundantly?
- Can the complete archive still be downloaded, opened, and decrypted?
- Is the included Home Assistant database structurally healthy?

Instead of checking dozens of technical values yourself, you get a health score, a readable status, a recommendation, native Repair issues, and optional mobile alerts.

## Main features

### Backup monitoring and analytics

- Reads the actual Home Assistant backup inventory
- Monitors automatic and manual backups separately
- Detects missing, stale, overdue, failed, incomplete, and unusually small backups
- Checks redundancy across configured storage locations
- Displays backup sizes in megabytes
- Provides a transparent health score from `0` to `100`
- Tracks size trends, average size, backup gaps, observed success rate, and consecutive failures

### Full backup integrity verification

The **Verify latest backup** button performs a complete, read-only check of the newest backup.

BackupCheckup downloads one available copy through Home Assistant's native backup agent, calculates a SHA-256 checksum, validates the backup metadata, and reads the outer archive plus every contained archive to the end. Protected backups are decrypted with Home Assistant's configured backup password.

An optional expert check can also run SQLite `PRAGMA integrity_check` against the included Home Assistant database.

The result is shown by `sensor.backup_checkup_integrity_status`. Corrupt or unreadable backups can also create a native Home Assistant Repair issue.

> [!IMPORTANT]
> A successful integrity check confirms that the backup is structurally readable and, when protected, decryptable. It is not a complete restore test and cannot guarantee that every integration, add-on, external service, or device will work after restoration.

### Optional automatic verification

BackupCheckup can automatically verify each newly detected backup. This is disabled by default because a full check may transfer and read several gigabytes and can temporarily increase disk, network, and CPU usage.

### Mobile notifications

BackupCheckup can send alerts to one or more smartphones or tablets registered through the Home Assistant Companion App.

Available notifications include:

- A newly detected backup problem
- A changed set of active problems
- An optional recovery message after all reported problems are resolved

Only Companion App mobile notification entities are shown in the selector. Repeated polling does not resend the same unchanged warning, and the **Send test notification** button lets you confirm the selected devices.

Mobile notifications are optional. Sensors, Repair issues, and dashboard cards continue to work without them.

### Selectable entity mode

Monitoring rules and visible entities are configured independently.

| Entity mode | Best for |
| --- | --- |
| **Standard mode** | Most users. Enables the main status, health, backup, integrity, analytics, and problem entities. |
| **Expert mode** | Advanced users. Enables all detailed schedule, checksum, database, manual-backup, diagnostic, and per-storage entities. |

You can switch modes later under **Settings → Devices & services → BackupCheckup → Configure**.

### Languages

English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish are included. Belgian users are covered by Dutch, French, and German.

## Installation

### HACS — recommended

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

1. Open HACS.
2. Add this repository as a custom repository of type **Integration**.
3. Install **BackupCheckup**.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Search for **BackupCheckup**.
7. Select a monitoring profile and an entity mode.

### Manual installation

Copy `custom_components/backup_checkup` to `/config/custom_components/backup_checkup`, restart Home Assistant, and add the integration through **Settings → Devices & services**.

## Configuration

BackupCheckup offers three monitoring profiles. The selected profile defines how strictly backups are evaluated, while the separate entity mode controls how much detail is visible.

| Monitoring profile | Best for |
| --- | --- |
| **Standard** | Most installations. Balanced monitoring with automatic size comparison. |
| **Secure** | Stricter monitoring with stronger age, size, and storage-redundancy expectations. |
| **Custom** | Full control over monitoring, analytics, integrity checks, Repairs, and notifications. |

For example, **Secure + Standard mode** applies stricter backup rules without filling Home Assistant with every technical entity.

### Mobile notification setup

During setup or later under **Settings → Devices & services → BackupCheckup → Configure**:

1. Enable **Mobile notifications**.
2. Select one or more Companion App devices.
3. Choose whether BackupCheckup should send a recovery message.
4. Save the options.
5. Press **Send test notification** on the BackupCheckup device.

Only enabled Home Assistant Companion App notification entities are listed. See the [troubleshooting guide](docs/troubleshooting.md) if a device is missing.

### Custom options

| Option | Purpose |
| --- | --- |
| Maximum backup age | Defines when a backup becomes too old. |
| Update interval | Controls how often the lightweight inventory check runs. |
| Size check mode | Uses automatic comparison, a fixed minimum, or no size check. |
| Maximum size drop | Defines how much smaller a comparable backup may be. |
| Required backup locations | Sets the minimum number of locations holding the newest backup. |
| Repair issues | Shows actionable backup problems under Home Assistant Repairs. |
| Analysis period | Defines the period used for backup analytics. |
| Automatically verify new backups | Runs a full integrity check when a new backup appears. |
| Database integrity check | Runs the optional expert SQLite database check. |
| Mobile notifications | Sends deduplicated alerts to selected mobile devices. |
| Notify on recovery | Sends a message when all previously reported problems are resolved. |

The database check is disabled by default and requires additional temporary storage roughly equal to the database size.

## Integrity states

| State | Meaning |
| --- | --- |
| Not checked | No complete integrity check has finished yet. |
| Checking | The backup is currently being downloaded and inspected. |
| Valid | The complete archive was read successfully. |
| Valid with warnings | The archive is readable, but a non-critical inconsistency was found. |
| Corrupt | The archive structure or optional database check failed. |
| Unreadable | The backup could not be downloaded or fully read. |
| Password required | The protected backup could not be decrypted with the available password. |

Normal Home Assistant cards and device pages display translated states. Developer Tools may show stable raw values such as `valid`, which is expected and useful for automations and templates.

The latest completed result and checksum are stored locally. Backup contents, passwords, names, and selected notification entity IDs are not included in exported diagnostics.

## Recommended dashboard

A ready-to-copy example is available in [`docs/examples/dashboard.yaml`](docs/examples/dashboard.yaml).

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

Built-in mobile notifications are the simplest option for most users. Home Assistant automations remain useful for custom channels, escalation rules, or advanced message formatting.

A complete example is available in [`docs/examples/automation.yaml`](docs/examples/automation.yaml).

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

BackupCheckup can create native Repair issues under **Settings → System → Repairs** and remove them automatically after recovery.

The diagnostics download includes health, integrity, storage, and privacy-safe notification information. Backup contents, passwords, names, and selected mobile entity IDs are excluded.

## Documentation

- [Entity reference](docs/entities.md)
- [Integrity verification details](docs/integrity.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Safe integrity test plan](docs/testing-2.0.md)
- [FAQ](docs/faq.md)
- [Dashboard example](docs/examples/dashboard.yaml)
- [Automation example](docs/examples/automation.yaml)
- [Changelog](CHANGELOG.md)

## Troubleshooting

Installation, notification, storage, integrity, size-unit, logging, diagnostics, update, and rollback guidance is available on the dedicated **[Troubleshooting page](docs/troubleshooting.md)**.

## Updating and removal

Install updates through HACS or replace the integration folder manually, then restart Home Assistant.

Removing the config entry also removes BackupCheckup's locally stored analytics, integrity result, and notification deduplication state. It does not delete any Home Assistant backups.

## License

MIT License
