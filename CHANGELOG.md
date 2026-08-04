# Changelog

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
