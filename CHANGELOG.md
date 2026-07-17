# Changelog

## 2.2.1

**Recommended patch update!**

Version 2.2.1 fixes upgrade, configuration-display, automatic-backup-state, integrity-verification, analytics, notification, and release-packaging issues discovered after the 2.2.0 release.

### Fixed

- Fixed the options form showing mixed, incorrectly typed, or incorrectly rendered values the first time it was opened after upgrading from BackupCheckup 2.1.2 or another older config-entry schema.
- Config-entry migration now normalizes both `entry.data` and `entry.options` into one canonical configuration snapshot before the integration and options flow use it. Existing options continue to override original setup data.
- Legacy configuration values are now normalized defensively: boolean strings are parsed strictly, numeric values are range-checked, invalid enum values fall back safely, unknown legacy keys are discarded, and a single notification target is converted to the supported list format.
- The coordinator and options flow now use the same centralized configuration normalization, preventing differences between the first and later form renders.
- Native automatic-backup state no longer depends only on fixed Home Assistant entity IDs. BackupCheckup now prefers Backup Manager data and resolves fallback entities through the entity registry by stable Backup integration unique IDs, so renamed entities remain supported.
- Stale `completed`, `failed`, or `in_progress` automatic-backup events are ignored unless their timestamps match the current backup attempt or the Backup Manager is actually running.
- A delayed automatic-backup success can now correct a matching history entry that had already been marked failed after the grace period.
- If backup metadata declares that the Home Assistant database is included but the canonical `data/home-assistant_v2.db` file is missing, the backup copy is now treated as structurally invalid instead of merely receiving a warning.
- Downloaded-byte, expanded-byte, and archive-member safety counters are reset for each redundant storage copy while all copy attempts continue to share the same overall verification deadline and cancellation signal.
- Temporary files from failed storage-copy verification attempts are removed before another copy is tried.
- Analytics now remain strictly inside the selected analysis window. When no backup exists in that window, results report insufficient data instead of silently analyzing older backups.
- Backup-size analytics now keep manual and automatic backups separate even when they share the same content-scope fingerprint.
- Newly added mobile notification targets now receive the currently active problem notification even when the problem signature itself has not changed. The normalized target set is persisted with the notification state.
- Backup-age values continue to advance from their stored timestamps while the Home Assistant Backup Manager is temporarily unavailable instead of remaining frozen at the previous refresh value.
- `valid_with_warnings`, `aborted`, and `password_required` verification outcomes now produce a consistent integrity-warning problem and Repair issue for the latest backup. `internal_error` is also represented by the integrity-failure Repair issue.
- Automatic verification now treats `internal_error`, `aborted`, `password_required`, and `unreadable` outcomes as eligible for a later retry instead of permanently considering the latest backup checked.
- Removed generated `.ruff_cache`, `.pytest_cache`, `.coverage`, `__pycache__`, and compiled Python files from the repository release package.

### Added

- Added `analyzed_backup_origin` to analytics sensor attributes and diagnostics so users can see whether the current size analysis represents manual or automatic backups.
- Added regression tests for legacy data/options normalization, analysis-window boundaries, manual-versus-automatic analytics separation, delayed-success correction, and per-copy verification budgets.

### Changed

- Config-entry schema updated to version 9 with automatic migration from all supported earlier BackupCheckup releases.
- Native backup timestamps read from Backup Manager data or fallback entities are normalized to timezone-aware UTC values before comparison.
- Integrity-warning Repair handling now covers controlled incomplete checks as well as valid results containing actionable warnings.

### Notes

- No configuration reset is required. Existing user settings and notification targets are migrated automatically.
- The first opening of the options flow after upgrading should now display the same values as every subsequent opening.
- An `aborted` or `password_required` result means verification did not complete; it does not by itself prove that the backup is corrupt.

## 2.2.0

**Recommended update!**

Version 2.2.0 is a major reliability, security, privacy, integrity-verification, backup-classification, storage-monitoring, and entity-management release.

It consolidates all improvements developed during the 2.2.0 beta cycle and includes automatic migration from BackupCheckup 2.1.2.

### Security

- Added configurable safety limits for maximum downloaded backup size, expanded archive size, archive-member count, metadata size, overall verification duration, and SQLite integrity-check duration.
- Added free-space validation before and during verification to prevent temporary backup data from exhausting the Home Assistant filesystem.
- Reworked TAR verification so archive members are processed as a stream instead of retaining the complete archive-member list in memory.
- Added cooperative deadline checks throughout backup download, archive reading, decompression, database extraction, and SQLite verification.
- Added an SQLite `quick_check` before the full integrity check, disabled trusted schemas during read-only verification, and restricted database verification to the canonical `data/home-assistant_v2.db` path.
- Duplicate, nested, or decoy database files are now rejected.
- Enforced exactly one canonical root-level `backup.json` and rejected nested or duplicate metadata files.
- Rejected duplicate JSON keys, unsafe archive identifiers, control characters, invalid database flags, duplicate declared apps or folders, logical archive-name collisions, and nested or duplicate inner archives.
- Undeclared inner archives are reported as bounded integrity warnings instead of being processed without limits.
- Temporary verification directories and files now use owner-only filesystem permissions.
- Added startup cleanup for stale BackupCheckup temporary directories and a persistent Home Assistant Repair issue when sensitive temporary verification data cannot be removed.
- Third-party backup-agent streams are explicitly closed after successful, cancelled, aborted, or failed downloads.
- Added strict validation and safe fallback defaults for corrupted integration options and persisted private state.
- Replaced raw third-party exception messages with stable privacy-safe error codes in entities, diagnostics, notifications, and logs.
- Sanitized untrusted identifiers before writing them to logs.
- Backup names, native backup IDs, storage-agent IDs, and checksums are hidden from normal entities and diagnostics by default.
- Added an advanced option for explicitly exposing detailed backup metadata.
- Refresh, manual verification, and test-notification actions are registered as administrator-only Home Assistant actions.

### Added

- Added an `aborted` integrity state for verification runs stopped by a configured resource or time limit.
- Added privacy-safe integrity error codes for download-size limits, expanded-size limits, insufficient free disk space, verification timeouts, excessive archive members, oversized metadata, and other controlled verification failures.
- Added stable installation-local backup references for correlating results without exposing native Home Assistant backup IDs.
- Added advanced configuration options for verification size limits, verification timeouts, SQLite timeout, manual verification cooldown, and detailed metadata exposure.
- Added backup-purpose classification using Home Assistant Supervisor's `supervisor.addon_update` metadata marker.
- Added privacy-safe content-scope fingerprints based on included Home Assistant data, database, apps, and folders.
- Added inventory, monitored-backup, ignored-update, comparison-count, analysis-scope, and discarded-record diagnostics.
- Added privacy-safe log messages when integrity verification starts, completes, is cancelled, or fails unexpectedly.
- Added active checksum-change monitoring with status information, a binary sensor, health-score deduction, Repair issue, diagnostics, and localized text.
- Added automatic download and archive-verification fallback to another available backup storage location when one copy cannot be retrieved or validated.
- Added privacy-safe storage references for entities, diagnostics, and Repair issue details.
- Added defensive validation of integrity results, automatic-backup history, and notification state, with dedicated Repair issues when invalid private data must be reset.
- Added a dedicated `backup_integrity_warning` problem signal for actionable integrity warnings.
- Added friendly storage-location names to storage summaries and latest-location attributes.
- Added precise age attributes for the newest regular, automatic, manual/other, and per-storage backups.
- Added extensive regression and adversarial tests covering resource limits, temporary-file permissions, metadata privacy, path validation, archive limits, duplicate metadata, duplicate JSON keys, nested archives, archive collisions, decoy databases, app-only backups, stream closure, event-state handling, corrupted stores, app-update filtering, scope-aware size comparison, and completed-day boundaries.
- Added entity-registry diagnostics showing enabled and disabled entity counts. Exact disabled entity IDs are included only when detailed metadata exposure is enabled.

### Changed

- Technical backups created before Home Assistant app updates are now classified separately from regular monitored backups.
- App-update backups no longer replace the newest monitored backup, reset its age, trigger backup-size warnings, affect averages or trends, influence redundancy checks, or start automatic integrity verification.
- Storage-agent freshness now uses the latest regular backup, while stored-byte totals continue to include technical app-update backups.
- Automatic backup-size checks now compare only backups with the same automatic/manual origin and the same content scope.
- Size-drop warnings now require at least two older comparable backups instead of relying on a single previous backup.
- Verification stopped by a configured safety limit is no longer classified as a corrupt backup.
- SQLite verification now uses a progress handler so the configured deadline can stop the database operation cooperatively.
- Backup integrity results and diagnostics now use privacy-safe backup serialization by default.
- All user-facing backup-age sensors now report fully completed 24-hour days as integers. Values remain at `0 d` until 24 complete hours have elapsed and then change to `1 d`.
- Precise age values in hours and decimal days remain available as entity attributes and in diagnostics.
- Standard entity mode now focuses on the two primary age sensors for the newest regular and newest automatic backup.
- Exact backup timestamp entities remain available in Expert mode for advanced automations and templates.
- Timestamp entity names now explicitly contain “timestamp” to distinguish them from backup-age entities.
- Per-storage backup-age sensors use the same completed-day presentation as the main device.
- The selected entity preset is re-applied after platform setup and during schema migration while preserving entities manually disabled by the user or disabled through Home Assistant's config-entry system option.
- The Standard entity preset now enables the checksum-change problem sensor.
- Detailed metadata exposure now clearly controls the visibility of backup names and raw identifiers, while entity mode independently controls which diagnostic entities are enabled.
- Per-storage **Latest backup size** and **Stored backup size** sensors now use decimal megabytes instead of raw bytes, including automatic migration of existing entity display units.
- Backup storage devices now use the friendly names supplied by Home Assistant.
- Added the BackupCheckup brand image to the README.
- Added a prominent disclosure that the integration and its ongoing maintenance are AI-coded and AI-maintained under human direction, testing, and release control.
- Config-entry schema updated to version 8 with automatic migration from previous releases.
- Mobile notification configuration now uses an explicit multi-select list, allowing any number of Home Assistant Companion App phones and tablets to be selected at the same time. Existing single-target settings remain compatible.

### Fixed

- Fixed technical app-update backups being treated as regular monitored backups and influencing backup-age, size, trend, redundancy, and integrity calculations.
- Fixed the manual **Verify latest backup** button remaining unavailable after verification when the configured cooldown was `0` minutes.
- The active verification task is now released before the final coordinator refresh so the button becomes available immediately after a completed or failed verification.
- Fixed app-only and folder-only backups receiving a false `database_not_found` warning; these now report `not_applicable`.
- Fixed HAOS backups containing the legitimate conditional `supervisor.tar` or `supervisor.tar.gz` archive receiving a false `unexpected_inner_archives_1` warning.
- Fixed background integrity-task failures potentially becoming unobserved asyncio exceptions.
- Fixed result-store and final-refresh failures destabilizing or repeatedly restarting automatic verification; controlled internal failures now use a retry backoff.
- Fixed automatic backups being marked failed while Home Assistant still reported them as `in_progress`. Native `completed` and `failed` events are now authoritative, with timestamp comparison retained as a compatibility fallback.
- Fixed backup-manager availability being inferred from a potentially disabled entity instead of the successful manager API response.
- Fixed invalid or duplicate backup IDs, malformed dates, invalid agent collections, and corrupted private state causing setup or refresh failures.
- Fixed fallback-copy size reporting including bytes downloaded during a previous failed attempt.
- Fixed a corrupt or unreadable preferred backup copy preventing verification of an intact redundant copy. Archive verification now tries available storage copies within the configured global safety budget.
- Fixed configured storage locations with no backups disappearing from storage monitoring.
- Fixed removed backup storage agents leaving permanently stale entities and devices. A missing storage agent must now remain absent for three consecutive refreshes before registry cleanup occurs.
- Fixed action buttons ignoring the coordinator's base availability state.
- Fixed temporary-data Repair issues remaining active after a later successful cleanup.
- Fixed downgrades accepting config entries created by a newer and unsupported schema version.
- Fixed less important configuration warnings taking precedence over integrity, backup-manager, storage, incomplete-backup, or automatic-backup failures.
- Fixed the integrity sensor exposing a raw backup-agent ID instead of the friendly storage-location name.
- Fixed genuine `valid_with_warnings` integrity results being displayed together with an excellent status and no-action recommendation. Integrity warnings now affect the overall status, recommendation, active problem state, and health score.
- Deleting the BackupCheckup config entry now performs a second exact-path cleanup for all three private `Store` files.
- On startup, BackupCheckup removes orphaned history, integrity, and notification stores belonging to config entries that no longer exist.
- Fixed Expert entity mode still leaving the three exact backup timestamp sensors and all per-storage latest-backup timestamp sensors disabled.

### Notes

- Existing backup monitoring and automatic-backup detection continue to operate normally after migration.
- Automatic integrity verification remains disabled by default.
- The optional SQLite database integrity check remains disabled by default.
- An `aborted` result means verification could not finish within its configured safety budget. It does not prove that the backup is corrupt.

## 2.2.0-beta6

### Changed
- All user-facing backup-age sensors now report fully completed 24-hour days as integers. Values remain at `0 d` until 24 hours have elapsed, then change to `1 d`.
- Exact backup timestamps and precise age values in hours and decimal days are retained as entity attributes and diagnostics instead of being mixed into the visible sensor state.
- Standard entity mode now focuses on the two useful age sensors for the newest regular and newest automatic backup. Exact timestamp entities remain available in Expert mode for templates and advanced automations.
- Timestamp entity names now explicitly say “timestamp” to distinguish them from backup-age entities.
- Per-storage backup-age sensors use the same completed-day presentation as the main device.
- Config-entry schema updated to version 7 so the streamlined entity preset is applied once to existing beta installations.

### Added
- Precise age attributes for the newest regular, automatic, manual/other, and per-storage backup-age sensors.
- Regression tests for completed-day boundaries at 0, 24, and 48 hours.

## 2.2.0-beta5

### Fixed
- Backup storage devices now use the friendly names supplied by Home Assistant instead of anonymous references, even when backup names and IDs remain hidden.
- Per-storage **Latest backup size** and **Stored backup size** sensors now expose decimal megabytes instead of raw bytes, including automatic migration of existing entity display units.
- HAOS backups containing the legitimate conditional `supervisor.tar` or `supervisor.tar.gz` archive no longer receive a false `unexpected_inner_archives_1` warning.
- The integrity sensor now shows the friendly storage location name without exposing the raw backup-agent ID.
- A genuine `valid_with_warnings` result now affects the overall status, recommendation, problem flag, and health score instead of being shown alongside an excellent/no-action assessment.

### Added
- Friendly storage location names in storage summaries and latest-location attributes.
- A dedicated `backup_integrity_warning` problem signal for actionable integrity warnings.

## 2.2.0-beta4

### Security
- Enforced a single canonical root `backup.json` and rejected nested or duplicate metadata files.
- Rejected duplicate JSON keys, unsafe metadata archive identifiers, duplicate declared add-ons or folders, and logical archive-name collisions.
- Rejected nested or duplicate inner archives and surfaced undeclared archives as bounded warnings.
- Restricted database verification to the canonical `data/home-assistant_v2.db` path and rejected duplicate or decoy database files.
- Added strict validation and safe fallback defaults for corrupted integration options and persisted private state.
- Explicitly closes third-party backup-agent streams after successful, aborted, or failed downloads.
- Added an SQLite quick check before the full integrity check, disabled trusted schemas for read-only verification, and tightened metadata/path validation for control characters and database flags.
- Protected refresh and test-notification actions with Home Assistant's administrator-only service registration, matching manual verification.
- Further redacted storage identifiers and checksums from diagnostics unless detailed metadata exposure is explicitly enabled.

### Fixed
- Fixed app-only and folder-only backups receiving a false `database_not_found` warning; these now use `not_applicable`.
- Fixed background integrity-task failures potentially becoming unobserved asyncio exceptions.
- Fixed result-store and final-refresh failures destabilizing or repeatedly restarting automatic verification; controlled internal errors now use a retry backoff.
- Fixed automatic backups being marked failed while Home Assistant reports them as `in_progress`. Native `completed` and `failed` events are now authoritative, with timestamp comparison retained as a compatibility fallback.
- Fixed backup-manager availability being inferred from a possibly disabled entity instead of the successful manager API response.
- Fixed invalid or duplicate backup IDs, malformed dates, invalid agent collections, and corrupted private store data causing setup or refresh failures.
- Fixed fallback-copy size reporting including bytes downloaded during an earlier failed attempt.
- Fixed a corrupt or unreadable preferred storage copy preventing verification of an intact redundant copy; archive verification now falls back across available locations within the configured global safety budget.
- Fixed configured backup storage locations with no backups disappearing from storage monitoring.
- Fixed removed backup storage agents leaving permanently stale entities and devices; disappearance is confirmed across three refreshes before registry cleanup.
- Fixed action buttons ignoring the base coordinator availability state.
- Fixed temporary-data Repair issues remaining active after a later successful cleanup.
- Fixed downgrades accepting config entries created by a newer, unsupported schema version.
- Fixed less important configuration warnings taking precedence over integrity, manager, storage, incomplete-backup, or automatic-backup failures.

### Added
- Active checksum-change status, binary sensor, health-score deduction, Repair issue, diagnostics, and localized text.
- Download and archive-verification fallback to another available backup storage location when one copy cannot be retrieved or validated.
- Privacy-safe storage references for normal entities, diagnostics, and Repair issue details.
- Defensive validation of integrity, automatic-history, and notification stores with dedicated Repair issues when invalid data is reset.
- Diagnostics for discarded invalid backup inventory records.
- Adversarial tests for duplicate metadata, duplicate JSON keys, nested archives, archive collisions, decoy databases, app-only backups, explicit stream closure, event-state handling, and corrupted stores.

### Changed
- Config-entry schema remains version 6; no user migration is required from beta1, beta2, or beta3.
- The standard entity preset now enables the checksum-change problem sensor.

## 2.2.0-beta3

### Fixed
- Fixed the manual **Verify latest backup** button remaining unavailable after a completed verification when the configured cooldown was `0` minutes.
- The active verification task reference is now released before the final coordinator refresh, so Home Assistant immediately publishes the button as available again after a completed or failed run.

### Changed
- Added the BackupCheckup brand image to the top of the README.
- Added a prominent disclosure that the complete integration and its ongoing maintenance are AI-coded and AI-maintained under human direction, testing, and release control.

## 2.2.0-beta2

### Fixed
- Technical backups created before Home Assistant app updates are no longer treated as regular backups.
- App-update backups no longer replace the newest monitored backup or reset its age.
- App-update backups no longer trigger backup-size warnings, affect size averages or trends, influence redundancy checks, or start automatic integrity verification.
- Automatic backup-size checks now compare only backups with the same automatic/manual origin and the same content scope.
- Automatic size-drop warnings now require at least two older comparable backups, avoiding alerts from an unreliable single-backup baseline.
- Storage-agent freshness now uses the latest regular backup while stored-byte totals still include technical update backups.

### Added
- Backup-purpose classification using Home Assistant Supervisor's `supervisor.addon_update` metadata marker.
- Privacy-safe content-scope fingerprints based on included Home Assistant data, database, apps, and folders.
- Inventory, monitored-backup, ignored-update, comparison-count, and analysis-scope diagnostics.
- Explicit privacy-safe log messages when integrity verification starts, completes, is cancelled, or fails unexpectedly.
- Regression tests for app-update filtering and scope-aware size comparison.

## 2.2.0-beta1 – Security Hardening

### Security
- Added configurable limits for downloaded backup size, expanded archive size, archive-member count, metadata size, overall verification duration, and SQLite integrity-check duration.
- Added free-space validation before and during verification so temporary data cannot silently exhaust Home Assistant's filesystem.
- Reworked archive verification to stream TAR members instead of retaining the complete member list in memory.
- Added cooperative deadline checks throughout download, archive reading, decompression, database extraction, and SQLite verification.
- Added an administrator-only `backup_checkup.verify_latest_backup` action and a configurable cooldown for manual checks.
- Replaced raw third-party exception messages with stable privacy-safe error codes in entities, diagnostics, notifications, and logs.
- Sanitized untrusted identifiers before including them in logs.
- Removed user-defined backup names and raw backup IDs from normal entity attributes by default.
- Added an explicit expert option for exposing detailed backup metadata.
- Restricted temporary verification directories and files to owner-only filesystem permissions.
- Added startup cleanup for stale BackupCheckup temporary directories and a persistent Repair issue when sensitive temporary data may remain.

### Added
- New `aborted` integrity state for checks stopped by a configured safety limit.
- New privacy-safe integrity error codes for size limits, insufficient disk space, timeouts, excessive archive members, oversized metadata, and other controlled failures.
- Stable installation-local backup references for correlating results without exposing native backup IDs.
- Advanced options for verification size limits, timeouts, manual cooldown, and metadata exposure.
- Regression tests for resource budgets, private temporary-file permissions, metadata privacy, path validation, and archive limits.

### Changed
- A check stopped by a safety limit is no longer classified as a corrupt backup.
- SQLite verification now uses a progress handler so its configured deadline can stop the actual database operation cooperatively.
- The latest-backup result sensor and diagnostics use privacy-safe backup serialization by default.
- Config-entry schema updated to version 6 with automatic migration from previous releases.

### Notes
- Existing backup monitoring and automatic-backup detection continue to operate normally.
- Automatic verification and the SQLite database check remain disabled by default.
- An `aborted` result means the check could not complete within its configured safety budget; it does not prove that the backup is corrupt.

## 2.1.2

### Fixed
- Fixed the Custom profile form where the entity-mode key was accidentally passed as an additional positional argument to `vol.Required()`.
- Moved temporary-directory creation, backup-file opening and closing, and cleanup of potentially large verification files out of Home Assistant's event loop.
- Corrected the minimum supported Home Assistant version to 2026.3.0 because full encrypted-backup verification uses the SecureTar archive API introduced with that Home Assistant release.
- Made the configured minimum backup size use decimal megabytes consistently with the MB sensor output.
- Classify malformed SecureTar headers as corrupt backups instead of unexpected read failures.

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
