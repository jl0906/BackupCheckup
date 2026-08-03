"""Privacy-safe backup-content and storage-resilience assessment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import BackupAgentSummary, BackupRecord

STORAGE_CLASS_LOCAL_DEVICE = "local_device"
STORAGE_CLASS_DIRECT_ATTACHED = "direct_attached"
STORAGE_CLASS_LOCAL_NETWORK = "local_network"
STORAGE_CLASS_REMOTE = "remote"
STORAGE_CLASS_CLOUD = "cloud"
STORAGE_CLASS_UNKNOWN = "unknown"
STORAGE_CLASS_OPTIONS = (
    STORAGE_CLASS_LOCAL_DEVICE,
    STORAGE_CLASS_DIRECT_ATTACHED,
    STORAGE_CLASS_LOCAL_NETWORK,
    STORAGE_CLASS_REMOTE,
    STORAGE_CLASS_CLOUD,
    STORAGE_CLASS_UNKNOWN,
)

_FAILURE_DOMAINS = {
    STORAGE_CLASS_LOCAL_DEVICE: "home_assistant_device",
    STORAGE_CLASS_DIRECT_ATTACHED: "local_site",
    STORAGE_CLASS_LOCAL_NETWORK: "local_network",
    STORAGE_CLASS_REMOTE: "remote_site",
    STORAGE_CLASS_CLOUD: "cloud_provider",
    STORAGE_CLASS_UNKNOWN: "unknown",
}
_OFF_DEVICE_CLASSES = {
    STORAGE_CLASS_LOCAL_NETWORK,
    STORAGE_CLASS_REMOTE,
    STORAGE_CLASS_CLOUD,
}

_CLOUD_TERMS = {
    "azure",
    "backblaze",
    "cloud",
    "dropbox",
    "gdrive",
    "google",
    "icloud",
    "onedrive",
    "s3",
    "wolke",
}
_REMOTE_TERMS = {"entfernt", "remote", "rsync", "sftp", "ssh", "webdav"}
_NETWORK_TERMS = {
    "cifs",
    "fritz",
    "lan",
    "nas",
    "network",
    "netzwerk",
    "nfs",
    "qnap",
    "samba",
    "smb",
    "synology",
}
_DIRECT_TERMS = {
    "angeschlossen",
    "attached",
    "disk",
    "extern",
    "external",
    "festplatte",
    "hdd",
    "ssd",
    "usb",
}
_LOCAL_TERMS = {"default", "homeassistant", "local", "lokal", "supervisor"}


@dataclass(frozen=True, slots=True)
class ContentInventory:
    """Privacy-safe inventory of the newest monitored backup."""

    backup_reference: str | None
    backup_date: str | None
    homeassistant_included: bool | None
    database_included: bool | None
    addon_count: int
    folder_count: int
    ssl_included: bool | None
    share_included: bool | None
    media_included: bool | None
    other_folder_count: int
    failed_agent_count: int
    failed_addon_count: int
    failed_folder_count: int
    incomplete: bool | None

    @classmethod
    def empty(cls) -> ContentInventory:
        """Return an inventory for an installation without a monitored backup."""
        return cls(
            backup_reference=None,
            backup_date=None,
            homeassistant_included=None,
            database_included=None,
            addon_count=0,
            folder_count=0,
            ssl_included=None,
            share_included=None,
            media_included=None,
            other_folder_count=0,
            failed_agent_count=0,
            failed_addon_count=0,
            failed_folder_count=0,
            incomplete=None,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible public attributes."""
        return {
            "backup_reference": self.backup_reference,
            "backup_date": self.backup_date,
            "homeassistant_included": self.homeassistant_included,
            "database_included": self.database_included,
            "addon_count": self.addon_count,
            "folder_count": self.folder_count,
            "ssl_included": self.ssl_included,
            "share_included": self.share_included,
            "media_included": self.media_included,
            "other_folder_count": self.other_folder_count,
            "failed_agent_count": self.failed_agent_count,
            "failed_addon_count": self.failed_addon_count,
            "failed_folder_count": self.failed_folder_count,
            "incomplete": self.incomplete,
        }


@dataclass(frozen=True, slots=True)
class ContentComparison:
    """Privacy-safe comparison with the previous complete monitored backup."""

    baseline_available: bool
    baseline_reference: str | None
    baseline_date: str | None
    changed: bool | None
    material_regression: bool | None
    homeassistant_removed: bool
    database_removed: bool
    missing_addon_count: int
    added_addon_count: int
    missing_folder_count: int
    added_folder_count: int
    critical_components_missing: tuple[str, ...]
    critical_components_added: tuple[str, ...]

    @classmethod
    def unavailable(cls) -> ContentComparison:
        """Return a comparison without a usable baseline."""
        return cls(
            baseline_available=False,
            baseline_reference=None,
            baseline_date=None,
            changed=None,
            material_regression=None,
            homeassistant_removed=False,
            database_removed=False,
            missing_addon_count=0,
            added_addon_count=0,
            missing_folder_count=0,
            added_folder_count=0,
            critical_components_missing=(),
            critical_components_added=(),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible public attributes without component names."""
        return {
            "baseline_available": self.baseline_available,
            "baseline_reference": self.baseline_reference,
            "baseline_date": self.baseline_date,
            "changed": self.changed,
            "material_regression": self.material_regression,
            "homeassistant_removed": self.homeassistant_removed,
            "database_removed": self.database_removed,
            "missing_addon_count": self.missing_addon_count,
            "added_addon_count": self.added_addon_count,
            "missing_folder_count": self.missing_folder_count,
            "added_folder_count": self.added_folder_count,
            "critical_components_missing": list(self.critical_components_missing),
            "critical_components_added": list(self.critical_components_added),
        }


@dataclass(frozen=True, slots=True)
class StorageResilience:
    """Storage-copy classification without exposing raw storage identifiers."""

    copy_count: int
    classified_copy_count: int
    unknown_copy_count: int
    storage_classes: tuple[str, ...]
    failure_domains: tuple[str, ...]
    failure_domain_count: int
    off_device_copy: bool | None
    multiple_failure_domains: bool | None
    independent_copy: bool | None
    copies: tuple[dict[str, Any], ...]

    @classmethod
    def empty(cls) -> StorageResilience:
        """Return an unknown storage assessment when no backup exists."""
        return cls(
            copy_count=0,
            classified_copy_count=0,
            unknown_copy_count=0,
            storage_classes=(),
            failure_domains=(),
            failure_domain_count=0,
            off_device_copy=None,
            multiple_failure_domains=None,
            independent_copy=None,
            copies=(),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible privacy-safe storage attributes."""
        return {
            "copy_count": self.copy_count,
            "classified_copy_count": self.classified_copy_count,
            "unknown_copy_count": self.unknown_copy_count,
            "storage_classes": list(self.storage_classes),
            "failure_domains": list(self.failure_domains),
            "failure_domain_count": self.failure_domain_count,
            "off_device_copy": self.off_device_copy,
            "multiple_failure_domains": self.multiple_failure_domains,
            "independent_copy": self.independent_copy,
            "copies": list(self.copies),
        }


@dataclass(frozen=True, slots=True)
class RecoveryInventory:
    """Combined content and storage assessment used by Recovery Readiness."""

    content: ContentInventory
    comparison: ContentComparison
    storage: StorageResilience


def _normalized_tokens(*values: str | None) -> set[str]:
    """Return case-folded alphanumeric tokens for heuristic classification."""
    text = " ".join(value for value in values if value).casefold()
    return set(re.findall(r"[a-z0-9]+", text))


def classify_storage(agent_id: str, storage_name: str | None = None) -> str:
    """Classify a backup target conservatively from Home Assistant metadata."""
    tokens = _normalized_tokens(agent_id, storage_name)
    if tokens & _CLOUD_TERMS:
        return STORAGE_CLASS_CLOUD
    if tokens & _REMOTE_TERMS:
        return STORAGE_CLASS_REMOTE
    if tokens & _NETWORK_TERMS:
        return STORAGE_CLASS_LOCAL_NETWORK
    if tokens & _DIRECT_TERMS:
        return STORAGE_CLASS_DIRECT_ATTACHED
    if tokens & _LOCAL_TERMS:
        return STORAGE_CLASS_LOCAL_DEVICE
    return STORAGE_CLASS_UNKNOWN


def _folder_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _folder_category_present(folders: tuple[str, ...], category: str) -> bool:
    return any(category in _folder_tokens(folder) for folder in folders)


def _critical_categories(record: BackupRecord) -> set[str]:
    return {
        category
        for category in ("ssl", "share", "media")
        if _folder_category_present(record.included_folders, category)
    }


def build_content_inventory(latest: BackupRecord | None) -> ContentInventory:
    """Create a detailed but privacy-safe inventory for the latest backup."""
    if latest is None:
        return ContentInventory.empty()
    critical = _critical_categories(latest)
    return ContentInventory(
        backup_reference=latest.backup_reference,
        backup_date=latest.date.isoformat(),
        homeassistant_included=latest.homeassistant_included,
        database_included=latest.database_included,
        addon_count=len(latest.included_addons),
        folder_count=len(latest.included_folders),
        ssl_included="ssl" in critical,
        share_included="share" in critical,
        media_included="media" in critical,
        other_folder_count=max(0, len(latest.included_folders) - len(critical)),
        failed_agent_count=len(latest.failed_agents),
        failed_addon_count=len(latest.failed_addons),
        failed_folder_count=len(latest.failed_folders),
        incomplete=latest.incomplete,
    )


def _previous_complete_backup(
    latest: BackupRecord,
    backups: tuple[BackupRecord, ...],
) -> BackupRecord | None:
    """Return the newest older complete monitored backup as comparison baseline."""
    return next(
        (
            record
            for record in backups
            if record.backup_id != latest.backup_id
            and record.date < latest.date
            and not record.incomplete
        ),
        None,
    )


def compare_backup_content(
    latest: BackupRecord | None,
    backups: tuple[BackupRecord, ...],
) -> ContentComparison:
    """Compare the newest backup with the previous complete backup."""
    if latest is None:
        return ContentComparison.unavailable()
    baseline = _previous_complete_backup(latest, backups)
    if baseline is None:
        return ContentComparison.unavailable()

    latest_addons = set(latest.included_addons)
    baseline_addons = set(baseline.included_addons)
    latest_folders = set(latest.included_folders)
    baseline_folders = set(baseline.included_folders)
    missing_addons = baseline_addons - latest_addons
    added_addons = latest_addons - baseline_addons
    missing_folders = baseline_folders - latest_folders
    added_folders = latest_folders - baseline_folders
    baseline_critical = _critical_categories(baseline)
    latest_critical = _critical_categories(latest)
    critical_missing = tuple(sorted(baseline_critical - latest_critical))
    critical_added = tuple(sorted(latest_critical - baseline_critical))
    homeassistant_removed = (
        baseline.homeassistant_included is True
        and latest.homeassistant_included is not True
    )
    database_removed = (
        baseline.database_included is True and latest.database_included is not True
    )
    changed = bool(
        missing_addons
        or added_addons
        or missing_folders
        or added_folders
        or latest.homeassistant_included != baseline.homeassistant_included
        or latest.database_included != baseline.database_included
        or latest.incomplete != baseline.incomplete
    )
    material_regression = bool(
        latest.incomplete
        or homeassistant_removed
        or database_removed
        or missing_addons
        or missing_folders
        or critical_missing
    )
    return ContentComparison(
        baseline_available=True,
        baseline_reference=baseline.backup_reference,
        baseline_date=baseline.date.isoformat(),
        changed=changed,
        material_regression=material_regression,
        homeassistant_removed=homeassistant_removed,
        database_removed=database_removed,
        missing_addon_count=len(missing_addons),
        added_addon_count=len(added_addons),
        missing_folder_count=len(missing_folders),
        added_folder_count=len(added_folders),
        critical_components_missing=critical_missing,
        critical_components_added=critical_added,
    )


def assess_storage_resilience(
    latest: BackupRecord | None,
    agent_summaries: tuple[BackupAgentSummary, ...],
) -> StorageResilience:
    """Classify copies and determine whether an off-device failure domain exists."""
    if latest is None:
        return StorageResilience.empty()
    names = {summary.agent_id: summary.storage_name for summary in agent_summaries}
    copies: list[dict[str, Any]] = []
    classes: list[str] = []
    domains: list[str] = []
    for copy in latest.agent_copies:
        storage_class = classify_storage(copy.agent_id, names.get(copy.agent_id))
        failure_domain = _FAILURE_DOMAINS[storage_class]
        classes.append(storage_class)
        if failure_domain != "unknown":
            domains.append(failure_domain)
        copies.append(
            {
                "storage_reference": copy.agent_reference,
                "storage_class": storage_class,
                "failure_domain": failure_domain,
                "off_device": storage_class in _OFF_DEVICE_CLASSES,
                "size": copy.size,
                "protected": copy.protected,
            }
        )

    copy_count = len(copies)
    unknown_count = classes.count(STORAGE_CLASS_UNKNOWN)
    known_domains = tuple(sorted(set(domains)))
    class_set = tuple(sorted(set(classes)))
    has_off_device = any(item in _OFF_DEVICE_CLASSES for item in classes)
    if copy_count == 0:
        off_device_copy: bool | None = None
    elif has_off_device:
        off_device_copy = True
    elif unknown_count:
        off_device_copy = None
    else:
        off_device_copy = False

    if copy_count < 2:
        multiple_domains: bool | None = False
        independent_copy: bool | None = False
    elif len(known_domains) >= 2:
        multiple_domains = True
        independent_copy = True if has_off_device else False
    elif unknown_count:
        multiple_domains = None
        independent_copy = None
    else:
        multiple_domains = False
        independent_copy = False

    return StorageResilience(
        copy_count=copy_count,
        classified_copy_count=copy_count - unknown_count,
        unknown_copy_count=unknown_count,
        storage_classes=class_set,
        failure_domains=known_domains,
        failure_domain_count=len(known_domains),
        off_device_copy=off_device_copy,
        multiple_failure_domains=multiple_domains,
        independent_copy=independent_copy,
        copies=tuple(copies),
    )


def build_recovery_inventory(
    latest: BackupRecord | None,
    backups: tuple[BackupRecord, ...],
    agent_summaries: tuple[BackupAgentSummary, ...],
) -> RecoveryInventory:
    """Build all alpha4 recovery inventory and redundancy information."""
    return RecoveryInventory(
        content=build_content_inventory(latest),
        comparison=compare_backup_content(latest, backups),
        storage=assess_storage_resilience(latest, agent_summaries),
    )
