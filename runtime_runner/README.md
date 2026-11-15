# BackupCheckup Runtime Runner

Optional Home Assistant OS companion app for BackupCheckup. The runner uses its
own release version and is updated only when its protocol or implementation changes.

Runner 4 can test backups that contain symbolic or hard links. Runner 3 added
live step progress, boot events, and an extended health endpoint.
Protocol 2 is unchanged, so older BackupCheckup versions keep working with it,
and BackupCheckup 3.2.0 keeps working with runner 2 without the live detail.

See the complete
[Runtime Runner documentation](https://github.com/jl0906/BackupCheckup/wiki/Runtime-Runner).
