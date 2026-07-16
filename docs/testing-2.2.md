# Safe test plan for BackupCheckup 2.2

Use this sequence after installing the update. Do not intentionally damage your only
backup copy.

## 1. Upgrade and inventory test

1. Replace the integration files and restart Home Assistant.
2. Open **Settings → Devices & services → BackupCheckup**.
3. Confirm that the existing status, age, size, health score, and problem entities still work.
4. Check the Home Assistant log for `custom_components.backup_checkup` errors.

Expected result: the normal lightweight coordinator refresh finishes successfully.

## 2. Manual archive verification

1. Keep the database expert option disabled initially.
2. Press **Verify latest backup**.
3. Watch `sensor.backup_checkup_integrity_status`.

Expected sequence:

```text
Not checked → Checking → Valid
```

`Valid with warnings` can also be correct; inspect the sensor attributes for the
warning code. `Aborted` means a configured safety limit stopped the test and must not
be interpreted as corruption.

## 3. Encryption test

If the newest regular backup is protected, repeat the manual check and confirm:

- `protected: true` appears in the integrity-status attributes;
- the result becomes `Valid` or `Valid with warnings`;
- no password appears in logs, diagnostics, or entity attributes.

A `Password required` result means the backup could not be decrypted with the
password currently available from Home Assistant.

## 4. Automatic verification test

1. Open BackupCheckup options.
2. Select **Custom**.
3. Enable **Automatically verify each new backup**.
4. Create one new native Home Assistant backup.
5. Wait for BackupCheckup's next inventory refresh.

Expected result: the new backup is checked once. Repeated normal polling must not
re-download the same backup.

## 5. Database expert test

1. Confirm that enough temporary disk space is available.
2. Enable **Run database integrity check (expert)**.
3. Press **Verify latest backup** again.
4. Enable the disabled entity
   `sensor.backup_checkup_database_integrity_status` if desired.

Expected result for a backup containing the database: `Passed`.

Expected result when the database was intentionally excluded: `Not found` without a
corruption Repair issue.


## 6. Safety-limit and authorization test

1. Confirm that a non-administrator account cannot invoke
   `backup_checkup.verify_latest_backup`.
2. As an administrator, start a check and immediately try to start a second one.
3. After completion, try again before the configured manual cooldown expires.
4. In a test installation, temporarily set the maximum download below the newest
   backup's reported size.

Expected results: unauthorized, overlapping, and cooldown-protected calls are rejected.
The deliberately undersized limit produces `Aborted` with
`error_code: download_size_limit`, not `Corrupt`. Restore the normal limit afterward.

## 7. Privacy and cleanup test

1. Keep **Expose detailed backup metadata** disabled.
2. Inspect `sensor.backup_checkup_latest_backup_result` and downloaded diagnostics.
3. Confirm that the user-defined backup name and native backup ID are absent and a
   `backup_reference` is present.
4. Confirm that no raw third-party exception message appears in entity attributes.
5. Review Repairs for a temporary-data cleanup warning after the test.

Expected result: privacy-safe metadata is used and no cleanup warning remains after a
normal run.

## 8. Repair behavior

Do not corrupt a production backup merely to test Repairs. A corrupt or unreadable
result will automatically create an issue under **Settings → System → Repairs**. The
issue is removed after the newest regular backup has a successful integrity result or when
the failed result no longer applies to the current newest regular backup.

For destructive corruption testing, use only a separate Home Assistant test instance
and a disposable backup copy.

## Useful diagnostic attributes

The integrity-status sensor provides:

- `applies_to_latest_backup`
- `checked_at`
- `backup_reference`
- `storage_location`
- `archive_count`
- `file_count`
- `protected`
- `database_status`
- `warnings`
- `error_code`

The full SHA-256 value is available through the disabled diagnostic entity
`sensor.backup_checkup_integrity_checksum`.

## 9. App-update backup classification

1. Note the current value of the latest regular backup, its age, and its size.
2. Update a Home Assistant app with the Supervisor backup-before-update option enabled.
3. Refresh BackupCheckup after the technical app backup appears.
4. Inspect the stored-backups and latest-backup-size sensor attributes.

Expected results:

- The app-update backup increases `inventory_backup_count` and
  `ignored_update_backup_count`.
- It does not increase the monitored backup state.
- It does not replace the latest regular backup or reset its age.
- It does not trigger a size warning or automatic integrity check.
- `comparable_backup_count` includes only older backups with the same scope and
  automatic/manual origin.
