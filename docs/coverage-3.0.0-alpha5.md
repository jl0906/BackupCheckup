# BackupCheckup 3.0.0-alpha5 – Coverage report

## Result

The alpha5 regression suite contains **65 passing tests**.

For all production modules introduced or materially changed by the 3.0 recovery
work:

| Metric | Result |
| --- | ---: |
| Functions executed | **40 / 40 (100%)** |
| Statements executed | **470 / 470 (100%)** |
| Branches executed | **108 / 108 (100%)** |
| Missing statements | **0** |
| Partial branches | **0** |

The measured modules are:

- `recovery.py`;
- `recovery_inventory.py`;
- `recovery_preparedness.py`;
- `frontend.py`.

## Covered alpha5 behavior

The suite exercises:

- private Store creation, loading, serialization, reset, removal, and malformed
  value rejection;
- fixed checklist/dependency key and status validation;
- 180-day expiry, timezone normalization, and expired-state handling;
- completion with detected dependencies and with an entirely manual
  not-applicable review;
- automatic dependency detection boundaries without secret/configuration access;
- Recovery Readiness deductions, status gating, and recommendation priority;
- administrator action registration and privacy-safe activity details;
- coordinator, entities, diagnostics, entity modes, translations, and exact-path
  store cleanup;
- visible German frontend output, editable admin controls, read-only non-admin
  controls, and the service call payload;
- versioned custom-element registration and JavaScript syntax.

## Scope

These percentages intentionally describe the 3.0 recovery modules rather than
claiming whole-repository coverage. Existing 2.x modules continue to be protected by
older regression tests and repository validation. The included coverage gates fail
below 95% statement or branch coverage and separately require every function in the
listed modules to execute.
