"""Notification-target selection tests."""

from types import SimpleNamespace

from custom_components.backup_checkup import notification_selection


def test_normalize_notification_targets_accepts_legacy_single_value() -> None:
    """A previously stored single entity is migrated in memory to a list."""
    assert notification_selection.normalize_notification_targets(
        "notify.mobile_app_phone"
    ) == ["notify.mobile_app_phone"]


def test_normalize_notification_targets_deduplicates_and_rejects_invalid() -> None:
    """Only unique notify entity IDs are retained."""
    assert notification_selection.normalize_notification_targets(
        [
            "notify.mobile_app_phone",
            "notify.mobile_app_phone",
            " sensor.invalid ",
            123,
            " notify.mobile_app_tablet ",
        ]
    ) == ["notify.mobile_app_phone", "notify.mobile_app_tablet"]


def test_mobile_notification_options_lists_multiple_companion_devices(
    monkeypatch,
) -> None:
    """All enabled Companion App notify entities become selectable options."""
    entries = {
        "notify.mobile_app_phone": SimpleNamespace(
            entity_id="notify.mobile_app_phone",
            platform="mobile_app",
            disabled_by=None,
            name=None,
            original_name="Phone",
        ),
        "notify.mobile_app_tablet": SimpleNamespace(
            entity_id="notify.mobile_app_tablet",
            platform="mobile_app",
            disabled_by=None,
            name="Tablet notifications",
            original_name="Tablet",
        ),
        "notify.other": SimpleNamespace(
            entity_id="notify.other",
            platform="other",
            disabled_by=None,
            name="Other",
            original_name="Other",
        ),
    }
    registry = SimpleNamespace(entities=entries)
    monkeypatch.setattr(
        notification_selection.er,
        "async_get",
        lambda _hass: registry,
    )
    states = {
        "notify.mobile_app_phone": SimpleNamespace(name="Jan's phone"),
    }
    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))

    options = notification_selection.mobile_notification_options(hass)

    assert options == [
        {"value": "notify.mobile_app_phone", "label": "Jan's phone"},
        {
            "value": "notify.mobile_app_tablet",
            "label": "Tablet notifications",
        },
    ]


def test_selected_unavailable_target_remains_editable(monkeypatch) -> None:
    """A saved target is not silently lost while its entity is unavailable."""
    registry = SimpleNamespace(entities={})
    monkeypatch.setattr(
        notification_selection.er,
        "async_get",
        lambda _hass: registry,
    )
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda _entity_id: None))

    options = notification_selection.mobile_notification_options(
        hass,
        ["notify.mobile_app_old_phone"],
    )

    assert options == [
        {
            "value": "notify.mobile_app_old_phone",
            "label": "notify.mobile_app_old_phone",
        }
    ]


def test_config_flow_uses_explicit_multiple_select() -> None:
    """The options flow renders a real multi-select instead of a single entity field."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "backup_checkup"
        / "config_flow.py"
    ).read_text()
    selector_block = source.split("CONF_NOTIFICATION_TARGETS", 2)[2].split(
        "CONF_NOTIFY_ON_RECOVERY", 1
    )[0]

    assert "mobile_notification_options" in selector_block
    assert "multiple=True" in selector_block
    assert "mode=SelectSelectorMode.LIST" in selector_block
