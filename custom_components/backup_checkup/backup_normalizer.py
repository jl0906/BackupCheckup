"""Defensive normalization of Home Assistant backup inventory models."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .classification import classify_backup_purpose
from .models import BackupAgentRecord, BackupRecord
from .security import (
    anonymous_agent_reference,
    anonymous_backup_reference,
    backup_scope_fingerprint,
)

_MAX_BACKUP_ID_LENGTH = 1024
_MAX_AGENT_ID_LENGTH = 512
_MAX_TEXT_ITEM_LENGTH = 512
_MAX_BACKUP_NAME_LENGTH = 512
_COPY_SIZE_MISMATCH_MIN_BYTES = 1_000_000
_COPY_SIZE_MISMATCH_RATIO = 0.01


@dataclass(frozen=True, slots=True)
class CopySizeComparison:
    """Material size difference between redundant copies."""

    mismatch: bool
    spread_bytes: int | None


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Normalized inventory plus discarded-record counters."""

    records: tuple[BackupRecord, ...]
    invalid_backups: int
    invalid_agent_copies: int


class ThirdPartyBoundary:
    """Contain unsafe properties and iterators from external backup agents."""

    @staticmethod
    def attribute(value: Any, name: str, default: Any = None) -> Any:
        """Read a third-party property without allowing it to break refresh."""
        try:
            return getattr(value, name, default)
        except (MemoryError, RecursionError):
            raise
        except Exception:  # noqa: BLE001 - deliberate external-object boundary
            return default

    @staticmethod
    def text(
        value: Any,
        *,
        maximum: int,
        strip: bool = True,
    ) -> str | None:
        """Return bounded text or None when conversion itself is unsafe."""
        try:
            text = str(value)
        except (MemoryError, RecursionError):
            raise
        except Exception:  # noqa: BLE001 - deliberate external-object boundary
            return None
        if strip:
            text = text.strip()
        return text[:maximum] if text else None

    @staticmethod
    def mapping_items(value: Any) -> tuple[tuple[Any, Any], ...]:
        """Materialize mapping items behind one guarded boundary."""
        if not isinstance(value, Mapping):
            return ()
        try:
            return tuple(value.items())
        except (MemoryError, RecursionError):
            raise
        except Exception:  # noqa: BLE001 - deliberate external-object boundary
            return ()

    @staticmethod
    def mapping_is_empty(value: Mapping[Any, Any]) -> bool | None:
        """Return mapping emptiness or None when even length access is unsafe."""
        try:
            return len(value) == 0
        except (MemoryError, RecursionError):
            raise
        except Exception:  # noqa: BLE001 - deliberate external-object boundary
            return None

    @staticmethod
    def iterable(value: Any) -> tuple[Any, ...]:
        """Materialize an arbitrary non-string iterable defensively."""
        if isinstance(value, str) or value is None:
            return ()
        try:
            return tuple(value)
        except (MemoryError, RecursionError):
            raise
        except Exception:  # noqa: BLE001 - deliberate external-object boundary
            return ()


class BackupRecordNormalizer:
    """Convert Home Assistant backup models to stable local records."""

    def __init__(self, entry_id: str) -> None:
        """Initialize the normalizer for installation-local references."""
        self._entry_id = entry_id

    @staticmethod
    def as_datetime(value: Any) -> datetime | None:
        """Convert a value to an aware UTC datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            text = ThirdPartyBoundary.text(value, maximum=128)
            parsed = dt_util.parse_datetime(text) if text else None
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return dt_util.as_utc(parsed)

    @staticmethod
    def as_bool(value: Any) -> bool | None:
        """Return a strict boolean value when one is available."""
        return value if isinstance(value, bool) else None

    @staticmethod
    def as_nonnegative_int(value: Any) -> int | None:
        """Return a finite integral non-negative number without truncation."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if isinstance(value, float):
            if not math.isfinite(value) or not value.is_integer():
                return None
        normalized = int(value)
        return normalized if normalized >= 0 else None

    @staticmethod
    def string_tuple(value: Any) -> tuple[str, ...]:
        """Normalize a mapping or iterable to sorted unique bounded strings."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            values = ThirdPartyBoundary.mapping_items(value)
            iterable = tuple(key for key, _item in values)
        elif isinstance(value, str):
            iterable = (value,)
        else:
            iterable = ThirdPartyBoundary.iterable(value)
        normalized = {
            text
            for item in iterable
            if (text := ThirdPartyBoundary.text(item, maximum=_MAX_TEXT_ITEM_LENGTH))
        }
        return tuple(sorted(normalized))

    @staticmethod
    def addon_slugs(value: Any) -> tuple[str, ...]:
        """Normalize Home Assistant add-on metadata to sorted slugs."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            iterable = tuple(
                item for _key, item in ThirdPartyBoundary.mapping_items(value)
            )
        elif isinstance(value, str):
            iterable = (value,)
        else:
            iterable = ThirdPartyBoundary.iterable(value)

        slugs: set[str] = set()
        for addon in iterable:
            slug = ThirdPartyBoundary.attribute(addon, "slug", None)
            if slug is None and isinstance(addon, Mapping):
                for key, candidate in ThirdPartyBoundary.mapping_items(addon):
                    if key == "slug":
                        slug = candidate
                        break
            text = ThirdPartyBoundary.text(slug, maximum=_MAX_TEXT_ITEM_LENGTH)
            if text:
                slugs.add(text)
        return tuple(sorted(slugs))

    @staticmethod
    def compare_copy_sizes(sizes: list[int]) -> CopySizeComparison:
        """Return whether reported redundant-copy sizes differ materially."""
        if len(sizes) < 2:
            return CopySizeComparison(False, None)
        smallest = min(sizes)
        largest = max(sizes)
        spread = largest - smallest
        tolerance = max(
            _COPY_SIZE_MISMATCH_MIN_BYTES,
            int(largest * _COPY_SIZE_MISMATCH_RATIO),
        )
        return CopySizeComparison(spread > tolerance, spread)

    def _agent_copy(self, agent_id: Any, details: Any) -> BackupAgentRecord | None:
        """Normalize one backup-agent copy record across HA model versions."""
        normalized_agent_id = ThirdPartyBoundary.text(
            agent_id,
            maximum=_MAX_AGENT_ID_LENGTH,
        )
        if normalized_agent_id is None:
            return None

        size_raw = ThirdPartyBoundary.attribute(details, "size", None)
        protected_raw = ThirdPartyBoundary.attribute(details, "protected", None)
        if protected_raw is None:
            protected_raw = ThirdPartyBoundary.attribute(details, "is_protected", None)
        if isinstance(details, Mapping):
            for key, value in ThirdPartyBoundary.mapping_items(details):
                if key == "size" and size_raw is None:
                    size_raw = value
                elif key in {"protected", "is_protected"} and protected_raw is None:
                    protected_raw = value

        return BackupAgentRecord(
            normalized_agent_id,
            anonymous_agent_reference(self._entry_id, normalized_agent_id),
            self.as_nonnegative_int(size_raw),
            protected_raw if isinstance(protected_raw, bool) else None,
        )

    def _agent_copies(self, value: Any) -> tuple[tuple[BackupAgentRecord, ...], int]:
        """Normalize all agent copies and return the invalid-copy count."""
        copies: list[BackupAgentRecord] = []
        invalid = 0
        if isinstance(value, Mapping):
            items = ThirdPartyBoundary.mapping_items(value)
            if not items:
                is_empty = ThirdPartyBoundary.mapping_is_empty(value)
                if is_empty is None:
                    return (), 1
                if is_empty:
                    return (), 0
            for agent_id, details in items:
                copy = self._agent_copy(agent_id, details)
                if copy is None:
                    invalid += 1
                else:
                    copies.append(copy)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for agent_id in ThirdPartyBoundary.iterable(value):
                normalized = ThirdPartyBoundary.text(
                    agent_id,
                    maximum=_MAX_AGENT_ID_LENGTH,
                )
                if normalized is None:
                    invalid += 1
                    continue
                copies.append(
                    BackupAgentRecord(
                        normalized,
                        anonymous_agent_reference(self._entry_id, normalized),
                        None,
                        None,
                    )
                )
        else:
            return (), 1

        deduplicated = {copy.agent_id: copy for copy in copies}
        return (
            tuple(sorted(deduplicated.values(), key=lambda item: item.agent_id)),
            invalid,
        )

    def _normalize_backup(self, backup: Any) -> tuple[BackupRecord, int]:
        """Normalize one backup or raise ValueError for an unusable record."""
        backup_id_raw = ThirdPartyBoundary.attribute(backup, "backup_id", None)
        if not isinstance(backup_id_raw, str):
            raise ValueError("invalid_backup_id")
        backup_id = backup_id_raw.strip()
        if not backup_id or len(backup_id) > _MAX_BACKUP_ID_LENGTH:
            raise ValueError("invalid_backup_id")

        backup_date = self.as_datetime(
            ThirdPartyBoundary.attribute(backup, "date", None)
        )
        if backup_date is None:
            raise ValueError("invalid_backup_date")

        agents_raw = ThirdPartyBoundary.attribute(backup, "agents", {}) or {}
        agent_copies, invalid_agent_copies = self._agent_copies(agents_raw)
        agents = tuple(copy.agent_id for copy in agent_copies)

        failed_agents = self.string_tuple(
            ThirdPartyBoundary.attribute(backup, "failed_agent_ids", None)
            or ThirdPartyBoundary.attribute(backup, "failed_agents", None)
        )
        failed_addons = self.string_tuple(
            ThirdPartyBoundary.attribute(backup, "failed_addons", None)
            or ThirdPartyBoundary.attribute(backup, "failed_addon_ids", None)
        )
        failed_folders = self.string_tuple(
            ThirdPartyBoundary.attribute(backup, "failed_folders", None)
            or ThirdPartyBoundary.attribute(backup, "failed_folder_ids", None)
        )

        known_sizes = [copy.size for copy in agent_copies if copy.size is not None]
        legacy_size = self.as_nonnegative_int(
            ThirdPartyBoundary.attribute(backup, "size", None)
        )
        size = max(known_sizes) if known_sizes else legacy_size
        size_comparison = self.compare_copy_sizes(known_sizes)
        automatic = (
            ThirdPartyBoundary.attribute(backup, "with_automatic_settings", None)
            is True
        )
        included_addons = self.addon_slugs(
            ThirdPartyBoundary.attribute(backup, "addons", None)
        )
        included_folders = self.string_tuple(
            ThirdPartyBoundary.attribute(backup, "folders", None)
        )
        database_included = self.as_bool(
            ThirdPartyBoundary.attribute(backup, "database_included", None)
        )
        homeassistant_included = self.as_bool(
            ThirdPartyBoundary.attribute(backup, "homeassistant_included", None)
        )
        name = (
            ThirdPartyBoundary.text(
                ThirdPartyBoundary.attribute(backup, "name", ""),
                maximum=_MAX_BACKUP_NAME_LENGTH,
                strip=False,
            )
            or ""
        )
        purpose = classify_backup_purpose(
            automatic=automatic,
            extra_metadata=ThirdPartyBoundary.attribute(backup, "extra_metadata", None),
        )

        record = BackupRecord(
            backup_id=backup_id,
            backup_reference=anonymous_backup_reference(self._entry_id, backup_id),
            name=name,
            date=backup_date,
            automatic=automatic,
            purpose=purpose,
            included_addons=included_addons,
            included_folders=included_folders,
            scope_fingerprint=backup_scope_fingerprint(
                entry_id=self._entry_id,
                homeassistant_included=homeassistant_included,
                database_included=database_included,
                addons=included_addons,
                folders=included_folders,
            ),
            agents=agents,
            agent_copies=agent_copies,
            failed_agents=failed_agents,
            failed_addons=failed_addons,
            failed_folders=failed_folders,
            database_included=database_included,
            homeassistant_included=homeassistant_included,
            size=size,
            incomplete=bool(failed_agents or failed_addons or failed_folders),
            copy_size_mismatch=size_comparison.mismatch,
            copy_size_spread_bytes=size_comparison.spread_bytes,
        )
        return record, invalid_agent_copies

    def normalize(self, backups: Mapping[str, Any]) -> NormalizationResult:
        """Normalize a complete inventory while isolating invalid records."""
        records: list[BackupRecord] = []
        invalid_backups = 0
        invalid_agent_copies = 0
        seen_backup_ids: set[str] = set()

        for _inventory_key, backup in ThirdPartyBoundary.mapping_items(backups):
            try:
                record, invalid_copies = self._normalize_backup(backup)
            except (MemoryError, RecursionError):
                raise
            except Exception:  # noqa: BLE001 - one external record boundary
                invalid_backups += 1
                continue
            if record.backup_id in seen_backup_ids:
                invalid_backups += 1
                continue
            # Register the ID only after the record is fully valid. A malformed first
            # duplicate can therefore no longer hide a later valid copy.
            seen_backup_ids.add(record.backup_id)
            invalid_agent_copies += invalid_copies
            records.append(record)

        records.sort(key=lambda item: item.date, reverse=True)
        return NormalizationResult(
            records=tuple(records),
            invalid_backups=invalid_backups,
            invalid_agent_copies=invalid_agent_copies,
        )
