# BackupCheckup FAQ

## Does BackupCheckup create, edit, delete, or restore backups?

No. It monitors and verifies Home Assistant's native backups. All verification is
read-only. Verification runs inside configured resource limits and private temporary
files are deleted after the check. A Repair issue is created if cleanup cannot be
confirmed.

## Does a successful integrity check guarantee a successful restore?

No. It confirms that the selected file can be downloaded, decrypted when needed,
and fully read as a structurally valid archive. The optional database check also
verifies SQLite integrity. Only an isolated test restore can test the complete
restore process and runtime behavior.

## Which backup is verified?

The newest regular backup is checked. BackupCheckup prefers an available local copy and
otherwise chooses another available native backup storage agent.

## Does automatic verification run at every polling interval?

No. When enabled, it runs once when BackupCheckup detects a new regular backup. The
normal inventory polling remains lightweight.

## Why is automatic verification disabled by default?

A full check downloads and reads the entire backup. Large backups can temporarily
use substantial network bandwidth, CPU time, and local temporary storage. Version
2.2 limits download size, expanded bytes, archive members, disk usage, and runtime.

## How are encrypted backups checked?

BackupCheckup uses the password configured in Home Assistant's native backup system.
The password is used only in memory and is never logged or persisted by the
integration.

## What does Password required mean?

The backup is marked as protected but could not be decrypted with the password
available from Home Assistant. This does not by itself prove corruption.

## What does Valid with warnings mean?

The archive was fully readable, but a non-fatal inconsistency was detected, such as
a downloaded size differing from the storage agent's reported size or a changed
checksum for the same backup ID.

## What does Aborted mean?

A configured safety budget stopped the check because of size, member count, free
space, overall duration, or database duration. The result is inconclusive and does
not mean that the backup is corrupt. Inspect the privacy-safe `error_code` attribute
before changing a limit.

## What does the database expert option do?

It temporarily extracts `home-assistant_v2.db` and runs SQLite
`PRAGMA integrity_check`. It is disabled by default because it needs additional disk
space and can considerably lengthen verification.

## Where is the checksum stored?

The last completed result is stored in Home Assistant's private integration storage.
It is removed when the BackupCheckup config entry is deleted.

## Are backup names and IDs exposed?

Not by default. Normal entity attributes and diagnostics use a stable
installation-local backup reference. The Custom profile contains an explicit expert
option for exposing the native newest-backup name and ID when an automation requires
them.

## Who can start a manual full verification?

The verification action requires Home Assistant administrator context. A configurable
cooldown and the single-running-check guard prevent repeated overlapping checks.

## Why are fewer entities enabled on a new installation?

Version 2.1 and newer present a compact everyday set. Detailed analytics, schedule,
per-storage, checksum, database, and troubleshooting entities remain available but
are disabled by default. Existing installations are not forcibly changed.

## Does it work with NAS and cloud backup locations?

Yes, when the location is exposed as a native Home Assistant backup agent and allows
the selected backup to be downloaded.

## Does BackupCheckup upload any data?

No. The integration has no cloud connection. Verification takes place locally.

## Can Repair notifications be disabled?

Yes. Select the Custom profile and disable **Show repair notifications**. Sensors
continue to work.

## Why is the automatic success rate initially unknown?

Home Assistant does not expose a complete historical attempt list. BackupCheckup
records outcomes locally from version 1.5.0 onward and does not invent earlier data.


## How are mobile notification targets selected?

The options flow lists only enabled `notify` entities provided by Home Assistant's
`mobile_app` integration. This normally corresponds to phones and tablets registered
through the official Companion App.

## Why did I receive only one notification?

BackupCheckup intentionally deduplicates alerts. The same unchanged problem is not
resent at every polling interval. A new message is sent when the active problem set
changes, and an optional recovery message is sent after all problems are resolved.

## Where is the full troubleshooting guide?

See [`docs/troubleshooting.md`](troubleshooting.md) for installation, notification,
size-unit, integrity, storage, diagnostics, and rollback guidance.
