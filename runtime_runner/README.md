# BackupCheckup Runtime Runner

Optional companion app for BackupCheckup 3.0.4. It receives only a backup that
has already passed structural verification, restores the Home Assistant portion
into a temporary private directory, and starts it in Recovery Mode inside a
separate network namespace.

The app does not expose a host port and does not receive Home Assistant API
access. Supervisor discovery connects it to the BackupCheckup integration with
a generated private token.
