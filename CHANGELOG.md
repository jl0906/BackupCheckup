# Changelog

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
