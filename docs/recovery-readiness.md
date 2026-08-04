# Recovery readiness

BackupCheckup 3.0.0 presents disaster recovery as one adaptive workflow.
The normal interface no longer exposes integrity verification, restore
simulation, integration checks, and test-restore documentation as competing
mandatory tasks.

## One protection check

The administrator action **Check backup protection** uses the existing hardened,
read-only pipeline. It selects an available copy, downloads the newest monitored
backup, decrypts it when required, validates its metadata, reads all outer and
inner archive members, optionally checks the SQLite database, and removes all
temporary data.

The structural phase never writes restored data or invokes Home Assistant's
restore endpoint. When the optional Runtime Runner is installed, the verified
archive is started only from a temporary copy in an isolated Recovery Mode
instance. The production configuration and add-ons are not started or changed.

The primary button calls `backup_checkup.simulate_restore`. The former
`backup_checkup.verify_latest_backup` action remains as a compatibility alias and
runs the same pipeline. Its separate button is disabled by default for new entity
registry entries.

## Evidence levels

BackupCheckup reports the strongest available recovery proof:

| Evidence | Meaning |
| --- | --- |
| Not recoverable | No usable monitored backup is available. |
| Limited | A confirmed blocker prevents reliable recovery. |
| Monitored | Inventory and health are known, but the backup has not been structurally verified. |
| Structurally verified | The current backup passed the complete protected read pipeline. |
| Runtime-ready | The exact structurally verified backup reached the local Home Assistant endpoint in an isolated Recovery Mode instance. |
| Fully tested | A current successful full external test restore is documented. |

A documented test restore is optional. Its absence does not reduce the Recovery
score, create a required action, or block the structurally verified level.
Similarly, the guided emergency checklist is optional preparedness information.

The legacy numeric Recovery score and diagnostic checks remain available for
automations and compatibility, but the normal frontend leads with the evidence
level.

## External dependencies

BackupCheckup automatically detects relevant dependency categories from
privacy-safe signals such as configured integration domains and aggregate backup
storage metadata. Current automatic coverage includes:

- MQTT;
- ZHA or deCONZ;
- Z-Wave JS;
- Thread or Matter;
- ESPHome;
- an external database when the database is excluded from the backup;
- network, remote, or cloud backup storage.

Only automatically detected or previously configured categories are shown. An
undetected category with no saved user state is hidden and does not count as an
unreviewed requirement.

Detection can establish that a dependency exists, but not whether its external
data is recoverable. The user therefore confirms only one bounded state:
`protected`, `unprotected`, `not_applicable`, or `unknown`. No addresses,
credentials, notes, configuration contents, or secrets are read or stored.

Detected unknown dependencies appear as an open confirmation request but do not
receive an automatic score deduction. A dependency explicitly marked
`unprotected` remains an actionable risk.

The frontend updates the selected state immediately. Persistence and recovery
recalculation continue asynchronously, avoiding the previous full-refresh delay
after each dropdown change.

## Adaptive system policy

One integration package serves all supported systems. The configured runtime
profile controls foreground detail density, polling, and resource budgets:

| Runtime profile | Presentation | Normal inventory interval |
| --- | --- | ---: |
| Energy saving | Compact | 15 minutes |
| Home Assistant appliance | Balanced | 10 minutes |
| Performance | Extended | 5 minutes |
| Server | Server-oriented | 2 minutes |

Custom and legacy-custom profiles use the configured interval and an extended
technical presentation.

Hardware strength never silently enables deeper verification. Automatic
structural checks and database inspection remain explicit settings. The runtime
phase is available only after the optional companion app is installed.

## Frontend structure

The Recovery tab contains:

1. the strongest confirmed evidence level;
2. one priority action;
3. the adaptive scope in use;
4. one graphical live protection pipeline;
5. open risks;
6. automatically detected dependencies.

Inventory details, comparison data, storage classification, the guided
checklist, optional external test-restore documentation, the legacy numeric score,
and recovery-plan exports are grouped under a collapsed technical-details area.

## Optional documented test restore

`backup_checkup.record_restore_test` stores only fixed enum values, the current
timestamp, and an anonymous backup reference. A current successful full restore
raises the evidence level to **Fully tested**. Failed, partial, expired, absent,
or malformed records do not invalidate an otherwise successful structural check.

## Optional isolated runtime runner

On Home Assistant OS, the separately installed BackupCheckup Runtime Runner is
connected through Supervisor discovery. It receives the already verified
archive over an authenticated internal connection and publishes live progress
for upload, temporary restore, boot, readiness probe, and cleanup. The frontend
shows those stages directly below the structural pipeline.

The runner extracts into private temporary storage and launches Home Assistant
in Recovery Mode inside a separate network namespace with loopback only. It
does not call a Supervisor restore endpoint, mount the production configuration,
start add-ons, use the Docker API, or receive Home Assistant API access. Uploaded
data and the extracted instance are deleted at completion. A result counts as
**Runtime-ready** only when its authenticated runner identity, backup reference,
SHA-256 digest, isolation proof, and readiness result all match.

This remains part of the existing protection check and evidence model. It does
not add a new score or primary action. Installation details are in
[`runtime_runner/DOCS.md`](../runtime_runner/DOCS.md).

## Privacy and cleanup

Recovery stores are private, bounded, and owned by the config entry. Removing the
entry removes preparedness and documented-test state. The live pipeline and
exports exclude raw backup IDs, backup names, paths, passwords, tokens, hostnames,
IP addresses, integration configuration, and backup contents.
