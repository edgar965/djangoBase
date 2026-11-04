# CLAUDE.md — djangoBase

Wiederverwendbares Django-Infrastruktur-Paket (App `djangobase`, Settings-Key `DJANGOBASE`).
Liefert: Hilfe-Seiten (`/hilfe/versionen|logs|tests|jobs|einstellungen`), dunkles Sidebar-Layout (Bootstrap 5;
Multi-Base-Templates `_shell.html` → `base_app.html` → `base.html`), Theme-System (`body[data-theme]`, 7 Paletten inkl.
`weiss`/`blau`; alle Farben/Schriften der Seiten über `var(--dbt-…, #alt)`, siehe Kopf von `themes.css`),
Sidebar-Resizer, Toast-Stack, Logging-Helfer (`dblog.config`), LogClassifier, Einstellungen-Store (JSON in
`BASE_DIR/.djangobase.json`, keine DB), optional: Benutzer/allauth, Traffic-Statistik, Übersetzungsmodul
(deep_translator/Google; seit 31.10.2026 umschaltbar auf Azure Translator mit `DJANGOBASE["uebersetzung_anbieter"] =
"azure"` + `settings.AZURE_TRANSLATOR_KEY`/`_REGION`, `uebersetzer_azure.py`; Vorgabe bleibt Google, liefert Azure
nichts, übernimmt Google — erster Nutzer StayNestor), Jobs-Seite.

## Repo & Workflow
- GitHub `edgar965/djangoBase` (privat), EIN Branch `main` — keine Feature-Branches/PRs.
- Kein Version-Bump (`pyproject.toml`) und kein Commit/Push ohne ausdrückliche Anweisung.
- Theme-Integrations-Doku: `HOWTO_INTEGRATION_THEMING.md`; ausführliche Entwurfsdoku in `doku/` (unten).

## Vor Änderungen (Breaking-Check)
- Shell-Templates (`base.html`, `base_app.html`, `_shell.html`, `_sidebar.html`, `_nav.html`, `sidebar.css`) treffen
  ALLE Konsumenten — nur additiv/opt-in ändern. Am assistant nie etwas kaputt machen.
- Tests laufen im Host-Kontext (kein Standalone-Runner): Wegwerf-Host `A:\tmp_dbhost` (py3.10-venv `venv310`,
  `DJANGO_SETTINGS_MODULE=settings python -m django test djangobase`, ~90 s). Teststruktur
  `djangobase/tests/{unit,component,integration,konform}`, Basisklasse `BasisTest` (+ `StoreIsolationMixin` lenkt den
  Store auf eine Temp-Datei). Stand 18.09.2026: 1757 grün, 25 übersprungen (24 Konform-Klassen, weil der Wirt kein
  Konsument ist; `tomllib` auf 3.10). Der Wirt braucht die Extras `codequalitaet` (radon, pyflakes, pycodestyle,
  ruff), sonst werden deren Prüfungen übersprungen; seine `urls_host.py` hängt `djangobase.fassungsstatik` ein, sonst
  meldet `cachekonzept` den Wirt im Leeren. Prüfungen dürfen nichts vom Wirt erwarten (Dateien, LOGGING):
  `test_fassungsstatik` bringt seinen Statik-Baum selbst mit (`Wegwerfordner.neu` + `Fassungsstatik.vergessen()`),
  `test_protokoll_ergebnis` filtert die Einstellungs-Befunde über `Anlassfall.dateibezogen`.
- Schneller Konsumenten-Check: `cd A:\assistant && pythonVENV\Scripts\python.exe manage.py check`.
- Nach einem Update beim Konsumenten ggf. `pip install -e A:/shared/djangoBase --no-deps` (sonst bleibt die
  Metadaten-Version stale).
- Vor jedem Commit `ruff check .` und `ruff format --check .` (djangoBase ist seit 18.09.2026 ruff-sauber;
  `doku/werkzeugkaesten.md`).

## Static-/Cache-Fallen
- Static-Edits (z. B. `sidebar.js`) kommen beim Konsumenten erst nach (a) runserver-Neustart UND (b)
  Service-Worker-Refresh an (assistant cached `/static/` cache-first in `sw.js` → `CACHE_VERSION` bumpen).
  Ausgelieferte Datei mit `?cb=<timestamp>` prüfen. Der Autoreloader watcht nur `.py`.
- `markActive` der generischen Menü-Sidebar keyed auf **pathname** — Einträge, die sich nur per `?query`/`#fragment`
  unterscheiden, kollidieren (HumanBodyWeb `/humanbody/config/` vs. `#tab-creator`; spin1more `/ausfluege-karte/` vs.
  `?neu=1`).
- Verbindliches Cache-Konzept: `djangobase/cachekonzept.py` (06.09.2026) mit drei Verbrauchern — Seite Hilfe → Cache
  (`views/cacheseite.py`), Werkzeug `skills/cachekonzept.py`, Prüfung `tests/konform/test_cachekonzept.py`. Kern: HTML
  `no-store`; Statik mit Fassung; ES-Module über `{% fassungspfad %}` (Fassung im Pfad, Importe erben sie), nie
  `{% static %}?t=`; kein `?t={% now %}` an Statik; keine Kennung in Import-Adressen. `test_statik.py` zählt
  `{% fassungspfad %}` als versionierte Einbindung (3DTools: alle 46 Stellen umgestellt).

## Integrations-Rezept (Kurzform)
1. `pip install -e A:\shared\djangoBase`
2. `INSTALLED_APPS += ['djangobase']`; Context-Processor `djangobase.context_processors.djangobase`
3. `path('hilfe/', include('djangobase.urls'))`
4. `LOGGING = dblog.config(BASE_DIR/'logs')` (rotierende django.log/error.log)
5. `DJANGOBASE = {...}` (titel, farben, menu bzw. sidebar_template, log_sources, repos, test_befehle, zugriff,
   theme_modes, resizable_sidebar, …)
6. `manage.py migrate djangobase`
7. Prüflauf: `TEST_RUNNER = "djangobase.testlaeufer.Testlaeufer"` (Netzsperre + Ablageumleitung nur im Prüflauf;
   `doku/werkzeugkaesten.md`, Bauformen aus gunSlinger)

- Eigene Sidebar: `DJANGOBASE['sidebar_template']` + darin `{% include "djangobase/_nav.html" %}`.
- Repo-Slugs leer (`""`) lassen → aus dem lokalen git-`origin`; Geschwister-Repos mit absolutem Pfad.
- Pro-Mandant-/Station-Logs: `DJANGOBASE['log_source_provider']` = Callable → je Request `(verzeichnis, sources)`.

## Tabellen: Einstellungen, Spalten verschieben, Speicher je Benutzer (04.11.2026, aus StayNestor)
- **Einstellungen → Tabellen** (`/hilfe/einstellungen/tabellen/`, `views/tabellen_seite.py`, Store-Gruppe
  `tabellen`): Schalter „Spalten verschieben“ (`tabellen_spalten_verschieben`, Vorgabe aus) und „Spalten
  anpassen“ (`tabellen_spalten_anpassen`, Vorgabe an = Breiten ziehen wie bisher). Aus heißt: keine Griffe bzw.
  kein Umstellen.
- `{{ djangobase.tabellen_element }}` (`tabellen_element.py` über den Kontextprozessor, in `_shell.html`;
  `{% djb_tabellen %}` für eigene Vorlagen) schreibt `#djb-tabellen` mit den Schaltern — bei den Vorgaben
  NICHTS, andere Projekte bleiben gleich.
- **Gemeinsame Vorlagen (`_shell.html`, `_nav.html`) nie mit `{% load %}` einer NEUEN Tag-Bibliothek und nie mit
  `{% url %}` auf eine NEUE Adresse ohne `as`:** laufende Server kennen beides erst nach dem Neustart, Vorlagen
  lesen sie sofort — am 04.11.2026 warf so jede Seite in shortlongx (`/depot/ib/`) TemplateSyntaxError. Neues
  über den Kontextprozessor (fehlt → leer) und `{% url … as x %}{% if x %}`.
- `tabellen_speicher.js`: Breiten, Sortierung, Spaltenwahl, Reihenfolge über EINEN Speicher (localStorage wie
  bisher). Mit `DJANGOBASE["tabellen_je_benutzer"] = True` je Benutzer in `TabellenEinstellung`
  (`tabellen_einstellung.py`, Migration 0009 — Projekte brauchen `migrate djangobase`), POST
  `djangobase:tabellen_einstellung`; Browser-Werte werden beim ersten Lesen übernommen.
- `tabellen_reihenfolge.js`: Überschrift greifen und ziehen, Zellen werden im DOM umgehängt, nachgeladene Zeilen
  ordnet ein MutationObserver ein; `data-spalten-fest` nimmt eine Tabelle aus, mehrzeilige Köpfe/`colspan` bleiben
  fest. Auch je Tabelle einschaltbar mit `data-spalten-verschieben`.
- `tabellen_auto.js` importiert seine Nachbarn relativ und kommt über die Middleware mit Fassung im Pfad
  (`/statik/v-…/`, wo `fassungsstatik` eingehängt ist) — vorher blieben geänderte Nachbarmodule bis zu 7 Tage im
  Browser (nginx `expires 7d` auf `/static/`).

## DJANGOBASE-Schlüssel (neuere)
- `logo_bild` (29.10.2026, StayNestor): Static-Pfad eines Bildes (SVG/PNG) oben in der Seitenleiste statt
  `logo_icon`; 30×30 px, auch eingeklappt.
- Theme-Variablen (29.10.2026, StayNestor): 752 feste Farben in 33 Vorlagen/Stilblättern als `var(--dbt-<rolle>, #alt)`;
  Themes `weiss` (setzt alle Rollen) und `blau` (früheres `light`). Neue Seiten schreiben Farben gleich so;
  `tests/unit/test_theme_variablen.py` prüft, dass `weiss` jede benutzte Rolle setzt.
- **Einstellungen → Theme** (01.11.2026, StayNestor, `/hilfe/einstellungen/theme/`): Farben und Schriftrollen je Theme,
  Ablage im Store (`theme_anpassung`), Ausgabe `<style id="dbt-theme-anpassung">` nach `extra_css`; Schlüssel
  `theme_vorgaben` und `theme_vorschau`; Schriftrollen `--dbt-s-*` in keinem Theme gesetzt. Einzelheiten:
  `doku/theme_seite.md`.
- `menu_provider` (14.10.2026, HumanBodyWeb): **Modulfunktion** `f(menue, request) -> Liste` im Format von `menu`
  (`context_processors._menue`, wie `hilfe_extra`; ein Klassenaufruf geht nicht, `import_string` zerlegt am letzten
  Punkt). Bekommt die feste Liste und baut Kopien;
  wirft sie oder liefert keine Liste, bleibt das feste Menü und `djangobase.nav` loggt. Läuft bei JEDER Seite —
  leichte Quellen nehmen. Tests und `testdeckung` lesen nur den festen Teil.
- `skills2_register` (Vorgabe `["fn"]`), `skills2_abrufklassen` (`["Serverabruf"]`), `skills2_funktionsgrenze` (90),
  `skills2_ignorieren`, `jobs_ausschluss` (Befehle, die auf der Jobs-Seite nicht als Ablauf gelten), `struktur`
  (Grenzen, Schalter, Bestandslisten der Strukturtests), `test_bereiche`/`test_kategorien` (`doku/hilfe_tests.md`).
- **Settings-Konstanten** (nur Tests): `DJANGOBASE_KONFORM_AUS` (Datenordner, die keine Prüfung ansieht),
  `DJANGOBASE_KONFORM_TABELLEN_AUS` (Dateien bewusst ohne Tabellen-Raster), `DJANGOBASE_NETZ_ERLAUBT` (Rechner, die
  der Prüflauf anfahren darf), `DJANGOBASE_NETZSPERRE` (`False` = Sperre aus), `DJANGOBASE_KONFORM` (`False` = Wirt
  ist kein Konsument), `DJANGOBASE_JOBAUFZEICHNUNG` (`False` = Jobs nicht aufzeichnen).

## Konsumenten
Alle als **editable Install** — Änderungen hier wirken SOFORT in allen Projekten:

| Projekt | Pfad | Besonderheit |
|---|---|---|
| assistant | `A:\assistant` (:8001) | eigene Sidebar `search/_sidebar.html`; voll integriert (`/hilfe/`, `djangobase.jobs`, Resizer mit Server-Persistenz) |
| WalkHop (ex spin1more/kachel) | `A:\WalkHop\djangoCode` | Standard-Shell; Multi-Brand walkhop.com + spin1more.com; wrappt den Context-Processor je Marke |
| NoiseSpy | `A:\NoiseSpy\NoiseSpy` | eigene Sidebar `tracker/_sidebar.html`; Server bindet per `sys.path` ein (Private-Repo, kein `pip git+`; Dateikopie) |
| HumanBodyWeb | `A:\3DTools\HumanBodyWeb` (:8081; früher hier :4040) | Standard-Shell (`DJANGOBASE["menu"]`, `menu_provider`) |
| shortlongx | `A:\shortlongx\shortlongxWeb` (:5020) | Standard-Shell, 3-Ebenen-Menü, Jobs-Seite (cron_runner) |
| CamTrack | `A:\CamTrack\CamTrackDjango` | eigene Sidebar `app/_sidebar.html` |
| SchweizerMakler | `A:\SchweizerMakler\server` (:8092) | **4-Ebenen-Menü** (vierte Stufe in `_sidebar.html` seit 19.09.2026, additiv), Settings-Paket, `Testlaeufer`, Strukturtests |
| StayNestor | `A:\staynestor\server` (:8095) | Standard-Shell, `logo_bild`, Theme-Vorgaben „weiss“, Azure-Übersetzung; live auf staynestor.com mit Dateikopie unter `/srv/shared/djangoBase` |

Enumeration prüfen: ripgrep respektiert `.gitignore` und übersieht Projekte (bei shortlongx passiert) — für
vollständige Suchen `rg --no-ignore` oder `grep -r`.

## Weiterführende Doku (`doku/`, bei Arbeit am Thema lesen)
- `doku/werkzeugkaesten.md` — `skills/` (Endpunkt-Werkzeuge), `skills2/` (Python- + 7 Frontend-Prüfer: jssyntax,
  jswaisen, jsregistrierung, jsfaenger, jsfunktionen, jsbefunde, jsstumm), `umbau/` (Fixer wie `fix-ausnahme`, die
  Quelltext ändern); Review mit `ziel: "werkzeug"` (CodeRabbit); Bauformen aus gunSlinger (Strukturtests mit Ratsche,
  Netzsperre im Prüflauf, `Pause` statt `time.sleep`); ruff-Vorgabe `djangobase/ruff_vorgabe.toml` und ihre Fallen.
- `doku/hilfe_tests.md` — Laufzeiten/Historie, Kategorie (Ordner) vs. Bereich (`test_bereiche`), Live-Lauf mit drei
  Netzen gegen verwaiste Prozesse und `Laufsperre`, Spalte „Nr.“, `testhelfer.Webmodul`, Konformitätsprüfungen
  `djangobase.tests.konform`.
- `doku/frontend_bausteine.md` — `serverabruf.js`/`protokoll.js` als kanonische Fassung, Tabellen-Fallen.
- `doku/hilfe_jobs.md` — Ablauf-Übersicht (Joberkennung, Jobkatalog, Jobverlauf, Aufzeichnung um
  `BaseCommand.execute`; keine Migration).
- `doku/theme_seite.md` — Einstellungen → Theme im Einzelnen.
