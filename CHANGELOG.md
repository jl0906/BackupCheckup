# Changelog

## 3.0.5

### Fixed

- Kept the backup protection progress moving during the blocking archive scan
  with bounded heartbeat updates until verified phase results are available.
- Fixed Runtime Runner metadata discovery for valid archives whose canonical
  `backup.json` entry cannot be resolved by random-access TAR lookup.

### Changed

- Reported Runtime Runner progress in consistent 10-percentage-point log steps.
