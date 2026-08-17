"""Persistente Laufzeit-Overrides fuer einen Teil der DJANGOBASE-Optionen.

Gespeichert als JSON-Datei (keine DB / keine Migration), damit das Paket in
beliebigen Projekten ohne Schema-Aenderung funktioniert. Nur Keys aus
EINSTELLBAR koennen ueber die Einstellungen-Seiten veraendert werden; alles
andere bleibt in settings.DJANGOBASE.

Die einstellbaren Felder sind in GRUPPEN aufgeteilt — je Gruppe eine eigene
Seite (Website / djangoBase). Beim Speichern wird nur die jeweilige Gruppe
aktualisiert, die andere bleibt erhalten (Merge).

Existiert keine JSON-Datei, verhaelt sich conf() exakt wie zuvor — bestehende
Projekte (z. B. der Assistant) bleiben damit unveraendert.
"""
import json
from pathlib import Path

from django.conf import settings

# Feld-Definition: (key, typ, label) — typ steuert Eingabefeld + Konvertierung.
#   "text"  -> Textfeld          "bool"  -> Checkbox
#   "int"   -> Zahlfeld          "color" -> Farbwaehler (-> farben.<key>)
#   "theme" -> Auswahl aus theme_modes (Fallback: Textfeld)
#   "csv"   -> Textfeld, im JSON als Liste gespeichert (Komma-getrennt)
#   "zeilen"-> mehrzeiliges Feld, im JSON als Liste von Zeilen gespeichert
#   "password" -> Passwort-Eingabefeld (Wert wird als Text gespeichert)
#   "layout" -> Auswahl-Combobox der verfuegbaren Layout-Templates (base_template)

# Mitgelieferte Layout-Shells fuer das base_template-Dropdown. Projekte koennen
# weitere via settings.DJANGOBASE["layouts"] = [(template, label), ...] ergaenzen.
LAYOUTS_BUILTIN = [
    ("djangobase/base.html", "djangoBase Standard (dunkel)"),
    ("djangobase/base_cleanorga.html", "CleanOrga (hell)"),
]

GRUPPEN = {
    "website": {
        "label": "Website",
        "icon": "bi-globe",
        "titel": "Einstellungen · Website",
        "beschreibung": "Name, Logo und Untertitel der Anwendung.",
        "felder": [
            ("titel", "text", "App-Name (Sidebar-Titel)"),
            ("logo_icon", "text", "Logo-Icon (Bootstrap-Icon-Klasse, z. B. bi-grid-1x2-fill)"),
            ("untertitel", "text", "Untertitel"),
        ],
    },
    "djangobase": {
        "label": "djangoBase",
        "icon": "bi-gear",
        "titel": "Einstellungen · djangoBase",
        "beschreibung": "Alle Layout-, Hilfe- und Versionen-Optionen von djangoBase auf einen Blick.",
        "felder": [
            # --- Layout-Auswahl ---
            ("base_template", "layout",
             "Layout (Basis-Template) — Auswahl der in djangoBase mitgelieferten "
             "Layout-Shells (Optik der Seiten)."),
            # --- Layout / Optik ---
            ("sidebar_bg", "color", "Sidebar-Hintergrund"),
            ("sidebar_light", "color", "Sidebar-Akzent (hell)"),
            ("sidebar_dark", "color", "Topbar / dunkel"),
            ("theme_default", "theme", "Standard-Theme"),
            ("resizable_sidebar", "bool", "Verschiebbarer Splitter (Sidebar-Breite ziehbar)"),
            ("sidebar_default", "int", "Sidebar-Standardbreite (px)"),
            ("sidebar_min", "int", "Sidebar-Mindestbreite (px)"),
            ("sidebar_max", "int", "Sidebar-Maximalbreite (px)"),
            ("toast_stack", "bool", "Toast-Meldungen anzeigen"),
            ("test_bereiche", "zeilen",
             "Test-Bereiche (Hilfe → Tests, Spalte „Bereich“) — eine Zeile je "
             "Bereich: slug | Anzeigename | modulpraefix, modulpraefix. "
             "Leer = aus dem Ordner abgeleitet."),
            ("test_kategorien", "zeilen",
             "Test-Kategorien — Reihenfolge und Namen der Reiter, eine Zeile "
             "je Kategorie: slug | Anzeigename. Erlaubt sind nur die Ordner "
             "unit, component, ui, automated, performance, longrunner."),
            ("tests_djangobase_sichtbar", "bool",
             "djangoBase-Testcases sichtbar (Hilfe → Tests) — die Fälle, die "
             "djangoBase selbst mitbringt (Grundtests, Endpunktprobe). Aus: "
             "die Liste zeigt nur die Tests dieses Projekts."),
            # --- Navigation / Menue ---
            ("einstellungen_menu", "bool",
             "Menue-Gruppe 'Einstellungen' im djangoBase-Nav-Block einblenden"),
            ("hilfe_menu", "bool",
             "Menue-Gruppe 'Hilfe' im djangoBase-Nav-Block einblenden"),
            # --- Versionen-Seite ---
            ("version_commits_per_page", "int",
             "Versionen-Seite: Commits pro Repo aus GitHub holen"),
            ("commit_text_transform", "text",
             "Versionen-Seite: optionaler Body-Transform (dotted Path, z. B. "
             "search.utils.umlauts.restore_umlauts) — wird auf Commit-Subject/Body angewendet"),
            # --- Logs-Seite ---
            ("log_noisy_sources", "csv",
             "Logs-Seite: Quell-Keys, die in 'Alle Quellen' uebersprungen werden "
             "(Komma-getrennt, z. B. mail_import, pst_worker)"),
        ],
    },
    "freigabe": {
        "label": "Konten-Freigabe",
        "icon": "bi-person-check",
        "titel": "Konten-Freigabe",
        "beschreibung": "Müssen neue Konten erst vom Admin freigegeben werden, "
                        "bevor sie sich anmelden können? (Seite „Nutzer-Freigabe“.)",
        "felder": [
            ("freigabe_nutzer_noetig", "bool", "Nutzer erst freigeben"),
            ("freigabe_provider_noetig", "bool", "Provider erst freigeben"),
        ],
    },
    "uebersetzung": {
        "label": "Übersetzung",
        "icon": "bi-translate",
        "titel": "Einstellungen · Übersetzung",
        "beschreibung": "Zielsprachen der automatischen Übersetzung der User-Seite "
                        "(eigene Seite: views/uebersetzung.py, kein Generik-Formular).",
        "felder": [
            ("uebersetzung_sprachen", "csv", "Aktive Zielsprachen (Sprachcodes)"),
        ],
    },
    "email": {
        "label": "E-Mail",
        "icon": "bi-envelope",
        "titel": "Einstellungen · E-Mail",
        "beschreibung": "SMTP-Versand für Bestätigungs- und System-Mails. "
                        "Wird vom djangoBase-E-Mail-Backend zur Laufzeit verwendet.",
        "felder": [
            ("email_host", "text", "SMTP-Server (Host)"),
            ("email_port", "int", "Port (587 = STARTTLS, 465 = SSL)"),
            ("email_host_user", "text", "Benutzer"),
            ("email_host_password", "password", "Passwort"),
            ("email_use_tls", "bool", "STARTTLS verwenden (Port 587)"),
            ("email_use_ssl", "bool", "SSL verwenden (Port 465)"),
            ("email_from", "text", "Absender-Adresse (From)"),
        ],
    },
}

# Flache Whitelist aller einstellbaren Keys (von conf() + speichern genutzt).
EINSTELLBAR = [f for g in GRUPPEN.values() for f in g["felder"]]

FARB_KEYS = {"sidebar_bg", "sidebar_light", "sidebar_dark"}


def _gruppe_keys(slug):
    return {k for k, _t, _l in GRUPPEN[slug]["felder"]}


def _pfad():
    p = (getattr(settings, "DJANGOBASE", {}) or {}).get("settings_speicher")
    if p:
        return Path(str(p))
    return Path(str(settings.BASE_DIR)) / ".djangobase.json"


# ---------------------------------------------------------------------------
# Profile: mehrere benannte Einstellungs-Saetze (z. B. "djangoBase Standard"
# und "CleanOrga"), umschaltbar ueber die Einstellungen-Seite. Genau EIN
# Profil ist aktiv; dessen Werte werden von conf() angewendet.
#
# JSON-Format v2:
#   {"format": 2, "aktiv": "<slug>",
#    "profile": {"<slug>": {"label": "...", "werte": {<key>: <wert>}}}}
#
# Altes flaches Format ({<key>: <wert>}) wird beim Lesen transparent in ein
# Standard-Profil migriert -> bestehende Projekte bleiben unveraendert.
# ---------------------------------------------------------------------------
import logging
import os
import re
import tempfile
import time

logger = logging.getLogger(__name__)

STANDARD_SLUG = "standard"
STANDARD_LABEL = "djangoBase Standard"


def _leer_struktur():
    return {"format": 2, "aktiv": STANDARD_SLUG,
            "profile": {STANDARD_SLUG: {"label": STANDARD_LABEL, "werte": {}}}}


def _normalisieren(daten):
    """Beliebige geladene JSON-Daten -> gueltige v2-Struktur."""
    if not isinstance(daten, dict):
        return _leer_struktur()
    if isinstance(daten.get("profile"), dict):
        prof_out = {}
        for slug, prof in daten["profile"].items():
            if isinstance(prof, dict):
                werte = prof.get("werte")
                prof_out[slug] = {
                    "label": str(prof.get("label") or slug),
                    "werte": werte if isinstance(werte, dict) else {},
                }
        if not prof_out:
            return _leer_struktur()
        aktiv = daten.get("aktiv")
        if aktiv not in prof_out:
            aktiv = next(iter(prof_out))
        return {"format": 2, "aktiv": aktiv, "profile": prof_out}
    # Altes flaches Format -> in Standard-Profil migrieren.
    s = _leer_struktur()
    s["profile"][STANDARD_SLUG]["werte"] = dict(daten)
    return s


def _roh_laden():
    """Vollstaendige (normalisierte) Profil-Struktur."""
    try:
        daten = json.loads(_pfad().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _leer_struktur()
    return _normalisieren(daten)


#: Serialisiert Lesen-Aendern-Schreiben. Zwei Ebenen, weil zwei Faelle:
#:   * `threading.RLock` gegen zwei Anfragen im SELBEN Prozess (der Regelfall:
#:     zwei offene Einstellungs-Tabs). RLock, weil `speichern_gruppe` intern
#:     `laden()` und `speichern()` aufruft — eine einfache Lock waere ein
#:     Selbstblock.
#:   * eine Sperrdatei gegen zwei PROZESSE (Dev-Server + Verwaltungsbefehl,
#:     oder zwei Server auf derselben Datei).
_rlock = __import__("threading").RLock()
_tiefe = {"n": 0}


class _Sperre:
    """Kontextverwalter um jedes Lesen-Aendern-Schreiben.

    WARUM (Review 13.08.2026, mit Gegenprobe belegt): Das SCHREIBEN war schon
    unteilbar (Nebendatei + `os.replace`), das Lesen-Aendern-Schreiben nicht.
    `Docu/gegenprobe_store_wettrennen.py` im 3DTools-Projekt zeigt es:

        Ausgangsstand            {'titel': 'Anfangswert', 'sidebar_default': 250}
        nacheinander gespeichert {'titel': 'von A',       'sidebar_default': 999}
        verschraenkt gespeichert {'titel': 'Anfangswert', 'sidebar_default': 999}

    Zwei Vorgaenge, die VERSCHIEDENE Gruppen speichern, lesen denselben Stand;
    der zweite schreibt seine Gruppe plus die ALTEN Werte der ersten zurueck.
    Die Aenderung der ersten ist still verschwunden — kein Fehler, keine Meldung.
    Das betrifft alle Projekte, die djangoBase einbinden; zwei offene
    Einstellungs-Tabs genuegen.

    Bekommt die Sperrdatei nicht frei, wird nach kurzem Warten TROTZDEM
    gespeichert: Ein verlorenes Speichern ist schlimmer als ein
    unwahrscheinliches Wettrennen, und eine liegengebliebene Sperrdatei (Prozess
    abgestuerzt) darf die Einstellungen nicht auf Dauer blockieren."""

    VERSUCHE = 20
    PAUSE_S = 0.05

    def __enter__(self):
        _rlock.acquire()
        _tiefe["n"] += 1
        self._datei = None
        if _tiefe["n"] > 1:            # verschachtelter Aufruf: Datei haelt schon
            return self
        pfad = _pfad().with_suffix(_pfad().suffix + ".lock")
        for _ in range(self.VERSUCHE):
            try:
                fd = os.open(str(pfad), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self._datei = pfad
                return self
            except FileExistsError:
                time.sleep(self.PAUSE_S)
            except OSError:
                return self            # kein Sperrdatei-Ort -> ohne weitermachen
        logger.warning("djangobase.store: Sperrdatei %s blieb belegt — es wird "
                       "trotzdem gespeichert", pfad)
        return self

    def __exit__(self, *_):
        if self._datei is not None:
            try:
                self._datei.unlink()
            except OSError:
                logger.warning("djangobase.store: Sperrdatei nicht entfernbar: %s",
                               self._datei)
        _tiefe["n"] -= 1
        _rlock.release()
        return False


def _atomar_schreiben(obj):
    pfad = _pfad()
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(pfad.parent), prefix=".djangobase-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(pfad))   # atomarer Rename
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _roh_speichern(struktur):
    """Schreibt die Struktur — Werte je Profil auf EINSTELLBAR-Keys gefiltert."""
    erlaubt = {k for k, _t, _l in EINSTELLBAR}
    profile = {}
    for slug, prof in (struktur.get("profile") or {}).items():
        werte = prof.get("werte") or {}
        profile[slug] = {
            "label": str(prof.get("label") or slug),
            "werte": {k: v for k, v in werte.items() if k in erlaubt},
        }
    if not profile:
        return _atomar_schreiben(_leer_struktur())
    aktiv = struktur.get("aktiv")
    if aktiv not in profile:
        aktiv = next(iter(profile))
    _atomar_schreiben({"format": 2, "aktiv": aktiv, "profile": profile})


def laden():
    """Overrides des AKTIVEN Profils als dict (leer, wenn keine gesetzt sind).
    Signatur unveraendert -> conf() und bestehende Aufrufer bleiben gleich."""
    s = _roh_laden()
    return dict(s["profile"][s["aktiv"]]["werte"])


def speichern(daten):
    """Schreibt die Overrides (nur EINSTELLBAR-Keys) ins AKTIVE Profil."""
    with _Sperre():
        s = _roh_laden()
        erlaubt = {k for k, _t, _l in EINSTELLBAR}
        s["profile"][s["aktiv"]]["werte"] = {k: v for k, v in daten.items() if k in erlaubt}
        _roh_speichern(s)


# ----- Profil-Verwaltung (Einstellungen-Seite) -----------------------------

def profile_liste():
    """[(slug, label, ist_aktiv), ...] in Einfuege-Reihenfolge."""
    s = _roh_laden()
    return [(slug, prof["label"], slug == s["aktiv"])
            for slug, prof in s["profile"].items()]


def aktiv_slug():
    return _roh_laden()["aktiv"]


def aktiv_setzen(slug):
    """Aktiviert ein vorhandenes Profil. True bei Erfolg."""
    with _Sperre():
        s = _roh_laden()
        if slug in s["profile"]:
            s["aktiv"] = slug
            _roh_speichern(s)
            return True
        return False


def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return s or "profil"


def profil_anlegen(label, kopie_von=None):
    """Legt ein neues Profil an (eindeutiger Slug aus Label) und gibt den Slug
    zurueck. Optional die Werte von `kopie_von` uebernehmen."""
    with _Sperre():
        s = _roh_laden()
        basis = _slugify(label)
        slug, i = basis, 2
        while slug in s["profile"]:
            slug = f"{basis}-{i}"
            i += 1
        werte = {}
        if kopie_von and kopie_von in s["profile"]:
            werte = dict(s["profile"][kopie_von]["werte"])
        s["profile"][slug] = {"label": str(label) or slug, "werte": werte}
        _roh_speichern(s)
        return slug


def profil_loeschen(slug):
    """Loescht ein Profil. Das letzte verbleibende kann nicht geloescht werden;
    war das geloeschte aktiv, wird das erste verbleibende aktiv. True bei Erfolg."""
    with _Sperre():
        s = _roh_laden()
        if slug not in s["profile"] or len(s["profile"]) <= 1:
            return False
        del s["profile"][slug]
        if s["aktiv"] == slug:
            s["aktiv"] = next(iter(s["profile"]))
        _roh_speichern(s)
        return True


def speichern_gruppe(slug, werte):
    """Aktualisiert nur die Felder der Gruppe `slug` und behaelt den Rest
    (Merge). Keys der Gruppe, die nicht in `werte` stehen, werden entfernt
    (-> Settings-Default greift wieder)."""
    with _Sperre():        # Lesen UND Schreiben unter derselben Sperre
        keys = _gruppe_keys(slug)
        bestehend = {k: v for k, v in laden().items() if k not in keys}
        bestehend.update({k: v for k, v in werte.items() if k in keys})
        speichern(bestehend)


def leeren_gruppe(slug):
    """Entfernt nur die Overrides der Gruppe `slug`."""
    with _Sperre():
        keys = _gruppe_keys(slug)
        speichern({k: v for k, v in laden().items() if k not in keys})
