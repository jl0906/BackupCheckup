# Recovery Readiness

BackupCheckup 3.0.0-alpha1 introduces a separate recovery assessment. It answers
whether the latest monitored backup provides a credible basis for recovery, not
only whether normal backup operation is healthy.

## Checks

The score evaluates backup availability and age, completeness, Home Assistant
and database inclusion, integrity verification, optional database verification,
an independent second copy, and consistent copy sizes. Confirmed missing items
receive their full deduction. Unknown optional metadata receives a smaller
deduction so the integration does not claim readiness without evidence.

## Status thresholds

- Ready: 85–100
- Limited: 55–84
- Insufficient: 0–54 or no backup

## Safety and privacy

The assessment is read-only. Entity attributes and diagnostics contain only
boolean checks, deduction names, scores, status, and recommendations. Backup
names, IDs, paths, passwords, notification targets, and file contents are not
exposed.

## Planned alpha sequence

Later 3.0 alphas can add a guided emergency checklist, persisted confirmation of
manual test restores, external-dependency declarations, and exportable recovery
plans. A destructive restore action is intentionally outside the alpha1 scope.
