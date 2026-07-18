"""Regression tests for BackupCheckup 2.3.1 authorization hardening."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.backup_checkup.button import BackupCheckupRefreshButton
from custom_components.backup_checkup.const import (
    CONF_ENTITY_MODE,
    ENTITY_MODE_EXPERT,
    ENTITY_MODE_STANDARD,
)
from custom_components.backup_checkup.entity import BackupCheckupEntity


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [ENTITY_MODE_STANDARD, ENTITY_MODE_EXPERT])
async def test_generic_update_entity_cannot_request_refresh(mode: str) -> None:
    """A permitted generic entity update remains a no-op in every entity mode."""
    coordinator = SimpleNamespace(
        hass=None,
        last_update_success=True,
        async_request_refresh=AsyncMock(),
    )
    entry = ConfigEntry(entry_id="entry", data={CONF_ENTITY_MODE: mode})
    entity = BackupCheckupRefreshButton(coordinator, entry)

    await entity.async_update()

    coordinator.async_request_refresh.assert_not_awaited()


def test_all_backupcheckup_entities_override_coordinator_refresh_hook() -> None:
    """The shared base class owns the hardening for every current entity platform."""
    assert "async_update" in BackupCheckupEntity.__dict__
