# BackupCheckup Runtime Runner

Optional companion app for BackupCheckup. It starts an already verified
backup in a temporary, network-isolated Home Assistant Recovery Mode instance.

Install and configure the BackupCheckup integration first, then start this app and
wait for automatic discovery. Archive size, expanded-size, and startup-time limits
are configured in the BackupCheckup panel and sent to the runner with each test.
The next **Check backup protection** run includes the isolated runtime phase.

The runner is versioned independently from the integration. It does not need an
update when only the BackupCheckup integration version changes.

## Runner 3

Protocol 2 is unchanged. Every new field is additive, so BackupCheckup 3.1.0 and
older keep working with this runner and simply ignore them. BackupCheckup 3.2.0
and newer use them for the live display.

- `GET /v1/runs/{id}` additionally returns `step` (the running step with
  `state`, `determinate`, `percent`, `done`, `total`, `unit`, `started_at`, and
  `heartbeat_at`), `steps` (every step with its state), and `events` (the boot
  milestones `sandbox_preflight_ok`, `process_started`, `port_listening`, and
  `http_responding`). `progress_percent` stays available and is now calculated
  from the same step weights the integration uses.
- Extraction progress is measured from the consumed archive bytes, and the
  upload reports real byte counters.
- The isolated boot no longer estimates a percentage from elapsed time. It
  reports its phase, its milestones, and a heartbeat every second.
- `GET /v1/health` additionally returns `runner_version`, `capabilities`
  (`step_progress`, `boot_events`), `uptime_seconds`, and `active_runs`. It
  still returns no paths and no host information.

BackupCheckup 3.2.0 requires at least runner 2 and recommends runner 3. With
runner 2 the runtime test keeps working and shows its phases; live step
progress, boot events, and the extended health details need runner 3.

Installation, options, security model, update procedure, result states and
troubleshooting are documented in the
[Runtime Runner Wiki guide](https://github.com/jl0906/BackupCheckup/wiki/Runtime-Runner).
