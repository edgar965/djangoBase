# djangoBase

Wiederverwendbare Django-Infrastruktur für mehrere Projekte:

- **Hilfe-Seiten** `/hilfe/versionen`, `/hilfe/logs`, `/hilfe/tests`
  (Versionen via `gh`/`git` + Umgebung/Pakete, Log-Viewer mit Tabs,
  Test-Runner) — exakt im Stil des „Assistant"-Projekts.
- **Dunkles Sidebar-Layout** (Bootstrap 5 + Bootstrap Icons, Sidebar `#003153`).
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
}
```

```python
# urls.py
path("hilfe/", include("djangobase.urls")),
```

Eigene Seiten: `{% extends "djangobase/base.html" %}`.
