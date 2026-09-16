# Changelog

## 3.2.0

### Fixed

- Live progress now follows the work instead of a timer. The archive scan
  reports the bytes it has really read, so the percentage rises continuously
  during the long phase of a check. The former time heartbeat that climbed to
  95 % after roughly 38 seconds and then stalled there for the rest of the run
  is gone.
- A deep check with a runtime test no longer reports "Start failed" and
  "Inconclusive result" at the same time when the Runtime Runner is not
  running. The runner is contacted before the test starts; if it does not
  answer, the test is not started at all and the new `not_started` status is
  reported with the matching error code. The progress bar stays where the run
  really stopped instead of jumping to 100 %.
- Runner errors are classified by what actually happened: failures before the
  upload become `not_started`, a failed upload or start becomes `failed`,
  resource limits and timeouts stay `aborted`, and only the runner's own
  unclassified failures remain `inconclusive`. An unknown remote status is now
  a failure with `runner_status_unknown` instead of silently becoming
  inconclusive.
- A stored runtime result is no longer shown as current proof once the runner
  has become unreachable and a newer verification has run since. A result that
  still matches the current backup and its checksum stays valid proof.
- A cancelled check no longer reports the step it interrupted as completed.
  Every step that was still running ends with the job, and an unfinished run
  never reads as one hundred percent.
- A runner that refuses a new run, for example because it is already busy, is
  reported as `not_started` instead of a failed test. The classification now
  follows the phase the failure happened in, not only its error code.
- Progress updates no longer refresh all BackupCheckup entities. Percentages
  travel on their own dispatcher channel that only the progress entities and
  the panel subscribe to.
- The live log is no longer flooded by a running check. Progress reaches the
  journal at most once per completed tenth of a measured step; the download no
  longer writes a record every five percent.
- The sidebar panel now renders a menu button in narrow layouts, so the Home
  Assistant sidebar can be opened by tapping on a phone in portrait
  orientation. The tab bar can no longer push the page wider than the screen,
  which previously swallowed the edge swipe.

### Added

- Runtime Runner reachability monitoring: a new `binary_sensor.backup_checkup_
  runtime_runner`, an Expert-mode `sensor.backup_checkup_runtime_runner`, an
  Expert-mode `button.backup_checkup_check_runner`, and the
  `backup_checkup.check_runner` action. The runner is checked at startup, on a
  configurable interval, whenever the panel is opened, and before every runtime
  test.
- New **Runtime runner check interval in minutes** setting (0 disables the
  background check, default 5) in the custom performance step of the setup
  assistant, the options flow, and the panel.
- Rebuilt panel overview with three equal status cards for Backups, Integrity
  check, and Runner & restore test. Both check cards show a live block with the
  overall bar, the current step, the step list, the runtime, and the last sign
  of life.
- Steps that cannot be measured - the SQLite check and the isolated Home
  Assistant start - are shown as indeterminate with a pulsing bar, their
  runtime, and their last sign of life. No percentage is invented for them.
- New `steps` attribute on `sensor.backup_checkup_restore_simulation_status`
  and `sensor.backup_checkup_runtime_test_status` with the weighted step model,
  plus `overall_percent`, `current_step`, `determinate`, `heartbeat_at`,
  `error_code`, and `source`. The former `progress_percent`, `stage`, and
  `stages` attributes remain as aliases.
- New WebSocket commands `backup_checkup/progress/subscribe` and
  `backup_checkup/runner/status` for the panel.
- Repair issues for a Runtime Runner that is too old, one that should be
  updated, and one that Supervisor no longer announces.
- CI checks for the shared progress weights, the progress model, the runner
  step model, the isolated boot events, intra-package import resolution, and
  the verification staging location.

### Changed

- The restore-simulation pipeline now uses the shared verification steps
  (`prepare`, `staging`, `download`, `archive_scan`, `nested_archives`,
  `database_check`, `evaluate`, `cleanup`) instead of the former stage names
  with fixed percentage ranges.
- The runtime-test poll interval is capped at two seconds so the live display
  keeps up with the runner.
- The recovery tab shows one protection-check block with a structure and a
  runtime section fed by the same step model, instead of two independent status
  blocks that could contradict each other.
- The log tab hides progress records by default and links to the live card.
- The configuration entry schema is now version 17. Existing settings migrate
  automatically; the runner check interval starts at five minutes.

### Runtime Runner

- Runtime Runner 3 released: live step progress, boot events
  (`sandbox_preflight_ok`, `process_started`, `port_listening`,
  `http_responding`), and an extended health endpoint that reports
  `runner_version`, `capabilities`, `uptime_seconds`, and `active_runs`.
  Protocol 2 is unchanged; Runner 2 keeps working without live progress.
- Extraction progress is measured from the consumed archive bytes instead of
  jumping from 35 % to 58 %, and the upload reports real byte counters.
- The isolated boot no longer estimates a percentage from the elapsed time. It
  reports its phase, its milestones, and a heartbeat every second.

### Compatibility

Minimum compatible Runtime Runner: **2**. Runtime Runner **3** is recommended:
live step progress and runner health details require it. Protocol 2 unchanged.

## 3.1.0

### Fixed

- Manual and automatic integrity verification no longer aborts with
  `insufficient_free_space` on Home Assistant OS although the data disk has
  plenty of room. Verification copies were staged in the Core container's
  `/tmp`, which Home Assistant OS mounts as a RAM-backed tmpfs, so any backup
  larger than roughly half of the installed memory could never be checked.
  Staging now defaults to `.cache/backup_checkup` inside the Home Assistant
  configuration directory on the persistent data partition.
- Capped the dynamic free-space reserve at 10 GB. On large data disks the
  previous 10 % rule could keep tens of gigabytes unusable for verification.

### Added

- Optional **Verification staging directory** setting in the integrity
  verification step of the setup assistant, the options flow, and the panel.
  Point it at any directory on a disk with enough space for a complete backup
  copy. The value is validated on entry (absolute path, existing real directory,
  writable, not the configuration root, `.storage`, `backups` or `tmp_backups`).
- Verification is refused while the native backup manager is creating,
  receiving, or restoring a backup, so staged copies never race a running
  backup. Manual requests receive a clear error; automatic checks retry on the
  next refresh.
- Diagnostics now report whether a custom staging directory is configured and
  the total and free capacity of the staging filesystem, without exposing the
  path itself.
- CI check that fails when verification data could fall back to the process
  temporary directory.

### Changed

- The automatic staging location is excluded from Home Assistant backups by
  Home Assistant itself (`.cache/*`), so a backup created during a running
  verification does not capture the working copy. A custom directory is not
  excluded automatically; see the Wiki.
- Stale verification data left in `/tmp` by earlier releases is removed once
  during the first start after the update. On Home Assistant OS this data
  disappears with the restart anyway.
- The configuration entry schema is now version 16. Existing settings migrate
  automatically; the staging directory starts empty, which selects the
  automatic location.

### Compatibility

- Minimum compatible Runtime Runner: **2**. No runner update is required for
  3.1.0; Runner 2 continues to implement protocol 2 unchanged.
- Existing configuration, entities, and stored analysis remain compatible.

## 3.0.14

### Changed

- Moved the optional Runtime Runner's archive, expanded-size, and startup-time
  limits into the BackupCheckup panel. The section is shown only when a runner
  has been discovered, and changes are sent with every runtime test.
- Removed the duplicated Home Assistant app options from Runtime Runner 2.
- Established independent versioning for the integration and runner. Runner
  version 2 implements protocol 2 and remains compatible with future BackupCheckup
  releases until the runner protocol or implementation actually changes.

### Security

- Kept immutable runner-side safety ranges for every integration-supplied limit,
  so a malformed or compromised client cannot request unbounded extraction or
  runtime duration.

### Compatibility

- BackupCheckup 3.0.14 requires the one-time Runtime Runner 2 update for
  isolated runtime tests. Structural verification remains available without it.

## 3.0.13

### Fixed

- Marked the native backup state listener as a Home Assistant `@callback` so
  adaptive-refresh state and `hass.async_create_task` remain on the event-loop
  thread instead of being invoked from an executor worker.
- Added a CI regression check requiring callbacks passed to
  `async_track_state_change_event` to be explicitly event-loop safe.

### Compatibility

- Integration, frontend asset, and Runtime Runner versions are synchronized as
  3.0.13. Existing configuration, entities, and stored analysis remain
  compatible.

## 3.0.12

### Fixed

- Synchronized the registered panel component with the 3.0.12 frontend and
  published a new versioned asset URL so HACS and browsers cannot reuse the
  broken component from the immutable 3.0.11 release tag.
- Added a CI consistency check that fails when the manifest version, backend
  panel registration, and JavaScript custom-element name diverge.
- Added a lightweight browser-environment probe that loads, registers, and
  renders the panel during CI instead of checking JavaScript syntax alone.
- Stopped suppressing runtime-directory deletion errors and added a ten-minute
  reaper for abandoned uploads and retained terminal results, preventing stale
  backup copies from occupying the runner container until its next restart.

### Compatibility

- Integration, frontend asset, and Runtime Runner versions are synchronized as
  3.0.12. Existing configuration and stored analysis data remain compatible.

## 3.0.11

### Fixed

- Prepared the ephemeral Home Assistant log with the sandbox UID/GID before
  startup so the unprivileged runtime can open its configured log file instead
  of exiting with `home_assistant_permission_denied`.
### Compatibility

- Integration, frontend asset, and Runtime Runner versions are synchronized as
  3.0.11. Existing configuration and stored analysis data remain compatible.

## 3.0.10

### Changed

- Consolidated the complete user guide in the GitHub Wiki, including every
  integration option, runner option, feature, entity, action, safety boundary,
  update path, FAQ entry, and troubleshooting workflow.
- Reduced the repository README to the product summary, HACS installation, the
  optional Runtime Runner note, and one canonical Wiki link.
- Removed obsolete coverage snapshots, historical audits, revision notes,
  duplicated guides, examples, and other superseded files from `docs/`.
- Redirected Home Assistant documentation and Repair help links to the Wiki.

### Compatibility

- This is an organizational release based on 3.0.9. Runtime behavior and stored
  configuration remain compatible; integration, frontend asset, and runner
  versions are synchronized as 3.0.10.

## 3.0.9

### Fixed

- Replaced duplicated multilingual frontend object structures with shared,
  data-driven translation schemas while preserving the rendered panel texts.
- Resolved the open runner maintainability findings by simplifying backup
  metadata discovery and centralizing its metadata filename.
- Sanitized child-process error values before publishing or logging them and
  documented the two required private/TLS transport boundaries for static
  security analysis.
- Raised the isolated Home Assistant virtual-memory and output-file limits so
  large verified backups no longer abort during startup despite low real memory
  use, while retaining hard process, descriptor, file, and address-space caps.
- Classify a bounded startup-log tail into stable, non-sensitive runner error
  codes instead of returning only the generic `home_assistant_exited` result.

## 3.0.8

### Fixed

- Restored Runtime Runner availability under Home Assistant's protected app
  environment by limiting namespace creation to the supported isolated network
  namespace.
- Retained the security boundary through an unprivileged runtime account, a
  secret-free environment, dropped Linux capabilities, `no_new_privs`, sandbox
  preflight verification, and resource limits.

## 3.0.7

### Fixed

- Synchronized the registered Home Assistant panel component with the 3.0.7
  frontend asset so the sidebar panel renders instead of remaining black.
- Published the fix under a new versioned asset URL to bypass cached copies of
  the broken 3.0.6 frontend module.

## 3.0.6

### Security

- Hardened the Runtime Runner boundary by starting restored Home Assistant as
  an unprivileged account without inherited Supervisor credentials, Linux
  capabilities, or permission to gain new privileges.
- Added mount, PID, IPC, and UTS isolation alongside the existing isolated
  network namespace, plus a mandatory sandbox preflight and resource limits.
- Prevented incomplete or concurrently replaced uploads from being started and
  bounded archive path length, path depth, and outer archive member processing.
- Added client socket timeouts to limit stalled authenticated requests.

## 3.0.5

### Fixed

- Kept the backup protection progress moving during the blocking archive scan
  with bounded heartbeat updates until verified phase results are available.
- Fixed Runtime Runner metadata discovery for valid archives whose canonical
  `backup.json` entry cannot be resolved by random-access TAR lookup.

### Changed

- Reported Runtime Runner progress in consistent 10-percentage-point log steps.
