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
    "menu": [],           # [{label, icon, url} | {label, icon, untermenu:[{label, icon, url}]}]
                          #  (Untermenü-Key heißt "untermenu", NICHT "items" -> dict.items-Kollision!)
    # djangoBase-eigene Menue-Gruppen im Nav-Block (djangobase/_nav.html):
    # Einstellungen (Website/djangoBase) + Hilfe. Projekte mit eigener Sidebar
    # koennen den Block per {% include "djangobase/_nav.html" %} einhaengen und
    # hierueber pro Gruppe ein-/ausblenden.
    "einstellungen_menu": True,
    "hilfe_menu": True,
    # Eingebaute Benutzer-Verwaltung (Teilnehmer/Provider) als Unterpunkt der
    # Einstellungen-Gruppe. Erscheint in jedem Projekt; benötigt einmalig
    # `migrate djangobase`.
    "benutzer_verwaltung": True,
    # Zusätzliche, projektspezifische Unterpunkte in der Einstellungen-Gruppe
    # (z. B. eine Benutzer-Verwaltung des Projekts). Liste von Dicts:
    #   {"label": "Benutzer", "url": "/benutzer/", "icon": "bi-people",
    #    "aktiv": "einstellungen_benutzer"}
    # 'aktiv' (optional) wird mit der Template-Variable `aktiv` verglichen.
    "einstellungen_extra": [],
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
    # Body-Ende-Scripts (nach Bootstrap + sidebar.js, vor Page-Scripts).
    # Gleiches Format wie extra_js_head: String / {static} / {raw}.
    # Fuer Projekte die ihre eigenen module-imports / Event-Wirings am
    # Body-Ende brauchen (z.B. CamTrack sidebar_nav.js, topbar_health.js).
    "extra_body_js": [],
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
    # ----- Versionen-Seite (erweitert) ------------------------------------
    # Optionaler Body-Transform fuer Commit-Subjects/Bodies. Dotted Path
    # zu einer Callable str -> str. Wird auf subject + title + body
    # angewendet — z.B. Umlaut-Restore fuer alte Commits ohne Umlaute.
    "commit_text_transform": None,  # "search.utils.umlauts.restore_umlauts"
    # Wie viele Commits pro Repo aus GitHub holen.
    "version_commits_per_page": 100,
    # Manuelle Versions-Eintraege — werden zusaetzlich zu den GitHub-Commits
    # gerendert (oben, vor den Repos). Fuer Projekte die einen handgepflegten
    # Changelog haben den sie nicht in Git-Commit-Bodies zwaengen wollen.
    # Liste von Dicts:
    #   {"version": "v0.83", "date": "2026-06-08", "title": "Synology-Pattern",
    #    "body_html": "<ul><li>...</li></ul>",  # ODER:
    #    "body_md": "- Punkt 1\n- Punkt 2"}     # wird wie Commit-Body gerendert
    "manual_versions": [],
    # ----- Logs-Seite (erweitert) -----------------------------------------
    # Source-Keys die in "all"-Mode komplett uebersprungen werden — fuer
    # spammige Quellen, deren _PROGRESS_RE-Filter nicht reicht (z.B.
    # PST-Import-Worker, der auch ohne Progress-Bar Zigtausend Zeilen
    # pro Minute schreiben kann).
    "log_noisy_sources": [],        # ["mail_import", ...]
    # ----- E-Mail (SMTP) – vom StoreSMTPBackend gelesen --------------------
    "email_host": "",
    "email_port": 587,
    "email_host_user": "",
    "email_host_password": "",
    "email_use_tls": True,
    "email_use_ssl": False,
    "email_from": "",
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
