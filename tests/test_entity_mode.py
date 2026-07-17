"""Entity preset behavior."""

from custom_components.backup_checkup.const import (
    ENTITY_MODE_EXPERT,
    ENTITY_MODE_STANDARD,
)
from custom_components.backup_checkup.entity_mode import (
    _registry_entry_should_be_enabled,
    entity_enabled_by_default,
)


def test_expert_mode_enables_every_global_entity() -> None:
    """Expert mode includes exact timestamps and deep diagnostics."""
    for key in (
        "latest_backup",
        "latest_automatic_backup",
        "latest_manual_backup",
        "integrity_checksum",
        "database_integrity_status",
        "required_location_missing",
    ):
        domain = "binary_sensor" if key == "required_location_missing" else "sensor"
        assert entity_enabled_by_default(domain, key, ENTITY_MODE_EXPERT)


def test_expert_mode_enables_every_storage_entity() -> None:
    """Per-storage timestamps are no longer hard-disabled in Expert mode."""
    for metric in (
        "backups",
        "latest_backup",
        "latest_backup_age",
        "latest_backup_size",
        "stored_bytes",
        "problem",
    ):
        domain = "binary_sensor" if metric == "problem" else "sensor"
        assert entity_enabled_by_default(
            domain,
            metric,
            ENTITY_MODE_EXPERT,
            agent_entity=True,
        )


def test_standard_mode_remains_compact() -> None:
    """Standard mode keeps duplicate timestamps and storage details disabled."""
    assert entity_enabled_by_default(
        "sensor", "latest_backup_age", ENTITY_MODE_STANDARD
    )
    assert not entity_enabled_by_default(
        "sensor", "latest_backup", ENTITY_MODE_STANDARD
    )
    assert not entity_enabled_by_default(
        "sensor",
        "latest_backup_age",
        ENTITY_MODE_STANDARD,
        agent_entity=True,
    )


def test_registry_mapping_matches_expert_preset() -> None:
    """Existing global and storage timestamp registry entries are enabled."""
    entry_id = "entry"
    assert _registry_entry_should_be_enabled(
        "sensor",
        f"{entry_id}_latest_backup",
        entry_id,
        ENTITY_MODE_EXPERT,
    )
    assert _registry_entry_should_be_enabled(
        "sensor",
        f"{entry_id}_agent_hassio.local_latest_backup",
        entry_id,
        ENTITY_MODE_EXPERT,
    )
    assert not _registry_entry_should_be_enabled(
        "sensor",
        f"{entry_id}_latest_backup",
        entry_id,
        ENTITY_MODE_STANDARD,
    )


def test_apply_expert_mode_repairs_only_integration_disabled_entities(
    monkeypatch,
) -> None:
    """Expert mode enables integration defaults without overriding user choices."""
    from types import SimpleNamespace

    from homeassistant.helpers.entity_registry import RegistryEntryDisabler

    from custom_components.backup_checkup import entity_mode

    entry_id = "entry"
    integration_disabled = SimpleNamespace(
        entity_id="sensor.backup_checkup_latest_backup",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_latest_backup",
        disabled_by=RegistryEntryDisabler.INTEGRATION,
    )
    user_disabled = SimpleNamespace(
        entity_id="sensor.backup_checkup_integrity_checksum",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_integrity_checksum",
        disabled_by=RegistryEntryDisabler.USER,
    )
    config_entry_disabled = SimpleNamespace(
        entity_id="sensor.backup_checkup_local_latest_backup",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_agent_hassio.local_latest_backup",
        disabled_by=RegistryEntryDisabler.CONFIG_ENTRY,
    )

    class Registry:
        def __init__(self) -> None:
            self.entities = {
                item.entity_id: item
                for item in (
                    integration_disabled,
                    user_disabled,
                    config_entry_disabled,
                )
            }

        def async_update_entity(self, entity_id: str, *, disabled_by) -> None:
            self.entities[entity_id].disabled_by = disabled_by

    registry = Registry()
    monkeypatch.setattr(entity_mode.er, "async_get", lambda _hass: registry)

    entity_mode.async_apply_entity_mode(
        object(),
        SimpleNamespace(entry_id=entry_id),
        ENTITY_MODE_EXPERT,
        disable_others=False,
    )

    assert integration_disabled.disabled_by is None
    assert user_disabled.disabled_by is RegistryEntryDisabler.USER
    assert config_entry_disabled.disabled_by is RegistryEntryDisabler.CONFIG_ENTRY
