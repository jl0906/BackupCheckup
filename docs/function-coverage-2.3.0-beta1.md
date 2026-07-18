# BackupCheckup 2.3.0-beta1 – Funktionscoverage und Beta-Härtung

## Umfang und Definition

Geprüft wurden sämtliche Python-Produktionsmodule unter
`custom_components/backup_checkup`. Die Funktionscoverage wird nicht aus der bloßen
Importierbarkeit abgeleitet: Ein AST-Inventar ermittelt jede synchrone und asynchrone
Funktion, Methode und verschachtelte Funktion. Eine Funktion gilt erst als abgedeckt,
wenn ihre erste ausführbare Anweisung im Coverage-Lauf tatsächlich ausgeführt wurde.

Diese Metrik weist nach, dass jeder vorhandene Funktionskörper mindestens einen realen
Testpfad besitzt. Sie ist kein mathematischer Beweis, dass jede denkbare Eingabe korrekt
verarbeitet wird. Deshalb werden zusätzlich Statement-, Branch-, Fehler-, Lifecycle-,
Datenschutz- und Zustandsübergangspfade geprüft.

## Ergebnis

| Kennzahl | Alpha2-Ausgangslage | Beta1 |
|---|---:|---:|
| Tests | 243 | 256 |
| Produktionsfunktionen ausgeführt | 358/371 (96,50%) | **371/371 (100,00%)** |
| Statement-Coverage | 92,57% | **95,01%** |
| Branch-Coverage | 83,08% | **86,98%** |
| Kombinierte Coverage | 90,72% | **93,45%** |
| Höchste zulässige Ruff-Komplexität | 15 | 15 |

## Coverage pro Produktionsdatei

| Datei | Funktionen | Funktionscoverage | Statements | Branches |
|---|---:|---:|---:|---:|
| `__init__.py` | 17 | 17/17 | 98.24% | 77.78% |
| `activity.py` | 10 | 10/10 | 100.00% | 100.00% |
| `age.py` | 2 | 2/2 | 100.00% | 100.00% |
| `agent_cleanup.py` | 3 | 3/3 | 97.37% | 75.00% |
| `analytics.py` | 10 | 10/10 | 99.07% | 96.43% |
| `backup_normalizer.py` | 27 | 27/27 | 88.49% | 81.43% |
| `binary_sensor.py` | 8 | 8/8 | 100.00% | 90.00% |
| `button.py` | 9 | 9/9 | 100.00% | 100.00% |
| `classification.py` | 5 | 5/5 | 100.00% | 100.00% |
| `config_flow.py` | 17 | 17/17 | 97.20% | 85.29% |
| `configuration.py` | 7 | 7/7 | 97.32% | 96.88% |
| `const.py` | 0 | 0/0 | 100.00% | 100.00% |
| `coordinator.py` | 45 | 45/45 | 95.29% | 85.19% |
| `diagnostics.py` | 11 | 11/11 | 100.00% | 100.00% |
| `entity.py` | 3 | 3/3 | 100.00% | 100.00% |
| `entity_mode.py` | 3 | 3/3 | 100.00% | 100.00% |
| `history.py` | 15 | 15/15 | 100.00% | 100.00% |
| `integrity.py` | 66 | 66/66 | 87.22% | 76.42% |
| `models.py` | 23 | 23/23 | 100.00% | 100.00% |
| `native_backup.py` | 11 | 11/11 | 100.00% | 100.00% |
| `notification_selection.py` | 2 | 2/2 | 100.00% | 100.00% |
| `notifications.py` | 18 | 18/18 | 90.00% | 77.78% |
| `problem_state.py` | 1 | 1/1 | 100.00% | 100.00% |
| `repairs.py` | 11 | 11/11 | 96.43% | 83.33% |
| `security.py` | 27 | 27/27 | 98.58% | 98.28% |
| `sensor.py` | 17 | 17/17 | 97.58% | 86.96% |
| `storage_cleanup.py` | 2 | 2/2 | 86.27% | 100.00% |
| `task_control.py` | 1 | 1/1 | 100.00% | 100.00% |

## Neu vollständig ausgeführte Funktionsbereiche

Die 13 in alpha2 vollständig unbetretenen Funktionen wurden durch konkrete
Funktionsprüfungen abgedeckt:

- kanonische Konfigurationsserialisierung,
- persistente Integritäts-Laufzeitdaten und Coordinator-Speicherung,
- SQLite-Fortschrittsabbruch bei Cancel und Timeout,
- Benachrichtigungs-Recovery und Store-Entfernung,
- vollständige Reparaturbereinigung und temporärer Cleanup-Hinweis,
- freundliche Storage-Namen sowie die Namen der neuesten Backup-Speicher,
- Migration von Enum-Übersetzungsschlüsseln und Größen-Sensoreinheiten.

## Realisierte Fehlerbehebungen

### Keine falsche Problembenachrichtigung im gesunden Zustand

Alpha2 speicherte beim Aktivieren der Benachrichtigungen ohne aktives Problem die
aktuelle Zielmenge nicht. Beim nächsten gesunden Refresh konnte eine Zielabweichung
deshalb wie eine neue Zielgruppe für ein bestehendes Problem behandelt werden. Beta1
speichert die Ziele bereits beim gesunden Aktivieren und aktualisiert gesunde
Zieländerungen ausschließlich im Deduplication-State. Der Problem-Sender wird in diesem
Zustand nicht mehr aufgerufen.

### Atomarer erster Ladevorgang des Integritäts-Stores

Alpha2 setzte `_loaded` vor dem ersten `await` auf `True`. Ein paralleler zweiter
Aufrufer konnte dadurch vor Abschluss des tatsächlichen Store-Ladevorgangs den
vorläufigen `not_checked`-Standardzustand erhalten. Beta1 serialisiert den ersten Load
mit einem Lock, prüft nach Erwerb nochmals den Ladezustand und markiert ihn erst nach
erfolgreichem Laden oder kontrollierter Reparatur als abgeschlossen.

### Ausführbare und verbindliche CI-Qualitätsprüfung

Der Workflow referenzierte `actions/checkout@v7`, obwohl dieser Major nicht verfügbar
war. Beta1 verwendet `actions/checkout@v6` und ergänzt einen vollständigen Python-Job:

- `ruff format --check`,
- `ruff check`,
- Python-Kompilierung,
- komplette pytest-Suite,
- Coverage mit allen Produktionsmodulen als Source,
- 100% Funktionscoverage,
- mindestens 95% Statements,
- mindestens 85% Branches,
- mindestens 93% kombinierte Coverage.

## Dauerhafte Gates

- `tools/check_function_coverage.py` schlägt fehl, sobald auch nur eine neue oder
  bestehende Produktionsfunktion nicht betreten wird.
- `tools/check_coverage_thresholds.py` bewertet Statements und Branches getrennt.
- `pyproject.toml` erzwingt 93% kombinierte Coverage.
- `.github/workflows/validate.yml` führt die Gates bei Push, Pull Request, täglich und
  manuell aus.

## Verbleibende Grenzen

Die Funktionscoverage beträgt vollständig 100%. Statement- und Branch-Coverage bleiben
bewusst unter 100%, weil zahlreiche defensive Pfade nur durch künstliche interne
Invarianten, seltene Betriebssystemfehler oder beschädigte Fremdobjekte erreichbar
sind. Diese verbleibenden Zeilen sind im Coverage-Bericht sichtbar und werden nicht
durch Ausschlüsse verborgen. Die sicherheitskritischen Archiv-, Timeout-,
Ressourcenlimit-, Store-Reparatur-, Benachrichtigungs- und Lifecycle-Pfade besitzen
explizite positive und negative Tests.

## Release-Kompatibilität

- Release: `2.3.0-beta1`
- Config-Entry-Schema: Version 9
- Keine Migration erforderlich
- Expertmodus: vollständiges Aktivitätsjournal aktiv
- Standardmodus: Aktivitätsjournal vollständig deaktiviert
