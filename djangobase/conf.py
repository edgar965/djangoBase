"""Zentraler Zugriff auf die Projekt-Konfiguration `settings.DJANGOBASE`
mit sinnvollen Defaults (Assistant-Look als Standard)."""
from pathlib import Path

from django.conf import settings

DEFAULTS = {
    "titel": "Verwaltung",
    "untertitel": "",
    "logo_icon": "bi-grid-1x2-fill",
    "farben": {
        "sidebar_bg": "#003153",
        "sidebar_light": "#004a7c",
        "sidebar_dark": "#001f3f",
    },
    # Logs
    "log_verzeichnis": None,  # None -> settings.BASE_DIR
    "log_sources": [
        ("all", "Alle Quellen — chronologisch gemischt", None, None),
        ("django", "Django-Server", "django.log", None),
        ("server", "Server-Start", "server.log", None),
    ],
    # Versionen
    "version": "",
    "version_pakete": ["django"],
    "repos": [],          # (Anzeige, "owner/repo", lokaler_unterordner)
    # Tests
    "test_befehle": [],   # {"slug","name","cmd": [..]}
    # Navigation
    "menu": [],           # [{label, icon, url} | {label, icon, items:[{label, icon, url}]}]
    # Zugriff: "staff" | "login" | "none"
    "zugriff": "staff",
}


def conf():
    c = dict(DEFAULTS)
    c.update(getattr(settings, "DJANGOBASE", {}) or {})
    c["log_verzeichnis"] = Path(str(c["log_verzeichnis"] or settings.BASE_DIR))
    farben = dict(DEFAULTS["farben"])
    farben.update(c.get("farben") or {})
    c["farben"] = farben
    if not c.get("version"):
        c["version"] = getattr(settings, "VERSION", "")
    return c
