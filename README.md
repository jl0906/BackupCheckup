<p align="center">
  <img src="custom_components/backup_checkup/brand/icon@2x.png" alt="BackupCheckup icon" width="170">
</p>

<h1 align="center">BackupCheckup</h1>

<p align="center">
  <strong>Know whether your Home Assistant backups are recent, complete, redundant, and readable.</strong>
</p>

<p align="center">
  <img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-orange.svg">
  <img alt="Version 2.6.2" src="https://img.shields.io/badge/version-2.6.2-blue.svg">
  <img alt="AI Coded and Maintained" src="https://img.shields.io/badge/AI-Coded_and_Maintained-8A2BE2.svg">
  <img alt="Home Assistant 2026.3 or newer" src="https://img.shields.io/badge/Home_Assistant-2026.3_or_newer-41BDF5.svg">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-yellow.svg">
</p>

BackupCheckup is a local Home Assistant custom integration that monitors the **actual backup inventory** reported by Home Assistant's native backup manager.

It warns you when backups are missing, outdated, incomplete, unexpectedly small, stored on too few locations, or no longer readable. No separate helpers or automations are required.

> [!NOTE]
> BackupCheckup is AI-coded and AI-maintained under human direction, testing, and release control.

## Install with HACS

[![Open your Home Assistant instance and add BackupCheckup to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jl0906&repository=BackupCheckup&category=integration)

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **BackupCheckup** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **BackupCheckup** and complete the guided setup.

**Requirement:** Home Assistant **2026.3.0 or newer**.

### Manual installation

Copy `custom_components/backup_checkup` to `/config/custom_components/backup_checkup`, restart Home Assistant, and add the integration through **Settings → Devices & services**.

## Guided setup in 2.5.0

BackupCheckup now separates system performance from backup safety. The assistant guides you through five focused steps:

1. **Performance profile** based on the detected Home Assistant system
2. **Monitoring policy** for backup age, size, and redundancy
3. **Integrity strategy** for manual or automatic archive checks
4. **Frontend, entity mode, and notifications**
5. **Final confirmation** without repeating technical configuration values

Hardware detection is only a recommendation. BackupCheckup never changes your selected profile later without confirmation.

### Optional sidebar frontend

Enable **Show BackupCheckup in the sidebar** during setup to add a responsive overview page directly to Home Assistant. It provides:

- overall backup status and Health Score
- the recommended next action and active problems
- latest backup age and size, stored-backup count, and integrity status
- a compact overview of every configured backup storage location
- administrator actions to refresh the data or verify the latest backup

The panel is bundled with BackupCheckup, uses the integration's existing privacy setting, and does not load external frontend resources. It is disabled by default and can be enabled or removed later under **Configure → Frontend, entities, and notifications**.

### Performance profiles

| Profile | Typical systems | Normal polling |
| --- | --- | ---: |
| **Energy saving** | Small Raspberry Pi or low-resource VM | 15 min |
| **Home Assistant appliance** | Home Assistant Green/Yellow or capable Pi with SSD | 10 min |
| **High performance** | x86 mini PC, NUC, normal VM or container | 5 min |
| **Server** | Generously provisioned server or large VM | 2 min |
| **Custom** | Manually selected intervals and resource limits | Custom |

The recommendation can use installation type, architecture, and known board information. When the current backup inventory is available, proposed verification limits are raised automatically if necessary to fit the largest known backup with a safety reserve.

### Monitoring policy

| Policy | Best for |
| --- | --- |
| **Balanced** | Recommended defaults for most installations. |
| **Strict** | Newer backups and at least two storage locations. |
| **Custom** | Full control over backup age, size, redundancy, and related limits. |

### Integrity strategy

| Strategy | Behaviour |
| --- | --- |
| **Manual only** | Full verification is started only by an administrator. |
| **Automatic** | Each newly detected newest regular backup is verified once. |
| **Deep** | Automatic verification plus an SQLite integrity check. |

Deep verification is never enabled only because powerful hardware was detected.

### Entity mode

| Entity mode | Best for |
| --- | --- |
| **Standard** | A focused set of useful status, health, integrity, and problem entities. |
| **Expert** | Every available entity, per-storage metrics, and advanced diagnostics. |

Detailed live logging is selected independently from the entity mode. All settings remain available later under **Settings → Devices & services → BackupCheckup → Configure**.

After updating BackupCheckup files, restart Home Assistant once. This reloads
the integration's backend translations and activates the versioned frontend
module; reloading only the config entry is not sufficient after a file update.

## Intelligent polling

When enabled, BackupCheckup combines the selected base interval with native backup activity:

- Refreshes immediately when a backup starts, completes, or fails
- Temporarily polls faster while a backup is running
- Returns to the normal interval after completion
- Uses a longer backoff after repeated backup-manager errors
- Coalesces rapid events without losing the final backup state
- Continues to follow renamed native backup entities through their registry IDs

Existing 2.3.x installations keep their previous resolved values and fixed polling during migration. The new recommendation is applied only when the assistant is run voluntarily.

## What BackupCheckup checks

- Whether any regular backup is available
- Age of the newest regular and automatic backup
- Failed, missing, or overdue automatic backups
- Incomplete backups and suspicious size changes
- Backup copies across all configured storage locations
- Required redundancy across multiple locations
- Storage errors and unavailable backup-manager data
- Overall backup health with a score from `0` to `100`

Technical backups created for Home Assistant app updates remain visible in the inventory but are excluded from normal backup-health and size analytics.

## Health Score v2

The Health Score groups related symptoms by their underlying cause instead of subtracting every correlated warning separately.

For example, one unavailable storage location may also cause missing redundancy. Both signals remain visible, but only the strongest deduction in that area is applied to the score.

The sensor exposes transparent attributes for:

- Applied deductions
- Raw detected deductions
- Deductions by health component
- Correlated deductions that were intentionally not counted twice
- Score model version

Backup age and missing redundancy are also weighted by severity instead of using only fixed penalties.

## Integrity verification

Press **Verify latest backup** to perform a read-only check of the newest regular backup.

BackupCheckup can:

- Download an available copy through Home Assistant
- Fall back to another storage location when necessary
- Read the complete outer archive and all included inner archives
- Verify encrypted backups with Home Assistant's configured backup password
- Detect structural archive problems and checksum changes
- Optionally run an SQLite integrity check on the included Home Assistant database
- Enforce configurable download, expansion, member-count, disk-space, and timeout limits
- Remove temporary files after the check finishes

> [!IMPORTANT]
> A successful check confirms that the backup is structurally readable and, when applicable, decryptable. It is not a complete restore test.

## Alerts and Repairs

BackupCheckup can create native issues under **Settings → System → Repairs** and remove them automatically after recovery.

Optional mobile notifications can be sent to one or more devices using the Home Assistant Companion App. Notifications are deduplicated, so unchanged problems are not sent again after every refresh.

Use the **Send test notification** button after selecting your devices.

## Local, read-only, and permission-aware

BackupCheckup runs locally inside Home Assistant.

It does **not**:

- Create, modify, delete, restore, or upload backups
- Send backup contents to an external service
- Store backup passwords
- Keep downloaded backup files after verification

Sensitive identifiers are hidden from normal entities and diagnostics unless detailed metadata exposure is explicitly enabled.

Manual refreshes, integrity verification, and test notifications are administrator-only. Generic `homeassistant.update_entity` calls cannot be used to bypass the protected refresh action.

## Advanced users

Expert mode additionally enables detailed per-storage entities. The separate **Enable detailed live logging** option records a privacy-safe journal for setup, refreshes, health changes, downloads, archive extraction, database checks, notifications, progress, and cleanup operations.

The sidebar frontend contains separate **Overview** and **Live log** tabs. The log is searchable, updates live, retains at most 250 runtime entries, and is also available in Home Assistant **Activity**, structured system logs, and integration diagnostics. It never includes backup names, raw IDs, paths, passwords, or backup contents.

## Documentation

- [Hardware-aware setup](docs/hardware-aware-setup-2.4.0.md)
- [Entity reference](docs/entities.md)
- [Integrity verification](docs/integrity.md)
- [Activity logging](docs/logging.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)
- [Dashboard example](docs/examples/dashboard.yaml)
- [Automation example](docs/examples/automation.yaml)
- [Function coverage report](docs/function-coverage-2.3.0.md)
- [Security hardening report](docs/security-hardening-2.3.1.md)
- [2.4.0 quality and Health Score audit](docs/quality-audit-health-score-2.4.0.md)
- [Changelog](CHANGELOG.md)

## Updating and removal

Install updates through HACS and restart Home Assistant when requested.

Removing the BackupCheckup config entry deletes only the integration's own local history, integrity result, and notification state. Your Home Assistant backups are never deleted.

## Languages

English, German, Dutch, Polish, Swedish, Italian, French, Danish, and Spanish are included.

## License

MIT License
