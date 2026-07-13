# BackupCheckup

BackupCheckup is a local Home Assistant custom integration that reads the **actual backup inventory** from Home Assistant's backup manager. It does not depend on a separate automation or helper and it detects when a backup file has subsequently been deleted.

Version: **1.0.0**

## Features

- Counts all currently stored backups across configured backup agents.
- Separates automatic backups from manual or other backups.
- Exposes the latest backup timestamps and their age.
- Detects an empty backup inventory, stale backups, failed automatic attempts, a missing or overdue automatic schedule, unavailable backup manager data, and storage-agent errors.
- Configurable maximum backup age and polling interval.
- German and English translations.
- No cloud connection and no external Python dependency.

## Installation with HACS

1. Add this repository to HACS as a custom repository of type **Integration**.
2. Install **BackupCheckup**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search for **BackupCheckup**.

## Manual installation

Copy `custom_components/backup_checkup` into your Home Assistant `/config/custom_components/` directory, restart Home Assistant, and add BackupCheckup from **Settings → Devices & services**.

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
