# BackupCheckup 3.0.0-beta2 – Coverage

## Release gate

The numerical beta2 gate covers the complete Recovery Readiness, restore
simulation, shared timestamp, frontend registration, and frontend configuration
surface selected in `pyproject.toml`.

| Metric | Result |
|---|---:|
| Tests | 126/126 passed |
| Function entry coverage | 85/85 (100%) |
| Statements | 1003/1003 (100%) |
| Branches | 230/230 (100%) |

The JavaScript panel is protected by syntax validation and executable source and
rendering regressions. Its lines are not mixed into Python's percentage.

## Whole-package cross-check

An additional unfiltered branch run over all Python modules reports 27% total
coverage (1682/5823 statements represented by the coverage result, with partial
branch execution). This number is intentionally reported rather than presenting
the selected 100% beta gate as whole-repository coverage. Older 2.x runtime
modules remain the largest test-expansion opportunity.

## Reproduction

```text
coverage erase
coverage run -m pytest -q
coverage json
coverage report -m
python tools/check_function_coverage.py
python tools/check_branch_coverage.py
node --check custom_components/backup_checkup/frontend/backup-checkup-panel.js
```

