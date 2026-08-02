# Logging and live activity

BackupCheckup 2.7.0 provides one central, privacy-safe activity journal. Each
record contains a UTC timestamp, a stable action name, an outcome, a severity,
and a small set of bounded details.

## Enable or disable logging

Open **Settings → Devices & services → BackupCheckup → Configure → Frontend,
entities, and notifications** and select **Enable detailed live logging**.

- Enabled: live Activity entries, the searchable sidebar log, structured Core
  records, and the bounded diagnostics journal are active.
- Disabled: no activity records are emitted or retained.

Enable **Keep live log after restarts** only when restart-spanning history is
useful. Persistence is disabled by default. The retention setting accepts 1–30
days, and both runtime and persistent history remain bounded to 250 entries.

Logging is independent of Standard or Expert entity mode. Changing the switch reloads
BackupCheckup so the new state applies immediately. Existing Expert installations are
migrated with logging enabled to preserve their previous behavior.

## Sidebar live log

When the optional BackupCheckup sidebar frontend is enabled, use its **Live log**
tab for a dedicated, searchable and filterable operational view. It updates while BackupCheckup
works and reports inventory reads, storage preparation, download progress,
encrypted or unencrypted archive extraction, database verification, result storage,
notifications, cleanup, and failures. Filters cover severity and operation types.
The list retains at most 250 entries. It resets when Home Assistant restarts unless
optional persistence is enabled.

When new events arrive while you are reading older entries, your scroll position
is preserved and **New entries available** appears. Automatic scrolling occurs only
when the view is already at the newest entry. The toolbar can export the complete
privacy-safe buffer as JSON; administrators can also clear it.

## Home Assistant Activity

With detailed logging enabled, open **Activity** in Home Assistant and filter for
**BackupCheckup**. Relevant workflow events appear live, including integration setup
and unloading, inventory refresh results, health-state changes, integrity
verification, notification delivery, manual services, and cleanup operations.

Routine high-frequency start events are kept out of Activity to avoid flooding the
timeline. They are still written to the structured Core log and retained in the
runtime diagnostics journal while detailed logging is enabled.

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
diagnostics. The journal retains at most 250 records and reports whether persistence
is active and how many retention days are configured. When disabled, diagnostics report `enabled: false` with empty
event counters and no recent records.

## Privacy and limits

BackupCheckup does not place notification entity IDs, raw backup IDs, backup names,
file paths, passwords, raw storage-agent IDs, or backup contents in the central
journal. Sensitive detail keys are dropped centrally. Private operations use general
phrases such as “Extracting encrypted backup” or “Reading and checking database”.
Detail keys and values, record count, and message lengths are bounded to prevent
accidental log amplification.
