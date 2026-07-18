# BackupCheckup 2.3.1 – non-administrator refresh hardening

## Scope

BackupCheckup 2.3.0 was explicitly tested with normal Home Assistant users in both
Standard and Expert mode. Its three integration actions were correctly registered as
administrator-only actions. However, Home Assistant's generic `homeassistant.update_entity`
service could still reach `CoordinatorEntity.async_update()` for an entity that the user
was allowed to control. The inherited implementation requested an immediate coordinator
refresh and therefore bypassed BackupCheckup's intended administrator-only refresh
boundary.

## Resolution

BackupCheckup 2.3.1 overrides `async_update()` in the shared `BackupCheckupEntity`
base class. The generic entity-update hook is now deliberately a no-op for every
BackupCheckup sensor, binary sensor, and button.

The following intended paths remain available:

- Home Assistant's scheduled coordinator polling;
- the initial config-entry refresh;
- internal coordinator refreshes;
- the administrator-protected `backup_checkup.refresh` action.

## Security impact

The 2.3.0 behavior did not grant administrator status, expose administrator tokens,
change integration options, or permit the manual integrity-check and test-notification
actions. It did allow a normal user with entity-control permission to trigger the
broader BackupCheckup refresh workflow and its resulting processing.

## Compatibility

- Release: `2.3.1`
- Config-entry schema: version 9
- Migration: none
- Standard mode: hardening active
- Expert mode: hardening active

## Validation

- 266 tests passed.
- 374/374 production functions entered (100.00%).
- Statement coverage: 95.03%.
- Branch coverage: 87.23%.
- Combined statement-and-branch coverage: 93.53%.
- Ruff, formatting, Bandit, Python compilation, strict-warning asyncio tests, and
  repository metadata parsing passed.
