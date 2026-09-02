# Plan: Hilfe → Werkzeug Language Server

Stand 02.09.2026. Ansage Edgar: „mach eine neue Seite Hilfe – Werkzeug Language
Server, die so ähnlich aufgebaut ist wie Werkzeug Code Review, und das
konfigurierbar auf Knopfdruck macht."

Ein Language Server versteht ein Projekt semantisch — Definitionen, Referenzen,
Typen, Fehler vor dem Lauf. Die Seite soll ihn auf Knopfdruck über das Projekt
laufen lassen, die Befunde als sortierbare Tabelle zeigen, den letzten Lauf
merken (wie Klassenmodell), und in einer zweiten Stufe Referenzen und
Umbenennen anbieten (das „Umgestalten").

## 1. Werkzeugwahl

| Sprache | Werkzeug | Warum | Stufe |
|---|---|---|---|
| Python | **basedpyright** | `pip install basedpyright`, bringt Node über `nodejs-wheel-binaries` selbst mit; CLI `basedpyright --outputjson`, Server `basedpyright-langserver --stdio` | 1 |
| Python | pyright (npm) | dasselbe Werkzeug, braucht npm; nur als Fallback erkennen | 1 |
| JavaScript | typescript-language-server / `tsc --checkJs --noEmit` | Node v24 ist da; ES-Module des Projekts prüfbar über `jsconfig.json` mit `allowJs` | 3 |

Zwei Betriebsarten, beide über dasselbe Werkzeug:

- **A · Stapellauf** über die CLI mit JSON-Ausgabe. Ein Prozess je Lauf, kein
  Zustand, robust. Stufe 1.
- **B · Sitzung** über das Language Server Protocol (JSON-RPC über stdio).
  Nötig für „wer benutzt X", „gehe zur Definition", „umbenennen". Stufe 2.

Fehlt das Werkzeug, erklärt die Seite, was zu installieren ist
(`pip install djangobase[languageserver]`) — dieselbe Bauart wie
`umbau/codequalitaet.py` mit `v.fehlt`. Nie ein leerer Kasten.

## 2. Optionen

Gespeichert in `.djangobase.json` über `store.speichern_gruppe("languageserver",
werte)`; die Optionen gehen in den Ablage-Abdruck, damit ein altes Ergebnis nie
für andere Optionen gilt.

| Option | Werte | Vorgabe | Wirkung |
|---|---|---|---|
| `werkzeug` | basedpyright / pyright / auto | auto | welches Programm gestartet wird |
| `modus` | off / basic / standard / strict | **basic** | `typeCheckingMode` — basic meldet undefinierte Namen, falsche Aufrufe, Importfehler; strict färbt Django rot |
| `pfade` | Häkchen je Hauptast (Vorschlag aus `umbau.globalbestand.hauptaeste`) | alle Python-Äste | `include` |
| `ausschluss` | venv, `migrations`, `.cache`, `node_modules`, `werkzeug/sicherung`, Tests (Schalter) | alle an außer Tests | `exclude` |
| `python` | Interpreter des Projekts | `sys.executable` | `venvPath`/`venv`, damit Importe aufgelöst werden |
| `regeln` | Häkchen je Regel-Gruppe | s. u. | `reportXxx` = error / warning / information / none |
| `stufe` | error / warning / information | warning | ab welcher Stufe die Tabelle zeigt |
| `deckel` | Zahl | 500 | höchstens so viele Befunde in der Tabelle, Rest als Zähler je Regel |
| `stubs` | an/aus | aus | `django-types` benutzen, wenn installiert (weniger Fehlalarme am Manager) |
| `zeitlimit` | Sekunden | 300 | `subprocess.run(timeout=…)`, danach sauberer Abbruch mit Meldung |

Regel-Gruppen, Vorgabe:

    an (error):     reportUndefinedVariable, reportCallIssue, reportArgumentType,
                    reportPossiblyUnbound, reportMissingImports
    an (warning):   reportUnusedImport, reportUnusedVariable, reportOptionalMemberAccess
    aus:            reportAttributeAccessIssue (Django-Manager `objects`, `import *`),
                    reportUnknownMemberType und alles, was nur strict kennt

Was der Server NICHT sieht, steht als Karte auf der Seite: `from x import *`,
`getattr` auf Slots, Djangos Manager, `SystemSetting.get`-Werte. Dort meldet er
entweder nichts oder Fehlalarme — das gehört neben die Tabelle, nicht in ein
Handbuch.

## 3. Code-Teile

### Python in djangoBase

`djangobase/umbau/` ist Django-frei (nur `pathlib`, `subprocess`, `json`);
`djangobase/views/` hält die Seite. Eine Klasse je Datei, unter 300 Zeilen.

| Datei | Klasse | Aufgabe |
|---|---|---|
| `umbau/ls_konfig.py` | `LsKonfig` | Vorgaben, `laden()`/`speichern()` über `store`, `als_pyrightconfig()` → dict, `abdruck()` |
| `umbau/languageserver.py` | `LanguageServer` | Programm finden (`shutil.which`, `Scripts/` des venv), `pyrightconfig.json` nach `BASE_DIR/.cache/umbau/languageserver/` schreiben (nie ins Temp — 100-GB-Regel), `basedpyright --outputjson -p <cfg>` starten, JSON lesen (`generalDiagnostics`: file, range, severity, message, rule), `LsErgebnis` liefern (Befunde, Dateien, Dauer, Werkzeug-Fassung, `fehlt`-Grund) |
| `umbau/ls_befunde.py` | `LsBefunde` | Gewichtung (error > warning > information), Gruppierung je Datei und je Regel, Deckel, Zeilen für `_tabelle.html` |
| `umbau/ls_sitzung.py` | `LsSitzung` | **Stufe 2.** `basedpyright-langserver --stdio` als Dauerprozess, JSON-RPC (`initialize`, `textDocument/didOpen`, `references`, `definition`, `rename` → `WorkspaceEdit`), Schloss, Zeitlimit, `beenden()`. EINE Sitzung je Prozess (Bauart wie `depot/IB/reihen_speicher.SPEICHER` in shortlongx) |
| `umbau/ls_umbenennen.py` | `Umbenennung` | **Stufe 2.** `WorkspaceEdit` → Vorschau (Datei, Zeile, alt → neu) → Anwenden mit Sicherung und Netz, dieselbe Bauart wie die Fixer (`skills/fixer.py`) |
| `views/languageserver.py` | `LanguageServerView(ZugriffMixin, View)` + `LsSpeicher(Speicher)` | GET zeigt den letzten Lauf aus der Ablage (`bereich = "languageserver"`, `quellen = (languageserver_modul, ls_konfig_modul)`), rechnet NIE. POST `aktion=lauf` startet den Lauf, `aktion=speichern` schreibt die Optionen, `aktion=neu` leert die Ablage. Reiter: Befunde · Je Regel · Je Datei · (Stufe 2) Referenzen |
| `views/languageserver_status.py` | `LanguageServerStatusView` | JSON: `wartet / laeuft / fertig / fehler`, Sekunden, Befundzahl — gepollt von der Seite |
| `views/languageserver_referenzen.py` | `LanguageServerReferenzenView` | **Stufe 2.** POST Datei/Zeile/Spalte → Referenzen, Definition; POST `umbenennen` → Vorschau, zweiter POST wendet an |
| `urls.py` | — | `languageserver/`, `languageserver/status/`, `languageserver/referenzen/`, `languageserver/umbenennen/` |
| `pflichtmenue.py` | — | `PflichtEintrag("Werkzeug Language Server", "bi-braces", "languageserver", "Ein Language Server (basedpyright) über das Projekt: undefinierte Namen, falsche Aufrufe, tote Importe — auf Knopfdruck, mit Referenzen und Umbenennen")` hinter Klassenmodell |
| `pyproject.toml` | — | `[project.optional-dependencies] languageserver = ["basedpyright>=1.19"]` |
| `skills/languageserver_werkzeug.py` | `LanguageServerWerkzeug(Werkzeug)` | optional: Adapter mit `slug = "languageserver"`, damit der Stapellauf auf „Werkzeug Code Review" den Bericht mitnimmt (`Ergebnis` mit Spalten Stufe/Datei/Zeile/Regel/Meldung) |

Der Lauf gehört in einen **Hintergrund-Thread** (`ls-lauf`), nicht in den
Request: Auf shortlongx sind es rund 700 `.py`-Dateien, und ein Request, der
eine Minute rechnet, sieht für den Watchdog (`watchdog_server.ps1`, TCP-Probe
mit 2 s) wie ein toter Server aus. Muster: `ReviewStartView` + `ReviewStatusView`
in `views/review.py`.

### Vorlagen und JS

| Datei | Inhalt |
|---|---|
| `templates/djangobase/hilfe/languageserver.html` | wie `skills.html`: Karte **Einstellungen** (Formular mit den Optionen, Knöpfe „Prüfen" und „Einstellungen speichern"), Karte **Ergebnis** (Kennzahlen Fehler/Warnungen/Hinweise, Dateien, Dauer, Stand und Alter wie Klassenmodell, Werkzeug-Fassung), Tabelle über `{% include "djangobase/_tabelle.html" %}`, Karte **Was der Server nicht sieht** |
| `templates/djangobase/hilfe/_ls_einstellungen.html` | Teilvorlage Formular — hält die Hauptvorlage unter 300 Zeilen |
| `templates/djangobase/hilfe/_ls_tabelle.html` | Spalten Stufe · Datei · Zeile · Regel · Meldung · (Stufe 2) Knopf „Referenzen"; `data-sort` an jeder Zelle, Sortierwerte ganzzahlig (Django lokalisiert Fließkommazahlen zu „7,3") |
| `static/djangobase/js/languageserver.js` | ES-Modul, Klasse `LanguageServerSeite`: Formular per `fetch` absenden, Status alle 2 s pollen, Tabelle nachladen, Filterzeile (Text, Regel, Stufe), Zähler „n von m Befunden". Mit `?v=`-Cache-Busting |
| `static/djangobase/js/languageserver_referenzen.js` | **Stufe 2.** Klasse `ReferenzenPanel`: Klick auf einen Befund öffnet Referenzen und Definition; Umbenennen-Dialog mit Vorschau und Bestätigung |
| Sortierung/Breiten | `tabellen_sortierung.js`, `tabellen_breiten.js` — genau wie auf skills |

### Tests (`djangobase/tests/unit/`)

| Datei | Prüft |
|---|---|
| `test_ls_konfig.py` | Vorgaben; Rundreise über den Store; `als_pyrightconfig()` enthält Ausschlüsse, venv, Regeln; Abdruck ändert sich mit jeder Option |
| `test_languageserver.py` | Parser gegen ein JSON-Fixture mit drei Befunden; fehlendes Programm → `fehlt` mit Installationshinweis, kein Traceback; Zeitlimit → sauberer Abbruch; Konfigurationsdatei liegt unter `BASE_DIR/.cache`, nie unter `%TEMP%` |
| `test_ls_befunde.py` | Gewichtung, Gruppierung, Deckel, Stufen-Filter |
| `test_ls_sitzung.py` | **Stufe 2.** Attrappen-Server über stdio (Echo der JSON-RPC-Antworten); Umbenennen liefert Vorschau ohne zu schreiben |

Gegenprobe (Regel „sabotieren → muss rot werden"): eine Datei mit
`undefinierter_name` unter `BASE_DIR/.cache/umbau/languageserver/probe/`
anlegen, Lauf starten, der Befund muss erscheinen, Datei wieder weg.

## 4. Ablauf eines Laufs (Stufe 1)

1. POST `aktion=lauf` → Optionen aus dem Formular → `LsKonfig.speichern()` →
   Schlüssel = Wurzel + Abdruck(Optionen, Werkzeug-Fassung).
2. `LsSpeicher.nachsehen()` — liegt ein Ergebnis zu diesem Schlüssel, wird es
   gezeigt. Sonst Thread `ls-lauf`: `pyrightconfig.json` schreiben, Prozess
   starten, JSON lesen, `LsErgebnis` in die Ablage (pickle, `ablage.py`),
   Status „fertig".
3. Die Seite pollt `languageserver/status/` alle 2 s und lädt dann die Tabelle
   (`GET ?reiter=befunde`).
4. GET ohne Lauf zeigt den letzten Stand mit Alter — ein GET rechnet nie
   (dieselbe Regel wie Klassenmodell seit 02.09.2026).

## 5. Erwartete Zahlen — und was noch keine Messung ist

- basedpyright im Basic-Modus über `shortlongxWeb`, `brain`, `depot`
  (rund 700 Dateien): Schätzung 20 bis 60 Sekunden. Das ist eine Schätzung,
  kein Messwert — der erste Lauf liefert die Zahl, und sie steht danach auf der
  Seite als „Dauer".
- Der erste Lauf wird viele Befunde zeigen (Django-Manager, `import *` in
  `views/basis_datensatz.py`). Deshalb die Vorgabe basic und abschaltbare
  Regeln. Die Zahl aus dem ersten Lauf gehört in den Bericht, bevor irgendeine
  Regel verschärft wird.
- Beleg für den Nutzen vom selben Tag: nach einem Patch fehlte in
  `brain/stock3_importer.py` der Alias `_unveraendert`; pyflakes hat es nicht
  gesehen, der Fehler kam erst beim Ausführen. `reportUndefinedVariable`
  hätte ihn vor dem Serverstart gemeldet.

## 6. Reihenfolge

1. **Stufe 1** (ein Arbeitstag): `ls_konfig`, `languageserver`, `ls_befunde`,
   View + Status, Vorlagen, JS, Menü, Tests, Installation in den venvs, erster
   Lauf auf shortlongx mit Zahl.
2. **Stufe 2**: `ls_sitzung`, Referenzen, Definition, Umbenennen mit Vorschau
   und Sicherung.
3. **Stufe 3**: JavaScript über tsserver oder `tsc --checkJs`.

## 7. Offene Entscheidungen

- basedpyright (pip, Node inklusive) oder pyright (npm)? Empfehlung
  basedpyright — ein `pip install` je venv, nichts weiter.
- Lauf im Hintergrund-Thread (empfohlen, wegen Watchdog) oder synchron?
- Soll die Seite in Stufe 2 wirklich Dateien umschreiben (Umbenennen) — mit
  Sicherung wie die Fixer — oder nur die Vorschau zeigen?
- `django-types` installieren, damit `Model.objects` keine Fehlalarme wirft?
