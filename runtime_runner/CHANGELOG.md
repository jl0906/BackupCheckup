# Changelog

## 3

### Added

- Live step progress. `GET /v1/runs/{id}` additionally returns `step` (the
  running step with `state`, `determinate`, `percent`, `done`, `total`, `unit`,
  `started_at`, and `heartbeat_at`) and `steps` (every step with its state).
  `progress_percent` stays available and is calculated from the same step
  weights the integration uses.
- Boot events. `GET /v1/runs/{id}` additionally returns `events` with the
  reached milestones `sandbox_preflight_ok`, `process_started`,
  `port_listening`, and `http_responding`.
- Extended health endpoint. `GET /v1/health` additionally returns
  `capabilities` (`step_progress`, `boot_events`), `uptime_seconds`, and
  `active_runs` next to `runner_version`. It still returns no paths and no host
  information.

### Changed

- Extraction progress is measured from the consumed archive bytes instead of
  jumping from 35 % to 58 %, and the upload reports real byte counters.
- The isolated boot no longer estimates a percentage from the elapsed time. It
  reports its phase, its milestones, and a heartbeat every second.

### Compatibility

- Protocol 2 is unchanged. Every new field is additive.
- Minimum BackupCheckup version: **3.0.14** (protocol 2). Older protocol-2
  integrations keep working and ignore the new fields; live step progress, boot
  events, and the health details need BackupCheckup **3.2.0** or newer.

## 2

### Changed

- Established an independent version line. Runner 2 implements protocol 2 and
  stays compatible with later BackupCheckup releases until the runner protocol
  or implementation actually changes.
- Removed the duplicated Home Assistant app options. The archive,
  expanded-size, and startup-time limits are configured in the BackupCheckup
  panel and sent to the runner with every runtime test.

### Security

- Immutable runner-side safety ranges for every integration-supplied limit, so
  a malformed or compromised client cannot request unbounded extraction or
  runtime duration.

### Compatibility

- Protocol 2.
- Minimum BackupCheckup version: **3.0.14**. BackupCheckup 3.0.14 requires this
  one-time runner update for isolated runtime tests.

## 1

### Added

- Initial release of the network-isolated recovery-mode runner (protocol 1).

### Compatibility

- Protocol 1.
- Minimum BackupCheckup version: the release with the same version number.
  Before the independent version line, runner builds were versioned together
  with BackupCheckup, up to 3.0.13. BackupCheckup 3.0.14 and newer require
  runner 2.
