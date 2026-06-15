"""Zentraler Zugriff auf die Projekt-Konfiguration `settings.DJANGOBASE`
mit sinnvollen Defaults (Assistant-Look als Standard)."""
from pathlib import Path

from django.conf import settings

DEFAULTS = {
    "titel": "Verwaltung",
    "untertitel": "",
    "logo_icon": "bi-grid-1x2-fill",
    # Optionales Favicon (Static-Pfad, z. B. "img/favicon.svg").
    # Leer = kein <link rel="icon"> (Default, bestehende Projekte unberuehrt).
    "favicon": "",
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
    # (Anzeige, "owner/repo", lokaler_unterordner). Ist "owner/repo" leer (""),
    # wird der GitHub-Slug zur Laufzeit aus dem origin-Remote des lokalen Repos
    # abgeleitet -> kein Projekt muss seinen Slug hardcoden, z.B.:
    #   ("HumanBodyWeb", "", "HumanBodyWeb")
    "repos": [],
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
    # localStorage-Key fuer die persistierte Sidebar-Breite. Default ist
    # djangobase-spezifisch, Projekte mit eigener Convention koennen z.B.
    # "ctSidebarWidth" setzen um zu bestehenden Cookie-Welten kompatibel
    # zu sein.
    "sidebar_storage_key": "",
    # Zusaetzliche CSS-Variablen die parallel zu --sidebar-width gesetzt
    # werden, fuer Projekte deren CSS auf eigene Variablen-Namen schaut
    # (z.B. CamTrack: --ct-sidebar-width). Komma-separiert.
    "sidebar_extra_css_vars": "",
    # Optional: Server-Persistenz der Sidebar-Breite. Wenn `sidebar_save_url`
    # gesetzt ist, POSTet der Resizer nach jeder Aenderung an diesen
    # Endpoint — zusaetzlich zum localStorage-Cache. Damit ist die Breite
    # pro-User statt pro-Browser persistiert (cross-device).
    # Body-Format:
    #   - mit `sidebar_save_field`: {"<field>": {"<key>": width}}
    #     z. B. {"pane_widths": {"sidebar": 280}} fuer pane-widths-JSON.
    #   - ohne `sidebar_save_field`: {"<key>": width}
    #     z. B. {"sidebar": 280} fuer simple Settings-API.
    # Initial-Breite vom Server: Projekt-Context-Processor setzt eine
    # Template-Variable namens `sidebar_initial_width` (px-Integer). Wenn
    # vorhanden, ueberschreibt sie localStorage beim Page-Load (kein
    # Flackern, kein Server-Roundtrip per JS noetig).
    "sidebar_save_url": None,
    "sidebar_save_field": None,
    "sidebar_save_key": "sidebar",
    "sidebar_save_debounce_ms": 350,
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
    # Optionaler Hook fuer projektspezifische Log-Quellen (dotted path oder
    # Callable). Wird pro Request mit `request` aufgerufen und darf die
    # Quellen dynamisch bestimmen — z.B. pro Mandant/Station, oder mit
    # datums-suffigierten Dateinamen (alerts_2026-06-15.log). Rueckgabe:
    #   - eine Liste sources [(key,label,out_name,err_name), ...], ODER
    #   - ein Tupel (verzeichnis, sources).
    # Dateinamen in sources duerfen ABSOLUT sein (dann gewinnt der absolute
    # Pfad gegenueber dem Basis-Verzeichnis). None -> statische log_sources.
    "log_source_provider": None,    # "tracker.logs.log_sources"
    # ----- Konten-Freigabe (Gating neuer Registrierungen) ------------------
    # Wenn True, wird ein neues Konto der jeweiligen Rolle bei der Registrierung
    # auf is_active=False gesetzt und kann sich erst nach Admin-Freigabe
    # anmelden. Über die Seite „Nutzer-Freigabe" umschaltbar (Store-Gruppe
    # „freigabe"). Default False → bestehende Projekte unverändert.
    "freigabe_nutzer_noetig": False,
    "freigabe_provider_noetig": False,
    # ----- Übersetzung der User-Seite (djangobase.uebersetzung) ------------
    # Aktive Zielsprachen (Codes aus uebersetzung.SPRACHEN); wird über die
    # Seite Einstellungen → Übersetzung gepflegt (Store-Gruppe "uebersetzung").
    "uebersetzung_sprachen": [],
    # ----- Traffic-Statistik (djangobase.traffic + views/traffic.py) -------
    # Erfassung ist opt-in: TrafficMiddleware in MIDDLEWARE eintragen.
    # mmdb-Datei für den offline-Länder-Lookup (DB-IP Country Lite, CC BY 4.0).
    # None -> BASE_DIR/daten/dbip-country-lite.mmdb
    "traffic_geo_db": None,
    # Pfad-Präfixe, die nicht erfasst werden (Verwaltung zählt nicht als
    # Besuch). Projekte ergänzen eigene Verwaltungspfade in den Settings.
    "traffic_ignorierte_pfade": ["/static/", "/media/", "/favicon",
                                 "/admin/", "/hilfe/"],
    # Eigene Domains, die nie als Referrer-Quelle zählen (zusätzlich zum
    # jeweiligen request.get_host()).
    "traffic_eigene_domains": [],
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
