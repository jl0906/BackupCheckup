# BackupCheckup FAQ

## Does BackupCheckup create backups?

No. BackupCheckup monitors Home Assistant's native backup system. Backup creation,
retention, restore, and deletion remain controlled by Home Assistant.

## Does it require an automation or helper?

No. Monitoring begins after the integration is added through the user interface.
Automations are optional and can use the provided sensors.

## Does it work with NAS and cloud backup locations?

Yes, provided the storage location is exposed to Home Assistant as a native backup
agent. Every detected agent receives its own monitoring device.

## Why does the Secure profile report a redundancy problem?

The Secure profile requires the newest backup on at least two storage locations.
Use local storage plus another backup agent, or choose Standard/Custom if one location
is intentional.

## How does automatic size checking work?

The newest backup is compared with up to five recent backups of the same type
(automatic or manual). The median is used to reduce false warnings from one unusual
older backup.

## Why is the automatic backup age an integer?

It intentionally shows fully completed days. It remains `0` until a complete 24
hours has elapsed, then changes to `1`. BackupCheckup keeps the precise value
internally for health calculations.

## Does BackupCheckup upload any data?

No. The integration has no cloud connection and no external dependency.

## What is included in diagnostics?

Diagnostics include configuration, status, storage summaries, and sanitized recent
backup metadata. User-defined backup names and backup IDs are excluded.

## Can Repair notifications be disabled?

Yes. Select the Custom profile and disable **Show repair notifications**. Sensors and
binary sensors continue working normally.
