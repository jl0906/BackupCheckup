# BackupCheckup

> **Backup health monitoring for Home Assistant**
>
> BackupCheckup checks whether your Home Assistant backups are available, recent,
> complete, plausible in size, stored on enough locations, and healthy over time.

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-1.5.1-blue.svg)
![License](https://img.shields.io/github/license/jl0906/BackupCheckup)

BackupCheckup reads the **actual backup inventory** from Home Assistant's native
backup manager. It does not depend on a separate automation or helper and notices
when a previously existing backup has been deleted.

Everything runs locally inside Home Assistant. No cloud service or external Python
package is required.

## Why BackupCheckup?

Creating backups is only half the job. A backup may be missing, too old, incomplete,
unusually small, or stored only on the same system it is meant to protect.

BackupCheckup detects problems such as:

- No backup is available.
- The newest backup is too old.
- An automatic backup failed or is overdue.
- The automatic schedule is missing or overdue.
- The backup manager or a storage location is unavailable.
- The newest backup is incomplete.
- The newest backup is unusually small.
- The newest backup is not stored on enough locations.

## Features

### Backup monitoring

- Counts all currently stored backups.
- Separates automatic backups from manual or other backups.
- Reports the newest backup, automatic backup, and manual backup.
- Reports backup ages and sizes.
- Keeps the automatic backup age as full completed days for a clean sensor value.
- Checks the native automatic-backup schedule and result sensors.

### Backup health checks

- Empty inventory and stale-backup detection.
- Failed and overdue automatic-backup detection.
- Automatic or fixed backup-size checking.
- Detection of incomplete backups with failed add-ons, folders, or storage agents.
- Redundancy checks across multiple backup locations.
- Central status, recommendation, and active-problem count.

### Intelligent backup analytics

- Transparent backup health score from `0` to `100`
- Human-readable health rating: Excellent, Good, Warning, or Critical
- Average backup size over a configurable analysis period
- Increasing, stable, or decreasing backup-size trend
- Longest interval between retained backups
- Observed automatic-backup success rate
- Consecutive automatic-backup failure counter
- Local persistence of automatic-backup outcomes

The health score is deterministic and exposes every deduction as a sensor attribute.
It does not use cloud services or artificial intelligence.

### Storage monitoring

Each detected Home Assistant backup storage agent is represented as its own device
with entities for:

- Backup count
- Newest backup
- Newest backup age
- Newest backup size
- Total stored backup size
- Storage problem state

### Home Assistant integration

- Guided **Standard**, **Secure**, and **Custom** profiles
- Native Config Flow and Options Flow
- Home Assistant Repair issues with automatic cleanup
- Diagnostics download for troubleshooting
- Manual **Refresh backup data** button
- Dashboard and automation ready
- English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish

Belgian users are covered by the Dutch, French, and German translations.

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

1. Copy `custom_components/backup_checkup` to
   `/config/custom_components/backup_checkup`.
2. Restart Home Assistant.
3. Add BackupCheckup under **Settings → Devices & services**.

## Configuration

BackupCheckup offers three monitoring profiles.

| Profile | Intended use |
| --- | --- |
| **Standard** | Recommended for most installations. Uses automatic size comparison and requires one storage location. |
| **Secure** | Uses stricter limits and expects the newest backup on at least two storage locations. |
| **Custom** | Exposes every threshold and notification setting. |

### Custom options

| Option | Description |
| --- | --- |
| Maximum backup age | Creates a problem after the configured number of days. |
| Update interval | Controls how often the actual backup inventory is read. |
| Size check mode | Automatic comparison, fixed minimum size, or disabled. |
| Fixed minimum size | Used only with fixed size checking. |
| Maximum size drop | Allowed reduction compared with recent comparable backups. |
| Required backup locations | Minimum number of locations containing the newest backup. |
| Repair notifications | Shows active backup problems under Home Assistant Repairs. |
| Analysis period | Number of days used for size, gap, and observed success-rate statistics. |

The automatic size mode compares the newest backup with up to five recent backups
of the same type. This means users do not need to know a suitable backup size in
advance.

### Health score

BackupCheckup starts at `100` points and subtracts documented values for active
problems such as stale, incomplete, suspiciously small, or non-redundant backups.
Repeated automatic failures and a reduced observed success rate can also lower the
score. Open the attributes of `sensor.backup_checkup_health_score` to see every
deduction.

| Score | Rating |
| --- | --- |
| 90–100 | Excellent |
| 75–89 | Good |
| 50–74 | Warning |
| 0–49 | Critical |

### Historical automatic-backup metrics

Home Assistant exposes only the latest automatic attempt and latest successful
automatic backup. BackupCheckup therefore starts its own small local outcome history
when version 1.5.0 is first run. The success-rate and consecutive-failure sensors do
not invent failures that occurred before tracking began. The history contains only
timestamps and result states and is removed when the integration entry is deleted.

## Recommended dashboard

A ready-to-copy example is available in
[`docs/examples/dashboard.yaml`](docs/examples/dashboard.yaml).

```yaml
type: entities
title: BackupCheckup
entities:
  - entity: sensor.backup_checkup_health_score
  - entity: sensor.backup_checkup_health_rating
  - entity: sensor.backup_checkup_status
  - entity: sensor.backup_checkup_recommendation
  - entity: sensor.backup_checkup_latest_backup
  - entity: sensor.backup_checkup_latest_backup_age
  - entity: sensor.backup_checkup_latest_backup_size
  - entity: sensor.backup_checkup_latest_backup_locations
  - entity: sensor.backup_checkup_size_trend
  - entity: sensor.backup_checkup_automatic_success_rate
  - entity: binary_sensor.backup_checkup_problem
  - entity: button.backup_checkup_refresh
```

## Automation example

The example below sends a notification when a new problem appears. A complete copy
is available in [`docs/examples/automation.yaml`](docs/examples/automation.yaml).

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
      message: >-
        {{ states('sensor.backup_checkup_recommendation') }}
mode: single
```

## Repairs

When enabled, BackupCheckup creates native Repair issues under
**Settings → System → Repairs**. Repair issues include a plain-language explanation
and suggested next step. They are removed automatically after the underlying problem
is resolved.

Repair issues can be disabled in the Custom profile without disabling any sensors.

## Diagnostics

Open the BackupCheckup integration page and choose **Download diagnostics** to export:

- Integration and Home Assistant versions
- Effective configuration
- Coordinator update state
- Health score, rating, deductions, active problems, and recommendation
- Backup inventory and intelligent analytics summary
- Automatic-backup schedule information
- Per-storage health information
- Sanitized details for the twenty newest backups

User-defined backup names and backup IDs are intentionally excluded.

## Entities

The complete entity reference, including default-enabled and diagnostic entities,
is available in [`docs/entities.md`](docs/entities.md).

## Troubleshooting

### Repair issue remains visible

Press **Refresh backup data** after correcting the problem. BackupCheckup also checks
again automatically at the configured update interval.

### Automatic schedule is reported as missing

Open **Settings → System → Backups** and confirm that automatic backups are enabled
and Home Assistant shows a next scheduled backup.

### A backup is reported as unusually small

Check free space on every storage location and inspect the native Home Assistant
backup log. Automatic mode compares only with recent backups of the same type. Use
the Custom profile to change the permitted size drop or disable size checking.

### Redundancy warning with only one storage location

Use the Standard profile or set **Required backup locations** to `1`. The Secure
profile intentionally expects at least two locations, for example local storage plus
a NAS or cloud backup agent.

### Storage location shown as unavailable

Check the storage connection, credentials, permissions, and free space. Then press
**Refresh backup data**.

More answers are available in [`docs/faq.md`](docs/faq.md).

## Updating and removal

### Update

Install the new version through HACS and restart Home Assistant. Existing entity IDs
and configuration entries are retained.

### Remove

1. Remove BackupCheckup under **Settings → Devices & services**.
2. Remove the integration through HACS or delete
   `/config/custom_components/backup_checkup`.
3. Restart Home Assistant.

## Documentation

- [Entity reference](docs/entities.md)
- [FAQ](docs/faq.md)
- [Dashboard example](docs/examples/dashboard.yaml)
- [Automation example](docs/examples/automation.yaml)
- [Screenshot contribution guide](docs/screenshots/README.md)
- [Changelog](CHANGELOG.md)

## License

BackupCheckup is released under the [MIT License](LICENSE).
