# Changelog

## 2.1.1

### Fixed
- Fixed a startup failure in the coordinator caused by an invalid `dict.get()` call while reading the database-integrity-check option.
- Restored successful setup after fresh installation or reconfiguration through HACS.

## 2.1.0

### Added
- Independent **Standard mode** and **Expert mode** entity presets in the initial setup and options flow.
- Standard mode enables the main monitoring, analytics, integrity, and global problem entities; Expert mode enables every BackupCheckup entity.
- Optional built-in mobile notifications for active backup problems.
- Guided selection of one or more Home Assistant Companion App notify entities, filtered to mobile-app devices only.
- Optional recovery notification after all previously reported backup problems are resolved.
- A **Send test notification** button for validating the selected mobile devices.
- Persistent notification deduplication so regular polling does not repeatedly send the same warning.
- A dedicated and expanded troubleshooting guide under `docs/troubleshooting.md`.

### Changed
- Expanded the default Standard entity set so the most useful entities are available without manually enabling almost every entity.
- Added entity-registry preset application when the entity mode is changed while preserving entities explicitly disabled by the user.
- Changed the newest-backup and newest-automatic-backup size sensors from bytes to megabytes with two decimal places.
- Added automatic entity-registry unit migration for existing installations of both size sensors.
- Updated diagnostics with sanitized notification configuration and the latest notification error without exposing selected entity IDs.
- Moved troubleshooting content out of the README and linked Repair issues directly to the dedicated guide.
- Updated integration, manifest, device, README, documentation, and config-entry metadata to 2.1.0.

### Fixed
- Repaired enum translation metadata for the backup integrity status so states such as `valid` are localized in normal Home Assistant entity views.
- Ensured enum translation metadata is migrated for all existing BackupCheckup enum sensors.

### Notes
- Developer Tools intentionally continues to show stable raw enum states such as `valid`; normal cards and device views use translated states.
- Mobile notifications are disabled by default and require the Home Assistant Companion App to expose an enabled `notify` entity.
- Notifications are sent only when the active problem set changes, not at every coordinator refresh.

## 2.0.0

### Added
- Manual full integrity verification of the newest backup through the native Home Assistant backup-agent download API.
- Optional automatic verification when a newly detected newest backup appears.
- Complete reading of the outer archive and every contained inner TAR/TAR.GZ archive.
- Validation of `backup.json`, expected archive components, member paths, and downloaded byte size.
- Decryption and complete reading of protected backups using Home Assistant's configured backup password.
- Optional expert SQLite `PRAGMA integrity_check` for the included Home Assistant database.
- Persistent SHA-256 checksum and last verification result.
- Integrity status, last-check, checksum, verified-size, duration, and database-result sensors.
- Manual **Verify latest backup** button.
- Aggregate integrity problem binary sensor and native Repair issue for a corrupt or unreadable newest backup.
- Dedicated integrity documentation and troubleshooting guidance.

### Changed
- Streamlined new installations to a smaller default entity set. Detailed analytics, schedule, per-storage, checksum, database, and troubleshooting entities remain available but are disabled by default.
- Existing entity registry choices are preserved during upgrades so current dashboards and automations are not forcibly changed.
- Added integrity failures to the central status, recommendation, active-problem list, diagnostics, and health-score deductions.
- Updated configuration-entry schema to version 3 with migration from all previous releases.
- Updated integration, manifest, device, README, and documentation metadata to 2.0.0.

### Security and privacy
- Verification is read-only and never modifies, restores, uploads, or retains backup contents.
- Backup passwords are used only in memory and are never logged or persisted by BackupCheckup.
- Temporary backup and database files are removed after every check.

### Notes
- A successful integrity check confirms structural readability and optional SQLite integrity; it is not a complete restore test.

## 1.5.1

### Fixed
- Explicitly bound translated enum-state metadata so the backup health rating and backup-size trend are shown in the selected Home Assistant language.
- Changed the average backup-size sensor from bytes to megabytes.
- Added an automatic entity-registry unit migration so existing installations switch from `B` to `MB` after updating.

## 1.5.0

### Added
- Transparent backup health score from 0 to 100 with per-problem deductions exposed as attributes.
- Human-readable Excellent, Good, Warning, and Critical health rating sensor.
- Backup-size trend analysis using recent retained backups.
- Average backup-size and longest-backup-gap sensors.
- Persistent local observation history for automatic backup attempts.
- Observed automatic-backup success-rate and consecutive-failure sensors.
- Configurable analytics period from 7 to 365 days.
- Analytics details in diagnostics, documentation, dashboard examples, and every supported translation.

### Changed
- Expanded the recommended dashboard around the health score and trend metrics.
- Updated integration, device, manifest, and documentation version metadata to 1.5.0.

### Notes
- Automatic success history begins when version 1.5.0 is first run because Home Assistant exposes only the latest attempt and latest success. No older failures are inferred.

## 1.4.0

### Added
- Native Home Assistant Repair issues for active backup problems with automatic removal after recovery.
- A `button.backup_checkup_refresh` entity for immediate manual refreshes.
- Separate Home Assistant devices for every detected backup storage location.
- Expanded privacy-conscious diagnostics with health, schedule, storage, and sanitized recent-backup data.
- Structured repository documentation under `docs/`, including entity, FAQ, dashboard, automation, and screenshot guidance.
- Optional Repair notifications in the Custom monitoring profile.
- GitHub issue templates, contribution guidance, security policy, and pull-request template.

### Changed
- Reorganized and expanded the README for easier installation, configuration, troubleshooting, and daily use.
- Completed the guided setup, recommendation, and problem translations in every supported language.
- Improved translated names for storage-location entities and the refresh button.
- Automatic size comparison now uses recent backups of the same type.
- Less frequently used storage metrics are disabled by default on new installations.

### Fixed
- Added automatic migration for configuration entries created by the public 1.0.0 release.
- Fixed a broken update-interval lookup in the 1.3.0 coordinator that could prevent the integration from starting.
- Removed backup names and IDs from exported diagnostics.

## 1.3.0

### Added
- Guided Standard, Secure, and Custom monitoring profiles.
- Automatic backup-size baseline based on recent backups.
- Recommendation sensor with clear next steps.
- Active-problem count and problem list.
- Explanations for every setup and options field.

### Changed
- Simplified initial setup for users without technical backup knowledge.
- Moved advanced diagnostic entities out of the default entity set.

## 1.2.0

- Added backup-size monitoring using the size reported by each Home Assistant backup storage agent.
- Added configurable minimum backup size and detection of unusually large size drops compared with the previous comparable backup.
- Added detection of incomplete backups with failed add-ons, folders, or storage agents.
- Added a backup-result sensor with detailed attributes for the latest backup.
- Added separate backup count, timestamp, age, size, stored-size, and problem entities for every detected storage agent.
- Added configurable redundancy monitoring based on the number of locations containing the latest backup.
- Added new status values, diagnostics, options, documentation, and translations for all supported languages.

## 1.1.1

- Fixed `sensor.backup_checkup_automatic_backup_age` displaying long fractional values.
- The existing sensor now reports only fully completed days and changes from 0 to 1 only after a full 24 hours.
- Kept the precise fractional age as a separate internal value for overdue checks and other calculations.

## 1.1.0

- Added Dutch, Polish, Swedish, Italian, French, Danish, and Spanish translations.
- Added Belgian language coverage through the available Dutch, French, and German translations.
- Updated integration and device version metadata to 1.1.0.

## 1.0.0

- Initial public release.
- Actual Home Assistant backup inventory monitoring.
- Config flow and options flow.
- Sensor and binary-sensor platforms.
- German and English translations.
- HACS-compatible repository structure.
