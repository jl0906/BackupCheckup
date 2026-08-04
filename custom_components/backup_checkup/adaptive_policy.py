"""Adaptive recovery-check policy derived from the configured system profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    RUNTIME_PROFILE_APPLIANCE,
    RUNTIME_PROFILE_CUSTOM,
    RUNTIME_PROFILE_ENERGY_SAVING,
    RUNTIME_PROFILE_LEGACY,
    RUNTIME_PROFILE_PERFORMANCE,
    RUNTIME_PROFILE_SERVER,
)

POLICY_COMPACT = "compact"
POLICY_BALANCED = "balanced"
POLICY_EXTENDED = "extended"
POLICY_ENTERPRISE = "enterprise"


@dataclass(frozen=True, slots=True)
class AdaptiveRecoveryPolicy:
    """Resource and presentation policy for one BackupCheckup installation."""

    profile: str
    presentation: str
    inventory_interval_minutes: int
    structural_check_automatic: bool
    database_check_enabled: bool
    ephemeral_runner_available: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return privacy-safe policy information for the frontend."""
        return {
            "profile": self.profile,
            "presentation": self.presentation,
            "inventory_interval_minutes": self.inventory_interval_minutes,
            "structural_check_automatic": self.structural_check_automatic,
            "database_check_enabled": self.database_check_enabled,
            "ephemeral_runner_available": self.ephemeral_runner_available,
            "ephemeral_test_mode": (
                "manual" if self.ephemeral_runner_available else "not_available"
            ),
        }


_PRESENTATION_BY_PROFILE = {
    RUNTIME_PROFILE_ENERGY_SAVING: POLICY_COMPACT,
    RUNTIME_PROFILE_APPLIANCE: POLICY_BALANCED,
    RUNTIME_PROFILE_PERFORMANCE: POLICY_EXTENDED,
    RUNTIME_PROFILE_SERVER: POLICY_ENTERPRISE,
    RUNTIME_PROFILE_CUSTOM: POLICY_EXTENDED,
    RUNTIME_PROFILE_LEGACY: POLICY_EXTENDED,
}


def resolve_adaptive_policy(
    *,
    runtime_profile: str,
    update_interval_minutes: int,
    auto_verify_new_backups: bool,
    database_integrity_check: bool,
    ephemeral_runner_available: bool = False,
) -> AdaptiveRecoveryPolicy:
    """Resolve a deterministic policy without silently enabling deeper checks."""
    return AdaptiveRecoveryPolicy(
        profile=runtime_profile,
        presentation=_PRESENTATION_BY_PROFILE.get(runtime_profile, POLICY_BALANCED),
        inventory_interval_minutes=max(1, int(update_interval_minutes)),
        structural_check_automatic=bool(auto_verify_new_backups),
        database_check_enabled=bool(database_integrity_check),
        ephemeral_runner_available=bool(ephemeral_runner_available),
    )
