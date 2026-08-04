# Changelog

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
