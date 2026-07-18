# BackupCheckup 2.2.5 – Technical-Debt- und Coverage-Audit

**Prüfdatum:** 17. Juli 2026  
**Release:** 2.2.5 (Version unverändert)  
**Umfang:** alle 27 Produktionsmodule unter `custom_components/backup_checkup`, Test-Suite, Release-Metadaten und Qualitätskonfiguration.

## Ergebnisübersicht

| Kennzahl | Ausgangsstand | Überarbeitete 2.2.5 | Veränderung |
|---|---:|---:|---:|
| Bestandene Tests | 196 | 233 | +37 |
| Statement-Coverage | 68,62 % | 92,06 % | +23,44 Prozentpunkte |
| Branch-Coverage | 61,20 % | 83,18 % | +21,98 Prozentpunkte |
| Kombinierte Coverage | 67,14 % | 90,33 % | +23,19 Prozentpunkte |
| Maximale zyklomatische Komplexität | 51 | 14 | −37 |
| Erzwungener Coverage-Grenzwert | 60 % | 90 % | +30 Prozentpunkte |

Die Suite ist vollständig grün. Ruff, der neue McCabe-Grenzwert, `compileall`, `git diff --check` und der Coverage-Gate mit 90 % bestehen.

## Wesentliche Befunde und Behebungen

### 1. Coverage war formal grün, aber inhaltlich unvollständig

Die bisherige Konfiguration hatte kein festes Produktions-`source`. Nicht importierte Module verschwanden dadurch aus normalen Coverage-Läufen. Bei einer vollständigen Messung lagen unter anderem `config_flow.py`, `sensor.py`, `binary_sensor.py`, `button.py`, `entity.py` und `agent_cleanup.py` zunächst bei 0 %. Die reale Ausgangslage betrug deshalb nur 68,62 % Statements und 61,20 % Branches.

**Behoben:** `source = ["custom_components/backup_checkup"]` ist nun fest konfiguriert. Der Gate-Wert wurde auf 90 % kombiniert angehoben. Unimportierte Produktionsdateien können nicht mehr unbemerkt aus dem Bericht fallen.

### 2. Sehr hohe Komplexität in sicherheitsrelevanten Pfaden

`BackupIntegrityVerifier.async_verify` lag bei 51, `_verify_archive` bei 28. Weitere Hotspots waren der Notification-Store-Loader (17), der Coordinator-Snapshot (16) und die Backup-Normalisierung (16). Diese Methoden mischten Budgetierung, IO, Fallback, Parsing, Validierung, Aggregation und Cleanup.

**Behoben:** Die Abläufe wurden in kleine, benannte Stufen zerlegt. Die höchste verbleibende Funktionskomplexität beträgt 14. Ruff erzwingt künftig maximal 15.

### 3. Nicht deterministische Ressourcenfreigabe bei Archivprüfung

TAR-, Metadaten-, Member- und verschachtelte Archiv-Streams wurden nicht auf jedem Abbruch-, Timeout- und Fallback-Pfad explizit geschlossen. Kandidatendateien konnten bis zur abschließenden Verzeichnisbereinigung liegen bleiben.

**Behoben:** Alle Reader und verschachtelten Archive besitzen jetzt klar begrenzte Lebenszyklen. Fehlgeschlagene Kandidatendateien werden vor dem nächsten redundanten Speicherort entfernt; das abschließende Cleanup bleibt zusätzlich bestehen.

### 4. Fehlerkaskade bei dynamischer Entitätsbereinigung

Ein einzelner Fehler beim Entfernen einer veralteten Storage-Entität konnte die Bereinigung der übrigen Entitäten und des leeren Geräts abbrechen.

**Behoben:** Jede Entität wird isoliert best effort entfernt. Danach wird unabhängig geprüft, ob das Agent-Gerät leer ist und gelöscht werden kann.

### 5. Produktions-`assert` in einem Verifier-Invariantenpfad

Ein `assert` sollte garantieren, dass ein finales Kandidatenergebnis immer einen Result-Wert enthält. Assertions können mit optimiertem Python deaktiviert werden und sind für kontrollierte Laufzeitfehler ungeeignet.

**Behoben:** Ein inkonsistenter finaler Zustand erzeugt nun explizit `internal_error` mit `candidate_result_missing` und ist durch einen Regressionstest abgesichert.

## Functional Coverage

Neu bzw. deutlich erweitert wurden funktionale Tests für:

- Config Flow und Options Flow einschließlich Abbruch- und Validierungspfaden.
- Setup, Migration, Reload, Unload und Removal des Config Entries.
- Native Backup-Manager-Zustände und Fallback-Entitäten.
- Sensor-, Binary-Sensor- und Button-Plattformen sowie gemeinsame Entity-Basis.
- Coordinator-Orchestrierung, Manager-Ausfälle, Storage-Auswertung, Größenprüfung, Retry-Backoff und manuelle/automatische Integritätsplanung.
- Integritätsprüfung mit redundanten Kopien, Limits, beschädigten Archiven, Datenbankprüfung, Stream-Cleanup und ungültigen Invarianten.
- Fehlerisolierte Agent-/Entity-Bereinigung.

Diese Tests laufen an der Python-Integrationsgrenze mit kontrollierten Home-Assistant-Testdoubles. Sie ersetzen keinen vollständigen End-to-End-Test in einer realen Home-Assistant-Instanz mit echten Backup-Agenten.

## Coverage je Produktionsdatei

| Datei | Statements | Statement | Branches | Branch | kombiniert |
|---|---:|---:|---:|---:|---:|
| `__init__.py` | 128 | 99.22 % | 38 | 86.84 % | 96.39 % |
| `age.py` | 11 | 100.00 % | 4 | 100.00 % | 100.00 % |
| `agent_cleanup.py` | 38 | 97.37 % | 8 | 75.00 % | 93.48 % |
| `analytics.py` | 107 | 99.07 % | 28 | 96.43 % | 98.52 % |
| `backup_normalizer.py` | 252 | 88.49 % | 70 | 81.43 % | 86.96 % |
| `binary_sensor.py` | 78 | 100.00 % | 10 | 90.00 % | 98.86 % |
| `button.py` | 47 | 100.00 % | 0 | 100.00 % | 100.00 % |
| `classification.py` | 28 | 100.00 % | 10 | 100.00 % | 100.00 % |
| `config_flow.py` | 107 | 97.20 % | 34 | 85.29 % | 94.33 % |
| `configuration.py` | 112 | 76.79 % | 32 | 96.88 % | 81.25 % |
| `const.py` | 157 | 100.00 % | 0 | 100.00 % | 100.00 % |
| `coordinator.py` | 482 | 95.44 % | 104 | 85.58 % | 93.69 % |
| `diagnostics.py` | 55 | 89.09 % | 8 | 37.50 % | 82.54 % |
| `entity.py` | 24 | 100.00 % | 0 | 100.00 % | 100.00 % |
| `entity_mode.py` | 45 | 100.00 % | 26 | 100.00 % | 100.00 % |
| `history.py` | 165 | 100.00 % | 48 | 100.00 % | 100.00 % |
| `integrity.py` | 716 | 85.89 % | 210 | 74.29 % | 83.26 % |
| `models.py` | 240 | 99.58 % | 24 | 95.83 % | 99.24 % |
| `native_backup.py` | 101 | 100.00 % | 30 | 100.00 % | 100.00 % |
| `notification_selection.py` | 38 | 100.00 % | 18 | 100.00 % | 100.00 % |
| `notifications.py` | 154 | 69.48 % | 32 | 53.12 % | 66.67 % |
| `problem_state.py` | 25 | 100.00 % | 2 | 100.00 % | 100.00 % |
| `repairs.py` | 56 | 87.50 % | 18 | 61.11 % | 81.08 % |
| `security.py` | 212 | 98.58 % | 58 | 98.28 % | 98.52 % |
| `sensor.py` | 165 | 81.21 % | 46 | 54.35 % | 75.36 % |
| `storage_cleanup.py` | 51 | 86.27 % | 14 | 100.00 % | 89.23 % |
| `task_control.py` | 10 | 100.00 % | 2 | 100.00 % | 100.00 % |
| **Gesamt** | **3604** | **92.06 %** | **874** | **83.18 %** | **90.33 %** |

## Verbleibende technische Schulden

1. **Modulgröße:** `integrity.py` und `coordinator.py` besitzen trotz kleinerer Methoden weiterhin einen Radon-Maintainability-Index C, hauptsächlich wegen ihrer Gesamtgröße und Verantwortungsbreite. Eine spätere physische Aufteilung in Download-, Archiv-, Persistenz- und Scheduling-Services wäre sinnvoll, sollte aber als eigener Release-Schritt erfolgen.
2. **Niedrigere Branch-Coverage:** Besonders `diagnostics.py` (37,50 %), `notifications.py` (53,12 %), `sensor.py` (54,35 %) und `repairs.py` (61,11 %) enthalten noch defensive Home-Assistant- und Fehlerpfade. Die Statement-Coverage ist dort bereits deutlich höher; echte HA-Fixture-Tests würden die verbleibenden Zweige besser abdecken.
3. **Externe Grenzen:** Breite Exception-Grenzen bleiben gezielt an Home-Assistant-, Store-, Dateisystem-, Notify- und Drittanbieterobjekt-Schnittstellen bestehen. Sie sind kommentiert und verhindern, dass ein defekter Agent die gesamte Integration stoppt; sie sollten bei API-Änderungen erneut geprüft werden.
4. **Kein Real-System-E2E:** Die Suite prüft keine Installation gegen eine vollständige Home-Assistant-Core-Laufzeit mit realen lokalen und entfernten Backup-Agenten. Für ein zukünftiges Release wäre mindestens ein automatisierter Smoke-Test in einer HA-Testinstanz empfehlenswert.

## Qualitätsgates

- `pytest -q`: **233 passed**
- Produktions-Coverage: **92,06 % Statements / 83,18 % Branches / 90,33 % kombiniert**
- `coverage report --fail-under=90`: bestanden
- `ruff check custom_components tests`: bestanden
- McCabe-Komplexität: Maximum **14**, zulässig **15**
- `python -m compileall -q custom_components tests`: bestanden
- `git diff --check`: bestanden
- Keine `TODO`, `FIXME`, `HACK` oder `XXX` in den Python-Quellen gefunden.

## Kompatibilität

Die Release-Version bleibt 2.2.5. Manifest und Konstante bleiben synchron, die Config-Entry-Version bleibt 9, und es ist keine Migration erforderlich. Ältere Changelog-Einträge ab 2.2.4 wurden unverändert beibehalten.
