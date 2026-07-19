"""Best-effort Home Assistant hardware classification for setup recommendations."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.system_info import async_get_system_info

from .const import (
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_ENERGY_SAVING,
    RUNTIME_PROFILE_PERFORMANCE,
)
from .security import safe_error_type

_UNKNOWN = "unknown"
_HARDWARE_DETECTION_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    """Sanitized detection result shown by the setup assistant."""

    installation_type: str
    architecture: str
    board: str
    recommended_profile: str
    confidence: str
    detection: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-safe config-entry representation."""
        return asdict(self)

    @property
    def display_name(self) -> str:
        """Return a concise, non-sensitive hardware description."""
        if self.board != _UNKNOWN:
            return self.board
        if self.architecture != _UNKNOWN:
            return self.architecture
        return _UNKNOWN


def _clean(value: Any) -> str:
    """Return a bounded printable value for the config entry and UI."""
    if not isinstance(value, str):
        return _UNKNOWN
    cleaned = " ".join(value.strip().split())
    return cleaned[:80] or _UNKNOWN


def recommend_runtime_profile(
    *, installation_type: str, architecture: str, board: str
) -> tuple[str, str]:
    """Return a conservative profile recommendation and confidence."""
    board_key = board.casefold()
    architecture_key = architecture.casefold()
    installation_key = installation_type.casefold()

    if board_key in {
        "green",
        "yellow",
        "home assistant green",
        "home assistant yellow",
    }:
        return RUNTIME_PROFILE_APPLIANCE, "high"
    if board_key.startswith(("rpi3", "rpi2", "rpi0")):
        return RUNTIME_PROFILE_ENERGY_SAVING, "high"
    if board_key.startswith(("rpi4", "rpi5")):
        return RUNTIME_PROFILE_APPLIANCE, "high"
    if board_key in {"ova", "generic-x86-64", "generic-aarch64"}:
        return RUNTIME_PROFILE_PERFORMANCE, "medium"
    if architecture_key in {"x86_64", "amd64"}:
        return RUNTIME_PROFILE_PERFORMANCE, "medium"
    if architecture_key in {"armv7", "armhf", "armv6"}:
        return RUNTIME_PROFILE_ENERGY_SAVING, "medium"
    if architecture_key in {"aarch64", "arm64"}:
        return RUNTIME_PROFILE_APPLIANCE, "low"
    if "container" in installation_key or "core" in installation_key:
        return RUNTIME_PROFILE_PERFORMANCE, "low"
    return RUNTIME_PROFILE_APPLIANCE, "low"


async def async_detect_hardware(hass: HomeAssistant) -> HardwareSnapshot:
    """Detect available system information without ever blocking setup."""
    try:
        async with asyncio.timeout(_HARDWARE_DETECTION_TIMEOUT_SECONDS):
            info = await async_get_system_info(hass)
    except Exception as err:  # noqa: BLE001 - optional Home Assistant helper boundary
        return HardwareSnapshot(
            installation_type=_UNKNOWN,
            architecture=_UNKNOWN,
            board=_UNKNOWN,
            recommended_profile=RUNTIME_PROFILE_APPLIANCE,
            confidence="low",
            detection=f"fallback:{safe_error_type(err)}",
        )

    installation_type = _clean(info.get("installation_type"))
    architecture = _clean(info.get("arch") or info.get("container_arch"))
    board = _clean(info.get("board"))
    recommended, confidence = recommend_runtime_profile(
        installation_type=installation_type,
        architecture=architecture,
        board=board,
    )
    return HardwareSnapshot(
        installation_type=installation_type,
        architecture=architecture,
        board=board,
        recommended_profile=recommended,
        confidence=confidence,
        detection="automatic",
    )
