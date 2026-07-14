# Backup integrity verification

BackupCheckup 2.x performs a non-destructive structural verification of the newest
Home Assistant backup.

## Verification process

1. Select an available backup copy, preferring local storage when available.
2. Download the complete file through the native Home Assistant backup agent.
3. Calculate SHA-256 while downloading.
4. Compare the downloaded byte count with the size reported by the storage agent.
5. Open the outer archive and read every member.
6. Parse `backup.json` and compare declared content with contained inner archives.
7. Open every inner TAR/TAR.GZ archive and read every regular file completely.
8. For protected backups, decrypt every inner archive with Home Assistant's configured backup password.
9. Optionally run SQLite `PRAGMA integrity_check` on `home-assistant_v2.db`.
10. Remove the temporary download and any temporarily extracted database.

No content is restored, edited, uploaded, or retained.

## SHA-256

The checksum identifies the exact downloaded byte sequence. BackupCheckup stores the
last completed checksum locally. If the same backup ID later produces a different
checksum, the result becomes **Valid with warnings** and contains the warning
`checksum_changed`.

A checksum alone does not prove that an archive is valid. BackupCheckup combines it
with complete archive reading.

## Encryption

BackupCheckup uses the backup password already configured in Home Assistant. It does
not expose, log, or persist that password. If a protected backup cannot be decrypted,
the result is **Password required** rather than **Corrupt**.

## Database expert check

When enabled, the included `home-assistant_v2.db` is copied to temporary storage and
opened read-only. SQLite's full `PRAGMA integrity_check` is executed.

Possible database states:

- `not_checked`
- `passed`
- `failed`
- `not_found`

This option can require significant temporary disk space and processing time.

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
