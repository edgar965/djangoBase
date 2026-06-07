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
    # ----- Layout-Erweiterungen (von Apps konsumiert) ----------------------
    # Pfade fuer {% static %}. Werden NACH djangoBase-CSS geladen
    # (Cascade-Override moeglich).
    "extra_css": [],            # ["mail/css/mail.css", ...]
    # Frueh-im-Head-Scripts (htmx, importmap-Snippet etc.). Roh-Strings
    # oder Static-Pfade: {"static": "search/js/htmx.min.js"} bzw.
    # {"raw": "<script>...</script>"}.
    "extra_js_head": [],
    # Sidebar-Override: wenn gesetzt, wird statt djangobase/_sidebar.html
    # dieses Template per {% include %} eingehaengt — Projekte koennen
    # ihre eigene Live-Sidebar weiterverwenden.
    "sidebar_template": None,   # z.B. "search/_sidebar.html"
    # Theme-Switcher im Topbar von base_app.html. Liste von
    # (slug, label, indicator_hex). Bei [] kein Switcher.
    "theme_modes": [],          # [("dark", "Dark", "#4ea8f6"), ...]
    # Default-Theme (body data-theme="..."). Fallback: erstes Element
    # aus theme_modes, sonst "".
    "theme_default": "",
    # Toast-Stack fuer Django-Messages. False = kein Stack rendern.
    "toast_stack": True,
    # ----- Verschiebbarer Splitter (Sidebar-Breite ziehbar) ----------------
    # Default aus, damit Projekte mit eigenem Resizer (z. B. Assistant)
    # unberuehrt bleiben. Breite wird clientseitig in localStorage gemerkt.
    "resizable_sidebar": False,
    "sidebar_default": 250,
    "sidebar_min": 140,
    "sidebar_max": 600,
    # Pfad der JSON-Datei mit Laufzeit-Overrides (Einstellungen-Seite).
    # None -> BASE_DIR/.djangobase.json
    "settings_speicher": None,
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
    if not c.get("theme_default") and c.get("theme_modes"):
        first = c["theme_modes"][0]
        c["theme_default"] = first[0] if isinstance(first, (list, tuple)) else str(first)
    _overrides_anwenden(c)
    return c


def _overrides_anwenden(c):
    """Wendet gespeicherte Laufzeit-Overrides (Einstellungen-Seite) an.
    Importiert store lokal, um Import-Zyklen zu vermeiden."""
    from .store import FARB_KEYS, laden
    for key, wert in laden().items():
        if key in FARB_KEYS:
            c["farben"][key] = wert
        else:
            c[key] = wert
