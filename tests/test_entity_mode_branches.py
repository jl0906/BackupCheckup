"""Additional entity-registry branch tests."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from custom_components.backup_checkup import entity_mode
from custom_components.backup_checkup.const import (
    ENTITY_MODE_EXPERT,
    ENTITY_MODE_STANDARD,
)


def test_standard_entity_domains_and_unknowns() -> None:
    assert entity_mode.entity_enabled_by_default(
        "binary_sensor", "problem", ENTITY_MODE_STANDARD
    )
    assert entity_mode.entity_enabled_by_default(
        "button", "refresh", ENTITY_MODE_STANDARD
    )
    assert not entity_mode.entity_enabled_by_default(
        "binary_sensor", "unknown", ENTITY_MODE_STANDARD
    )
    assert not entity_mode.entity_enabled_by_default(
        "button", "unknown", ENTITY_MODE_STANDARD
    )
    assert not entity_mode.entity_enabled_by_default(
        "switch", "anything", ENTITY_MODE_STANDARD
    )


def test_registry_mapping_rejects_foreign_prefix_and_standard_agent() -> None:
    assert not entity_mode._registry_entry_should_be_enabled(
        "sensor", "other_latest_backup_age", "entry", ENTITY_MODE_EXPERT
    )
    assert not entity_mode._registry_entry_should_be_enabled(
        "sensor",
        "entry_agent_hassio.local_latest_backup_age",
        "entry",
        ENTITY_MODE_STANDARD,
    )


def test_apply_standard_mode_filters_and_updates_expected_entries(monkeypatch) -> None:
    entry_id = "entry"
    foreign_entry = SimpleNamespace(
        entity_id="sensor.foreign_entry",
        config_entry_id="other",
        platform="backup_checkup",
        domain="sensor",
        unique_id="other_latest_backup_age",
        disabled_by=None,
    )
    foreign_platform = SimpleNamespace(
        entity_id="sensor.foreign_platform",
        config_entry_id=entry_id,
        platform="other",
        domain="sensor",
        unique_id=f"{entry_id}_latest_backup_age",
        disabled_by=None,
    )
    standard_disabled = SimpleNamespace(
        entity_id="sensor.standard_disabled",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_latest_backup_age",
        disabled_by=RegistryEntryDisabler.INTEGRATION,
    )
    expert_only_enabled = SimpleNamespace(
        entity_id="sensor.expert_only",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_integrity_checksum",
        disabled_by=None,
    )
    expert_only_user_disabled = SimpleNamespace(
        entity_id="sensor.user_disabled",
        config_entry_id=entry_id,
        platform="backup_checkup",
        domain="sensor",
        unique_id=f"{entry_id}_integrity_checksum",
        disabled_by=RegistryEntryDisabler.USER,
    )

    class Registry:
        def __init__(self) -> None:
            self.entities = {
                item.entity_id: item
                for item in (
                    foreign_entry,
                    foreign_platform,
                    standard_disabled,
                    expert_only_enabled,
                    expert_only_user_disabled,
                )
            }
            self.updates: list[tuple[str, object]] = []

        def async_update_entity(self, entity_id: str, *, disabled_by) -> None:
            self.updates.append((entity_id, disabled_by))
            self.entities[entity_id].disabled_by = disabled_by

    registry = Registry()
    monkeypatch.setattr(entity_mode.er, "async_get", lambda _hass: registry)

    entity_mode.async_apply_entity_mode(
        object(),
        SimpleNamespace(entry_id=entry_id),
        ENTITY_MODE_STANDARD,
    )

    assert standard_disabled.disabled_by is None
    assert expert_only_enabled.disabled_by is RegistryEntryDisabler.INTEGRATION
    assert expert_only_user_disabled.disabled_by is RegistryEntryDisabler.USER
    assert foreign_entry.disabled_by is None
    assert foreign_platform.disabled_by is None
    assert len(registry.updates) == 2


def test_apply_mode_can_skip_disabling_other_entities(monkeypatch) -> None:
    entity = SimpleNamespace(
        entity_id="sensor.expert_only",
        config_entry_id="entry",
        platform="backup_checkup",
        domain="sensor",
        unique_id="entry_integrity_checksum",
        disabled_by=None,
    )
    registry = SimpleNamespace(
        entities={entity.entity_id: entity},
        async_update_entity=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not update")
        ),
    )
    monkeypatch.setattr(entity_mode.er, "async_get", lambda _hass: registry)

    entity_mode.async_apply_entity_mode(
        object(),
        SimpleNamespace(entry_id="entry"),
        ENTITY_MODE_STANDARD,
        disable_others=False,
    )
    assert entity.disabled_by is None
