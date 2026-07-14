# Changelog

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
