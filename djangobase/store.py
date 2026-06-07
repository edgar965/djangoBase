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


def laden():
    """Gespeicherte Overrides als dict (leer, wenn keine/ungueltige Datei)."""
    try:
        daten = json.loads(_pfad().read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


def speichern(daten):
    """Schreibt die Overrides (nur EINSTELLBAR-Keys) als JSON — vollstaendig."""
    erlaubt = {k for k, _t, _l in EINSTELLBAR}
    sauber = {k: v for k, v in daten.items() if k in erlaubt}
    _pfad().write_text(json.dumps(sauber, ensure_ascii=False, indent=2),
                       encoding="utf-8")


def speichern_gruppe(slug, werte):
    """Aktualisiert nur die Felder der Gruppe `slug` und behaelt den Rest
    (Merge). Keys der Gruppe, die nicht in `werte` stehen, werden entfernt
    (-> Settings-Default greift wieder)."""
    keys = _gruppe_keys(slug)
    bestehend = {k: v for k, v in laden().items() if k not in keys}
    bestehend.update({k: v for k, v in werte.items() if k in keys})
    speichern(bestehend)


def leeren_gruppe(slug):
    """Entfernt nur die Overrides der Gruppe `slug`."""
    keys = _gruppe_keys(slug)
    speichern({k: v for k, v in laden().items() if k not in keys})
