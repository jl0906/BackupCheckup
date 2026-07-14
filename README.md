# BackupCheckup

BackupCheckup is a local Home Assistant custom integration that reads the **actual backup inventory** from Home Assistant's backup manager. It does not depend on a separate automation or helper and it detects when a backup file has subsequently been deleted.

Version: **1.2.0**

## Features

- Counts all currently stored backups across configured backup agents.
- Separates automatic backups from manual or other backups.
- Exposes the latest backup timestamps and their age.
- Reports the automatic backup age in fully completed days while retaining the precise age internally for status calculations.
- Detects an empty backup inventory, stale backups, failed automatic attempts, a missing or overdue automatic schedule, unavailable backup manager data, and storage-agent errors.
- Configurable maximum backup age and polling interval.
- English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish translations.
- Belgian users are covered by the available Dutch, French, and German translations.
- Checks the latest backup size against a configurable minimum and the previous comparable backup.
- Detects partial backups with failed add-ons, folders, or storage agents.
- Creates separate monitoring entities for every detected backup storage agent.
- Checks whether the latest backup is stored on a configurable minimum number of locations.
- No cloud connection and no external Python dependency.

## Installation with HACS

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

1. Add this repository to HACS as a custom repository of type **Integration**.
2. Install **BackupCheckup**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search for **BackupCheckup**.

## Manual installation

Copy `custom_components/backup_checkup` into your Home Assistant `/config/custom_components/` directory, restart Home Assistant, and add BackupCheckup from **Settings → Devices & services**.

## Health-check options

The integration options allow you to configure the maximum backup age, polling interval, minimum backup size, maximum permitted size drop compared with the previous comparable backup, and the minimum number of storage locations required for redundancy. Set the minimum backup size to `0` to disable the absolute size threshold.

## Default entities

### Sensors

- `sensor.backup_checkup_status`
- `sensor.backup_checkup_stored_backups`
- `sensor.backup_checkup_automatic_backups`
- `sensor.backup_checkup_manual_backups`
- `sensor.backup_checkup_latest_backup`
- `sensor.backup_checkup_latest_automatic_backup`
- `sensor.backup_checkup_latest_manual_backup`
- `sensor.backup_checkup_latest_backup_age`
- `sensor.backup_checkup_automatic_backup_age`
- `sensor.backup_checkup_manual_backup_age`
- `sensor.backup_checkup_last_automatic_attempt`
- `sensor.backup_checkup_last_successful_automatic_event`
- `sensor.backup_checkup_next_automatic_backup`
- `sensor.backup_checkup_backup_manager_state`
- `sensor.backup_checkup_latest_backup_size`
- `sensor.backup_checkup_latest_automatic_backup_size`
- `sensor.backup_checkup_latest_backup_size_change`
- `sensor.backup_checkup_latest_backup_result`
- `sensor.backup_checkup_latest_backup_locations`

For every detected storage agent, BackupCheckup also creates sensors for backup count, latest backup, latest backup age, latest backup size, and total stored backup size.

### Binary sensors

- `binary_sensor.backup_checkup_problem`
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

A separate problem binary sensor is also created for every detected storage agent.

The default automatic-backup rule is considered overdue when the latest automatic backup is older than the configured maximum age and no newer manual or other backup still exists. The integration also separately reports when the newest backup of any type is too old.

## Automations and dashboards

BackupCheckup is intentionally independent. Use its sensors and binary sensors in any dashboard, automation, notification, or external monitoring solution.

Example:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.backup_checkup_problem
    to: "on"
actions:
  - action: notify.notify
    data:
      message: >-
        BackupCheckup reports: {{ states('sensor.backup_checkup_status') }}
```

## License

MIT
