# BackupCheckup 3.0.0-alpha3 – Coverage report

## Scope

Alpha3 retains the complete Recovery Readiness calculation and Python frontend
registration coverage from alpha2 and adds executable frontend-view regression
tests for the newly visible recovery interface.

Numerical Python coverage includes:

- `custom_components/backup_checkup/recovery.py`
- `custom_components/backup_checkup/frontend.py`

The bundled JavaScript is additionally executed in a browser-like Node VM. The
test verifies custom-element registration, configured and fallback entity IDs,
German localization, model creation, overview rendering, the dedicated recovery
tab, all check result states, deduction rows, empty deductions, and recovery tone
branches.

## Result

| Metric | Result |
|---|---:|
| Tests | 24 passed |
| Python function coverage | 6/6 (100.00%) |
| Python statement coverage | 94/94 (100.00%) |
| Python branch coverage | 26/26 (100.00%) |
| Uncovered Python lines | 0 |
| Partial Python branches | 0 |
| JavaScript syntax and registration | Passed |
| JavaScript visible recovery view execution | Passed |

## Frontend regression guarantees

- Recovery Readiness is shown as a metric in the Overview tab.
- A dedicated Recovery / Notfallvorsorge tab is present.
- Score, status, priority recommendation, checks, and deductions are read from
  the three recovery entities and rendered visibly.
- True, false, and unknown check states are distinguishable.
- An empty deduction set is rendered as a positive result.
- Python and JavaScript use the identical versioned custom-element name.
