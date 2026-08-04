# BackupCheckup Runtime Runner

## Installation

1. Install and configure the BackupCheckup integration.
2. Add `https://github.com/jl0906/BackupCheckup` as an App Store repository.
3. Install and start **BackupCheckup Runtime Runner**.
4. Wait for Home Assistant to report that the discovered runner was connected.

The Home Assistant App Store reads this companion app from the repository's
default branch, not from the HACS/GitHub release ZIP. For runner updates, commit
the updated `runtime_runner` directory to that branch, refresh the App Store, and
install the offered app update.

The next **Check backup protection** run includes the isolated runtime phase.
Its upload, restore, boot, readiness probe, and cleanup progress is shown live
in the BackupCheckup Recovery page.

## Safety model

- No Supervisor restore endpoint is called.
- The production Home Assistant configuration is never mounted into the app.
- Home Assistant starts from an extracted temporary copy in Recovery Mode.
- The child process has its own network namespace with loopback only.
- The restored Home Assistant process runs as an unprivileged account with no
  Linux capabilities, no privilege escalation, a secret-free environment, and
  conservative process, file-descriptor, core-dump, and file-size limits.
- The uploaded archive, extracted copy, password, and logs are removed when the
  run completes.
- The API is reachable only on the internal app network. Connections use a
  certificate-pinned TLS channel and require a generated bearer token. Terminal
  evidence is authenticated with HMAC.

The app needs `NET_ADMIN` and `SYS_ADMIN` solely to create and initialize the
network namespace. Those capabilities remain with the small runner controller and
are removed before the restored Home Assistant process starts. Supervisor API access
is used only for the app's self-information and discovery endpoints. The app does
not enable host networking, Docker API access, or Home Assistant API access.

## Options

- `maximum_archive_gb`: Reject larger uploaded archives.
- `maximum_expanded_gb`: Stop extraction when the expanded data exceeds this
  limit.
- `runtime_timeout_minutes`: Stop an ephemeral start that does not become ready
  within this period.

Only one runtime test can run at a time.
