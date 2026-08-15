# BackupCheckup Runtime Runner

Optional companion app for BackupCheckup. It starts an already verified
backup in a temporary, network-isolated Home Assistant Recovery Mode instance.

Install and configure the BackupCheckup integration first, then start this app and
wait for automatic discovery. Archive size, expanded-size, and startup-time limits
are configured in the BackupCheckup panel and sent to runner 2 with each test.
The next **Check backup protection** run includes the isolated runtime phase.

The runner is versioned independently from the integration. It does not need an
update when only the BackupCheckup integration version changes.

Installation, options, security model, update procedure, result states and
troubleshooting are documented in the
[Runtime Runner Wiki guide](https://github.com/jl0906/BackupCheckup/wiki/Runtime-Runner).
