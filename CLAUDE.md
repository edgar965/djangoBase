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
