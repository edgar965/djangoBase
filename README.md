# djangoBase

Wiederverwendbare Django-Infrastruktur für mehrere Projekte:

- **Hilfe-Seiten** `/hilfe/versionen`, `/hilfe/logs`, `/hilfe/tests`,
  `/hilfe/einstellungen` (Versionen via `gh`/`git` + Umgebung/Pakete,
  Log-Viewer mit Tabs, Test-Runner, Einstellungen-Formular) — exakt im Stil
  des „Assistant"-Projekts.
- **Dunkles Sidebar-Layout** (Bootstrap 5 + Bootstrap Icons, Sidebar `#003153`)
  mit optionalem **verschiebbarem Splitter** (`resizable_sidebar`, Breite in
  `localStorage`).
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
