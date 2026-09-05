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
    # MEHRERE Zeichen, mit Cache-Kennung (26.08.2026, aus CamTrack).
    # `favicon` nimmt genau eines und haengt keine Kennung an; CamTrack
    # braucht zwei — eine SVG, die scharf skaliert, und eine .ico als
    # Rueckfall — und die Kennung, weil ein zwischengespeichertes Zeichen
    # genau so hartnaeckig ist wie ein altes Stilblatt.
    #
    # Eintrag = Static-Pfad-String, oder Dict {static: "...", typ: "..."},
    # oder Dict {roh: "/favicon.ico", typ: "..."} fuer Adressen, die nicht
    # ueber die Statik laufen. Gesetzt gewinnt es gegen `favicon`.
    "favicons": (),
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
    "test_befehle": [],   # {"slug","name","cmd": [..]}  – ganze Suiten (Batch), Tab „Suiten"
    # Einzeltest-Discovery pro Typ → Tabs mit Run-Button je Test. Optional/opt-in:
    #   [{"typ": "Unit", "labels": ["tests.unit", "djangobase.tests.unit"]}, ...]
    # Jeder gefundene Test (z. B. tests.unit.test_geo.GeoTest.test_x) ist einzeln
    # ausführbar (manage.py test <id>).
    "test_discover": [],
    # Die BEREICHE (Spalte „Bereich" in jeder Testcase-Tabelle) — die zweite
    # Einteilung neben der Kategorie: Kategorie = WIE getestet wird (unit,
    # component, …), Bereich = WAS getestet wird (Chat, Mail, Musik, …).
    # Gibt das PROJEKT an (Ansage 17.08.2026), hier oder ueber Einstellungen →
    # djangoBase; leer = aus dem Ordner abgeleitet.
    #   [{"slug": "musik", "name": "Musik", "praefixe": ["search.tests.musik"]}]
    # Auch erlaubt: Zeilen „musik | Musik | search.tests.musik" (Oberflaeche)
    # oder die Kurzform {"schedule": "Kalender"} (nur Umbenennung).
    "test_bereiche": [],
    # Reihenfolge und Anzeigenamen der KATEGORIEN (unit, component, …). Eine
    # Zeile je Kategorie: „unit | Unit". Leer = eingebaute Reihenfolge.
    "test_kategorien": [],
    # Browser-/UI-Tests (laufen client-seitig im Iframe). Optional:
    #   {"runner": "/static/tests/runner.js", "cases": "/static/tests/testcases.js",
    #    "seiten": {"navi": "/navi/ziel/?…&demo=1", "osm": "/ausfluege/", ...}}
    "test_ui": None,
    # Klassen, die in DIESEM Projekt eine Testbasis sind, ohne von
    # `TestCase` zu erben — weil ein Adapter sie in Tests verwandelt.
    #
    # WARUM ES DEN SCHALTER GIBT (27.08.2026, 3DTools)
    # ===============================================
    # `test_pruefcode` meldete dort 16 Klassen als „verwaist: unittest fuehrt
    # sie NIE aus". Sie erben von `TestCategory` (Projektbasis ohne
    # Vorfahren) — und `core/tests/ui/test_oberflaeche.py` macht aus jeder
    # eine `django.test.TestCase`-Klasse. Sie laufen also sehr wohl, nur
    # sieht man es der Klasse nicht an.
    #
    # Beispiel: DJANGOBASE["test_basen"] = ["TestCategory"]
    "test_basen": [],
    # ----- Hilfe -> Aktuell (rollierendes Fenster, Claude-CLI) --------------
    # Die Seite erscheint in JEDEM Projekt. Geschrieben wird ueber
    # `manage.py aktuell` (kein HTTP-Schreibweg). None -> <log_verzeichnis>/aktuell.jsonl
    "aktuell_datei": None,
    # ----- Hilfe -> Review (Code-Review im Gespraech mit einem Modell) -----
    # Die Seite erscheint in JEDEM Projekt (Vorgabe 13.08.2026). Ohne Partner
    # zeigt sie die Anleitung, was hier einzutragen ist.
    #   [{"slug": "nemotron", "name": "Nemotron 550B", "ziel": "online",
    #     "modell": "nvidia/nemotron-3-ultra-550b-a55b"},
    #    {"slug": "gemma", "name": "Gemma 4 26B (lokal)", "ziel": "lokal",
    #     "modell": "gemma4:26b-a4b-it-qat", "num_ctx": 32768}]
    # `ziel`: "lokal" = Ollama auf diesem Rechner, "online" = OpenAI-kompatibler
    # Endpunkt. Bei "online" verlaesst der gesendete Quelltext den Rechner.
    #
    # DRITTE SORTE: ein PRUEFWERKZEUG statt eines Modells (31.08.2026). Es
    # fuehrt kein Gespraech, sondern liest den Git-Stand seines Verzeichnisses
    # und meldet Befunde. Der Befehl steht NUR hier - aus dem Browser kommt
    # allein der Schluessel einer der `auswahlen`:
    #   {"slug": "coderabbit", "name": "CodeRabbit", "ziel": "werkzeug",
    #    "modell": "CodeRabbit CLI",
    #    "befehl": ["cr", "review"],
    #    "wurzel": "A:\\meinprojekt",          # das Git-Repository
    #    "timeout": 900,
    #    "auswahlen": [
    #        {"wert": "uncommitted", "name": "Noch nicht committet",
    #         "argumente": ["--uncommitted"]},
    #        {"wert": "committed", "name": "Committet, noch nicht gepusht",
    #         "argumente": ["--committed"]},
    #    ]}
    "review_partner": [],
    # Die Codebereiche, ueber die gesprochen werden kann. Dateien relativ zu
    # `review_wurzel`. Nur DIESE Dateien werden gesendet — die Seite nimmt keine
    # Pfade aus dem Browser entgegen.
    #   [{"slug": "retarget", "name": "Retarget-Mathematik",
    #     "dateien": ["humanbody_core/skeleton/retarget.py"],
    #     "hinweis": "Was der Bereich tut, was das Modell wissen muss.",
    #     "fragen": ["Wo kippt die Quaternionen-Kette?", ...]}]
    # Ein Bereich darf zusaetzlich "wurzel" setzen und damit eine eigene Basis
    # mitbringen — fuer geteilten Code, der ausserhalb des Projekts liegt (z.B.
    # djangoBase selbst). Die Pruefung bleibt scharf: Jede Datei muss unter DER
    # Wurzel liegen, die ihr Bereich nennt.
    "review_bereiche": [],
    # Basisverzeichnis der Bereichs-Dateien. None -> BASE_DIR. Fuer Projekte,
    # deren Kern-Bibliothek neben dem Django-Teil liegt, auf den gemeinsamen
    # Ordner darueber setzen.
    "review_wurzel": None,
    # Wohin die Mitschriften geschrieben werden. None -> <log_verzeichnis>/review.
    "review_ablage": None,
    # Rolle des Gegenuebers. None -> djangobase.review.ROLLE (auf Widerspruch
    # getrimmt). Projekte mit eigenem Schwerpunkt (Finanzen, Medizin) setzen hier
    # ihre eigene.
    "review_rolle": None,
    # Datei mit dem API-Schluessel fuer "online" — EINE Zeile, ausserhalb des
    # Projekts. None -> ~/.sparring_key
    "review_schluessel_datei": None,
    "review_ollama_url": None,   # None -> http://127.0.0.1:11434/api/chat
    "review_online_url": None,   # None -> https://openrouter.ai/api/v1/chat/completions
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
    # Dasselbe fuer die HILFE-Gruppe (24.08.2026, auf Ansage: „camtrack soll
    # NICHT seine eigene Hilfe Seitenleiste nutzen, sondern die von
    # djangoBase"). Ohne dieses Gegenstueck musste ein Projekt mit eigenen
    # Hilfeseiten die ganze Gruppe selbst nachbauen — und dann fehlten
    # regelmaessig die djangoBase-Seiten. Genau das hat CamTrack getan, und
    # djangoBases eigene Pruefung `test_menue_zeigt_aktuell_und_review_ohne_
    # konfiguration` war dort dauerhaft rot.
    #
    # Format wie oben, zusaetzlich optional ein Untermenue:
    #   {"label": "Tests", "icon": "bi-list-check", "untermenu": [
    #       {"label": "Alle", "url": "/test/", "aktiv": "test_alle"}]}
    "hilfe_extra": [],
    # Optionaler Projekt-Provider für Zusatz-Details im Benutzer-Verlauf-Popup
    # (Benutzerliste). Dotted path oder Callable f(user_ids) -> {user_id:
    #   [{"titel": str, "zeilen": [(label, wert), ...]}, ...]}. Wird gebündelt für
    # alle gelisteten Nutzer aufgerufen; fehlt er / wirft er, bleibt das Popup gleich.
    "benutzer_details_provider": None,
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
    # Basis-Template (Layout-Shell), das die djangoBase-Seiten (Hilfe,
    # Einstellungen) per {% extends %} erweitern. Default = djangoBase-
    # Standard-Look. Projekte koennen ein eigenes Base-Template angeben
    # (z. B. "cleanorga/base.html"), damit die djangoBase-Seiten im
    # Projekt-Look erscheinen. Das Template MUSS die Blocks bereitstellen,
    # die die Seiten fuellen (mind. `content`, `topbar_title`, `title_extra`).
    # Per Einstellungen-Seite / Profil zur Laufzeit umschaltbar; ein leerer
    # Wert faellt auf den djangoBase-Standard zurueck.
    "base_template": "djangobase/base.html",
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
    # Profil-Umschalter (Combobox + Anlegen/Loeschen) auf der Einstellungsseite.
    # False = ausblenden (fuer Projekte mit nur EINEM Profil). Das Profil-System
    # bleibt intern bestehen; nur die UI verschwindet.
    "profile_switcher": True,
    # ----- Hilfe -> Tests: die Testfaelle von djangoBase SELBST --------------
    # djangoBase bringt eigene Faelle mit (Grundtests, Endpunktprobe). Sie
    # laufen im Wirt-Projekt mit, gehoeren aber nicht zu SEINEM Code: Sie liegen
    # in `A:\shared\djangoBase`, sind nicht verschiebbar, und in der Liste des
    # Projekts stehen sie im Weg (Ansage 17.08.2026, deshalb Default AUS).
    # True = sie erscheinen mit der Kategorie „DjangoBase".
    "tests_djangobase_sichtbar": False,
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
    # Zusaetzliche CSS-Klasse am Ziehgriff, fuer Projekte die ihn ueber
    # einen eigenen Selektor stylen (CamTrack: ct-sidebar-resizer).
    # 26.08.2026 — ohne das musste CamTrack den ganzen Griff samt seiner
    # neun Datenattribute von Hand im eigenen Grundgeruest nachbauen.
    "sidebar_extra_class": "",
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
    # ----- Language Server: zusaetzliche Import-Wurzeln --------------------
    # Ordner AUSSERHALB der Projektwurzel, aus denen das Projekt importiert.
    # Wer eine Bibliothek per `sys.path.insert` in `settings.py` einhaengt,
    # statt sie zu installieren, bekommt sonst je Import eine rote Zeile:
    # HumanBodyWeb laedt `humanbody_core` aus `A:\3DTools\HumanBody` und
    # hatte deshalb **151 `reportMissingImports`** (gemessen 05.09.2026, 12 %
    # aller Befunde) — kein einziger davon ein Fehler im Projekt.
    #
    # Es ist DIESELBE Fehlerklasse, gegen die `views.languageserver.extra_pfade`
    # den djangobase-Pfad nachtraegt; nur laesst sie sich hier nicht erraten,
    # weil der Ordner projekteigen ist. Absolute Pfade oder `Path`-Objekte.
    "ls_extra_pfade": [],           # [HUMANBODY_ROOT]
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
    # Bekannte Scanner-/Angriffspfade (Substring, case-insensitiv). Aufrufe
    # darauf gelten als Bot — auch mit gefälschtem Browser-UA. Diese Pfade
    # liefern meist 404 (werden dann gar nicht erfasst); die Markierung greift
    # bei Catch-all-Routen / vorhandenen Pfaden. Projekte können ergänzen.
    "traffic_bot_pfade": [
        "/wp-login", "/wp-admin", "/wp-content", "/wp-includes",
        "/xmlrpc.php", "/.env", "/.git", "/.aws", "/.ssh", "/.vscode",
        "/phpmyadmin", "/phpunit", "/vendor/", "/cgi-bin/", "/shell",
        "/administrator/", "/solr/", "/actuator", "/manager/html",
        "/owa/", "/autodiscover", "/boaform/", "/hudson",
    ],
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
    # Leerer base_template (z. B. Profil "Standard" mit leerem Feld) ->
    # djangoBase-Standard-Layout.
    if not c.get("base_template"):
        c["base_template"] = DEFAULTS["base_template"]
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
