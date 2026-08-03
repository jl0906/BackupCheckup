# Vollständige Revision – BackupCheckup 3.0.0-beta2

Stand: 3. August 2026

## Ergebnis

Die 3.0.0-beta1 enthielt bereits umfangreiche Notfallvorsorge, aber noch keine
eigenständige Wiederherstellungssimulation im technischen Sinn. Der Button im
Recovery-Reiter startete dieselbe Integritätsprüfung wie der normale
Verifizieren-Button. Der angezeigte Simulationsstatus wurde erst nachträglich aus
deren Endergebnis abgeleitet; ein eigener Ablauf, Live-Fortschritt und präzise
Abbruchzustände fehlten.

Beta2 ersetzt dieses Alias durch die administratorgeschützte Aktion
`backup_checkup.simulate_restore`. Sie verwendet bewusst dieselbe gehärtete,
schreibgeschützte Prüfstrecke für Auswahl der Speicherkopie, Download,
Entschlüsselung, Archivlesen, Ressourcenlimits, optionale SQLite-Prüfung und
Cleanup. Dadurch wird sicherheitskritische Archivlogik nicht dupliziert. Es wird
kein Home-Assistant-Restore-Endpunkt aufgerufen und kein produktiver Inhalt
überschrieben.

## Abgleich mit der geplanten Idee

| Anforderung | Beta1 | Beta2 |
|---|---|---|
| Eigenständiger Simulationsstart | Nein, Alias der Integritätsprüfung | Ja, eigener Admin-Service und eigener Button |
| Backup real einlesen | Ja, indirekt über die Integritätsprüfung | Ja, ausdrücklich als Simulationslauf derselben sicheren Pipeline |
| Entschlüsselung und Agent-Fallback | Vorhanden | Wiederverwendet |
| Alle inneren Archive lesen | Vorhanden | Wiederverwendet und live abgebildet |
| SQLite-Integrität | Optional vorhanden | Eigene sichtbare Stufe |
| Live-Einsicht | Nur allgemeines Aktivitätsjournal | Achtstufige Pipeline, Fortschritt und Messwerte |
| Differenzierte Endzustände | Zu grob | `passed`, `warning`, `failed`, `aborted`, `password_required`, `inconclusive` |
| Isolierte vollständige Extraktion | Nein | Noch nicht; Standardmodus liest sicher, extrahiert aber keinen kompletten Testbaum |
| Statische YAML-/JSON-/Manifest-Prüfung | Nein | Noch nicht Bestandteil des Standardmodus |
| Echter Home-Assistant-Start | Nein | Bewusst nein |

Damit ist die zuerst beschriebene Idee in ihrem sicheren Standardmodus umgesetzt.
Der Begriff bleibt bewusst „Simulation“ und nicht „garantierter Restore-Test“:
Add-on-Images, externe Datenbanken, Netzwerkdienste, Hardware und das tatsächliche
Startverhalten können durch statisches Einlesen nicht abschließend bewiesen werden.

## Funktionsrevision

Alle 39 Python-Produktionsmodule wurden syntaktisch und statisch inventarisiert.
Der AST enthält 580 Funktionen und Methoden. Geprüft wurden insbesondere:

- Setup, Konfiguration, Optionen, Migration und Presets;
- Backup-Normalisierung, Klassifikation, Historie und Analytics;
- Coordinator, Entitäten, Diagnose, Reparaturen und Benachrichtigungen;
- Agenten-, Speicher- und Task-Cleanup;
- Integrität, Verschlüsselung, Archivpfade, Limits, SQLite und Fehlerklassifikation;
- Recovery-Inventar, Inhaltsvergleich, Speicherresilienz, Checkliste,
  dokumentierter Test-Restore, Planexport und Simulation;
- Frontend-Registrierung, vollständige Frontend-Konfiguration und Live-Journal.

Die ausführbaren Regressionstests bestehen mit 126/126. Der für die neuen
3.0-Recovery- und Frontend-Module definierte Release-Gate erreicht 100 %
Funktions-, Statement- und Branch-Abdeckung. Eine zusätzliche, ungefilterte
Messung über das gesamte Paket ergibt jedoch nur 27 %. Das ist kein Fehler der
neuen Funktionen, aber ein ehrlicher verbleibender Testschuld-Befund der älteren
Module; Beta2 behauptet deshalb ausdrücklich keine 100-%-Gesamtabdeckung.

## Doppelungsprüfung

Eine kanonische AST-Prüfung fand in Beta1 vier identische UTC-Datumsparser. Beta2
führt diese gemeinsam in `datetime_utils.py`; danach gibt es keine Gruppe
identischer Funktionskörper mehr.

Die tokenbasierte Prüfung meldet noch drei kleine strukturelle Klone mit zusammen
76 von 10.941 Python-Zeilen (0,69 %): einen Importblock und zwei ähnliche
Konfigurations-/Schema-Standardblöcke. Diese Bereiche erfüllen unterschiedliche
Schichten und liegen deutlich unter der üblichen 3-%-Duplikationsschwelle. Eine
weitere Abstraktion würde die Lesbarkeit hier eher verschlechtern.

Zusätzlich wurde die Planerzeugung aus einem D-Komplexitätsbereich herausgelöst.
Verbleibende Wartungsschwerpunkte sind
`resolve_frontend_configuration` (D/21) und `compare_backup_content` (C/16).
Beide sind vollständig vom ausgewählten Branch-Gate erfasst; eine spätere
Aufteilung wäre dennoch sinnvoll.

## Frontend und Live-Einsicht

Der Recovery-Reiter zeigt jetzt:

- einen technischen Fortschrittsbalken;
- acht grafische Stufenkarten von Vorbereitung bis Abschluss;
- laufende, bestandene, übersprungene, gewarnte und fehlgeschlagene Stufen;
- gelesene Archive, Dateien und Datenmenge sowie Laufzeit;
- bestandene, offene und blockierende Prüfungen;
- einen unmissverständlichen Hinweis, dass kein echter Restore ausgeführt wurde;
- das parallel weiterlaufende, datenschutzgefilterte Live-Protokoll.

Zwischenstände werden über den normalen Home-Assistant-Zustandsfluss sofort
publiziert. Integritätsprüfung und Simulation teilen dieselbe Task-Sperre und den
gleichen manuellen Cooldown. Der doppelte Verifizieren-Button wurde im
Recovery-Reiter entfernt.

## Alternative Ausbaustufen

1. **Tiefer statischer Modus:** vollständige Extraktion in ein privates,
   limitiertes temporäres Verzeichnis; danach sichere JSON-, YAML- und
   `manifest.json`-Parser. Das wäre der sinnvollste nächste Schritt.
2. **Ephemere Testinstanz:** Start einer isolierten Home-Assistant-Umgebung aus
   dem extrahierten Backup. Das liefert mehr Realitätsnähe, benötigt aber Images,
   viel Speicher, klare Netzwerkisolation und versionsspezifische Migrationen.
3. **Echter Test-Restore auf separater Hardware/VM:** höchste Aussagekraft, aber
   kein sicherer In-Process-Test. BackupCheckup sollte ihn weiterhin nur
   dokumentieren und niemals automatisch auf dem Produktivsystem auslösen.

Beta2 wählt daher bewusst Stufe 1 in der ressourcenschonenden Standardvariante.
Der vorhandene dokumentierte externe Test-Restore bleibt als stärkster Nachweis
separat erhalten.

## Durchgeführte Prüfungen

- 126 Pytest-Tests: bestanden;
- Ruff für Produktions- und Testcode: bestanden;
- Python-Bytecode-Kompilierung: bestanden;
- JavaScript-Syntaxprüfung: bestanden;
- Manifest-Version und JSON: bestanden;
- neun Übersetzungsdateien mit vollständiger Schlüsselparität: bestanden;
- YAML-Beispiele, Services und Workflows: bestanden;
- AST-Duplikationsprüfung: keine identischen Funktionskörper;
- tokenbasierte Duplikation: 0,69 %;
- ZIP-Integrität wird beim Paketbau nochmals geprüft.

