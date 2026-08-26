# CLAUDE.md — djangoBase

Wiederverwendbares Django-Infrastruktur-Paket (App `djangobase`, Settings-Key `DJANGOBASE`).
Liefert: Hilfe-Seiten (`/hilfe/versionen|logs|tests|jobs|einstellungen`), dunkles
Sidebar-Layout (Bootstrap 5; Multi-Base-Templates `_shell.html` → `base_app.html` →
`base.html`), Theme-System (`body[data-theme]`, 5 Paletten), Sidebar-Resizer,
Toast-Stack, Logging-Helfer (`dblog.config`), LogClassifier, Einstellungen-Store
(JSON in `BASE_DIR/.djangobase.json`, keine DB), optional: Benutzer/allauth,
Traffic-Statistik, Übersetzungsmodul (deep_translator), Jobs-Seite.

## Repo & Workflow
- GitHub: `edgar965/djangoBase` (privat), EIN Branch `main` — direkt committen/pushen,
  keine Feature-Branches/PRs (explizite User-Vorgabe).
- Kein Version-Bump (`pyproject.toml`) und kein Commit/Push ohne explizite Anweisung
  (siehe globale `C:\Users\e\.claude\CLAUDE.md`).
- Theme-Integrations-Doku: `HOWTO_INTEGRATION_THEMING.md` (hier im Repo).

## Konsumenten (Stand 2026-07-07)
Alle als **editable Install** (`pip install -e A:\shared\djangoBase`) — Änderungen hier
wirken SOFORT live in allen Projekten:

| Projekt | Pfad | Besonderheit |
|---|---|---|
| assistant | `A:\assistant` (:8001) | eigene Sidebar `search/_sidebar.html`; voll integriert: INSTALLED_APPS, `/hilfe/`-URLs, `djangobase.jobs`, Resizer mit Server-Persistenz |
| WalkHop (ex spin1more/kachel) | `A:\WalkHop\djangoCode` | Standard-Shell; Multi-Brand walkhop.com + spin1more.com; wrappt den djangobase-Context-Processor pro Marke |
| NoiseSpy | `A:\NoiseSpy\NoiseSpy` | eigene Sidebar `tracker/_sidebar.html`; Server bindet per `sys.path` ein (Private-Repo, kein `pip git+`) |
| HumanBodyWeb | `A:\3DTools\HumanBodyWeb` (:4040) | Standard-Shell (`DJANGOBASE["menu"]`) |
| shortlongx | `A:\shortlongx\shortlongxWeb` (:5020) | Standard-Shell, 3-Ebenen-Menü, nutzt Jobs-Seite (cron_runner) |
| CamTrack | `A:\CamTrack\CamTrackDjango` | eigene Sidebar `app/_sidebar.html` |

Enumeration prüfen: ripgrep respektiert `.gitignore` und übersieht dabei Projekte
(ist mit shortlongx passiert) — für vollständige Suchen `rg --no-ignore` oder `grep -r`.

## Werkzeugkästen (skills / skills2 / umbau)

Drei Pakete, drei Zwecke — nicht vermischen:

| Paket | Was drin ist | Aufruf |
|---|---|---|
| `djangobase/skills/` | 12 Python-/Endpunkt-Werkzeuge (3DTools-Durchgang) | Hilfe→Skills |
| `djangobase/skills2/` | Python-Prüfer + **6 Frontend-Prüfer** (JS/Vorlagen) | Hilfe→Skills2 |
| `djangobase/umbau/` | Werkzeuge, die Quelltext **ändern** — kein Web-Knopf | `python -m djangobase.umbau.<name>` |

### Die sechs Frontend-Prüfer in skills2 (16.08.2026, aus 3DTools)

| Kennung | Findet | Belegter Fall |
|---|---|---|
| `jssyntax` | kaputte ES-Module (kopiert nach `.mjs`, dann `node --check`) | 3 Dateien mit Import mitten in einem Import — als `.js` grün, als `.mjs` rot |
| `jswaisen` | Module, die niemand lädt; Importe ins Leere | 3 verwaiste Module, die Funktionen anmeldeten → 3 tote Seitenzweige |
| `jsregistrierung` | `fn.x()` ohne `fn.x = …` | 4 Namen gerufen, nie angemeldet |
| `jsfaenger` | werfende Server-Abrufe ohne `try` | 16 von 101; zwei direkt hinter einem Nutzerklick |
| `jsfunktionen` | Funktionen ab N Zeilen (`skills2_funktionsgrenze`) | `loadClothUI` mit 245 Zeilen |
| `jsbefunde` | 10 zählbare Auffälligkeiten in `.js`/`.html` | 3.290 Befunde erhoben, davon `.ok`-Prüfung 71→0, `console.log` 144→0, `var` 157→0 |
| `jsstumm` | verschluckte Rückmeldungen: Meldung hängt an einem fehlenden Element, `catch` ohne Inhalt, `.catch(() => {})`, `if (!antwort.ok) return;` | assistant 67 → 0. Anlass: ein Sync-Knopf gab 31 s keine Rückmeldung, weil `if (!el) return;` in der Anzeige-Methode stand (17.08.2026) |

### Fixer, der schreibt: `fix-ausnahme` (17.08.2026, aus assistant)

Setzt in stumme `except`-Blöcke einen Log-Aufruf — Stufe aus dem Code abgeleitet
(`debug` bei `continue` in Schleifen, `warning` bei erwarteten Typen wie
ValueError/KeyError, `exception` mit Traceback bei `except Exception`) — und
`# stumm gewollt: <Grund>` bei ImportError/KeyboardInterrupt. Die Meldung nennt
nur Funktionsname und Typ, nie Variablen: So kann durch den Umbau nichts
Geheimes ins Log geraten. Im Projekt assistant: 636 Blöcke in 205 Modulen,
`protokoll` 656 → 0, danach 649 Tests grün.

**Netz (nicht verhandelbar):** `compile()`, „`protokoll` sieht hier weniger", UND
die Frage, ob der Name `logging` modulweit gebunden ist. Der letzte Punkt kostete
einen Vorfall: In `mail/models.py` stand weiter unten `import logging as
_logging`; der Fixer hielt das für den Import, die Datei kompilierte, und die
Anwendung startete nicht mehr (`NameError`).

### Testlaufzeiten je Testcase (Hilfe → Tests)

`testdauern.Dauern` hängt `--durations 0` an (nur wenn der Interpreter des
Projekts Python 3.12+ ist — sonst bricht der Lauf an einem unbekannten Argument
ab) und liest die Laufzeiten aus der Ausgabe. `testhistorie.Testhistorie` hält
die **letzten vier Läufe je Testcase und je Suite** mit Datum/Uhrzeit in
`BASE_DIR/logs/testhistorie.json` (keine DB — die Seite muss auch beim
Neuaufbau der Test-DB Zahlen zeigen). `testtabelle.Testtabelle` baut daraus die
sortierbare Tabelle (`_tabelle.html`): Testcase · letzte · Ø · Trend ·
letzte 4 Läufe · Run. Trend erst ab 25 % Abweichung, alles darunter ist Rauschen.

Fehlt `DJANGOBASE["test_discover"]`, leitet die Seite die Labels aus denselben
`test_befehle` ab — die Einzeltest-Reiter stehen damit in JEDEM Projekt. Die
Discovery ist 10 Minuten gecacht (sie importiert jedes Testmodul).

### Zwei Einteilungen: Kategorie und Bereich (17.08.2026)

**Kategorie** = wie getestet wird (`unit`, `component`, `ui`, `automated`,
`performance`, `longrunner`). Sie ist der ORDNER `app/tests/<art>/`; die
Combo-Box „Verschieben" hängt die Testdatei um (`testverschieben.Verschieber`).

**Bereich** = was getestet wird (Chat, Mail, Musik …). Den gibt **das Projekt**
an, in `settings.py` oder unter Einstellungen → djangoBase (Feldtyp `zeilen`,
eine Angabe je Zeile):

    DJANGOBASE["test_bereiche"] = [
        {"slug": "musik", "name": "Musik", "praefixe": ["search.tests.musik"],
         "beschreibung": "…"},          # oder: "musik | Musik | search.tests.musik | …"
    ]

Ohne Angabe wird der Bereich aus dem Ordner abgeleitet (`app/tests/<bereich>/
<art>/`, sonst die App). Die REIHENFOLGE der Angabe ist die Reihenfolge in der
Tabelle; dasselbe gilt für `test_kategorien` („unit | Unit", nur bekannte Slugs).

Darstellung: **EINE Tabelle je Kategorie**, Bereich als eigene Spalte, Zeilen
danach vorsortiert, vor jedem Bereich eine Abschnittszeile mit „Auswählen" und
„Bereich ausführen". Sortiert der Nutzer nach einer anderen Spalte, nimmt
`tabellen_sortierung.js` die Abschnittszeilen heraus (`data-gruppe`) und meldet
`tabelle:sortiert`; `tests_bereiche.js` setzt sie zurück, sobald wieder nach
Bereich sortiert wird.

**Ein Bereich, dessen Präfix über anderen liegt** (`search.tests` über
`search.tests.chat`), ist KEIN Verschiebeziel — sonst landet die Datei in
`search/tests/<art>/` und verschwindet aus der Gliederung. Genau das ist am
17.08.2026 einmal passiert (`Bereiche.ziele`).

Projektseiten mit eigenem Runner nehmen `Testtabelle(..., run_modus="knopf")`
(rendert `<button data-run=…>` statt `?run=`-Link) und setzen
`data-tests-auswahl="ereignis"` auf einen Vorfahren; die Auswahl meldet dann
`tests:auswahl-lauf` statt zu posten. Laufzeiten aus einem fremden Runner gehen
über `testmitschrift.Mitschrift` in dieselbe Historie.

**Statische Dateien:** Vorlagen hängen `?v={{ djangobase.statik_v }}` an Skripte
UND an ES-Importe (`statik.Statik` = jüngste mtime der djangoBase-JS/CSS). Ohne
das liefert der Browser-Cache alte Module — gemessen: mit Cache-Buster kam die
neue Fassung, ohne die alte, bei frisch aktiviertem Service Worker.

**Logging:** Testläufe und Verschiebungen loggen auf `djangobase.tests` (nicht
`django` — dort hängt `django.server` mit jeder Anfrage). Ein Konsument, der
nichts konfiguriert, sieht davon nichts; im assistant liegt dafür
`djangobase.log` samt Eintrag in `log_sources`.

### Live-Lauf und Spalte „Nr." (17.08.2026)

**Live-Lauf:** `POST /hilfe/tests/strom/` (`teststrom.Teststrom`) fährt die
geprüften Ziele und streamt JSON-Zeilen: `start` → `log`/`progress` → `summary`.
`tests_strom.js` fängt Run-Link, „Alle ausführen", „Bereich ausführen" und die
Checkbox-Auswahl ab, schreibt ✓/✗ in **alle** Zeilen mit dieser Test-ID (der
Fall steht im Kategorie-Reiter UND in „Alle") und am Ende die Laufzeiten. Die
`?run=`-Links bleiben im HTML — ohne das Modul läuft es wie vorher mit
Seitenwechsel.

**Der Prozess darf nie zurückbleiben — drei Netze, nicht eins** (18.08.2026
nachgezogen; das `finally` allein deckte den Fall nicht ab):

1. `readline()` blockiert, also kommt `GeneratorExit` erst beim nächsten `yield`.
   Ein Test, der hängt und nichts ausgibt, hätte den Prozess endlos gehalten →
   **Wächter-Thread** (`threading.Timer`) beendet nach Ablauf der Frist ohne auf
   Ausgabe zu warten. Gemessen an einem Prozess, der eine Zeile schreibt und dann
   schläft: Abbruch nach 6,2 s bei Frist 6 s (vorher: 300 s).
2. `kill()` trifft nur den einen Prozess; ein Testlauf hat Kinder
   (`ProcessPoolExecutor`), und auf Windows sterben die NICHT mit dem Eltern-
   prozess → `testtoeter.Toeter` beendet den **Baum** (`taskkill /F /T` bzw.
   `os.killpg`; dafür startet der Lauf auf POSIX mit `start_new_session=True`).
3. Endet der SERVER mitten im Lauf, wäre der Testprozess verwaist → `atexit`.

Nebenbefund derselben Runde: `OpenProcess` gelingt auf Windows auch für einen
BEENDETEN Prozess, solange noch ein Handle offen ist. „Läuft der noch?" fragt
deshalb `GetExitCodeProcess` (259 = `STILL_ACTIVE`) — sonst hätte eine vergessene
Sperre bis zur Frist gehalten.

**EIN Lauf zur Zeit** über `testsperre.Laufsperre`: eine Datei
(`logs/teststrom.lock`, `O_EXCL`) mit der Server-PID. Die JS-Sperre der ersten
Fassung galt nur für den EINEN Tab — ein zweiter Tab startete munter einen
zweiten Lauf auf derselben Testdatenbank. Stirbt der Server, gilt die Sperre
nicht mehr (PID-Prüfung), spätestens nach `FRIST` verfällt sie. Der Knopf
**„Abbrechen"** (`POST … {"abbrechen": true}`) beendet Baum und Sperre — ohne ihn
hielte ein hängender Lauf eine Stunde.

Den Fortschritt aus der Ausgabe liest `testzeilen.Testzeilen` — drei gemessene
Fallen: Name und Ergebnis stehen nicht in einer Zeile, Zeitstempel können mitten
in der Zeile stehen, und bei Tests mit Docstring zeigt `-v 2` dessen erste Zeile
statt des Namens.

**Was ausgeführt werden darf** steht an EINER Stelle: `testziele.Testziele`
(entdeckte Test-IDs, Slugs konfigurierter Befehle, Karten-Labels; Form geprüft).
Seiten-Lauf und Live-Lauf benutzen sie gemeinsam.

**Spalte „Nr.":** der Platz in der Tabelle, änderbar.
`POST /hilfe/tests/nummer/` bekommt Kennung, Nummer und die aktuell angezeigte
Reihenfolge des Abschnitts; `testreihenfolge.Reihenfolge` ordnet um und speichert
`logs/testreihenfolge.json`. Erst die Antwort hängt die Zeilen um — sonst gäbe es
zwei Meinungen darüber, wo ein Test steht. Die Nummer gilt INNERHALB des
Bereichs und wandert beim Verschieben mit. Sie ist keine
Ausführungsreihenfolge — `manage.py test` bestimmt die selbst.

**Spaltenordnung** (in `Testtabelle.SPALTEN`, und `testzeiten.js` muss dazu
passen — Test `test_js_kennt_dieselben_spalten`):
Auswahl · Nr. · Kategorie · Bereich · Testcase · Ziel · letzte · Ø · Trend ·
letzte 4 Läufe · Run.

### Zwei Fallen in den Tabellen-Modulen, beide am 17.08.2026 behoben

`TabellenBreiten` merkte beim Ziehen NUR die angefasste Spalte; nach F5 verteilte
der Browser den Rest neu, und es sah aus wie „nicht gemerkt". Jetzt speichert
`_merkenAlle()` die ganze Gruppe (gelesen aus einer SICHTBAREN Tabelle — in einem
`display:none`-Panel ist jede Breite 0).

`TabellenSortierung` merkte nur den Spalten-INDEX. Kommen Spalten dazu, zeigt er
auf etwas anderes: Nach dem Einfügen von „Nr." und „Kategorie" sortierte die
Seite nach „Nr." (einer `sortAus`-Spalte), und die Bereichs-Abschnitte
verschwanden. Jetzt wird der Spalten-**Key** mitgespeichert, der Index daraus neu
bestimmt, und ein Eintrag auf eine `sortAus`-Spalte wird verworfen.

Regeln von `jsbefunde` stehen in `skills2/jsregeln.py` (eine Klasse je Regel),
der Klammerzähler in `skills2/jsklammern.py` (Template-Strings über mehrere
Zeilen, `} catch (e) {`).

Tests: `djangobase/tests/unit/test_skills2_frontend.py` — je Werkzeug ein Fund
UND eine Gegenprobe, dazu die vier Fehlalarme, die beim Bau aufgefallen sind.

### Frontend-Klassen, die dazugehören

`djangobase/static/djangobase/js/serverabruf.js` und `protokoll.js` sind die
**kanonische Fassung** (die Umsteller schreiben Importe auf genau sie).
Konsumenten mit vielen kurzen relativen Importen legen eine Weiterleitung an,
statt zu kopieren:

```js
export { Serverabruf } from '/static/djangobase/js/serverabruf.js';
```

`Serverabruf` prüft `response.ok`, hängt bei Fehlern **Status, Rumpf und
geparstes JSON** an die Ausnahme (`fehler.status/.rumpf/.daten`), setzt den
CSRF-Kopf und kennt `senden`/`formular`/`jsonOderNull`. Cookiename über
`Serverabruf.COOKIENAME` oder `<meta name="csrf-cookie">`.

### JS in der Testsuite: `djangobase.testhelfer.Webmodul`

Lädt ein ES-Modul der Seite in Node — spiegelt die Importkette und biegt
absolute `/static/…`-Pfade um (die Node sonst als `A:\static\…` sucht) sowie
`?v=`-Anhänge. Ein Import ins Leere wirft, statt still zu überspringen.

### Konformitätsprüfungen: `djangobase.tests.konform` (21.08.2026)

Neun Testdateien, die im KONSUMENTEN laufen (`manage.py test
djangobase.tests.konform`) und fragen: erbt dieses Projekt djangoBase wirklich?
Alle ohne Datenbank (`SimpleTestCase`, `databases = []`) — geprüft werden
Einstellungen, Vorlagen und Quelltext, nicht Daten.

**Was sie durchsuchen dürfen, entscheidet `tests/konform/quellen.py`** — eine
Stelle für alle Prüfer. Draußen bleiben: `TABU`-Ordner (Umgebungen, Caches),
das djangoBase-Paket selbst, `MEDIA_ROOT` und alles aus dem neuen Schlüssel
`DJANGOBASE_KONFORM_AUS` (Pfad-Teilstrings). Gelaufen wird mit `os.walk` und
Ast-Abschnitt VOR dem Abstieg; das Ergebnis liegt im Zwischenspeicher.

Der erste Lauf im `assistant` meldete **199 Verstöße, davon 6 echt**: 111 aus
dem Chrome-Profil eines Verkaufs-Werkzeugs, 56 Vorlagen aus demselben Ordner,
23 JS-Dateien aus der Virensuche-Quarantäne (Dateien, welche die App
UNTERSUCHT). Laufzeit 81 s, weil `rglob` durch 84.442 archivierte Mails lief —
je Suchmuster und je Testmethode erneut. Nach dem Umbau: 102 Tests, **1,0 s**.

Drei Prüfer waren zudem selbst falsch geeicht (alle mit Gegenprobe repariert):

| Fehlalarm | Ursache | Jetzt |
|---|---|---|
| „Seitenleiste leer" | nur `menu` gefragt | `sidebar_template` zählt genauso |
| „Modul nirgends gebunden" | unter `BASE_DIR` gesucht | `tabellen_auto.js` zählt |
| Kontrastfehler in Prosa | `pre|code` im ganzen Dokument | nur `<style>`-Blöcke |

Umgekehrt hatte `test_statik` einen **blinden Fleck**: Es sah nur Adressen, die
selbst auf `.js` enden — `src="{% static 'app/x.js' %}?v=3"` bricht am inneren
Anführungszeichen ab. Damit war die häufigste Django-Schreibweise unsichtbar.

### Hilfe → Jobs: die Ablauf-Übersicht (26.08.2026)

Die Seite hat **zwei Teile mit verschiedenen Fragen**:

| Teil | Frage | Quelle |
|---|---|---|
| oben (alt) | Was tut der Daemon **gerade**? | `djangobase.jobs` — Registry, im Speicher, vom Projekt angemeldet |
| unten (neu) | Was ist **passiert**? | `Jobkatalog` + `Jobverlauf` — Dateien, überleben den Neustart |

Anlass war die Frage, ob ein iPaaS-Werkzeug (n8n, Activepieces) nötig ist.
Antwort: Was fehlte, war keine Ablauf-**Steuerung**, sondern die
Ablauf-**Übersicht** — „welcher Job wann zuletzt lief, wie lange er
brauchte und ob er Fehler warf".

**Vier Klassen, vier Zuständigkeiten:**

- `joberkennung.Joberkennung` — findet die Jobs selbst: die
  Management-Commands der Projekt-Apps plus die angemeldeten Daemons.
  Django-eigene Befehle (`migrate`, `runserver`, …), Namen mit
  führendem `_` und `DJANGOBASE["jobs_ausschluss"]` fallen heraus.
- `jobkatalog.Jobkatalog` — merkt den Bestand in
  `logs/jobkatalog.json`, **Frist ein Tag**. Grund: Für die
  Beschreibung wird jede Befehlsklasse importiert (assistant: 93).
  Der Knopf „Jetzt aktualisieren" erzwingt es sofort.
- `jobverlauf.Jobverlauf` — `logs/joblaeufe.jsonl`, **eine Zeile je
  Lauf**. Anhängen statt Umschreiben, weil Commands eigene Prozesse
  sind und gleichzeitig schreiben; ein Umschreiber würde den anderen
  verlieren.
- `jobuebersicht.Jobuebersicht` — führt beides zusammen. Gescheiterte
  zuerst, dann die Gelaufenen, dann die nie Gelaufenen.

**Die Aufzeichnung** (`jobaufzeichnung.Jobaufzeichnung`) legt sich in
`AppConfig.ready()` um `BaseCommand.execute` — einmal, für alle
Befehle, auch für künftige. Sie **misst nur**: jede Ausnahme wird
notiert und unverändert weitergereicht, jeder Fehler beim Aufzeichnen
verschluckt. Abschalten: `DJANGOBASE_JOBAUFZEICHNUNG = False`.

**Keine Migration** — bewusst. djangoBase steckt in sechs Projekten;
eine Tabelle müsste jedes erst migrieren. Dateien neben den Logs gehen
denselben Weg wie `logs/testhistorie.json`.

Prüfungen: `tests/unit/test_job{verlauf,katalog,uebersicht,aufzeichnung}.py`
— 61 Stück, nach Kriterium 19 („BDD ohne Gherkin") geschrieben: Die
Klasse nennt die Ausgangslage (`EinBestandVonGestern`), die Methode das
erwartete Verhalten (`test_wird_beim_lesen_neu_ermittelt`). Helfer in
`tests/unit/jobwerkzeug.py`.

### Neue DJANGOBASE-Schlüssel

`skills2_register` (Vorgabe `["fn"]`), `skills2_abrufklassen`
(`["Serverabruf"]`), `skills2_funktionsgrenze` (90), `skills2_ignorieren`,
`jobs_ausschluss` (Befehle, die auf der Jobs-Seite nicht als Ablauf
gelten — Liste oder eine Angabe je Zeile).

Als **Settings-Konstanten** (nicht im `DJANGOBASE`-Dict, weil sie nur Tests
betreffen): `DJANGOBASE_KONFORM_AUS` (Datenordner, die keine Prüfung ansieht)
und `DJANGOBASE_KONFORM_TABELLEN_AUS` (einzelne Dateien, die bewusst kein
Tabellen-Raster bekommen — Druckansichten, feste Gliederungen, Tabellen mit
eigener serverseitiger Sortierung).

## Vor Änderungen (Breaking-Check)
- Shell-Templates (`base.html`, `base_app.html`, `_shell.html`, `_sidebar.html`,
  `_nav.html`, `sidebar.css`) treffen ALLE Konsumenten — nur additiv/opt-in ändern.
  Am assistant nie etwas kaputt machen.
- Tests laufen im Host-Kontext (kein Standalone-Runner): Wegwerf-Host `A:\tmp_dbhost`
  (py3.10-venv, `python -m django test djangobase`). Teststruktur:
  `djangobase/tests/{unit,component,integration}`, Basisklasse `BasisTest`
  (+ `StoreIsolationMixin` lenkt den Store auf eine Temp-Datei).
- Schneller Konsumenten-Realitäts-Check:
  `cd A:\assistant && pythonVENV\Scripts\python.exe manage.py check`
- Nach djangoBase-Update beim Konsumenten ggf. `pip install -e A:/shared/djangoBase
  --no-deps` neu ausführen (sonst bleibt die Metadaten-Version stale).

## Static-/Cache-Fallen
- Static-Edits (z.B. `sidebar.js`) kommen beim Konsumenten erst an nach
  (a) runserver-Neustart UND (b) Service-Worker-Cache-Refresh (der assistant cached
  `/static/` cache-first in `sw.js` → dort `CACHE_VERSION` bumpen). Ausgelieferte
  Datei verifizieren mit Cache-Bust-Query (`?cb=<timestamp>`). Der Django-Autoreloader
  watcht nur `.py`-Dateien.
- `markActive` der generischen Menü-Sidebar keyed auf **pathname** — Menüeinträge, die
  sich nur per `?query`/`#fragment` unterscheiden, kollidieren (z.B. HumanBodyWeb
  `/humanbody/config/` vs. `#tab-creator`; spin1more `/ausfluege-karte/` vs. `?neu=1`).

## Integrations-Rezept (Kurzform)
1. `pip install -e A:\shared\djangoBase`
2. `INSTALLED_APPS += ['djangobase']`; Context-Processor
   `djangobase.context_processors.djangobase`
3. `path('hilfe/', include('djangobase.urls'))`
4. `LOGGING = dblog.config(BASE_DIR/'logs')` (rotierende django.log/error.log)
5. `DJANGOBASE = {...}` konfiguriert alles (titel, farben, menu bzw. sidebar_template,
   log_sources, repos, test_befehle, zugriff, theme_modes, resizable_sidebar, …)
6. `manage.py migrate djangobase`

- Eigene Sidebar behalten: `DJANGOBASE['sidebar_template']` setzen + darin
  `{% include "djangobase/_nav.html" %}` für den Einstellungen-/Hilfe-Block.
- Repo-Slugs nicht hardcoden: leer (`""`) lassen → wird aus dem lokalen git-`origin`
  abgeleitet; Geschwister-Repos mit absolutem Pfad eintragen.
- Pro-Mandant-/Station-Logs: `DJANGOBASE['log_source_provider']` = Callable, liefert
  pro Request `(verzeichnis, sources)`; Dateinamen dürfen absolut sein.
