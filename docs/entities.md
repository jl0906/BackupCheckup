# BackupCheckup entity reference

## Entity modes

The monitoring profile and entity mode are separate settings.

- **Standard mode** enables the main status, health, integrity, backup, analytics,
  and global problem entities used by most dashboards and automations.
- **Expert mode** enables every entity, including detailed schedule, checksum,
  database, manual-backup, and per-storage-location diagnostics.

Changing the mode under **Settings → Devices & services → BackupCheckup → Configure**
applies the selected preset. Entities explicitly disabled by the user stay disabled.

## Default-enabled main entities

| Entity | Purpose |
| --- | --- |
| `sensor.backup_checkup_health_score` | Deterministic backup health score from 0 to 100 |
| `sensor.backup_checkup_status` | Highest-priority current backup status |
| `sensor.backup_checkup_recommendation` | Recommended next action |
| `sensor.backup_checkup_stored_backups` | Number of retained regular backups used for monitoring |
| `sensor.backup_checkup_latest_backup` | Timestamp of the newest regular backup |
| `sensor.backup_checkup_latest_backup_age` | Age of the newest regular backup in days |
| `sensor.backup_checkup_latest_backup_size` | Reported size of the newest regular backup in MB |
| `sensor.backup_checkup_integrity_status` | Result of the full integrity verification |
| `binary_sensor.backup_checkup_problem` | On when at least one monitored problem is active |
| `button.backup_checkup_verify_latest_backup` | Starts a full read-only check of the newest regular backup |
| `button.backup_checkup_refresh` | Immediately refreshes the lightweight backup inventory |
| `button.backup_checkup_test_notification` | Sends a test message to the configured Companion App devices |

## Mobile notification behavior

Mobile notifications are configured in the integration options. The selector is
filtered to enabled `notify` entities created by the Home Assistant Companion App.
One or more smartphones or tablets can be selected.

BackupCheckup sends a message when the active problem set first appears or changes.
It does not resend an unchanged problem at every polling interval. An optional
recovery message is sent when all previously reported problems are resolved.

The selected entity IDs are not exposed in diagnostics. Only the target count and a
privacy-safe last error are included.

## Technical app-update backups

Home Assistant Supervisor can create a small app-only backup before updating an app.
BackupCheckup recognizes these snapshots through the `supervisor.addon_update`
metadata marker. They remain visible in inventory diagnostics and contribute to total
stored bytes, but are excluded from backup age, health, redundancy, size analytics,
and automatic integrity verification.

The stored-backups sensor exposes `inventory_backup_count` and
`ignored_update_backup_count` attributes so the difference remains transparent.

## Integrity entities

| Entity | Default | Purpose |
| --- | --- | --- |
| `sensor.backup_checkup_integrity_status` | Enabled | `not_checked`, `checking`, `valid`, `valid_with_warnings`, `corrupt`, `unreadable`, `password_required`, or `aborted` |
| `sensor.backup_checkup_last_integrity_check` | Standard | Timestamp of the last completed check |
| `sensor.backup_checkup_integrity_checksum` | Disabled | Stored SHA-256 checksum of the downloaded backup |
| `sensor.backup_checkup_verified_backup_size` | Disabled | Number of downloaded and verified megabytes |
| `sensor.backup_checkup_integrity_check_duration` | Disabled | Duration of the last complete check |
| `sensor.backup_checkup_database_integrity_status` | Disabled | SQLite expert-check result |
| `binary_sensor.backup_checkup_backup_integrity_problem` | Standard | On when the newest regular backup is corrupt or unreadable |

The integrity-status attributes include the check time, a privacy-safe backup
reference, selected storage location, archive count, file count, encryption state,
database result, warnings, and a privacy-safe error code. An `aborted` state means a
configured safety budget stopped the check and is not treated as corruption.

`sensor.backup_checkup_latest_backup_result` exposes only a backup reference and
aggregate failure counts by default. The Custom-profile option **Expose detailed
backup metadata** adds the native backup name, ID, and detailed failure lists for
users who explicitly need them in automations.

## Additional backup sensors

| Entity | Default | Purpose |
| --- | --- | --- |
| `sensor.backup_checkup_health_rating` | Standard | Excellent, Good, Warning, or Critical rating |
| `sensor.backup_checkup_problem_count` | Standard | Number of simultaneously active problems |
| `sensor.backup_checkup_automatic_backups` | Standard | Number of automatic backups |
| `sensor.backup_checkup_manual_backups` | Disabled | Number of manual or other backups |
| `sensor.backup_checkup_latest_automatic_backup` | Standard | Timestamp of the newest automatic backup |
| `sensor.backup_checkup_latest_manual_backup` | Disabled | Timestamp of the newest manual or other backup |
| `sensor.backup_checkup_automatic_backup_age` | Standard | Automatic-backup age in fully completed days |
| `sensor.backup_checkup_manual_backup_age` | Disabled | Manual-backup age in days |
| `sensor.backup_checkup_latest_automatic_backup_size` | Standard | Size of the newest automatic backup in MB |
| `sensor.backup_checkup_latest_backup_size_change` | Disabled | Change from the previous backup with the same origin and content scope |
| `sensor.backup_checkup_latest_backup_result` | Standard | `complete`, `partial`, or `unknown` |
| `sensor.backup_checkup_latest_backup_locations` | Standard | Number of locations holding the newest regular backup |
| `sensor.backup_checkup_last_automatic_attempt` | Disabled | Latest native automatic attempt |
| `sensor.backup_checkup_last_successful_automatic_event` | Disabled | Latest successful native automatic event |
| `sensor.backup_checkup_next_automatic_backup` | Disabled | Next native automatic backup schedule |
| `sensor.backup_checkup_backup_manager_state` | Disabled | Native backup manager state |

## Analytics entities

| Entity | Default | Purpose |
| --- | --- | --- |
| `sensor.backup_checkup_size_trend` | Standard | Increasing, stable, or decreasing sizes for the latest comparable backup scope |
| `sensor.backup_checkup_average_backup_size` | Standard | Average size in MB for the latest comparable backup scope |
| `sensor.backup_checkup_longest_backup_gap` | Disabled | Longest observed gap between retained backups |
| `sensor.backup_checkup_automatic_success_rate` | Standard | Locally observed automatic success rate |
| `sensor.backup_checkup_consecutive_automatic_failures` | Standard | Consecutive locally resolved failures |

## Detailed problem binary sensors

Standard mode enables the global detailed problem sensors so automations can react
to specific causes. `binary_sensor.backup_checkup_required_location_missing` and all
per-storage problem sensors remain Expert-only because they duplicate higher-level
status information.

- `binary_sensor.backup_checkup_no_backup`
- `binary_sensor.backup_checkup_backup_stale`
- `binary_sensor.backup_checkup_automatic_backup_overdue`
- `binary_sensor.backup_checkup_automatic_backup_failed`
- `binary_sensor.backup_checkup_automatic_schedule_missing`
- `binary_sensor.backup_checkup_automatic_schedule_overdue`
- `binary_sensor.backup_checkup_backup_manager_unavailable`
- `binary_sensor.backup_checkup_storage_error`
- `binary_sensor.backup_checkup_backup_size_suspicious`
- `binary_sensor.backup_checkup_latest_backup_incomplete`
- `binary_sensor.backup_checkup_backup_not_redundant`
- `binary_sensor.backup_checkup_required_location_missing`
- `binary_sensor.backup_checkup_backup_integrity_problem`

## Storage location devices

BackupCheckup creates a separate device for each detected native backup storage
agent. Its detailed entities are enabled in Expert mode and disabled in Standard mode:

- Regular monitored backup count, with inventory and ignored-update counts in attributes
- Latest regular backup timestamp
- Latest backup age
- Latest backup size
- Total stored backup size
- Storage-location problem binary sensor

This keeps the main device compact while retaining per-location troubleshooting.
Entity IDs use a normalized agent ID, for example:

```text
sensor.backup_checkup_local_latest_backup
binary_sensor.backup_checkup_local_problem
```

## Health-score deductions

| Condition | Deduction |
| --- | ---: |
| No backup available | 100 |
| Newest backup corrupt or unreadable | 50 |
| Backup manager unavailable | 50 |
| Backup too old | 25 |
| Latest backup incomplete | 25 |
| Latest automatic backup failed | 20 |
| Storage error | 20 |
| Backup unusually small | 15 |
| Backup not redundant | 15 |
| Automatic backup overdue | 15 |
| Automatic schedule missing | 10 |
| Automatic schedule overdue | 10 |
| Required location unhealthy | 10 |
| Observed success rate below 95% / 80% / 60% | 5 / 12 / 20 |
| Consecutive automatic failures | 5 each, maximum 15 |

Deductions can overlap. The final score cannot fall below `0`.
