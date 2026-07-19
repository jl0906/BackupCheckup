"""Best-effort setup recommendations derived from the current backup inventory."""

from __future__ import annotations

import math
from collections.abc import Mapping

from homeassistant.components.backup import async_get_manager
from homeassistant.core import HomeAssistant

from .backup_normalizer import BackupRecordNormalizer
from .const import MAX_MAX_VERIFICATION_SIZE_GB, MIN_MAX_VERIFICATION_SIZE_GB

_SETUP_NORMALIZER_ID = "setup-recommendation"
_DOWNLOAD_HEADROOM_RATIO = 1.25
_BYTES_PER_GB = 1_000_000_000


async def async_recommended_verification_size_gb(
    hass: HomeAssistant,
) -> int | None:
    """Return a safe download limit from the largest known backup, when available."""
    try:
        manager = async_get_manager(hass)
        backups, _agent_errors = await manager.async_get_backups()
        if not isinstance(backups, Mapping):
            return None
        normalized = BackupRecordNormalizer(_SETUP_NORMALIZER_ID).normalize(backups)
    except Exception:  # noqa: BLE001 - optional Home Assistant/agent setup boundary
        return None

    sizes = [record.size for record in normalized.records if record.size is not None]
    if not sizes:
        return None
    recommended = math.ceil(max(sizes) * _DOWNLOAD_HEADROOM_RATIO / _BYTES_PER_GB)
    return min(
        MAX_MAX_VERIFICATION_SIZE_GB,
        max(MIN_MAX_VERIFICATION_SIZE_GB, recommended),
    )
