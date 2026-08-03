# BackupCheckup 3.0.0-alpha4 – Coverage report

## Result

The alpha4 regression suite contains **45 passing tests**.

For the production modules introduced or materially changed by the 3.0 Recovery
Readiness work:

| Metric | Result |
| --- | ---: |
| Function entry coverage | 25/25 – 100% |
| Statement coverage | 287/287 – 100% |
| Branch coverage | 62/62 – 100% |
| Missing statements | 0 |
| Partially covered branches | 0 |

The numerical gate covers:

- `custom_components/backup_checkup/recovery.py`
- `custom_components/backup_checkup/recovery_inventory.py`
- `custom_components/backup_checkup/frontend.py`

Existing production modules outside this alpha-specific scope are compiled and
validated by wiring, metadata, translation, and source regression tests, but are
not included in the numerical delta percentage.

## Covered alpha4 behavior

The tests execute and verify:

- all Recovery Readiness score thresholds, deductions, and recommendation
  priorities;
- missing backups and unknown optional metadata;
- detailed privacy-safe content inventory;
- comparison with the previous complete backup;
- additions versus material content regressions;
- removal of Home Assistant, database, add-on, folder, SSL, Share, and Media
  coverage without exposing raw names;
- local, direct-attached, network/NAS, remote, cloud, localized, and unknown
  storage classification;
- confirmed independent failure domains, same-domain copies, local-site copies,
  single copies, zero copies, and unknown targets;
- alpha4 entity, coordinator, diagnostics, translation, and entity-mode wiring;
- exact Python/JavaScript frontend component-name consistency;
- executable JavaScript rendering of the German Recovery tab with content
  inventory, comparison result, and storage-resilience sections.

## Commands

```text
coverage run -m pytest -q
coverage json -o coverage.json
coverage report -m
python tools/check_function_coverage.py
python tools/check_branch_coverage.py
node --check custom_components/backup_checkup/frontend/backup-checkup-panel.js
```
