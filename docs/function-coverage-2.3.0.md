# BackupCheckup 2.3.0 – finale Funktionscoverage und Release-Prüfung

## Prüfumfang

Geprüft wurden sämtliche Python-Produktionsmodule unter
`custom_components/backup_checkup`. Ein AST-Inventar ermittelt jede synchrone und
asynchrone Funktion, Methode und verschachtelte Funktion. Eine Funktion gilt nur dann
als abgedeckt, wenn ihre erste ausführbare Anweisung im Coverage-Lauf tatsächlich
betreten wurde.

Zusätzlich wurden Statement- und Branch-Coverage, negative Fehlerpfade,
Parallelität, Config-Entry-Lifecycle, Store-Löschung, Event-Loop-Sicherheit,
Datenschutz des Aktivitätsjournals und die vollständige Release-Metadatenkette
wiederholt geprüft.

## Gesamtergebnis

| Kennzahl | Beta1 | Final 2.3.0 |
|---|---:|---:|
| Tests | 256 | **263** |
| Produktionsfunktionen ausgeführt | 371/371 | **373/373 (100,00%)** |
| Statement-Coverage | 95,01% | **95,03%** |
| Branch-Coverage | 86,98% | **87,23%** |
| Kombinierte Coverage | 93,45% | **93,52%** |
| Config-Entry-Schema | 9 | **9** |

## Coverage pro Produktionsdatei

| Datei | Funktionen | Funktionscoverage | Statements | Branches |
|---|---:|---:|---:|---:|
| `__init__.py` | 17 | 17/17 | 98,24% | 77,78% |
| `activity.py` | 10 | 10/10 | 100,00% | 100,00% |
| `age.py` | 2 | 2/2 | 100,00% | 100,00% |
| `agent_cleanup.py` | 3 | 3/3 | 97,37% | 75,00% |
| `analytics.py` | 10 | 10/10 | 99,07% | 96,43% |
| `backup_normalizer.py` | 27 | 27/27 | 88,49% | 81,43% |
| `binary_sensor.py` | 8 | 8/8 | 100,00% | 90,00% |
| `button.py` | 9 | 9/9 | 100,00% | 100,00% |
| `classification.py` | 5 | 5/5 | 100,00% | 100,00% |
| `config_flow.py` | 17 | 17/17 | 97,20% | 85,29% |
| `configuration.py` | 7 | 7/7 | 97,32% | 96,88% |
| `const.py` | 0 | 0/0 | 100,00% | 100,00% |
| `coordinator.py` | 45 | 45/45 | 95,29% | 85,19% |
| `diagnostics.py` | 11 | 11/11 | 100,00% | 100,00% |
| `entity.py` | 3 | 3/3 | 100,00% | 100,00% |
| `entity_mode.py` | 3 | 3/3 | 100,00% | 100,00% |
| `history.py` | 15 | 15/15 | 100,00% | 100,00% |
| `integrity.py` | 68 | 68/68 | 87,57% | 77,36% |
| `models.py` | 23 | 23/23 | 100,00% | 100,00% |
| `native_backup.py` | 11 | 11/11 | 100,00% | 100,00% |
| `notification_selection.py` | 2 | 2/2 | 100,00% | 100,00% |
| `notifications.py` | 18 | 18/18 | 90,00% | 77,78% |
| `problem_state.py` | 1 | 1/1 | 100,00% | 100,00% |
| `repairs.py` | 11 | 11/11 | 96,43% | 83,33% |
| `security.py` | 27 | 27/27 | 98,58% | 98,28% |
| `sensor.py` | 17 | 17/17 | 97,58% | 86,96% |
| `storage_cleanup.py` | 2 | 2/2 | 86,27% | 100,00% |
| `task_control.py` | 1 | 1/1 | 100,00% | 100,00% |

## Im finalen Lauf gefundene und behobene Fehler

### Store-Löschung gegen laufende Speicherung abgesichert

Ein sofortiger Home-Assistant-`Store`-Schreibvorgang kann noch laufen, während eine
Config Entry gelöscht wird. Ohne integrationsseitige Serialisierung konnte die
Löschung zuerst abgeschlossen werden und der ältere Schreibvorgang die private
Integritätsdatei anschließend erneut anlegen. Vollständige Zustandsänderungen,
Laufzeitänderungen und Entfernung verwenden nun eine gemeinsame Mutation-Sperre.

### Cleanup darf ein Prüfergebnis nicht mehr verdecken

Fehler an der Executor-Grenze der temporären Bereinigung wurden zuvor aus dem
`finally`-Block weitergereicht. Dadurch konnte ein korrekt ermitteltes Ergebnis durch
einen nachgelagerten Cleanup-Fehler ersetzt werden. Beide Cleanup-Stufen sind nun
voneinander isoliert, protokollieren nur den sicheren Fehlertyp und setzen bei Bedarf
den Repair-Hinweis.

### Kein blockierendes Löschen im Event-Loop

Temporäre TAR-Kandidaten und die extrahierte SQLite-Datei wurden in einzelnen Pfaden
mit `Path.unlink()` direkt aus asynchronem Code entfernt. Die Dateisystemaufrufe laufen
nun vollständig über `hass.async_add_executor_job`.

### Setup-Abbruch räumt den Coordinator zuverlässig auf

Der Shutdown-Callback wird nun direkt nach Erstellung des Coordinators und vor dem
ersten `await` registriert. Scheitert Cleanup, erster Refresh oder ein späterer
Setup-Schritt, kann Home Assistant bereits gestartete Coordinator-Aufgaben trotzdem
abbrechen und freigeben.

### Aktivitätsdetails bleiben verlustfrei

Unterschiedliche Detailnamen wie `error-type`, `error type` und `error_type` werden
alle zu strukturierten Schlüsseln normalisiert. Kollisionen erhalten nun deterministisch
`_2`, `_3` usw., sodass der Diagnose-Export keinen Wert mehr durch Dictionary-
Überschreibung verliert.

## Ausgeführte Freigabeprüfungen

- vollständige pytest-Suite,
- AST-basierte 100%-Funktionscoverage,
- getrennte Mindestwerte für Statements und Branches,
- Coverage-Source über alle Produktionsmodule,
- `PYTHONASYNCIODEBUG=1` und Python-Warnungen als Fehler,
- Ruff-Lint und Ruff-Formatprüfung,
- Bandit-Sicherheitsanalyse,
- Python-Kompilierung aller Produktions-, Test- und Tool-Dateien,
- JSON- und YAML-Parsing,
- Übersetzungsstruktur und Platzhaltergleichheit,
- Manifest-, Konstante-, README- und Changelog-Konsistenz,
- erneute Prüfung des entpackten Release-Archivs.

## Release-Kompatibilität

- Release: `2.3.0`
- Config-Entry-Schema: Version 9
- Keine Migration erforderlich
- Expertenmodus: vollständiges Aktivitätsjournal aktiv
- Standardmodus: Aktivitätsjournal vollständig deaktiviert
