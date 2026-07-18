# Logging and live activity

BackupCheckup 2.3.0 provides one central, privacy-safe activity journal
exclusively in **Expert entity mode**. Each record contains a UTC timestamp, a
stable action name, an outcome, and a small set of bounded details.

## Enable or disable logging

Open **Settings → Devices & services → BackupCheckup → Configure** and select the
entity mode:

- **Expert mode:** live Activity entries, structured activity logs, and the bounded
  diagnostics journal are enabled.
- **Standard mode:** the complete activity-logging feature is disabled. No live
  Activity entries are published, no structured activity records are emitted, and no
  events are retained in the runtime journal.

Changing the entity mode reloads BackupCheckup, so the new logging state applies
immediately. The config-entry schema remains version 9 and no migration is required.

## Home Assistant Activity

With Expert mode enabled, open **Activity** in Home Assistant and filter for
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

In Expert mode, structured records use the logger
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

In Expert mode, the latest 100 activity records are included in integration
diagnostics. The in-memory journal retains at most 250 records and is reset when Home
Assistant restarts. In Standard mode, diagnostics report `enabled: false` with empty
event counters and no recent records.

## Privacy and limits

BackupCheckup does not place notification entity IDs, raw backup IDs, backup names,
file paths, passwords, or raw storage-agent IDs in the central journal. Storage
references are anonymized. Detail keys and values, record count, and message lengths
are bounded to prevent accidental log amplification.
