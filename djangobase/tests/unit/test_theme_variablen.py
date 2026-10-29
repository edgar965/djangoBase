"""Theme-Variablen --dbt-*: Jede Rolle, die eine Vorlage oder ein Stilblatt benutzt, setzt das
Theme „weiss“ (themes.css). Sonst bliebe genau dort die alte dunkle Farbe stehen — ohne Fehler,
nur als dunkler Fleck auf weißer Seite.

Eingeführt am 29.10.2026 mit der Umstellung von 696 festen Farben auf ``var(--dbt-…, #alt)``.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

PAKET = Path(__file__).resolve().parents[2]
THEMES = PAKET / "static" / "djangobase" / "css" / "themes.css"
BENUTZT = re.compile(r"var\(\s*(--dbt-[a-z0-9-]+)")
GESETZT = re.compile(r"(--dbt-[a-z0-9-]+)\s*:")
OHNE_RUECKFALL = re.compile(r"var\(\s*--dbt-[a-z0-9-]+\s*\)")


def _weiss_block(text):
    anfang = text.index('body[data-theme="weiss"] {')
    return text[anfang : text.index("}", anfang)]


def _dateien(*muster):
    return [p for m in muster for p in PAKET.rglob(m) if "tests" not in p.parts]


def _lesen(pfad):
    return pfad.read_text(encoding="utf-8", errors="replace")


class ThemeVariablenGedeckt(SimpleTestCase):
    databases = []

    def test_weiss_setzt_jede_benutzte_rolle(self):
        gesetzt = set(GESETZT.findall(_weiss_block(_lesen(THEMES))))
        fehlend = {}
        for pfad in _dateien("*.html", "*.css", "*.js"):
            for name in set(BENUTZT.findall(_lesen(pfad))) - gesetzt:
                fehlend.setdefault(name, []).append(pfad.name)
        self.assertEqual(fehlend, {}, "Rollen ohne Wert im Theme weiss")

    def test_gegenprobe_findet_eine_fehlende_rolle(self):
        gesetzt = set(GESETZT.findall('body[data-theme="weiss"] { --dbt-text: #111; }'))
        css = ".x { color: var(--dbt-text, #fff); background: var(--dbt-neu, #000); }"
        self.assertEqual(set(BENUTZT.findall(css)) - gesetzt, {"--dbt-neu"})

    def test_rueckfallwert_steht_ueberall_dabei(self):
        """Ohne Rückfallwert sähe jedes andere Theme die Stelle farblos."""
        ohne = [
            f"{pfad.name}: {m.group(0)}"
            for pfad in _dateien("*.html", "*.css")
            if pfad != THEMES
            for m in OHNE_RUECKFALL.finditer(_lesen(pfad))
        ]
        self.assertEqual(ohne, [])
