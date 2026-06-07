"""Persistente Laufzeit-Overrides fuer einen Teil der DJANGOBASE-Optionen.

Gespeichert als JSON-Datei (keine DB / keine Migration), damit das Paket in
beliebigen Projekten ohne Schema-Aenderung funktioniert. Nur die Keys aus
EINSTELLBAR koennen ueber die Einstellungen-Seite veraendert werden; alles
andere bleibt in settings.DJANGOBASE.

Existiert keine JSON-Datei, verhaelt sich conf() exakt wie zuvor — bestehende
Projekte (z. B. der Assistant) bleiben damit unveraendert.
"""
import json
from pathlib import Path

from django.conf import settings

# (key, typ, label) — typ steuert Eingabefeld + Konvertierung.
#   "text"  -> Textfeld          "bool"  -> Checkbox
#   "int"   -> Zahlfeld          "color" -> Farbwaehler (-> farben.<key>)
#   "theme" -> Auswahl aus theme_modes (Fallback: Textfeld)
EINSTELLBAR = [
    ("titel", "text", "App-Name (Sidebar-Titel)"),
    ("untertitel", "text", "Untertitel"),
    ("logo_icon", "text", "Logo-Icon (Bootstrap-Icon-Klasse)"),
    ("sidebar_bg", "color", "Sidebar-Hintergrund"),
    ("sidebar_light", "color", "Sidebar-Akzent (hell)"),
    ("sidebar_dark", "color", "Topbar / dunkel"),
    ("theme_default", "theme", "Standard-Theme"),
    ("resizable_sidebar", "bool", "Verschiebbarer Splitter (Sidebar-Breite ziehbar)"),
    ("sidebar_default", "int", "Sidebar-Standardbreite (px)"),
    ("sidebar_min", "int", "Sidebar-Mindestbreite (px)"),
    ("sidebar_max", "int", "Sidebar-Maximalbreite (px)"),
    ("toast_stack", "bool", "Toast-Meldungen anzeigen"),
]

FARB_KEYS = {"sidebar_bg", "sidebar_light", "sidebar_dark"}


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
    """Schreibt die Overrides (nur EINSTELLBAR-Keys) als JSON."""
    erlaubt = {k for k, _t, _l in EINSTELLBAR}
    sauber = {k: v for k, v in daten.items() if k in erlaubt}
    _pfad().write_text(json.dumps(sauber, ensure_ascii=False, indent=2),
                       encoding="utf-8")
