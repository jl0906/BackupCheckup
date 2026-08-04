# Revision - BackupCheckup 3.0.0

## Release outcome

Version 3.0.0 consolidates the adaptive Recovery Readiness work into one stable
workflow and adds the optional isolated Runtime Runner for Home Assistant OS.

## Live runtime pipeline

The existing **Check backup protection** action now performs these phases when
the companion app is available:

1. structural verification of the selected backup copy;
2. authenticated streaming upload of that exact temporary archive;
3. bounded extraction into private runner storage;
4. Home Assistant startup in Recovery Mode and an isolated network namespace;
5. a loopback readiness probe;
6. termination and deterministic cleanup.

Both structural and runtime stages are published immediately through the
coordinator. The Recovery frontend displays their stage states and percentages
without polling a second service or introducing a new primary button.

## Evidence and scoring

A passed runtime test upgrades the existing evidence level to
**Runtime-ready** only if the runner response is authenticated and matches the
backup reference and SHA-256 digest produced by structural verification. It is
an additional internal proof level, not a separate check or score. The legacy
numeric Recovery score is unchanged.

## Safety boundaries

- No Supervisor restore endpoint is used.
- No production Home Assistant directory is mounted or modified.
- The ephemeral child receives loopback networking only.
- The companion app has no Home Assistant API or Docker API access.
- Passwords are held only for the active protected-archive extraction and are
  never included in frontend state, diagnostics, logs, or stored evidence.
- Archive size, expanded size, member count, paths, and runtime duration are
  bounded.
- Uploaded and extracted data is removed after every terminal outcome.
