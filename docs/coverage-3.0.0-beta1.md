# BackupCheckup 3.0.0-beta1 – Coverage report

The beta1 regression suite contains **114 passing tests**.

## Selected production-module coverage

| Metric | Covered | Total | Result |
| --- | ---: | ---: | ---: |
| Functions | 71 | 71 | 100% |
| Statements | 867 | 867 | 100% |
| Branches | 218 | 218 | 100% |

The numerical gate covers the complete 3.0 recovery production set plus the
frontend registration and new frontend configuration API:

- `recovery.py`
- `recovery_inventory.py`
- `recovery_preparedness.py`
- `recovery_restore.py`
- `recovery_simulation.py`
- `recovery_plan.py`
- `frontend.py`
- `frontend_config.py`

## Beta1-specific execution coverage

The suite executes:

- both administrator-only WebSocket commands;
- valid and invalid config-entry resolution;
- all preset and custom resolution paths;
- strict boolean, integer, range, enum and notification-target validation;
- every cross-field validation branch;
- legacy runtime-profile presentation;
- privacy-safe payload generation;
- config-entry persistence and exactly one scheduled reload;
- command registration during integration setup;
- the real JavaScript settings editor in Node, including loading, visible German
  content, form edits, multiple notification targets, saving, validation feedback,
  resetting and non-admin hiding.

JavaScript is protected through executable behavior tests and syntax checks. Its
coverage is not mixed into Python's numerical percentages.

The included coverage gates require 100% functions, statements and branches for
all listed Python modules.
