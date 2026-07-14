# Security policy

## Reporting a vulnerability

Do not publish security-sensitive details, backup contents, passwords, checksums,
or diagnostic exports in a public issue.

Report a suspected vulnerability privately through GitHub's security advisory
feature for this repository. Include the affected version, reproduction steps, and
the potential impact.

## Backup data handling

BackupCheckup 2.0 can download the newest backup to Home Assistant's temporary local
storage for a read-only integrity check. The temporary backup and any extracted
SQLite database are removed when the check finishes.

The integration may use Home Assistant's configured backup password in memory to
decrypt protected archives. It never logs or persists that password.

The last SHA-256 checksum and privacy-safe result metadata are stored in Home
Assistant's private integration storage. Diagnostics exclude user-defined backup
names and backup IDs.
