# djangoBase

Gemeinsames Django-Paket (App `djangobase`, Einstellung `DJANGOBASE`) für mehrere Projekte: Hilfe-Seiten
(`/hilfe/versionen|logs|tests|jobs|einstellungen`), Sidebar-Layout (Bootstrap 5, `_shell.html` → `base_app.html` →
`base.html`), Themes (`body[data-theme]`, 7 Paletten, Farben über `var(--dbt-…, #alt)`), Toasts, Logging
(`dblog.config`), Einstellungsspeicher (`BASE_DIR/.djangobase.json`, keine DB), optional Benutzer/allauth, Traffic,
Übersetzung (Google, wahlweise Azure mit Rückfall auf Google), Jobs-Seite. Ausführlich: `doku/claude_vollfassung.md`.

## Repo
GitHub `edgar965/djangoBase` (privat), ein Branch `main`. Kein Version-Bump und kein Commit/Push ohne Anweisung. Vor
jedem Commit `ruff check .` und `ruff format --check .`.

## Vor jeder Änderung
- **Alle Projekte binden djangoBase editierbar ein — jede Änderung wirkt sofort überall.** Die Rahmen-Templates
  (`base.html`, `base_app.html`, `_shell.html`, `_sidebar.html`, `_nav.html`, `sidebar.css`) nur ergänzend oder
  abschaltbar ändern; den assistant nie kaputt machen.
- **In gemeinsamen Templates nie `{% load %}` einer neuen Tag-Bibliothek und nie `{% url %}` auf eine neue Adresse ohne
  `as`** — laufende Server kennen beides erst nach dem Neustart (04.11.2026: Fehler auf jeder shortlongx-Seite). Neues
  über den Kontextprozessor (fehlt → leer) und `{% url … as x %}{% if x %}`.
- Tests im Wirt `A:\tmp_dbhost` (`venv310`, `DJANGO_SETTINGS_MODULE=settings python -m django test djangobase`, ~90 s,
  nur auf Ansage). Ordner `djangobase/tests/{unit,component,integration,konform}`, Basis `BasisTest` +
  `StoreIsolationMixin`. Prüfungen dürfen nichts vom Wirt erwarten.
- Schneller Check bei einem Nutzer: `cd A:\assistant && pythonVENV\Scripts\python.exe manage.py check`. Nach einem
  Update ggf. `pip install -e A:/shared/djangoBase --no-deps`.

## Statik und Cache
- Verbindlich ist `djangobase/cachekonzept.py` (Hilfe → Cache, Prüfung `tests/konform/test_cachekonzept.py`): HTML
  `no-store`; Statik mit Fassung im Pfad; ES-Module über `{% fassungspfad %}`, nie `{% static %}?t=`; keine Kennung in
  Importadressen. Unter `daphne` wirkt `StatikKopfzeilen` nur mit `runserver --nostatic`.
- Der Autoreloader beobachtet nur `.py`; geänderte Statik braucht beim Nutzer einen Neustart.
- `markActive` der Sidebar vergleicht nur den Pfad — Einträge, die sich nur in `?query` oder `#fragment` unterscheiden,
  kollidieren.

## Einbinden
1. `pip install -e A:\shared\djangoBase`; `INSTALLED_APPS += ['djangobase']`; Kontextprozessor
   `djangobase.context_processors.djangobase`; `path('hilfe/', include('djangobase.urls'))`.
2. `LOGGING = dblog.config(BASE_DIR/'logs')`; `DJANGOBASE = {...}`; `manage.py migrate djangobase`.
3. `TEST_RUNNER = "djangobase.testlaeufer.Testlaeufer"` (sperrt im Testlauf Netz und echte Ablagen).

Eigene Sidebar: `DJANGOBASE['sidebar_template']` mit `{% include "djangobase/_nav.html" %}`. `menu_provider` ist eine
Funktion `f(menue, request) -> Liste`, läuft auf jeder Seite (nur leichte Quellen; wirft sie, bleibt das feste Menü).
Weitere Schlüssel in der Vollfassung.

## Tabellen
Einstellungen → Tabellen: „Spalten verschieben“ (Vorgabe aus), „Spalten anpassen“ (an). `tabellen_speicher.js` ist der
eine Speicher (localStorage, mit `tabellen_je_benutzer` in der DB). `data-spalten-gemeinsam="<name>"` lässt Tabellen
die Spaltenbreiten teilen.

## Nutzer (alle editierbar eingebunden)
assistant (:8001), WalkHop, NoiseSpy (Server per Dateikopie), HumanBodyWeb (:8081), shortlongx (:5020), CamTrack,
SchweizerMakler (:8092), StayNestor (:8095, live als Dateikopie unter `/srv/shared/djangoBase`). Für vollständige Suchen
`rg --no-ignore` oder `grep -r` — ripgrep übersieht Projekte hinter `.gitignore`.

Weitere Doku in `doku/`: `werkzeugkaesten.md`, `hilfe_tests.md`, `frontend_bausteine.md`, `hilfe_jobs.md`,
`theme_seite.md`, `HOWTO_INTEGRATION_THEMING.md`.
