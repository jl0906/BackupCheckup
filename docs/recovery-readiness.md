# Recovery Readiness

BackupCheckup 3.0.0-alpha4 provides a separate disaster-recovery assessment. It
answers whether the newest monitored backup provides a credible basis for
restoring Home Assistant after a total system failure, not only whether routine
backup operation is healthy.

## Readiness checks

The score evaluates eleven points:

- a monitored backup exists;
- the backup is current;
- the backup completed without failed components;
- Home Assistant data is included;
- the database is included;
- the archive was successfully verified;
- the optional database verification succeeded;
- a copy exists in a confirmed independent failure domain;
- multiple failure domains are represented;
- redundant copy sizes are consistent;
- the latest backup has not lost contents that were present in the previous
  complete backup.

Confirmed missing items receive their full deduction. Unknown Home Assistant,
database, or storage classification receives a smaller deduction so the
integration does not claim readiness without evidence. A missing comparison
baseline is shown as **Not assessed** and does not reduce the score.

## Backup content inventory

The Recovery tab shows a privacy-safe inventory of the latest monitored backup:

- Home Assistant data and database inclusion;
- number of included add-ons and folders;
- whether SSL, Share, and Media are represented;
- aggregate counts of failed storage copies, add-ons, and folders;
- whether the backup is incomplete.

Raw add-on names, folder names, backup names, IDs, and paths are not published.

## Comparison with the previous complete backup

Alpha4 compares the latest monitored backup with the newest older backup that
completed without failed components. It reports:

- added and removed add-on counts;
- added and removed folder counts;
- removal of Home Assistant or database data;
- generic critical categories that disappeared: SSL, Share, or Media;
- whether the change is only an expansion or a material regression.

Adding new contents does not create a problem. A material regression turns on
`binary_sensor.backup_checkup_backup_content_changed`, reduces the Recovery
Readiness Score, and becomes the highest-priority recovery recommendation unless
the newest backup is already incomplete.

## Failure-domain-aware storage assessment

A second storage target is no longer automatically treated as independent.
BackupCheckup conservatively classifies copies as:

- Home Assistant device;
- directly attached storage;
- local network or NAS;
- remote storage;
- cloud storage;
- unknown.

An independent copy requires at least two copies, a known off-device target, and
at least two known failure domains. Two copies on the same NAS class, two unknown
targets, or local storage plus a directly attached disk are therefore not
presented as confirmed independent disaster-recovery copies.

`binary_sensor.backup_checkup_external_copy_missing` is on only when the known
storage classification confirms that no independent off-device copy exists.
Unknown targets remain **Not assessed** instead of being reported as definitely
independent or definitely missing.

## Status thresholds

- Ready: 85–100
- Limited: 55–84
- Insufficient: 0–54 or no backup

## Sidebar frontend

The optional sidebar panel shows the Recovery Readiness Score in the main
overview and provides a dedicated **Recovery / Notfallvorsorge** tab. The tab
contains the localized recovery status, highest-priority recommendation, all
eleven checks, weighted deductions, detailed content inventory, comparison with
the previous complete backup, and failure-domain-aware storage resilience.

## Safety and privacy

The complete assessment is read-only. It does not create, modify, restore,
upload, or delete backups. Normal entities and diagnostics contain only anonymous
references, booleans, generic storage classes, generic critical folder
categories, aggregate counts, scores, status, and recommendations.

## Planned later alphas

Later 3.0 alphas can add a guided emergency checklist, persisted confirmation of
manual test restores, external-dependency declarations, and exportable recovery
plans. A destructive restore action remains intentionally outside the planned
integration scope.
