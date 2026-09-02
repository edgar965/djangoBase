# -*- coding: utf-8 -*-
u"""Rahmenmodule: was ein Laufzeit-``__all__`` ist — und was der Filter NICHT anfasst."""
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.ls_befunde import LsBefunde
from djangobase.umbau.ls_konfig import LsKonfig
from djangobase.umbau.rahmenmodule import Rahmenmodule

RAHMEN = u"""
from pathlib import Path
def helfer():
    return 1
__all__ = [_n for _n in list(globals()) if not _n.startswith("__")]
"""

STATISCH = u"""
def helfer():
    return 1
__all__ = ["helfer"]
"""

KONSUMENT = u"""
from .rahmen import *
def seite():
    return helfer()
"""


def _befund(datei, regel, stufe="error"):
    return {"datei": datei, "zeile": 1, "spalte": 1, "stufe": stufe,
            "regel": regel, "text": u"egal"}


class RahmenmoduleTest(unittest.TestCase):

    def _projekt(self, dateien):
        u"""Ein Wegwerf-Projekt; liefert (Ordner, Rahmenmodule)."""
        ordner = tempfile.mkdtemp()
        for name, inhalt in dateien.items():
            ziel = Path(ordner) / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        return ordner, Rahmenmodule(ordner)

    # ── Erkennung ────────────────────────────────────────────────────────
    def test_all_aus_globals_ist_ein_rahmen_eine_literalliste_nicht(self):
        ordner, rm = self._projekt({"rahmen.py": RAHMEN, "sauber.py": STATISCH})
        rm.einlesen({"rahmen.py", "sauber.py"})
        self.assertEqual(rm.rahmen(), {"rahmen.py"})

    def test_wer_per_stern_aus_einem_rahmen_holt_ist_konsument(self):
        ordner, rm = self._projekt({"app/rahmen.py": RAHMEN,
                                    "app/seite.py": KONSUMENT})
        rm.einlesen({"app/seite.py"})
        self.assertEqual(rm.konsumenten(), {"app/seite.py"})
        self.assertIn("app/rahmen.py", rm.rahmen(),
                      u"das Ziel wird mitgelesen, auch ohne eigenen Befund")

    def test_stern_import_aus_einem_STATISCHEN_modul_zaehlt_nicht(self):
        u"""Steht ``__all__`` als Liste da, kann der Typprüfer es auflösen —
        dann ist eine Meldung über einen unbekannten Namen echt."""
        ordner, rm = self._projekt({"app/rahmen.py": STATISCH,
                                    "app/seite.py": KONSUMENT})
        rm.einlesen({"app/seite.py"})
        self.assertEqual(rm.konsumenten(), set())

    def test_unaufloesbares_ziel_schaltet_nichts_stumm(self):
        ordner, rm = self._projekt({"app/seite.py": u"from .fehlt import *\nx = y\n"})
        rm.einlesen({"app/seite.py"})
        self.assertEqual(rm.konsumenten(), set())

    def test_kaputte_datei_wirft_nicht(self):
        ordner, rm = self._projekt({"app/seite.py": u"def (:::\n"})
        rm.einlesen({"app/seite.py"})
        self.assertEqual(rm.rahmen(), set())

    # ── Filterentscheidung ───────────────────────────────────────────────
    def test_nur_die_drei_regeln_fallen_und_nur_am_richtigen_ort(self):
        ordner, rm = self._projekt({"app/rahmen.py": RAHMEN,
                                    "app/seite.py": KONSUMENT})
        rm.einlesen({"app/rahmen.py", "app/seite.py"})
        stumm = [
            _befund("app/rahmen.py", "reportUnsupportedDunderAll"),
            _befund("app/rahmen.py", "reportUnusedImport"),
            _befund("app/seite.py", "reportUndefinedVariable"),
        ]
        laut = [
            # dieselben Regeln, aber am jeweils anderen Ort
            _befund("app/seite.py", "reportUnusedImport"),
            _befund("app/rahmen.py", "reportUndefinedVariable"),
            # und alles andere bleibt ueberall sichtbar
            _befund("app/seite.py", "reportCallIssue"),
            _befund("app/rahmen.py", "reportArgumentType"),
        ]
        self.assertTrue(all(rm.stumm(b) for b in stumm))
        self.assertFalse(any(rm.stumm(b) for b in laut))

    # ── Zusammenspiel mit LsBefunde ──────────────────────────────────────
    def test_haken_aus_zeigt_alles_haken_an_zaehlt_es_in_der_kennzahl(self):
        ordner, rm = self._projekt({"app/rahmen.py": RAHMEN,
                                    "app/seite.py": KONSUMENT})
        befunde = [_befund("app/seite.py", "reportUndefinedVariable"),
                   _befund("app/seite.py", "reportCallIssue")]

        class Ergebnis:
            pass
        erg = Ergebnis()
        erg.befunde, erg.dateien, erg.dauer_s = befunde, 2, 1.0

        aus = LsBefunde(erg, LsKonfig({"rahmen_stumm": False, "js_stumm": []}),
                        Rahmenmodule(ordner))
        self.assertEqual(len(aus.roh()), 2)
        self.assertEqual(aus.kennzahlen()["stumm_rahmen"], 0)

        an = LsBefunde(erg, LsKonfig({"rahmen_stumm": True, "js_stumm": []}),
                       Rahmenmodule(ordner))
        self.assertEqual(len(an.roh()), 1)
        k = an.kennzahlen()
        self.assertEqual(k["stumm_rahmen"], 1)
        self.assertEqual(k["konsumenten"], 1)

    def test_ohne_rahmenobjekt_bleibt_alles_wie_bisher(self):
        u"""Andere Aufrufer von ``LsBefunde`` dürfen nichts merken."""
        class Ergebnis:
            pass
        erg = Ergebnis()
        erg.befunde = [_befund("a.py", "reportUndefinedVariable")]
        erg.dateien, erg.dauer_s = 1, 1.0
        b = LsBefunde(erg, LsKonfig({"rahmen_stumm": True, "js_stumm": []}))
        self.assertEqual(len(b.roh()), 1)
        self.assertEqual(b.kennzahlen()["stumm_rahmen"], 0)

    # ── Konfiguration ────────────────────────────────────────────────────
    def test_filter_steht_nicht_im_abdruck_kostet_also_keinen_neuen_lauf(self):
        an = LsKonfig({"rahmen_stumm": True})
        aus = LsKonfig({"rahmen_stumm": False})
        self.assertEqual(an.abdruck(), aus.abdruck())
        self.assertNotIn("rahmen_stumm", LsKonfig.LAUFFELDER)
        self.assertIn("rahmen_stumm", LsKonfig.FELDER)

    def test_vorgabe_ist_an_und_ueberlebt_die_rundreise(self):
        self.assertTrue(LsKonfig().rahmen_stumm)
        k = LsKonfig({"rahmen_stumm": False})
        self.assertFalse(LsKonfig(k.alle_werte()).rahmen_stumm)


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
