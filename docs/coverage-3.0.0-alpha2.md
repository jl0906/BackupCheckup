# BackupCheckup 3.0.0-alpha2 – Coverage report

## Scope

The alpha2 regression suite covers every new or changed production path introduced
by the Recovery Readiness generation and the frontend loading repair:

- `custom_components/backup_checkup/recovery.py`
- `custom_components/backup_checkup/frontend.py`
- the bundled `frontend/backup-checkup-panel.js` registration entry point

The JavaScript smoke test executes the complete bundle in a minimal browser-like
custom-element registry. Python coverage uses branch instrumentation and an AST-based
function-entry gate. Existing integration modules that were unchanged by alpha2 are
still checked through compilation, JSON/YAML parsing, translation consistency, and
frontend syntax validation, but are not included in the numerical alpha2 delta
coverage percentages below.

## Result

| Metric | Result |
|---|---:|
| Tests | 22 passed |
| Function coverage | 6/6 (100.00%) |
| Statement coverage | 94/94 (100.00%) |
| Branch coverage | 26/26 (100.00%) |
| Uncovered lines | 0 |
| Partial branches | 0 |

## Regressions explicitly covered

- Python and JavaScript custom-element names must be identical.
- The versioned alpha2 panel asset must be registered with cache headers.
- Disabled, successful, renamed-entity, fallback-entity, and duplicate-panel paths.
- No-backup readiness must be exactly 0%.
- Ready, limited, and insufficient score boundaries.
- Valid and valid-with-warnings integrity results.
- Stale, incomplete, unverified, non-redundant, database-unverified, unknown-content,
  missing-content, and inconsistent-copy paths.
- Recommendation priority: complete backup, verification, external copy, database
  verification, then no action.
