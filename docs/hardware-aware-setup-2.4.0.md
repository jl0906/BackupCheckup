# BackupCheckup 2.4.0 – hardware-aware setup and adaptive polling

## Purpose

BackupCheckup 2.4.0 replaces the combined 2.3.x monitoring profile with independent configuration groups:

- runtime and resource profile;
- backup-health monitoring policy;
- integrity-verification strategy;
- entity, privacy, and notification settings.

This prevents hardware performance from implicitly deciding how strict backup protection should be.

## Detection and recommendation

During initial setup BackupCheckup reads Home Assistant's available system information. It uses installation type, CPU architecture, and board information when Home Assistant exposes it. Detection is best effort and setup always continues with a conservative fallback if system information is unavailable.

The detected values are sanitized, bounded, and stored only as setup metadata. BackupCheckup does not benchmark the host, inspect arbitrary files, or infer CPU and memory limits that Home Assistant does not expose consistently.

The recommendation is never applied silently after setup. The user must confirm the profile, and future BackupCheckup versions do not automatically replace stored values.

## Runtime profiles

| Profile | Base | Active | Error backoff | Download | Expanded | Verify timeout | DB timeout | Manual cooldown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Energy saving | 15 min | 2 min | 45 min | 25 GB | 125 GB | 90 min | 20 min | 30 min |
| Home Assistant appliance | 10 min | 1 min | 30 min | 50 GB | 250 GB | 60 min | 15 min | 15 min |
| High performance | 5 min | 1 min | 20 min | 100 GB | 500 GB | 45 min | 10 min | 10 min |
| Server | 2 min | 1 min | 10 min | 250 GB | 1000 GB | 30 min | 10 min | 5 min |

Custom mode exposes all values. The active interval cannot be longer than the base interval, and the error-backoff interval cannot be shorter than the base interval.

During the guided assistant, BackupCheckup also reads the current inventory on a best-effort basis. When a known backup is larger than the selected profile budget, the proposed download limit is raised to at least 125% of the largest known backup and the expanded-data limit is raised consistently. Inventory failure never blocks setup, and Custom mode remains fully user-controlled.

## Adaptive polling

When enabled, BackupCheckup subscribes to the native backup-manager state and automatic-backup event entities by stable registry identity. This continues to work if the user renames those entities.

- Native backup activity schedules an immediate coalesced refresh.
- While the manager reports an active backup, the active interval is used.
- After the configured number of consecutive inventory failures, the error-backoff interval is used.
- A successful inventory read resets the error counter and restores the appropriate normal or active interval.
- Unload cancels pending adaptive refresh tasks and removes every event subscription.

Disabling adaptive polling retains a fixed base interval.

## Monitoring policies

Balanced and Strict resolve to complete concrete values. Custom exposes all health thresholds. Monitoring policy is independent from the runtime profile and integrity strategy.

## Verification strategies

- Manual only: automatic verification and database checking are disabled.
- Automatic: each newly detected newest regular backup is verified once.
- Deep: automatic verification plus SQLite `PRAGMA integrity_check`.

Deep verification is never selected solely because a powerful hardware profile was recommended.

## Config-entry migration

Schema version 10 migrates existing 2.3.x entries without changing behavior:

- every stored numeric threshold, interval, limit, privacy setting, notification target, and entity mode is preserved;
- the runtime profile becomes `legacy_custom`;
- adaptive polling remains disabled so the previous fixed polling behavior is retained;
- monitoring and verification policy labels are derived from the old resolved settings;
- the complete assistant can later be run voluntarily from the options menu.

No entity-registry changes occur during migration. Entity-mode application remains part of normal config-entry setup.

## Diagnostics

Diagnostics include the saved runtime, monitoring, and verification configuration plus the current adaptive state: disabled, normal, backup active, or error backoff. Hardware metadata remains bounded and contains no file paths, hostnames, IP addresses, tokens, or arbitrary exception messages.
