# Logging and live activity

BackupCheckup 2.3.0-alpha1 introduces one central, privacy-safe activity journal.
Each record contains a UTC timestamp, a stable action name, an outcome, and a
small set of bounded details.

## Home Assistant Activity

Open **Activity** in Home Assistant and filter for **BackupCheckup**. Relevant
workflow events appear live, including integration setup and unloading,
inventory refresh results, health-state changes, integrity verification,
notification delivery, manual services, and cleanup operations.

Routine high-frequency start events are kept out of Activity to avoid flooding
the timeline. They are still written to the structured Core log and retained in
the runtime diagnostics journal.

Activity is the correct surface for operational history. Home Assistant Repairs
is reserved for actionable problems, so BackupCheckup continues to create
Repair issues only when user intervention is required.

## Core log

Structured records use the logger
`custom_components.backup_checkup.activity` and the format:

```text
activity timestamp=2026-07-18T00:00:00+00:00 action=inventory_refresh outcome=completed backup_count=4 duration_ms=83
```

To explicitly enable detailed BackupCheckup logs, add this to
`configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.backup_checkup: info
```

Use `debug` temporarily when troubleshooting. Avoid leaving debug logging
enabled permanently because Home Assistant and third-party libraries may emit
additional detail.

## Downloaded diagnostics

The latest 100 activity records are included in the integration diagnostics.
The in-memory journal retains at most 250 records and is reset when Home
Assistant restarts. Persistent history remains Home Assistant's responsibility
through Activity/Recorder and the Core log configuration.

## Privacy and limits

BackupCheckup does not place notification entity IDs, raw backup IDs, backup
names, file paths, passwords, or raw storage-agent IDs in the central journal.
Storage references are anonymized. Detail keys and values, record count, and
message lengths are bounded to prevent accidental log amplification.
