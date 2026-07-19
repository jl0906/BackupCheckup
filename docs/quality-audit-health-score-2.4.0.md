# BackupCheckup 2.4.0 – Coverage-, Fehler- und Health-Score-Audit

## Ergebnis

- 294 Tests bestanden.
- 453/453 Produktionsfunktionen betreten: 100,00 %.
- Statement-Coverage: 95.61 %.
- Branch-Coverage: 88.78 %.
- Kombinierte Coverage: 94.27 %.
- Ruff-Lint und Formatprüfung bestanden.
- Bandit-Sicherheitsprüfung bestanden.
- asyncio-Debug und sämtliche Python-Warnungen als Fehler bestanden.

Funktionscoverage bedeutet hier, dass jede definierte Produktionsfunktion mindestens über einen realen Testpfad betreten wurde. Sie beweist nicht, dass jede theoretische Kombination externer Home-Assistant-, Dateisystem-, Netzwerk- und Archivfehler vollständig ausgeschlossen ist.

## Realisierte Fehlerbehebungen

### 1. Health Score zählte korrelierte Symptome mehrfach

Der bisherige Score addierte jedes aktive Flag. Ein Storage-Ausfall konnte dadurch zugleich als `storage_error`, `required_location_missing` und `backup_not_redundant` zählen. Dasselbe galt für automatische Backupfehler und Integritätsprobleme. Health Score Version 2 gruppiert korrelierte Signale nach Ursache und wendet pro Gruppe nur den stärksten Abzug an. Alle Rohsignale bleiben sichtbar.

### 2. Inkonsistente Verlaufsmetriken konnten den Score verfälschen

Eine beschädigte oder widersprüchliche Kombination aus null aufgelösten Versuchen und mehreren aufeinanderfolgenden Fehlern wurde bisher trotzdem abgezogen. Fehlerfolgen werden nun auf die tatsächlich aufgelösten Versuche begrenzt.

### 3. Schweregrad war bei Alter und Redundanz zu grob

Ein knapp überfälliges und ein extrem altes Backup erhielten denselben Abzug. Ebenso wurde nur ein fehlender Speicherort genauso bewertet wie mehrere. Die Abzüge werden jetzt defensiv und begrenzt nach Überschreitung beziehungsweise fehlenden Speicherorten gestaffelt.

### 4. Adaptives Polling konnte ein Abschlussereignis verlieren

Traf ein weiteres natives Backupereignis während einer laufenden Sofortaktualisierung ein, wurde es bisher verworfen. Der Coordinator merkt nun ein Folgeereignis und führt nach dem laufenden Refresh genau einen weiteren zusammengefassten Refresh aus.

### 5. Setup-Zusammenfassung zeigte unnötig „unknown“

War das Board unbekannt, aber die Architektur bekannt, verwendete die Zusammenfassung trotzdem den truthy String `unknown`. Sie fällt nun korrekt auf die Architektur zurück.

### 6. Health-Score-Dokumentation war nicht konsistent

Die Dokumentation nannte für einen korrupten oder unlesbaren Backupstand 50 Punkte, der Code verwendete 60. Die Dokumentation beschreibt nun Score Version 2 und die tatsächlichen Abzüge.

## Health Score Version 2

Der bestehende Sensor und die Rating-Grenzen bleiben kompatibel. Neue Attribute sind:

- `score_version`: Berechnungsmodell, aktuell `2`.
- `deductions`: tatsächlich angewendete Abzüge.
- `component_deductions`: angewendeter Abzug je Ursachenbereich.
- `raw_deductions`: sämtliche erkannten Kandidaten.
- `suppressed_correlated_deductions`: erkannte Symptome, die nicht ein zweites Mal gezählt wurden.

Die Ursachenbereiche sind Verfügbarkeit, Integrität, Backupqualität, Aktualität, Speicher/Redundanz und Automatik. Unabhängige Bereiche können weiterhin gemeinsam abgezogen werden; korrelierte Symptome innerhalb eines Bereichs nicht.

## Coverage je Produktionsdatei

| Datei | Funktionen | Funktionscoverage | Statements | Branches | Kombiniert |
| --- | ---: | ---: | ---: | ---: | ---: |
| `__init__.py` | 16 | 100,00 % | 98.18 % | 78.85 % | 93.55 % |
| `activity.py` | 10 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `age.py` | 2 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `agent_cleanup.py` | 3 | 100,00 % | 97.37 % | 75.00 % | 93.48 % |
| `analytics.py` | 14 | 100,00 % | 99.35 % | 97.92 % | 99.01 % |
| `backup_normalizer.py` | 27 | 100,00 % | 88.89 % | 82.86 % | 87.58 % |
| `binary_sensor.py` | 8 | 100,00 % | 100.00 % | 90.00 % | 98.86 % |
| `button.py` | 9 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `classification.py` | 5 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `config_flow.py` | 36 | 100,00 % | 98.18 % | 91.18 % | 96.29 % |
| `configuration.py` | 38 | 100,00 % | 98.68 % | 98.15 % | 98.58 % |
| `const.py` | 0 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `coordinator.py` | 51 | 100,00 % | 95.52 % | 86.72 % | 93.93 % |
| `diagnostics.py` | 11 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `entity.py` | 4 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `entity_mode.py` | 3 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `flow_schemas.py` | 9 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `hardware_profile.py` | 5 | 100,00 % | 98.36 % | 95.45 % | 97.59 % |
| `history.py` | 15 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `integrity.py` | 68 | 100,00 % | 87.57 % | 77.36 % | 85.31 % |
| `models.py` | 23 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `native_backup.py` | 12 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `notification_selection.py` | 2 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `notifications.py` | 18 | 100,00 % | 90.00 % | 77.78 % | 87.86 % |
| `presets.py` | 4 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `problem_state.py` | 1 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `repairs.py` | 11 | 100,00 % | 96.43 % | 83.33 % | 93.24 % |
| `security.py` | 27 | 100,00 % | 98.58 % | 98.28 % | 98.52 % |
| `sensor.py` | 17 | 100,00 % | 97.58 % | 86.96 % | 95.26 % |
| `setup_recommendation.py` | 1 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |
| `storage_cleanup.py` | 2 | 100,00 % | 86.27 % | 100.00 % | 89.23 % |
| `task_control.py` | 1 | 100,00 % | 100.00 % | 100.00 % | 100.00 % |

## Verbleibende technische Risiken

- `integrity.py` bleibt mit rund 87,57 % Statement- und 77,36 % Branch-Coverage der größte Restbereich. Nicht abgedeckt sind überwiegend seltene Kombinationen aus beschädigten TAR-Strukturen, Streamfehlern, Executorfehlern und konkurrierenden Cleanup-Pfaden.
- `notifications.py` liegt bei 90,00 % Statements und 77,78 % Branches. Restpfade betreffen vor allem fehlgeschlagene Übersetzungsabfragen, Sendefehler und Store-Reparaturfehler.
- `backup_normalizer.py` liegt bei 88,89 % Statements und 82,86 % Branches. Hier verbleiben vor allem defensive Third-Party-Typfehler, die mit regulären Home-Assistant-Objekten schwer realistisch zu erzeugen sind.
- Coverage allein erkennt keine fachlich falsche Gewichtung. Deshalb wurden für den Health Score zusätzliche Szenario- und Korrelationsregressionen ergänzt.

## Vorschläge für weitere Verbesserungen

1. **Score-Vertrauen separat ausweisen:** Ein Score von 100 ohne jemals ausgeführte Integritätsprüfung sollte zusätzlich eine niedrige oder mittlere Datenvertrauensstufe anzeigen. Das darf den eigentlichen Gesundheitswert nicht künstlich verschlechtern.
2. **Verfügbarkeit und Backupgesundheit trennen:** Ein zweiter Sensor für „Beobachtbarkeit“ könnte klar unterscheiden, ob Backups schlecht sind oder BackupCheckup den Manager gerade nicht auslesen kann.
3. **Zeitbasierte Hysterese:** Sehr kurze Manager- oder Storage-Ausfälle könnten zunächst als vorübergehend markiert werden, bevor sie den Score voll beeinflussen.
4. **Score-Szenariomatrix als CI-Gate:** Eine feste Tabelle typischer Zustände mit erwarteten Scorebereichen würde künftige Änderungen an Gewichtungen sichtbar und reviewbar machen.
5. **Integritäts-Coverage gezielt erhöhen:** Statt nur den Gesamtwert anzuheben, sollten die noch offenen Archiv- und Cleanup-Randpfade einzeln priorisiert werden.
6. **Keine frei konfigurierbaren Gewichte:** Benutzerdefinierte Gewichtungen würden Vergleiche und Support erschweren. Sinnvoller wären später wenige dokumentierte Score-Profile mit eigener Versionsnummer.

## Freigabeurteil

Die überarbeitete 2.4.0 ist gegenüber der ursprünglichen Fassung funktional robuster und der Health Score fachlich nachvollziehbarer. Ein vollständiger Fehlerfreiheitsnachweis ist bei einer Home-Assistant-Integration mit externen Backup-Agenten und Dateiformaten nicht möglich; die verbleibenden Risiken sind oben transparent ausgewiesen.
