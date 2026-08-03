"""Generate privacy-safe, exportable Home Assistant disaster-recovery plans."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import BackupIntegrityResult, BackupRecord
from .recovery_preparedness import RecoveryPreparednessSnapshot
from .recovery_restore import RestoreTestSnapshot
from .recovery_simulation import RecoverySimulation


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """One localized, privacy-safe recovery plan and its rendered exports."""

    generated_at: datetime
    language: str
    title: str
    summary: str
    installation_type: str
    backup_reference: str | None
    backup_date: str | None
    steps: tuple[str, ...]
    required_items: tuple[str, ...]
    external_dependencies: tuple[str, ...]
    post_restore_checks: tuple[str, ...]
    warnings: tuple[str, ...]
    markdown: str
    html: str
    json_text: str

    def as_dict(self) -> dict[str, Any]:
        """Return plan data plus ready-to-download renderings."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "language": self.language,
            "title": self.title,
            "summary": self.summary,
            "installation_type": self.installation_type,
            "backup_reference": self.backup_reference,
            "backup_date": self.backup_date,
            "steps": list(self.steps),
            "required_items": list(self.required_items),
            "external_dependencies": list(self.external_dependencies),
            "post_restore_checks": list(self.post_restore_checks),
            "warnings": list(self.warnings),
            "exports": {
                "markdown": self.markdown,
                "html": self.html,
                "json": self.json_text,
            },
            "contains_secrets": False,
        }


_TEXT = {
    "en": {
        "title": "BackupCheckup emergency recovery plan",
        "summary_ready": "The latest backup has a usable recovery foundation.",
        "summary_limited": "Important recovery gaps remain and are listed below.",
        "unknown_install": "Home Assistant installation",
        "step_install": "Prepare or reinstall {installation} on the replacement system.",
        "step_restore": "During onboarding, select restore from backup and use the verified backup dated {date} (reference {reference}).",
        "step_password": "Retrieve the separately stored backup password before starting the restore.",
        "step_wait": "Allow the restore to complete without interrupting power or network access.",
        "step_dependencies": "Restore or reconnect the separately protected external dependencies.",
        "required_password": "Backup password or encryption key",
        "required_storage": "Access to the backup storage location",
        "required_network": "Documented network and administrator access",
        "required_hardware": "Replacement hardware or installation media",
        "post_login": "Confirm administrator login and Home Assistant startup.",
        "post_integrations": "Check integrations, automations, dashboards and notifications.",
        "post_radios": "Check Zigbee, Z-Wave, Thread/Matter and ESPHome connectivity where applicable.",
        "post_database": "Confirm recorder/database operation and recent history.",
        "post_backup": "Create and verify a new backup after recovery.",
        "warning_simulation": "The simulated restore assessment has not passed completely.",
        "warning_restore_test": "No current successful full test restore is documented.",
        "warning_checklist": "The guided emergency checklist is incomplete or expired.",
        "warning_dependencies": "External dependencies are not fully assessed or protected.",
        "warning_integrity": "The latest backup has not been successfully verified.",
        "label_installation": "Installation",
        "label_backup_reference": "Backup reference",
        "label_backup_date": "Backup date",
        "section_required": "Required before recovery",
        "section_steps": "Recovery procedure",
        "section_dependencies": "External dependencies",
        "section_checks": "Checks after recovery",
        "section_warnings": "Open risks",
        "none": "None recorded",
        "privacy": "This export intentionally contains no passwords, tokens, paths, hostnames, IP addresses or backup names.",
    },
    "de": {
        "title": "BackupCheckup-Notfallplan zur Wiederherstellung",
        "summary_ready": "Das neueste Backup besitzt eine nutzbare Grundlage für die Wiederherstellung.",
        "summary_limited": "Wichtige Lücken der Notfallvorsorge bestehen weiterhin und sind unten aufgeführt.",
        "unknown_install": "Home-Assistant-Installation",
        "step_install": "{installation} auf dem Ersatzsystem vorbereiten oder neu installieren.",
        "step_restore": "Während des Onboardings die Wiederherstellung aus einem Backup auswählen und das geprüfte Backup vom {date} (Referenz {reference}) verwenden.",
        "step_password": "Vor Beginn der Wiederherstellung das separat aufbewahrte Backup-Passwort bereithalten.",
        "step_wait": "Die Wiederherstellung ohne Unterbrechung der Strom- oder Netzwerkversorgung abschließen lassen.",
        "step_dependencies": "Separat abgesicherte externe Abhängigkeiten wiederherstellen oder erneut verbinden.",
        "required_password": "Backup-Passwort oder Verschlüsselungsschlüssel",
        "required_storage": "Zugang zum Backup-Speicherort",
        "required_network": "Dokumentierter Netzwerk- und Administratorzugang",
        "required_hardware": "Ersatzgerät oder Installationsmedium",
        "post_login": "Administratoranmeldung und Start von Home Assistant bestätigen.",
        "post_integrations": "Integrationen, Automationen, Dashboards und Benachrichtigungen prüfen.",
        "post_radios": "Falls vorhanden Zigbee-, Z-Wave-, Thread-/Matter- und ESPHome-Verbindungen prüfen.",
        "post_database": "Funktion von Recorder beziehungsweise Datenbank und aktuelle Verlaufsdaten bestätigen.",
        "post_backup": "Nach der Wiederherstellung ein neues Backup erstellen und prüfen.",
        "warning_simulation": "Der simulierte Wiederherstellungstest wurde nicht vollständig bestanden.",
        "warning_restore_test": "Es ist kein aktueller erfolgreicher vollständiger Test-Restore dokumentiert.",
        "warning_checklist": "Der geführte Notfallcheck ist unvollständig oder abgelaufen.",
        "warning_dependencies": "Externe Abhängigkeiten sind nicht vollständig bewertet oder abgesichert.",
        "warning_integrity": "Das neueste Backup wurde nicht erfolgreich geprüft.",
        "label_installation": "Installation",
        "label_backup_reference": "Backup-Referenz",
        "label_backup_date": "Backup-Datum",
        "section_required": "Vor der Wiederherstellung erforderlich",
        "section_steps": "Ablauf der Wiederherstellung",
        "section_dependencies": "Externe Abhängigkeiten",
        "section_checks": "Prüfungen nach der Wiederherstellung",
        "section_warnings": "Offene Risiken",
        "none": "Keine Einträge",
        "privacy": "Dieser Export enthält absichtlich keine Passwörter, Tokens, Pfade, Hostnamen, IP-Adressen oder Backup-Namen.",
    },
}

_PLAN_SECTIONS = (
    ("section_required", "required_items"),
    ("section_steps", "steps"),
    ("section_dependencies", "external_dependencies"),
    ("section_checks", "post_restore_checks"),
    ("section_warnings", "warnings"),
)


def _markdown_escape(value: Any) -> str:
    """Neutralize inline HTML in values written to a Markdown export."""
    return html.escape(str(value), quote=False)


def _render_markdown(data: dict[str, Any], text: dict[str, str]) -> str:
    lines = [
        f"# {_markdown_escape(data['title'])}",
        "",
        _markdown_escape(data["summary"]),
        "",
    ]
    lines.append(
        f"**{_markdown_escape(text['label_installation'])}:** "
        f"{_markdown_escape(data['installation_type'])}"
    )
    lines.append(
        f"**{_markdown_escape(text['label_backup_reference'])}:** "
        f"{_markdown_escape(data['backup_reference'] or '—')}"
    )
    lines.append(
        f"**{_markdown_escape(text['label_backup_date'])}:** "
        f"{_markdown_escape(data['backup_date'] or '—')}"
    )
    lines.append("")
    for key, data_key in _PLAN_SECTIONS:
        values = data[data_key]
        lines.append(f"## {text[key]}")
        if values:
            lines.extend(f"- {_markdown_escape(value)}" for value in values)
        else:
            lines.append(f"- {_markdown_escape(text['none'])}")
        lines.append("")
    lines.append(f"> {_markdown_escape(text['privacy'])}")
    return "\n".join(lines).rstrip() + "\n"


def _render_html(data: dict[str, Any], text: dict[str, str]) -> str:
    def list_html(values: list[str]) -> str:
        items = values or [text["none"]]
        return (
            "<ul>"
            + "".join(f"<li>{html.escape(item)}</li>" for item in items)
            + "</ul>"
        )

    sections = "".join(
        f"<section><h2>{html.escape(text[key])}</h2>"
        f"{list_html(data[data_key])}</section>"
        for key, data_key in _PLAN_SECTIONS
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>'
        + html.escape(data["title"])
        + "</title><style>body{font-family:system-ui,sans-serif;max-width:850px;margin:40px auto;padding:0 20px;line-height:1.5}"
        "h1,h2{line-height:1.2}section{margin-top:28px}.meta{padding:16px;background:#f3f4f6;border-radius:8px}"
        ".privacy{margin-top:32px;font-size:.9em;color:#555}</style></head><body>"
        f"<h1>{html.escape(data['title'])}</h1><p>{html.escape(data['summary'])}</p>"
        f'<div class="meta"><strong>{html.escape(text["label_installation"])}:</strong> {html.escape(data["installation_type"])}<br>'
        f"<strong>{html.escape(text['label_backup_reference'])}:</strong> {html.escape(data['backup_reference'] or '—')}<br>"
        f"<strong>{html.escape(text['label_backup_date'])}:</strong> {html.escape(data['backup_date'] or '—')}</div>"
        + sections
        + f'<p class="privacy">{html.escape(text["privacy"])}</p></body></html>'
    )


def _recovery_instructions(
    text: dict[str, str],
    *,
    installation: str,
    backup_date: str | None,
    reference: str | None,
    protected: bool,
    has_dependencies: bool,
) -> tuple[list[str], list[str]]:
    """Build required items and ordered recovery steps without duplicated branches."""
    required_items = [
        text["required_storage"],
        text["required_network"],
        text["required_hardware"],
    ]
    steps = [
        text["step_install"].format(installation=installation),
        text["step_restore"].format(
            date=backup_date or "—", reference=reference or "—"
        ),
    ]
    if protected:
        required_items.insert(0, text["required_password"])
        steps.insert(1, text["step_password"])
    steps.append(text["step_wait"])
    if has_dependencies:
        steps.append(text["step_dependencies"])
    return required_items, steps


def _dependency_labels(
    preparedness: RecoveryPreparednessSnapshot,
) -> tuple[str, ...]:
    """Return fixed dependency keys that need to appear in the plan."""
    return tuple(
        key
        for key, value in preparedness.dependencies.items()
        if value.get("detected") is True
        or value.get("effective_status") in {"protected", "unprotected"}
    )


def _plan_warnings(
    text: dict[str, str],
    preparedness: RecoveryPreparednessSnapshot,
    simulation: RecoverySimulation,
    restore_test: RestoreTestSnapshot,
) -> list[str]:
    """Return localized unresolved risks in stable priority order."""
    warning_checks = (
        (simulation.passed is not True, "warning_simulation"),
        (restore_test.passed is not True, "warning_restore_test"),
        (preparedness.checklist_complete is not True, "warning_checklist"),
        (
            preparedness.dependencies_protected is not True,
            "warning_dependencies",
        ),
        (
            simulation.checks.get("integrity_verified") is not True,
            "warning_integrity",
        ),
    )
    return [text[key] for active, key in warning_checks if active]


def build_recovery_plan(
    latest: BackupRecord | None,
    integrity: BackupIntegrityResult,
    preparedness: RecoveryPreparednessSnapshot,
    simulation: RecoverySimulation,
    restore_test: RestoreTestSnapshot,
    *,
    generated_at: datetime,
    installation_type: str | None = None,
    language: str = "en",
) -> RecoveryPlan:
    """Build a localized emergency plan from privacy-safe assessment data."""
    locale = "de" if str(language).lower().startswith("de") else "en"
    text = _TEXT[locale]
    installation = (installation_type or "").strip() or text["unknown_install"]
    reference = latest.backup_reference if latest else None
    backup_date = latest.date.isoformat() if latest else None
    readiness_ready = (
        simulation.passed is True
        and restore_test.passed is True
        and preparedness.checklist_complete is True
        and preparedness.dependencies_protected is True
    )
    summary = text["summary_ready"] if readiness_ready else text["summary_limited"]

    dependency_labels = _dependency_labels(preparedness)
    required_items, steps = _recovery_instructions(
        text,
        installation=installation,
        backup_date=backup_date,
        reference=reference,
        protected=integrity.protected is True,
        has_dependencies=bool(dependency_labels),
    )
    warnings = _plan_warnings(text, preparedness, simulation, restore_test)

    data = {
        "title": text["title"],
        "summary": summary,
        "installation_type": installation,
        "backup_reference": reference,
        "backup_date": backup_date,
        "steps": steps,
        "required_items": required_items,
        "external_dependencies": list(dependency_labels),
        "post_restore_checks": [
            text["post_login"],
            text["post_integrations"],
            text["post_radios"],
            text["post_database"],
            text["post_backup"],
        ],
        "warnings": warnings,
    }
    markdown = _render_markdown(data, text)
    html_text = _render_html(data, text)
    json_text = json.dumps(
        {
            "generated_at": generated_at.isoformat(),
            "language": locale,
            **data,
            "privacy": text["privacy"],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return RecoveryPlan(
        generated_at=generated_at,
        language=locale,
        title=data["title"],
        summary=summary,
        installation_type=installation,
        backup_reference=reference,
        backup_date=backup_date,
        steps=tuple(steps),
        required_items=tuple(required_items),
        external_dependencies=dependency_labels,
        post_restore_checks=tuple(data["post_restore_checks"]),
        warnings=tuple(warnings),
        markdown=markdown,
        html=html_text,
        json_text=json_text,
    )
