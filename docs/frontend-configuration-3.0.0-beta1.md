# Integrated frontend configuration – 3.0.0-beta1

BackupCheckup beta1 can manage its complete integration configuration directly
inside the optional sidebar panel. The standard Home Assistant options flow is
still available and uses the same canonical configuration model.

## Why a dedicated API is used

A custom panel should not depend on Home Assistant's internal config-flow frontend
protocol. BackupCheckup therefore registers two integration-owned WebSocket
commands:

- `backup_checkup/config/get`
- `backup_checkup/config/update`

Both commands require an administrator. The browser never writes the config entry
directly. Python validates and resolves the complete submitted snapshot before it
calls Home Assistant's config-entry update API.

## Settings available in the panel

The editor includes:

- runtime profile, adaptive polling, polling intervals, error backoff, download,
  expansion and timeout limits;
- monitoring policy, age, size and redundancy thresholds, repairs and analytics;
- verification policy, automatic verification and optional database checks;
- entity mode, metadata exposure and sidebar visibility;
- detailed live logging, persistence and retention;
- mobile notifications, multiple Companion App targets and recovery notices.

Preset-specific values are resolved on the backend. Selecting `custom` exposes the
same underlying limits that are available through the Home Assistant options flow.

## Validation and persistence

The backend accepts only known configuration keys and strict JSON value types. It
checks numeric ranges, enum values and relationships between settings, including:

- active polling cannot be slower than normal polling;
- error backoff cannot be shorter than normal polling;
- the expanded-size limit cannot be below the download limit;
- fixed size monitoring requires a non-zero minimum;
- enabled notifications require at least one valid target.

A valid snapshot is normalized, stored atomically in both config-entry data and
options, and followed by one integration reload. Invalid input is returned as
field-specific error codes without changing the existing configuration.

## Permissions and privacy

Only Home Assistant administrators can load or save settings. The panel also hides
the settings tab from non-administrators, but the backend permission check remains
the security boundary.

The API returns only BackupCheckup's own configuration, published limits, fixed
option lists, privacy-safe hardware recommendation fields, and available mobile
notification entity IDs with display labels. It does not expose backup contents,
passwords, tokens, paths, hosts, IP addresses or configuration from other
integrations.

## Fallback behavior

The normal **Settings → Devices & services → BackupCheckup → Configure** flow is
kept deliberately. It remains useful when:

- the sidebar panel is disabled;
- frontend assets cannot be loaded;
- an administrator turns off the sidebar from inside the panel;
- a future Home Assistant frontend change temporarily affects the custom panel.

Both interfaces use the same normalized settings and can be used interchangeably.
