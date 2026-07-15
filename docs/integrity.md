# Backup integrity verification

BackupCheckup 2.2 performs a non-destructive structural verification of the newest
Home Assistant backup with explicit resource, privacy, and authorization safeguards.

## Verification process

1. Select an available backup copy, preferring local storage when available.
2. Validate the reported size and available temporary disk space.
3. Download the complete file through the native Home Assistant backup agent while
   enforcing the configured download-size and overall-time limits.
4. Calculate SHA-256 while downloading and compare the byte count with the size
   reported by the storage agent.
5. Read `backup.json` with a fixed metadata-size limit.
6. Stream the outer archive without retaining its complete member list in memory.
7. Validate declared content, member paths, the archive-member count, and the total
   expanded byte count.
8. Stream every regular file in every inner TAR/TAR.GZ archive to the end.
9. For protected backups, decrypt every inner archive with Home Assistant's configured
   backup password.
10. Optionally copy the included database to a private temporary file and run SQLite
    `PRAGMA integrity_check` with a cooperative database deadline.
11. Remove the private temporary directory and create a Repair issue if cleanup fails.

No content is restored, edited, uploaded, or deliberately retained.

## Safety limits

The Custom profile exposes these limits:

| Limit | Default | Purpose |
| --- | ---: | --- |
| Maximum verification download | 50 GB | Stops downloading an unexpectedly large backup. |
| Maximum expanded archive size | 250 GB | Limits decompressed/expanded bytes read across archive members. |
| Overall verification timeout | 30 minutes | Bounds the complete download and archive check. |
| Database timeout | 10 minutes | Bounds the optional SQLite operation. |
| Manual verification cooldown | 10 minutes | Prevents repeated expensive administrator-triggered checks. |

Additional fixed safeguards limit `backup.json` to 2 MiB and one verification to
1,000,000 archive members. BackupCheckup also keeps at least 1 GiB or 10 percent of
the temporary filesystem free, whichever reserve is larger.

When a safety limit is reached, the integrity state is **Aborted** and a stable error
code identifies the reason. An aborted check is inconclusive; it is not classified as
a corrupt backup.

Common codes include:

- `download_size_limit`
- `expanded_size_limit`
- `archive_member_limit`
- `metadata_size_limit`
- `insufficient_free_space`
- `verification_timeout`
- `database_timeout`

## Authorization and cooldown

The **Verify latest backup** button calls the administrator-only
`backup_checkup.verify_latest_backup` action. The coordinator independently enforces
that no other check is running and that the manual cooldown has expired. Automatic
verification observes all resource limits but is not blocked by the manual cooldown.

## SHA-256

The checksum identifies the exact downloaded byte sequence. BackupCheckup stores the
last completed checksum locally. If the same backup later produces a different
checksum, the result becomes **Valid with warnings** and contains the warning
`checksum_changed`.

A checksum alone does not prove that an archive is valid. BackupCheckup combines it
with complete archive reading.

## Encryption

BackupCheckup uses the backup password already configured in Home Assistant. It does
not expose, log, or persist that password. If a protected backup cannot be decrypted,
the result is **Password required** rather than **Corrupt**.

## Temporary data

Verification uses an owner-only temporary directory (`0700`) and owner-only backup
and database files (`0600`) on POSIX systems. Normal completion removes the complete
directory tree. At startup, BackupCheckup checks for old prefixed verification
directories, removes eligible stale data, and keeps a Repair issue active when
sensitive temporary data may remain.

## Privacy

Normal entity attributes and diagnostics do not expose the user-defined backup name
or native backup ID. They use a stable installation-local `backup_reference` instead.
The Custom profile contains an explicit, disabled-by-default option for exposing full
metadata in the newest-backup result entity.

Errors from backup agents and notification services are mapped to stable categories
such as `timeout`, `permission_denied`, or `connection_error`. Raw third-party
exception messages are not copied into entities or diagnostics.

## Database expert check

When enabled, the included `home-assistant_v2.db` is copied to temporary storage and
opened read-only. SQLite's full `PRAGMA integrity_check` is executed with a progress
handler that interrupts the operation when the configured database or overall
deadline expires.

Possible database states:

- `not_checked`
- `passed`
- `failed`
- `not_found`

This option can require significant temporary disk space and processing time and
remains disabled by default.

## Limitations

A successful result means that the selected backup copy was downloaded completely,
its archives were structurally readable, its encrypted contents were decryptable,
and the optional SQLite check passed.

It does **not** perform a restore and therefore cannot prove that:

- every integration or add-on starts successfully;
- external services, credentials, devices, or network shares remain available;
- a different Home Assistant version can restore every component;
- the restored system behaves exactly like the source system.

A fully isolated test restore remains the strongest recovery test.
