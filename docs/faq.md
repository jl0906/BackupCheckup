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

## How is the backup health score calculated?

The score starts at 100 and applies fixed deductions for active problems. Examples
include an old, incomplete, suspiciously small, or non-redundant backup. A low
observed automatic success rate and repeated automatic failures can add further
deductions. The complete deduction list is available as an attribute of the health
score sensor. The calculation is local and deterministic.

## Why is the automatic success rate unknown after updating?

Home Assistant exposes the latest automatic attempt and latest successful automatic
backup, but not a full historical attempt list. BackupCheckup begins recording
outcomes locally when version 1.5.0 first runs. The success rate becomes available
after at least one attempt has been resolved as successful or failed.

## What does the backup-size trend compare?

BackupCheckup uses up to six recent backups from the configured analysis period. It
prefers automatic backups when enough comparable entries exist. The median of the
newer group is compared with the older group; changes within five percent are shown
as stable.
