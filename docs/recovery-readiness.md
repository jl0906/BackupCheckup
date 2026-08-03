# Recovery Readiness

BackupCheckup 3.0.0-alpha5 provides a separate disaster-recovery assessment. It
answers whether the newest monitored backup and the surrounding recovery
preparation provide a credible basis for restoring Home Assistant after a total
system failure. It remains separate from the normal backup Health Score.

## Readiness checks

The score evaluates thirteen points:

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
  complete backup;
- the guided emergency checklist is complete;
- external dependencies have been reviewed and are protected or not applicable.

Confirmed missing items receive their full deduction. Unknown Home Assistant,
database, storage, checklist, or dependency information receives a smaller
uncertainty deduction so the integration does not claim readiness without evidence.
A missing content-comparison baseline is shown as **Not assessed** and does not
reduce the score.

A numeric score of at least 85 is not sufficient by itself for the `ready` status.
Both the guided checklist and the external-dependency review must also be complete.
Otherwise the status remains `limited` and the next required action is shown.

## Guided emergency checklist

The Recovery / Notfallvorsorge tab allows an administrator to confirm fixed states
for:

- availability of the backup password;
- documented access to external backup storage;
- knowledge of the restore procedure;
- availability of replacement hardware or installation media;
- documented network access required after a restore;
- documented recovery contacts and account ownership.

Each item supports only `confirmed`, `missing`, `not_required`, or `unknown`.
BackupCheckup does not accept free text, passwords, paths, notes, hostnames, account
names, or tokens. Confirmations are stored only in a private Home Assistant Store
belonging to the config entry.

Confirmations expire after 180 days. An expired item becomes effectively `unknown`
until it is reviewed again, while the original timestamp remains available for the
frontend to show that a review expired.

## External dependencies

Alpha5 provides fixed categories for:

- external databases;
- MQTT brokers;
- Zigbee coordinators;
- Z-Wave controllers;
- Thread or Matter infrastructure;
- ESPHome configuration;
- network storage or NAS systems;
- reverse proxies;
- certificates;
- cloud services and API access.

Each category can be marked `protected`, `unprotected`, `not_applicable`, or
`unknown`. Every category must be reviewed before BackupCheckup reports external
dependencies as fully protected. This also allows installations without an
automatically detected dependency to complete the review by marking irrelevant
categories as not applicable.

BackupCheckup can highlight possible dependencies by reading only configured
integration domains and existing aggregate backup/storage metadata. It does not
inspect integration configuration, broker addresses, database URLs, credentials,
certificates, API keys, or other secrets. Automatic detection currently covers
MQTT, ZHA/deCONZ, Z-Wave JS, Thread/Matter, ESPHome, an excluded database, and
off-device network/cloud backup storage. Other categories remain available for
manual assessment.

## Administrator action

The frontend uses the administrator-only action:

`backup_checkup.set_recovery_preparedness`

It accepts exactly three fixed fields: `section`, `item`, and `status`. Both the
action schema and the handler validate the values. Normal users can view the
privacy-safe assessment but cannot change it.

## Backup content inventory

The Recovery tab shows a privacy-safe inventory of the latest monitored backup:

- Home Assistant data and database inclusion;
- number of included add-ons and folders;
- whether SSL, Share, and Media are represented;
- aggregate counts of failed storage copies, add-ons, and folders;
- whether the backup is incomplete.

Raw add-on names, folder names, backup names, IDs, and paths are not published.

## Comparison with the previous complete backup

BackupCheckup compares the latest monitored backup with the newest older backup
that completed without failed components. It reports:

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

A second storage target is not automatically treated as independent. BackupCheckup
conservatively classifies copies as:

- Home Assistant device;
- directly attached storage;
- local network or NAS;
- remote storage;
- cloud storage;
- unknown.

An independent copy requires at least two copies, a known off-device target, and at
least two known failure domains. Two copies on the same NAS class, two unknown
targets, or local storage plus a directly attached disk are therefore not presented
as confirmed independent disaster-recovery copies.

`binary_sensor.backup_checkup_external_copy_missing` is on only when the known
storage classification confirms that no independent off-device copy exists. Unknown
targets remain **Not assessed** instead of being reported as definitely independent
or definitely missing.

## Status thresholds

- Ready: score 85–100 and both preparedness reviews complete
- Limited: score 55–100 with a remaining preparedness gap, or score 55–84
- Insufficient: score 0–54 or no backup

## Entities

The main Recovery Readiness entities are:

- `sensor.backup_checkup_recovery_readiness`;
- `sensor.backup_checkup_recovery_status`;
- `sensor.backup_checkup_recovery_recommendation`;
- `binary_sensor.backup_checkup_external_copy_missing`;
- `binary_sensor.backup_checkup_backup_content_changed`;
- `binary_sensor.backup_checkup_recovery_checklist_incomplete`;
- `binary_sensor.backup_checkup_external_dependency_unprotected`.

The readiness sensor includes the complete privacy-safe checklist and dependency
snapshot as attributes. Diagnostics contain the same bounded enum states and
aggregate counts.

## Safety and privacy

The assessment is non-destructive. It does not create, modify, restore, upload, or
delete backups. Normal entities and diagnostics contain only anonymous references,
booleans, fixed enum states, generic storage/dependency classes, aggregate counts,
scores, timestamps, and recommendations.

Removing the config entry removes the dedicated private preparedness Store together
with BackupCheckup's other private stores. Orphan cleanup also recognizes the new
store type.

## Planned later alphas

Later 3.0 alphas can add persisted confirmation of manual test restores, an expanded
simulated restore assessment, and exportable recovery plans. A destructive restore
action remains intentionally outside the planned integration scope.
