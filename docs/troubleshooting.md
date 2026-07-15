# BackupCheckup troubleshooting

This guide covers installation, configuration, mobile notifications, backup-size
units, integrity verification, storage locations, diagnostics, and safe rollback.

## Start with these checks

1. Confirm that Home Assistant is version **2026.3.0 or newer**.
2. Confirm that the complete integration folder exists at
   `/config/custom_components/backup_checkup`.
3. Confirm that `manifest.json` reports the expected version.
4. Restart Home Assistant after replacing Python files. Reloading the integration is
   not always sufficient after an update.
5. Open **Settings → System → Logs** and search for `backup_checkup`.
6. Open **Settings → Devices & services → BackupCheckup** and press
   **Refresh backup data**.

A successful refresh normally creates a debug line similar to:

```text
Finished fetching backup_checkup data ... (success: True)
```

The standard warning that a custom integration has not been tested by Home Assistant
is expected and is not itself an error.

## Integration does not load

### Verify the folder structure

The integration must be located directly at:

```text
/config/custom_components/backup_checkup/
```

Files such as `manifest.json`, `__init__.py`, `coordinator.py`, and `sensor.py` must
be inside that folder. An extra release folder level prevents discovery.

Correct:

```text
/config/custom_components/backup_checkup/manifest.json
```

Incorrect:

```text
/config/custom_components/BackupCheckup-2.1.2/custom_components/backup_checkup/
```

### Remove old parallel copies

Do not keep another folder such as `backup_checkup_old` inside `custom_components`
when it still contains a valid manifest with the same domain. Move backups outside
`custom_components` before restarting.

### Check the log traceback

Copy the complete traceback beginning with the first `custom_components.backup_checkup`
line. Errors from Hue, Petlibro, Petkit, Apple TV, or another integration do not
necessarily indicate a BackupCheckup problem.

## Mobile notification configuration

### No smartphones or tablets are listed

BackupCheckup deliberately lists only enabled `notify` entities supplied by Home
Assistant's `mobile_app` integration.

Check the following:

1. Install and sign in to the official Home Assistant Companion App on the device.
2. Allow notifications in the phone's operating-system settings.
3. In Home Assistant, open **Settings → Devices & services → Mobile App** and confirm
   that the phone or tablet is registered.
4. Open **Settings → Devices & services → Entities** and search for the device's
   `notify` entity.
5. Enable the entity when it is disabled in the entity registry.
6. Restart Home Assistant or reload the Mobile App integration, then reopen the
   BackupCheckup options.

Browser-only sessions, ordinary `device_tracker` entities, and notification services
from unrelated integrations are intentionally not shown.

### Mobile notifications cannot be enabled

At least one mobile target must be selected. BackupCheckup rejects the form when
notifications are enabled without a target.

### The test notification button is unavailable

The button becomes available only when:

- Mobile notifications are enabled, and
- At least one Companion App notify entity is selected.

Save the options and allow the integration to reload before testing.

### Test notification fails

1. Confirm that the selected `notify` entity is available.
2. Verify that the Companion App still has push permission.
3. Open the device in the Mobile App integration and check its connectivity.
4. Review **Settings → System → Logs** for
   `Unable to send BackupCheckup notification`.
5. Download BackupCheckup diagnostics and inspect `notifications.last_error`.

Re-select the device if its notify entity was renamed, removed, or recreated.

### No warning is sent for an existing problem

When notifications are newly enabled while problems already exist, BackupCheckup
sends one initial warning after the next successful refresh. Press **Refresh backup
data** to trigger that evaluation immediately.

### The same warning is not repeated

This is intentional. BackupCheckup stores the active problem signature and sends a
new warning only when the set of problems changes. This prevents a message at every
polling interval.

A recovery message is sent once when all previously reported problems are resolved
and **Notify when problems are resolved** is enabled.

### Notifications are duplicated

Check whether a separate Home Assistant automation also watches
`binary_sensor.backup_checkup_problem`. Disable either the built-in notifications or
the duplicate automation.

## Backup sizes still appear in bytes

Version 2.1 reports these sensors in MB:

- `sensor.backup_checkup_latest_backup_size`
- `sensor.backup_checkup_latest_automatic_backup_size`
- `sensor.backup_checkup_average_backup_size`

After updating:

1. Restart Home Assistant.
2. Open the affected entity's settings.
3. Remove a manually selected display unit when one is set.
4. Reload BackupCheckup or restart again.

BackupCheckup migrates the entity-registry unit to MB, but an explicit dashboard card
format or frontend cache may still temporarily show the previous unit.

The exact byte value remains available as the `size_bytes` attribute for diagnostics.

## Integrity verification

### Verification stays on Checking

A full check downloads and reads the complete backup. Large files, slow NAS storage,
or cloud-backed agents can require several minutes.

Check:

- Free space in Home Assistant's temporary directory
- Network connectivity to the selected storage location
- CPU and disk load
- Whether the storage agent can download the backup

Reloading or restarting BackupCheckup cancels the running task without modifying the
backup.

### Password required

The backup is protected but could not be decrypted with the password available from
Home Assistant.

1. Open Home Assistant's native backup settings.
2. Confirm that the configured emergency kit or backup password belongs to this
   backup.
3. Test the backup through Home Assistant's native backup interface.
4. Run the verification again.

BackupCheckup does not request, log, or permanently store a separate password.

### Corrupt

The outer archive, an inner archive, declared metadata, a contained file, or the
optional SQLite integrity check failed.

Recommended action:

1. Do not delete the affected backup immediately; retain it for diagnosis.
2. Verify another copy from a different storage location when available.
3. Create a new backup.
4. Verify the new backup.
5. Do not rely on the failed file as the only recovery point.

### Unreadable

The backup could not be downloaded or opened. Check the storage location,
permissions, network connectivity, and free temporary storage. An unreadable result
can indicate an agent or transfer problem rather than archive corruption.

### Valid with warnings

The complete archive was readable, but a non-fatal inconsistency was detected. Open
the integrity-status attributes and diagnostics to inspect the warning list.

### Database integrity check fails

The expert database check runs SQLite `PRAGMA integrity_check` against the included
Home Assistant database. A failure should be treated as serious even when the TAR
archives themselves are readable.

Create and verify a new backup. Investigate recorder/database health before relying
on older files.

### Not enough temporary space

A full verification needs enough temporary space for the downloaded backup. The
expert database check additionally extracts the database and may temporarily require
space close to the combined backup and database size.

Disable the database expert option or free space before retrying.

## Backup manager or storage problems

### Backup manager unavailable

Confirm that Home Assistant's native Backup integration is loaded and that the native
backup page opens. Restart Home Assistant when the backup manager remains unavailable.

### A storage location is unhealthy

1. Open Home Assistant's native backup settings.
2. Verify the NAS, network share, or cloud-agent connection.
3. Confirm credentials and write/read permissions.
4. Check available space on the destination.
5. Press **Refresh backup data** after the location recovers.

### Redundancy warning despite existing backups

Redundancy is evaluated for the **newest backup**, not merely for any old file on
each storage location. Confirm that the same newest backup has been copied to the
required number of locations.

## Unexpected health score or status

Open the attributes of `sensor.backup_checkup_health_score`. The `deductions`
attribute lists every applied penalty. Multiple conditions can overlap.

The central status shows the highest-priority problem, while `active_problems` and
the problem-count sensor can expose simultaneous conditions.

## Integrity status shows `valid` instead of a translated value

BackupCheckup exposes the integrity result as an enum with stable raw states for
automations. In normal entity cards and device views, Home Assistant should translate
`valid`, `corrupt`, `unreadable`, and the other states into the configured interface
language.

After updating:

1. Restart Home Assistant completely.
2. Reload the browser with `Ctrl+F5` or clear the Companion App frontend cache.
3. Open the entity from **Settings → Devices & services → BackupCheckup**.
4. Remember that **Developer Tools → States** intentionally shows the raw state used
   by templates and automations.

Version 2.1.2 also repairs missing enum translation metadata on existing
BackupCheckup entities during startup.

## Too many or too few entities are enabled

Open **Settings → Devices & services → BackupCheckup → Configure** and select an
entity mode independently of the monitoring profile:

- **Standard mode** enables the main monitoring, integrity, analytics, and global
  problem entities.
- **Expert mode** enables all BackupCheckup entities, including per-storage and
  detailed diagnostic entities.

Changing the mode updates entities disabled by BackupCheckup. An entity explicitly
disabled by the user remains disabled.

## Logs and diagnostics

### Enable debug logging

Add this temporarily to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.backup_checkup: debug
```

Restart Home Assistant, reproduce the problem, then download the relevant log.
Remove debug logging afterward to avoid unnecessary log volume.

### Download diagnostics

Open:

**Settings → Devices & services → BackupCheckup → three-dot menu → Download diagnostics**

Diagnostics intentionally exclude:

- Backup names and IDs
- Backup contents
- Backup passwords
- Selected notification entity IDs

They include sanitized configuration, counts, status details, integrity results, and
the latest notification error.

## Updating safely

1. Create a native Home Assistant backup.
2. Stop replacing files until the previous copy operation has completed.
3. Replace the entire `backup_checkup` folder, not only selected Python files.
4. Restart Home Assistant.
5. Check the integration version and logs.
6. Press **Refresh backup data**, **Send test notification**, and optionally
   **Verify latest backup**.

## Roll back to an earlier release

1. Download the previous release.
2. Remove `/config/custom_components/backup_checkup`.
3. Copy the previous integration folder into place.
4. Restart Home Assistant.

Do not delete the BackupCheckup config entry solely for a rollback. Keeping it
preserves entity IDs and existing dashboard references. Newer stored analysis or
notification state is isolated and does not alter Home Assistant backup files.

## Reporting a bug

Include:

- BackupCheckup version
- Home Assistant version and installation type
- Exact steps to reproduce
- Relevant `backup_checkup` log traceback
- Sanitized diagnostics
- Whether the problem occurs with manual refresh, integrity verification, or mobile
  notification testing

Do not publish backup files, passwords, emergency-kit data, or unredacted private
configuration.
