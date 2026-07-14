# Changelog

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
