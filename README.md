# djangoBase

Wiederverwendbare Django-Infrastruktur für mehrere Projekte:

- **Hilfe-Seiten** `/hilfe/versionen`, `/hilfe/logs`, `/hilfe/tests`,
  `/hilfe/jobs`, `/hilfe/einstellungen` (Versionen via `gh`/`git` +
  Umgebung/Pakete, Log-Viewer mit Tabs, Test-Runner, **Jobs-Übersicht**,
  Einstellungen-Formular) — exakt im Stil des „Assistant"-Projekts.
- **Dunkles Sidebar-Layout** (Bootstrap 5 + Bootstrap Icons, Sidebar `#003153`)
  mit optionalem **verschiebbarem Splitter** (`resizable_sidebar`, Breite in
  `localStorage`) und **bis zu 3 Menü-Ebenen** (verschachteltes `untermenu`).
- **Einstellungen-Seite**: Branding, Farben, Theme und Splitter zur Laufzeit
  konfigurierbar; Persistenz als JSON-Datei (keine DB/Migration). Überschreibt
  `settings.DJANGOBASE`.
- **Logging-Helfer** für rotierende Logdateien.

## Installation

```bash
pip install -e A:\shared\djangoBase
# oder Pfad in settings.py: sys.path.insert(0, r"A:\shared\djangoBase")
```

## Einbinden (settings.py)

```python
INSTALLED_APPS += ["djangobase"]

# Context-Processor in TEMPLATES["OPTIONS"]["context_processors"]:
#   "djangobase.context_processors.djangobase"

import djangobase.logging as dblog
LOGGING = dblog.config(BASE_DIR / "logs")

DJANGOBASE = {
    "titel": "Meine Verwaltung",
    "farben": {"sidebar_bg": "#003153", "sidebar_light": "#004a7c", "sidebar_dark": "#001f3f"},
    "log_verzeichnis": BASE_DIR / "logs",
    "log_sources": [("all", "Alle Quellen", None, None), ("django", "Django", "django.log", None)],
    "version": "0.0.1",
    "version_pakete": ["django"],
    "repos": [("MeinRepo", "owner/repo", ".")],
    "test_befehle": [{"slug": "alle", "name": "Alle Tests", "cmd": ["python", "manage.py", "test"]}],
    "menu": [{"label": "Start", "icon": "bi-house", "url": "/"}],
    "zugriff": "staff",   # "staff" | "login" | "none"
    "resizable_sidebar": True,   # verschiebbarer Splitter (Default False)
    # "sidebar_default": 250, "sidebar_min": 140, "sidebar_max": 600,
}
```

```python
# urls.py
path("hilfe/", include("djangobase.urls")),
```

Eigene Seiten: `{% extends "djangobase/base.html" %}`.

## Profile + umschaltbares Layout-Template (`base_template`)

Die Einstellungen-Seite (`/hilfe/einstellungen`) ist seit 0.0.13 **eine Seite mit
Tabs** (Website / djangoBase / Konten-Freigabe / E-Mail) und oben einer
**Profil-Combobox**. Ein **Profil** ist ein vollständiger, benannter Satz von
Laufzeit-Einstellungen; genau eines ist aktiv und überschreibt `settings.DJANGOBASE`.
So lassen sich z. B. ein „djangoBase Standard"- und ein „CleanOrga"-Profil
nebeneinander pflegen und per Klick umschalten (Persistenz: JSON, keine DB).

Neuer Schlüssel **`base_template`** (Feld im Tab *djangoBase*): legt fest, welches
Layout-Template die djangoBase-Seiten (Hilfe, Einstellungen) per `{% extends %}`
erweitern. Default ist `djangobase/base.html` (der djangoBase-Look); ein Projekt
kann sein eigenes Base-Template angeben, damit die djangoBase-Seiten im
Projekt-Look erscheinen:

```python
DJANGOBASE = {
    ...
    "base_template": "cleanorga/base.html",   # leer / weglassen = djangoBase-Standard
}
```

Das Projekt-Base-Template muss die von den Seiten gefüllten Blocks bereitstellen
(mindestens `content`, `topbar_title`, `title_extra`). Ein ungültiger Wert wird
beim Speichern abgelehnt (kein Aussperren); ein leerer Wert fällt auf den
djangoBase-Standard zurück. `base_template` ist – wie alle Felder – pro Profil
getrennt, sodass die Combobox zugleich den Look umschaltet.

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
