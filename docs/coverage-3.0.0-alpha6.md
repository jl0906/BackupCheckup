# BackupCheckup 3.0.0-alpha6 – Coverage report

## Result

The alpha6 regression suite contains **88 passing tests**.

For every production module introduced or materially changed by the complete 3.0
Recovery Readiness work:

| Metric | Result |
| --- | ---: |
| Functions executed | **60 / 60 (100%)** |
| Statements executed | **724 / 724 (100%)** |
| Branches executed | **166 / 166 (100%)** |
| Missing statements | **0** |
| Partial branches | **0** |

The measured modules are:

- `recovery.py`;
- `recovery_inventory.py`;
- `recovery_preparedness.py`;
- `recovery_restore.py`;
- `recovery_simulation.py`;
- `recovery_plan.py`;
- `frontend.py`.

## Covered alpha6 behavior

The suite executes:

- private restore-test Store creation, date normalization, bounded validity,
  serialization, loading, clearing, removal, malformed-data rejection, and
  storage failures;
- strict fixed result and scope validation, successful, failed, full, partial,
  current, expired, and future-timestamp behavior;
- all structural simulation outcomes: not run, passed, passed with warnings, and
  failed with blocking conditions;
- latest-backup matching, archive/file counts, verified-size plausibility,
  optional database verification, encrypted backup readability, and storage-copy
  availability;
- German and English emergency-plan generation, fallback installation labels,
  dependency inclusion, warning generation, HTML escaping, and Markdown, HTML,
  and JSON exports;
- Recovery Readiness score deductions, status gates, and simulation/test-restore
  recommendation priority;
- coordinator, service, entity, entity-mode, diagnostics, translation, migration,
  and exact-path private-store cleanup wiring;
- executable German frontend rendering for the simulation, documented restore,
  and emergency-plan cards;
- administrator service payloads, read-only non-admin behavior, browser download
  creation, file extensions, and object-URL cleanup;
- custom-element registration and JavaScript syntax.

## Scope and gates

These percentages describe the complete 3.0 Recovery Readiness production-module
set rather than claiming whole-repository coverage. Existing 2.x modules remain
protected by their established regression tests and repository validation.

Alpha6's included gates require **100% statement coverage, 100% branch coverage,
and execution of every function** in the listed modules.
