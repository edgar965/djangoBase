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

### Neue DJANGOBASE-Schlüssel

`skills2_register` (Vorgabe `["fn"]`), `skills2_abrufklassen`
(`["Serverabruf"]`), `skills2_funktionsgrenze` (90), `skills2_ignorieren`.

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
