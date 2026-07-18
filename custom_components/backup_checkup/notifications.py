"""Mobile notification support for BackupCheckup."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations

from .activity import (
    ACTIVITY_OUTCOME_CHANGED,
    ACTIVITY_OUTCOME_COMPLETED,
    ACTIVITY_OUTCOME_FAILED,
    ACTIVITY_OUTCOME_STARTED,
    BackupCheckupActivityLog,
)
from .const import DOMAIN
from .models import BackupCheckupData
from .notification_selection import normalize_notification_targets
from .repairs import async_set_storage_data_issue
from .security import classify_exception, safe_error_type

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "problem_title": "BackupCheckup: Problem detected",
        "problem_message": (
            "Status: {status}\nRecommendation: {recommendation}\n"
            "Active problems: {count}"
        ),
        "recovery_title": "BackupCheckup: Backups healthy",
        "recovery_message": (
            "All previously reported backup problems have been resolved."
        ),
        "test_title": "BackupCheckup: Test notification",
        "test_message": "Mobile notifications are configured correctly.",
    },
    "de": {
        "problem_title": "BackupCheckup: Problem erkannt",
        "problem_message": (
            "Status: {status}\nEmpfehlung: {recommendation}\nAktive Probleme: {count}"
        ),
        "recovery_title": "BackupCheckup: Backups in Ordnung",
        "recovery_message": "Alle zuvor gemeldeten Backup-Probleme wurden behoben.",
        "test_title": "BackupCheckup: Testbenachrichtigung",
        "test_message": "Mobile Benachrichtigungen sind korrekt eingerichtet.",
    },
    "nl": {
        "problem_title": "BackupCheckup: Probleem gedetecteerd",
        "problem_message": (
            "Status: {status}\nAanbeveling: {recommendation}\n"
            "Actieve problemen: {count}"
        ),
        "recovery_title": "BackupCheckup: Back-ups in orde",
        "recovery_message": "Alle eerder gemelde back-upproblemen zijn opgelost.",
        "test_title": "BackupCheckup: Testmelding",
        "test_message": "Mobiele meldingen zijn correct ingesteld.",
    },
    "pl": {
        "problem_title": "BackupCheckup: Wykryto problem",
        "problem_message": (
            "Stan: {status}\nZalecenie: {recommendation}\nAktywne problemy: {count}"
        ),
        "recovery_title": "BackupCheckup: Kopie są prawidłowe",
        "recovery_message": (
            "Wszystkie wcześniej zgłoszone problemy z kopiami zostały rozwiązane."
        ),
        "test_title": "BackupCheckup: Powiadomienie testowe",
        "test_message": "Powiadomienia mobilne są skonfigurowane prawidłowo.",
    },
    "sv": {
        "problem_title": "BackupCheckup: Problem upptäckt",
        "problem_message": (
            "Status: {status}\nRekommendation: {recommendation}\n"
            "Aktiva problem: {count}"
        ),
        "recovery_title": "BackupCheckup: Säkerhetskopiorna är OK",
        "recovery_message": (
            "Alla tidigare rapporterade säkerhetskopieringsproblem har lösts."
        ),
        "test_title": "BackupCheckup: Testavisering",
        "test_message": "Mobilaviseringar är korrekt konfigurerade.",
    },
    "it": {
        "problem_title": "BackupCheckup: Problema rilevato",
        "problem_message": (
            "Stato: {status}\nRaccomandazione: {recommendation}\n"
            "Problemi attivi: {count}"
        ),
        "recovery_title": "BackupCheckup: Backup in ordine",
        "recovery_message": (
            "Tutti i problemi di backup segnalati in precedenza sono stati risolti."
        ),
        "test_title": "BackupCheckup: Notifica di prova",
        "test_message": "Le notifiche mobili sono configurate correttamente.",
    },
    "fr": {
        "problem_title": "BackupCheckup : problème détecté",
        "problem_message": (
            "État : {status}\nRecommandation : {recommendation}\n"
            "Problèmes actifs : {count}"
        ),
        "recovery_title": "BackupCheckup : sauvegardes correctes",
        "recovery_message": (
            "Tous les problèmes de sauvegarde précédemment signalés ont été résolus."
        ),
        "test_title": "BackupCheckup : notification de test",
        "test_message": "Les notifications mobiles sont correctement configurées.",
    },
    "da": {
        "problem_title": "BackupCheckup: Problem registreret",
        "problem_message": (
            "Status: {status}\nAnbefaling: {recommendation}\nAktive problemer: {count}"
        ),
        "recovery_title": "BackupCheckup: Sikkerhedskopier er i orden",
        "recovery_message": (
            "Alle tidligere rapporterede problemer med sikkerhedskopier er løst."
        ),
        "test_title": "BackupCheckup: Testnotifikation",
        "test_message": "Mobilnotifikationer er konfigureret korrekt.",
    },
    "es": {
        "problem_title": "BackupCheckup: Problema detectado",
        "problem_message": (
            "Estado: {status}\nRecomendación: {recommendation}\n"
            "Problemas activos: {count}"
        ),
        "recovery_title": "BackupCheckup: Copias correctas",
        "recovery_message": (
            "Todos los problemas de copia de seguridad notificados anteriormente "
            "se han resuelto."
        ),
        "test_title": "BackupCheckup: Notificación de prueba",
        "test_message": "Las notificaciones móviles están configuradas correctamente.",
    },
}


class BackupCheckupNotificationManager:
    """Send deduplicated notifications to selected Companion App devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        activity: BackupCheckupActivityLog | None = None,
    ) -> None:
        """Initialize notification state storage."""
        self.hass = hass
        self._hass = hass
        self._activity = activity
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.notifications",
            private=True,
            atomic_writes=True,
        )
        self._loaded = False
        self._last_signature = ""
        self._last_targets: tuple[str, ...] = ()
        self._was_enabled = False
        self._lock = asyncio.Lock()
        self.last_error: str | None = None

    async def _async_disable(self) -> None:
        """Persist the transition to disabled notification processing."""
        if not self._was_enabled:
            return
        self._was_enabled = False
        await self._async_save()
        self._record_activity(
            "notification_processing",
            ACTIVITY_OUTCOME_CHANGED,
            details={"enabled": False},
        )

    async def _async_enable_first_problem(
        self,
        data: BackupCheckupData,
        signature: str,
        targets: tuple[str, ...],
    ) -> None:
        """Enable processing and optionally send the currently active problem."""
        self._was_enabled = True
        if not signature:
            self._last_signature = ""
            await self._async_save()
            return
        if await self._async_send_problem(data, targets):
            self._last_signature = signature
            self._last_targets = targets
            await self._async_save()

    async def _async_sync_targets_for_existing_problem(
        self,
        data: BackupCheckupData,
        targets: tuple[str, ...],
    ) -> None:
        """Notify only newly added targets for an unchanged active problem."""
        added_targets = tuple(
            target for target in targets if target not in self._last_targets
        )
        if added_targets and not await self._async_send_problem(data, added_targets):
            return
        self._last_targets = targets
        await self._async_save()

    async def _async_send_state_change(
        self,
        data: BackupCheckupData,
        signature: str,
        targets: tuple[str, ...],
        *,
        notify_on_recovery: bool,
    ) -> None:
        """Send one changed problem or recovery state and persist it on success."""
        if signature:
            sent = await self._async_send_problem(data, targets)
        elif self._last_signature and notify_on_recovery:
            sent = await self._async_send_recovery(targets)
        else:
            sent = True
        if not sent:
            return
        self._last_signature = signature
        self._last_targets = targets
        await self._async_save()

    async def async_process(
        self,
        data: BackupCheckupData,
        *,
        enabled: bool,
        targets: tuple[str, ...],
        notify_on_recovery: bool,
    ) -> None:
        """Send a message only when the active problem set changes."""
        async with self._lock:
            await self._async_load()
            signature = "|".join(sorted(data.active_problems))
            normalized_targets = tuple(sorted(set(targets)))
            if not enabled or not normalized_targets:
                await self._async_disable()
                return
            if not self._was_enabled:
                await self._async_enable_first_problem(
                    data,
                    signature,
                    normalized_targets,
                )
                return
            if signature == self._last_signature:
                if normalized_targets != self._last_targets:
                    await self._async_sync_targets_for_existing_problem(
                        data,
                        normalized_targets,
                    )
                return
            await self._async_send_state_change(
                data,
                signature,
                normalized_targets,
                notify_on_recovery=notify_on_recovery,
            )

    async def async_send_test(self, targets: tuple[str, ...]) -> bool:
        """Send one localized test notification."""
        language = self._language()
        strings = _MESSAGES.get(language, _MESSAGES["en"])
        return await self._async_send(
            targets,
            title=strings["test_title"],
            message=strings["test_message"],
            notification_type="test",
        )

    async def async_remove(self) -> None:
        """Remove persisted notification state."""
        await self._store.async_remove()

    async def _async_send_problem(
        self,
        data: BackupCheckupData,
        targets: tuple[str, ...],
    ) -> bool:
        """Send a localized problem notification."""
        language = self._language()
        strings = _MESSAGES.get(language, _MESSAGES["en"])
        try:
            translations = await async_get_translations(
                self.hass,
                self.hass.config.language,
                "entity",
                integrations={DOMAIN},
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Unable to load localized notification states: error_type=%s",
                safe_error_type(err),
            )
            translations = {}
        status = translations.get(
            f"component.{DOMAIN}.entity.sensor.status.state.{data.status}",
            data.status,
        )
        recommendation = translations.get(
            f"component.{DOMAIN}.entity.sensor.recommendation.state."
            f"{data.recommendation}",
            data.recommendation,
        )
        return await self._async_send(
            targets,
            title=strings["problem_title"],
            message=strings["problem_message"].format(
                status=status,
                recommendation=recommendation,
                count=data.problem_count,
            ),
            notification_type="problem",
        )

    async def _async_send_recovery(self, targets: tuple[str, ...]) -> bool:
        """Send a localized recovery notification."""
        language = self._language()
        strings = _MESSAGES.get(language, _MESSAGES["en"])
        return await self._async_send(
            targets,
            title=strings["recovery_title"],
            message=strings["recovery_message"],
            notification_type="recovery",
        )

    async def _async_send(
        self,
        targets: tuple[str, ...],
        *,
        title: str,
        message: str,
        notification_type: str,
    ) -> bool:
        """Call the native notify entity action."""
        self._record_activity(
            "notification_send",
            ACTIVITY_OUTCOME_STARTED,
            details={
                "notification_type": notification_type,
                "target_count": len(targets),
            },
        )
        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {"title": title, "message": message},
                target={"entity_id": list(targets)},
                blocking=True,
            )
        except (HomeAssistantError, ValueError) as err:
            self.last_error = classify_exception(err)
            _LOGGER.warning(
                "Unable to send BackupCheckup notification: error_type=%s "
                "error_code=%s",
                safe_error_type(err),
                self.last_error,
            )
            self._record_activity(
                "notification_send",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.WARNING,
                details={
                    "error_code": self.last_error,
                    "notification_type": notification_type,
                    "target_count": len(targets),
                },
            )
            return False
        except Exception as err:  # noqa: BLE001
            self.last_error = classify_exception(err)
            _LOGGER.error(
                "Unexpected BackupCheckup notification error: error_type=%s "
                "error_code=%s",
                safe_error_type(err),
                self.last_error,
            )
            self._record_activity(
                "notification_send",
                ACTIVITY_OUTCOME_FAILED,
                level=logging.ERROR,
                details={
                    "error_code": self.last_error,
                    "notification_type": notification_type,
                    "target_count": len(targets),
                },
            )
            return False
        self.last_error = None
        self._record_activity(
            "notification_send",
            ACTIVITY_OUTCOME_COMPLETED,
            details={
                "notification_type": notification_type,
                "target_count": len(targets),
            },
        )
        return True

    async def _async_read_store(self) -> tuple[dict[str, Any], bool]:
        """Return validated store data and whether persistence repair is needed."""
        try:
            stored = await self._store.async_load()
            if stored is None:
                return {}, False
            if not isinstance(stored, dict):
                raise ValueError("invalid_store_root")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Invalid notification store data was reset: error_type=%s",
                safe_error_type(err),
            )
            async_set_storage_data_issue(
                self._hass, store_name="notifications", active=True
            )
            return {}, True
        async_set_storage_data_issue(
            self._hass, store_name="notifications", active=False
        )
        return stored, False

    def _apply_stored_state(self, stored: dict[str, Any]) -> bool:
        """Apply bounded notification state and report malformed content."""
        signature = stored.get("last_signature", "")
        was_enabled = stored.get("was_enabled", False)
        targets = stored.get("last_targets", [])
        invalid_content = (
            not isinstance(signature, str)
            or not isinstance(was_enabled, bool)
            or not isinstance(targets, list)
            or any(not isinstance(item, str) for item in targets)
        )
        self._last_signature = signature[:512] if isinstance(signature, str) else ""
        self._was_enabled = was_enabled is True
        normalized_targets = normalize_notification_targets(targets)[:100]
        self._last_targets = tuple(sorted(normalized_targets))
        return invalid_content or (
            isinstance(targets, list) and targets != normalized_targets
        )

    async def _async_persist_repaired_store(self) -> None:
        """Persist sanitized state and clear the repair issue on success."""
        try:
            await self._async_save()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Unable to persist repaired notification store data: error_type=%s",
                safe_error_type(err),
            )
            return
        async_set_storage_data_issue(
            self._hass, store_name="notifications", active=False
        )

    async def _async_load(self) -> None:
        """Load the last notification state once."""
        if self._loaded:
            return
        stored, repair_needed = await self._async_read_store()
        if self._apply_stored_state(stored):
            repair_needed = True
            async_set_storage_data_issue(
                self._hass, store_name="notifications", active=True
            )
        self._loaded = True
        if repair_needed:
            await self._async_persist_repaired_store()

    async def _async_save(self) -> None:
        """Persist notification deduplication state."""
        await self._store.async_save(
            {
                "last_signature": self._last_signature,
                "was_enabled": self._was_enabled,
                "last_targets": list(self._last_targets),
            }
        )

    def _record_activity(
        self,
        action: str,
        outcome: str,
        *,
        level: int = logging.INFO,
        details: dict[str, object] | None = None,
    ) -> None:
        """Record an activity when a coordinator journal is available."""
        if self._activity is not None:
            self._activity.record(action, outcome, level=level, details=details)

    def _language(self) -> str:
        """Return the supported language key with English fallback."""
        language = self.hass.config.language.lower().replace("_", "-").split("-", 1)[0]
        return language if language in _MESSAGES else "en"
