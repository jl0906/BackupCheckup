# BackupCheckup entity reference

Entity IDs shown below are the default IDs for the main BackupCheckup device.
Home Assistant may preserve a previously customized entity ID after an update.

## Main sensors

| Entity | Purpose | Default |
| --- | --- | --- |
| `sensor.backup_checkup_status` | Highest-priority overall backup health state | Enabled |
| `sensor.backup_checkup_recommendation` | Suggested next action | Enabled |
| `sensor.backup_checkup_problem_count` | Number of active problems; problem keys are available as an attribute | Enabled |
| `sensor.backup_checkup_stored_backups` | Total number of stored backups | Enabled |
| `sensor.backup_checkup_latest_backup` | Timestamp of the newest backup | Enabled |
| `sensor.backup_checkup_latest_automatic_backup` | Timestamp of the newest automatic backup | Enabled |
| `sensor.backup_checkup_latest_backup_age` | Precise age of the newest backup in days | Enabled |
| `sensor.backup_checkup_automatic_backup_age` | Age of the newest automatic backup in fully completed days | Enabled |
| `sensor.backup_checkup_latest_backup_size` | Size of the newest backup | Enabled |
| `sensor.backup_checkup_latest_automatic_backup_size` | Size of the newest automatic backup | Enabled |
| `sensor.backup_checkup_latest_backup_result` | `complete`, `partial`, or `unknown` | Enabled |
| `sensor.backup_checkup_latest_backup_locations` | Number of locations containing the newest backup | Enabled |

## Diagnostic sensors

These entities are useful for detailed dashboards or troubleshooting. Some are
disabled by default and can be enabled from the entity registry.

| Entity | Purpose |
| --- | --- |
| `sensor.backup_checkup_automatic_backups` | Number of automatic backups |
| `sensor.backup_checkup_manual_backups` | Number of manual or other backups |
| `sensor.backup_checkup_latest_manual_backup` | Timestamp of the newest manual or other backup |
| `sensor.backup_checkup_manual_backup_age` | Age of the newest manual or other backup |
| `sensor.backup_checkup_latest_backup_size_change` | Percentage change from the previous comparable backup |
| `sensor.backup_checkup_last_automatic_attempt` | Last native automatic backup attempt |
| `sensor.backup_checkup_last_successful_automatic_event` | Last successful native automatic backup event |
| `sensor.backup_checkup_next_automatic_backup` | Next native automatic backup schedule |
| `sensor.backup_checkup_backup_manager_state` | Native Home Assistant backup manager state |

## Main binary sensors

| Entity | Turns on when |
| --- | --- |
| `binary_sensor.backup_checkup_problem` | At least one monitored problem is active |
| `binary_sensor.backup_checkup_no_backup` | No backup exists |
| `binary_sensor.backup_checkup_backup_stale` | The newest backup exceeds the configured age |
| `binary_sensor.backup_checkup_automatic_backup_overdue` | No sufficiently recent automatic backup exists |
| `binary_sensor.backup_checkup_automatic_backup_failed` | The latest automatic attempt is newer than the latest success |
| `binary_sensor.backup_checkup_automatic_schedule_missing` | Home Assistant reports no next automatic backup |
| `binary_sensor.backup_checkup_automatic_schedule_overdue` | The reported next automatic backup is more than six hours in the past |
| `binary_sensor.backup_checkup_backup_manager_unavailable` | The native backup manager state is unavailable or unknown |
| `binary_sensor.backup_checkup_storage_error` | Home Assistant reports an error from a backup agent |
| `binary_sensor.backup_checkup_backup_size_suspicious` | The configured size rule is violated |
| `binary_sensor.backup_checkup_latest_backup_incomplete` | Add-ons, folders, or storage agents failed in the newest backup |
| `binary_sensor.backup_checkup_backup_not_redundant` | The newest backup exists on fewer locations than required |
| `binary_sensor.backup_checkup_required_location_missing` | A location holding the newest backup currently reports a problem |

## Storage location devices

BackupCheckup creates a separate device for every detected Home Assistant backup
storage agent. The agent ID is included in the device name.

Each device can provide:

- Backup count
- Latest backup timestamp
- Latest backup age
- Latest backup size
- Total stored backup size
- Problem binary sensor

Entity IDs use the normalized storage agent ID, for example:

```text
sensor.backup_checkup_local_latest_backup
binary_sensor.backup_checkup_local_problem
```

## Button

| Entity | Action |
| --- | --- |
| `button.backup_checkup_refresh` | Immediately reads and evaluates the native backup inventory |
