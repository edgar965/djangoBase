# djangoBase

## Wofür das gut ist

Eine Django-App, die jedem Projekt den immer gleichen Unterbau **fertig**
mitbringt, statt ihn sechsmal nachzubauen. Eingebunden wird sie als ganz normale
App; danach existieren die folgenden Seiten unter `/hilfe/`, ohne dass das
Projekt dafür eine Zeile Code schreibt:

| Seite | Was sie kann |
|---|---|
| `/hilfe/versionen` | Versions-Historie direkt aus `git` (Commits, Datum, Text) plus Umgebung und Paketstände |
| `/hilfe/logs` | Log-Betrachter mit Tabs je Quelle, getrennt nach „Exceptions" und „Allgemein" |
| `/hilfe/tests` | Test-Läufer: Testfälle nach Kategorie (unit/component/…) **und** Bereich, Laufzeit-Historie je Fall, Live-Fortschritt beim Lauf |
| `/hilfe/skills` | Werkzeugkasten: Prüfwerkzeuge, die den Code nach Befunden absuchen (tote Importe, Doppelcode, Namens-Dubletten …) |
| `/hilfe/jobs` | Zustand registrierter Hintergrund-Jobs, optional mit „Jetzt ausführen" |
| `/hilfe/einstellungen` | Branding, Farben, Layout, E-Mail und Benutzer zur Laufzeit — als benannte Profile, persistiert in JSON |
| `/hilfe/traffic`, `/hilfe/aktuell` | Zugriffs-Statistik und Live-Blick auf das laufende System |

Dazu kommt das **Sidebar-Layout** (Bootstrap 5 + Bootstrap Icons, dunkle
Sidebar `#003153`, optionaler verschiebbarer Splitter, bis zu drei Menü-Ebenen)
und ein **Logging-Helfer** für rotierende Logdateien.

## Voraussetzungen

| | Version | Anmerkung |
|---|---|---|
| Python | ≥ 3.10 | geprüft mit 3.14.2 |
| Django | ≥ 4.2 | geprüft mit 6.1 |
| Pillow | beliebig | **Pflicht** — `Provider.logo`/`Teilnehmer.avatar` sind `ImageField`; ohne Pillow bricht schon `manage.py check` ab |
| Datenbank | beliebig | SQLite genügt; djangoBase bringt eigene Migrationen mit |

Sonst nichts. Die folgenden Pakete sind **optional** — djangoBase importiert sie
erst im Bedarfsfall und läuft ohne sie vollständig, nur die genannte Funktion
fehlt dann:

| Paket | Schaltet frei |
|---|---|
| `psutil` | CPU-/RAM-/Netz-Werte auf `/hilfe/aktuell` (GPU zusätzlich über `nvidia-smi`) |
| `django-allauth` | Registrierung, Anmeldung, E-Mail-Bestätigung (`djangobase.allauth_config`) |
| `concurrent-log-handler` | prozesssicheres Log-Rotieren (mehrere Worker auf derselben Datei) |
| `deep-translator` | Übersetzungs-Seite unter `/hilfe/einstellungen/uebersetzung` |
| `maxminddb` | Herkunftsland in der Traffic-Auswertung |

Auf dem Rechner sollte `git` vorhanden sein — die Versionen-Seite ruft es auf.
Fehlt es, bleibt die Seite leer, alles andere läuft.

## Schnellstart

Nachvollzogen am 18.08.2026 in einem **leeren** venv, von Null bis zur laufenden
Seite. Wer diesen Abschnitt abarbeitet, hat djangoBase am Laufen.

```bash
python -m venv venv

# Django und Pillow kommen als Abhängigkeit mit - nicht extra installieren:
venv/Scripts/python -m pip install -e /pfad/zu/djangoBase
#   von GitHub statt lokal:  pip install git+https://github.com/edgar965/djangoBase

venv/Scripts/python -m django startproject probe .
```

**1. `settings.py` — den Context-Processor eintragen.** Das ist der Schritt, den
man übersieht, und er rächt sich mit einer Meldung, die ihn nicht erwähnt: Jede
djangoBase-Seite stirbt dann an `TemplateDoesNotExist: No template names
provided`, weil das Layout-Template über den Context kommt und ohne ihn leer
ist. In `TEMPLATES[0]["OPTIONS"]["context_processors"]`:

```python
"djangobase.context_processors.djangobase",
```

**2. `settings.py` — App und Konfiguration.** Ans Ende der Datei:

```python
INSTALLED_APPS += ["djangobase"]

import djangobase.logging as dblog
LOGGING = dblog.config(BASE_DIR / "logs")

DJANGOBASE = {
    "titel": "Meine Verwaltung",
    "version": "0.0.1",
    "log_verzeichnis": BASE_DIR / "logs",
    "log_sources": [("django", "Django", "django.log", None)],
    "menu": [{"label": "Start", "icon": "bi-house", "url": "/"}],
    "zugriff": "staff",          # "staff" | "login" | "none"
    "test_befehle": [
        {"slug": "alle", "name": "Alle Tests",
         "cmd": ["python", "manage.py", "test"]},
    ],
}
```

**3. `urls.py`:**

```python
from django.urls import include, path      # `include` ergänzen

urlpatterns = [
    path("hilfe/", include("djangobase.urls")),
    ...
]
```

**4. Datenbank anlegen und einen Zugang schaffen** — `zugriff: "staff"` heißt:
Ohne Staff-Flag zeigen die Hilfe-Seiten nichts.

```bash
venv/Scripts/python manage.py migrate
venv/Scripts/python manage.py createsuperuser
venv/Scripts/python manage.py runserver
```

**5. Prüfen:** `http://127.0.0.1:8000/hilfe/tests/` — Sidebar, Menü und
Testtabelle stehen. Alle Hilfe-Seiten antworten mit 200.

Eigene Seiten erben anschließend das Layout mit
`{% extends "djangobase/base.html" %}`.

### Die vollständige Konfiguration

Der Block oben ist das Minimum. Alles Weitere ist optional:

```python
DJANGOBASE = {
    ...
    "farben": {"sidebar_bg": "#003153", "sidebar_light": "#004a7c",
               "sidebar_dark": "#001f3f"},
    "favicon": "meineapp/favicon.svg",   # Pfad unterhalb von static/
    "version_pakete": ["django"],        # Paketstände auf der Versionen-Seite
    "repos": [("MeinRepo", "owner/repo", ".")],   # Quelle der Versions-Historie
    # Zweite Einteilung neben der Kategorie: Welcher Testfall gehoert zu
    # welchem Bereich, erkannt am Modulpraefix. Laengstes Praefix gewinnt.
    "test_bereiche": [
        {"slug": "mail", "name": "Mail", "praefixe": ["mail.tests"]},
        {"slug": "musik", "name": "Musik", "praefixe": ["search.tests.musik"]},
    ],
    "resizable_sidebar": True,           # verschiebbarer Splitter (Default False)
    # "sidebar_default": 250, "sidebar_min": 140, "sidebar_max": 600,
    "einstellungen_menu": True,          # Menügruppen ein-/ausblenden
    "hilfe_menu": True,
}
```

## Stolpersteine

- **`TemplateDoesNotExist: No template names provided` auf allen Hilfe-Seiten**
  heißt: Der Context-Processor fehlt (Schritt 1). Die Meldung nennt ihn nicht,
  weil das Layout-Template aus dem Context kommt und `{% extends %}` mit einem
  leeren Namen abbricht.
- **`400 Bad Request` auf allem** heißt `ALLOWED_HOSTS` — nicht djangoBase.
  Betrifft besonders eigene Prüfskripte mit `django.test.Client` außerhalb von
  `manage.py test`: Der Client meldet sich als Host `testserver`.
- **Editable Install wirkt sofort überall.** djangoBase steckt in rund sechs
  Projekten als `pip install -e`. Eine Änderung hier ist eine Änderung in allen
  — vor dem Anfassen `CLAUDE.md` lesen, dort stehen Konsumentenliste und
  Breaking-Checks.
- **Statische Dateien werden hart gecacht.** Nach einem Edit an JS/CSS greifen
  drei Ebenen: die `?v=`-Query im Template, die Importe der ES-Module und ein
  eventueller Service Worker im Projekt. Details im Abschnitt „Static-/Cache-
  Fallen" der `CLAUDE.md`.
- **Template-Änderungen brauchen einen Neustart**, sobald `DEBUG=False` den
  gecachten Loader benutzt — der Reload allein zeigt sie nicht.
- **`test_befehle` bestimmt, was die Tests-Seite anbietet.** Ohne Eintrag ist
  die Seite leer; das ist kein Fehler, sondern fehlende Konfiguration.

## Weiterführend

- `CLAUDE.md` — Arbeitsweise am Paket selbst: Konsumenten, Breaking-Checks,
  Werkzeugkästen, die Tests-Seite im Detail.
- `HOWTO_INTEGRATION_THEMING.md` — Themes, helle Layouts, Farbumstellung über
  alle Seiten, Checkliste für ein neues Consumer-Projekt.

## Profile + umschaltbares Layout-Template (`base_template`)

Die Einstellungen-Seite (`/hilfe/einstellungen`) ist seit 0.0.13 **eine Seite mit
Tabs** (Website / djangoBase / Konten-Freigabe / E-Mail) und oben einer
**Profil-Combobox**. Ein **Profil** ist ein vollständiger, benannter Satz von
Laufzeit-Einstellungen; genau eines ist aktiv und überschreibt `settings.DJANGOBASE`.
So lassen sich z. B. ein „djangoBase Standard"- und ein „CleanOrga"-Profil
nebeneinander pflegen und per Klick umschalten (Persistenz: JSON, keine DB).

Im Tab *djangoBase* gibt es das **Layout-Dropdown** (`base_template`): eine
Combobox, die ausschließlich die **in djangoBase mitgelieferten** Layout-Shells
listet. **Projekte können keine eigenen Templates einhängen** — neue Layouts
werden in djangoBase selbst angelegt. Aktuell mitgeliefert:

| Auswahl | Template | Look |
|---|---|---|
| djangoBase Standard (dunkel) | `djangobase/base.html` | dunkle Sidebar `#003153` |
| CleanOrga (hell) | `djangobase/base_cleanorga.html` | weiße Sidebar, Akzent `#2196F3`, BS5 + Font Awesome |

Die djangoBase-Seiten (Hilfe, Einstellungen) erweitern das gewählte Template per
`{% extends %}`. Per Code vorbelegbar:

```python
DJANGOBASE = { ..., "base_template": "djangobase/base_cleanorga.html" }
```

`base_cleanorga.html` erbt die djangoBase-Shell (Sidebar/Menü/Collapse/Toasts
bleiben funktionsfähig) und färbt nur per `cleanorga.css` auf den hellen Look um.
`base_template` ist – wie alle Felder – pro Profil getrennt, sodass die
Profil-Combobox zugleich den Look umschalten kann. Leerer/ungültiger Wert fällt
auf den djangoBase-Standard zurück.

**Neues Layout hinzufügen (in djangoBase):** ein Template unter
`djangobase/templates/djangobase/base_<name>.html` anlegen (analog
`base_cleanorga.html`, erbt `djangobase/base_app.html`), optional ein CSS unter
`static/djangobase/css/`, und das Paar in `store.LAYOUTS_BUILTIN` eintragen —
danach erscheint es automatisch im Dropdown.

Altes flaches JSON-Format (vor 0.0.13) wird beim ersten Lesen transparent in ein
Standard-Profil migriert – bestehende Projekte bleiben unverändert.

## Hilfe-/Einstellungen-Menü in ein Projekt mit eigener Sidebar einbinden

Projekte, die eine **eigene Sidebar** verwenden (`DJANGOBASE["sidebar_template"]`),
bekommen den djangoBase-Navigationsblock (Gruppen **Einstellungen** mit
*djangoBase*/*Website* und **Hilfe** mit *Versionen/Logs/Tests*) per einzeiligem
Include in ihr eigenes Sidebar-Template:

```django
<ul class="nav flex-column">
    ...   {# eigene Menüpunkte #}
    {% include "djangobase/_nav.html" %}
</ul>
```

Voraussetzungen: `path("hilfe/", include("djangobase.urls"))`, der Context-Processor
`djangobase.context_processors.djangobase` sowie Bootstrap (Collapse) + Bootstrap-Icons.
Sichtbarkeit pro Gruppe über Settings:

```python
DJANGOBASE = {
    ...
    "einstellungen_menu": True,   # Einstellungen-Gruppe zeigen (Default True)
    "hilfe_menu": True,           # Hilfe-Gruppe zeigen (Default True)
}
```

Die Einstellungen-Seiten selbst (`/hilfe/einstellungen`, `/hilfe/einstellungen/website`)
sind unabhängig von der Sidebar in jedem Projekt erreichbar, das `djangobase.urls`
einbindet.

## Menü mit bis zu 3 Ebenen

`DJANGOBASE["menu"]` rendert eine Top-Ebene aus Links bzw. aufklappbaren
Gruppen (`untermenu`). Seit 0.0.11 darf ein `untermenu`-Eintrag **selbst** ein
`untermenu` haben → dritte Ebene. Einträge ohne eigenes `untermenu` werden
unverändert als Link gerendert; 2-stufige Menüs bestehender Projekte bleiben
damit byte-identisch.

```python
DJANGOBASE["menu"] = [
    {"label": "Dashboard", "icon": "bi-grid", "url": "/"},
    {"label": "Handelssysteme", "icon": "bi-graph-up", "untermenu": [
        {"label": "Korrelationen", "icon": "bi-diagram-3", "untermenu": [   # 3. Ebene
            {"label": "Indikator", "icon": "bi-dot", "url": "/korr/"},
            {"label": "Hilfe",     "icon": "bi-dot", "url": "/korr/hilfe/"},
        ]},
        {"label": "Wochentage", "icon": "bi-calendar", "url": "/wochentage/"},
    ]},
]
```

Der Active-State (`sidebar.js`) markiert den zur URL passenden Link und klappt
die **komplette** Gruppen-Kette darüber auf — auch über drei Ebenen.

## Hintergrund-Jobs (`/hilfe/jobs`)

Projekte mit Daemon-Threads o. ä. registrieren ihre Jobs in der In-Memory-
Registry `djangobase.jobs` (keine DB/Migration). Die Jobs-Seite listet alle
registrierten Jobs, zeigt deren Zustand live (Auto-Refresh per JSON) und blendet
optional Buttons für „Jetzt ausführen" und Aktivieren/Deaktivieren ein.

```python
# AppConfig.ready():
from djangobase import jobs
from . import cron_runner
jobs.register(
    "intraday", "Intraday-Abruf",
    state=cron_runner.get_state,          # Callable -> dict (beliebige Keys)
    beschreibung="Holt 1-Minuten-Bars im konfigurierten Intervall.",
    trigger=cron_runner.trigger_now,      # optional: Button „Jetzt ausführen"
    set_enabled=cron_runner.set_enabled,  # optional: An/Aus-Buttons
)
```

Der Nav-Eintrag „Jobs" (Gruppe **Hilfe**) erscheint **nur**, wenn mindestens ein
Job registriert ist — Projekte ohne Jobs sind unverändert. Voraussetzung wie bei
den übrigen Hilfe-Seiten: `djangobase.urls` eingebunden + Context-Processor aktiv.
