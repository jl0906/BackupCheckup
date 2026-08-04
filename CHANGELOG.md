# Changelog

## 3.0.0

### Added

- Added Recovery Readiness with a single evidence level: monitored,
  structurally verified, runtime-ready, fully tested, limited, or not recoverable.
- Added **Check backup protection**, a unified administrator action for the
  strongest available backup verification.
- Added a live recovery pipeline with stage status, total progress, runtime,
  archive and file counters, processed data volume, and grouped results.
- Added the optional Home Assistant OS Runtime Runner for starting the exact
  verified backup in a temporary, isolated Home Assistant Recovery Mode instance.
- Added authenticated runner discovery, internal archive upload, bounded
  extraction, readiness probing, signed evidence, timeouts, and cleanup.
- Added recovery inventory and comparison of the newest complete backups without
  exposing backup names or content details.
- Added failure-domain-aware storage classification for local, direct-attached,
  network, cloud, and unknown storage.
- Added a guided emergency checklist and automatic detection of relevant external
  dependencies such as MQTT, Zigbee, Z-Wave, Thread/Matter, ESPHome, external
  databases, and network storage.
- Added privacy-safe documentation of external restore tests and local emergency
  plan exports in Markdown, HTML, and JSON.
- Added an administrator-only Settings page to the sidebar.

### Changed

- Replaced separate verification and simulation controls with one primary
  protection check. The former verify service remains as a compatibility alias.
- Simplified the Recovery page around one evidence status, one priority action,
  open risks, live progress, and optional preparedness details.
- Made runtime verification and documented external restore tests additional
  evidence instead of separate scores or required checks.
- Made recovery presentation and resource budgets adapt to the selected system
  profile without silently enabling deeper checks.
- Made only detected or previously configured external dependencies require user
  confirmation.
- Kept successful structural readiness independent of optional preparedness
  confirmations and external restore documentation.

### Fixed

- Fixed dependency selections waiting for a full coordinator refresh before
  appearing in the interface.
- Fixed unused dependency categories being shown as required.
- Fixed missing optional restore documentation reducing the Recovery score.
- Fixed resource profiles presenting the same foreground detail on small and
  high-performance installations.
- Fixed runner failures, cancellations, timeouts, and malformed responses losing
  their precise terminal state or cleanup path.
