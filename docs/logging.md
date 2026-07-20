# Logging and live activity

BackupCheckup 2.6.1 provides one central, privacy-safe activity journal. Each
record contains a UTC timestamp, a stable action name, an outcome, a severity,
and a small set of bounded details.

## Enable or disable logging

Open **Settings → Devices & services → BackupCheckup → Configure → Frontend,
entities, and notifications** and select **Enable detailed live logging**.

- Enabled: live Activity entries, the searchable sidebar log, structured Core
  records, and the bounded diagnostics journal are active.
- Disabled: no activity records are emitted or retained.

Logging is independent of Standard or Expert entity mode. Changing the switch reloads
BackupCheckup so the new state applies immediately. Existing Expert installations are
migrated with logging enabled to preserve their previous behavior.

## Sidebar live log

When the optional BackupCheckup sidebar frontend is enabled, use its **Live log**
tab for a dedicated, searchable operational view. It updates while BackupCheckup
works and reports inventory reads, storage preparation, download progress,
encrypted or unencrypted archive extraction, database verification, result storage,
notifications, cleanup, and failures. The in-memory list retains at most 250 entries
and resets when Home Assistant restarts.

## Home Assistant Activity

With detailed logging enabled, open **Activity** in Home Assistant and filter for
**BackupCheckup**. Relevant workflow events appear live, including integration setup
and unloading, inventory refresh results, health-state changes, integrity
verification, notification delivery, manual services, and cleanup operations.

Routine high-frequency start events are kept out of Activity to avoid flooding the
timeline. They are still written to the structured Core log and retained in the
runtime diagnostics journal while Expert mode is active.

Activity is the correct surface for operational history. Home Assistant Repairs is
reserved for actionable problems, so BackupCheckup continues to create Repair issues
only when user intervention is required.

## Core log

When enabled, structured records use the logger
`custom_components.backup_checkup.activity` and the format:

```text
activity timestamp=2026-07-18T00:00:00+00:00 action=inventory_refresh outcome=completed backup_count=4 duration_seconds=0.083
```

To explicitly display informational BackupCheckup records, add this to
`configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.backup_checkup: info
```

Use `debug` temporarily when troubleshooting. Avoid leaving debug logging enabled
permanently because Home Assistant and third-party libraries may emit additional
detail.

## Downloaded diagnostics

When enabled, the latest 100 activity records are included in integration
diagnostics. The in-memory journal retains at most 250 records and is reset when Home
Assistant restarts. When disabled, diagnostics report `enabled: false` with empty
event counters and no recent records.

## Privacy and limits

BackupCheckup does not place notification entity IDs, raw backup IDs, backup names,
file paths, passwords, raw storage-agent IDs, or backup contents in the central
journal. Sensitive detail keys are dropped centrally. Private operations use general
phrases such as “Extracting encrypted backup” or “Reading and checking database”.
Detail keys and values, record count, and message lengths are bounded to prevent
accidental log amplification.
