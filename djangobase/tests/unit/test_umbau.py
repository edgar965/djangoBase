# -*- coding: utf-8 -*-
u"""Tests des Werkzeugkastens ``djangobase.umbau``.

WARUM UEBERHAUPT TESTS FUER WERKZEUGE, DIE NUR AUF DER KOMMANDOZEILE LAUFEN:
Sie schreiben Quelltext. Ein Werkzeug, das beim Import scheitert, faellt beim
naechsten Umbau auf — ein Werkzeug, das falsch BERICHTET, faellt nie auf. Beim
ersten Kommandozeilenlauf des `modulschneider` (17.08.2026) stand
``OFFEN: p, pfad, x`` im Bericht: Parameter und lokale Namen. Die OFFEN-Liste ist
die wichtigste Ausgabe des Werkzeugs — sie nennt die Namen, die im neuen Modul
zur Laufzeit fehlen. Fehlalarme darin verdecken den einen echten Fall.

Dazu zwei Struktur-Pruefungen, die verhindern, dass der Kasten still zerfaellt:
jede Klasse in ``KLASSEN`` muss erreichbar sein, und der verzoegerte Import darf
kein Modul beim Paketimport mitladen (sonst laeuft
``python -m djangobase.umbau.<modul>`` zweimal).
"""
import shutil
import sys
import tempfile
from pathlib import Path

from djangobase import umbau

from ..base import BasisTest


#: Eine Datei mit genau einem echten offenen Namen — alles andere ist
#: Parameter, lokale Variable, Ausnahmename, Konstante, Import oder Builtin.
QUELLE = '''# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path

GRENZE = 42


def klein(x):
    return x * 2


def gross(pfad):
    p = Path(pfad)
    zahl = len(p.name)
    for teil in p.parts:
        zahl += len(teil)
    try:
        return re.sub(r"a", "b", p.name), zahl, GRENZE
    except ValueError as fehler:
        return str(fehler), os.sep, FEHLT_WIRKLICH


def bleibt():
    return GRENZE
'''


class UmbauPaketTest(BasisTest):

    def test_jede_klasse_ist_erreichbar(self):
        for name in umbau.KLASSEN:
            self.assertTrue(hasattr(umbau, name),
                            "%s fehlt im Modul %s" % (name, umbau.KLASSEN[name]))

    def test_all_und_klassen_stimmen_ueberein(self):
        self.assertEqual(sorted(umbau.__all__), sorted(umbau.KLASSEN))

    def test_unbekannter_name_wirft(self):
        u"""Ein Tippfehler muss auffallen, nicht None liefern."""
        with self.assertRaises(AttributeError):
            umbau.GibtEsNicht

    def test_paketimport_laedt_keine_module(self):
        u"""Sonst laeuft `python -m djangobase.umbau.<modul>` zweimal.

        Python warnt dann mit „found in sys.modules after import of package",
        und die Warnung stand vor der Ausgabe des Werkzeugs. Bei Werkzeugen, die
        Dateien schreiben, ist doppelt ausgefuehrter Modulcode kein
        Schoenheitsfehler.
        """
        for modul in set(umbau.KLASSEN.values()):
            sys.modules.pop("djangobase.umbau." + modul, None)
        import importlib
        importlib.reload(umbau)
        geladen = [m for m in set(umbau.KLASSEN.values())
                   if "djangobase.umbau." + m in sys.modules]
        self.assertEqual(geladen, [], "beim Paketimport mitgeladen: %s" % geladen)


class ModulSchneiderTest(BasisTest):

    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="umbau_schnitt_"))
        self.addCleanup(shutil.rmtree, self.ordner, True)
        self.quelle = self.ordner / "gross.py"
        self.quelle.write_text(QUELLE, encoding="utf-8")

    def bericht(self):
        schneider = umbau.ModulSchneider(self.quelle)
        return schneider.schreiben(["gross", "klein"],
                                   self.ordner / "neu.py",
                                   "# -*- coding: utf-8 -*-", trocken=True)

    def test_offen_nennt_nur_den_echten_fall(self):
        self.assertEqual(self.bericht()["offen"], ["FEHLT_WIRKLICH"])

    def test_parameter_und_lokale_sind_nicht_offen(self):
        offen = self.bericht()["offen"]
        for name in ("x", "pfad", "p", "zahl", "teil", "fehler"):
            self.assertNotIn(name, offen)

    def test_builtins_sind_nicht_offen(self):
        u"""`dir(__builtins__)` griff nur im direkt gestarteten Skript.

        In einem importierten Modul ist `__builtins__` ein dict — `dir()` liefert
        dann `keys`/`items`/… statt `len`/`str`/`range`.
        """
        offen = self.bericht()["offen"]
        for name in ("len", "str", "ValueError"):
            self.assertNotIn(name, offen)

    def test_importe_und_konstanten_werden_erkannt(self):
        bericht = self.bericht()
        self.assertEqual(bericht["importe"], ["Path", "os", "re"])
        self.assertEqual(bericht["konstanten"], ["GRENZE"])

    def test_probelauf_schreibt_nichts(self):
        self.bericht()
        self.assertFalse((self.ordner / "neu.py").exists())
        self.assertEqual(self.quelle.read_text(encoding="utf-8"), QUELLE)

    def test_schreiben_teilt_und_beides_parst(self):
        import ast
        umbau.ModulSchneider(self.quelle).schreiben(
            ["gross", "klein"], self.ordner / "neu.py",
            "# -*- coding: utf-8 -*-")
        neu = (self.ordner / "neu.py").read_text(encoding="utf-8")
        rest = self.quelle.read_text(encoding="utf-8")
        ast.parse(neu)
        ast.parse(rest)
        self.assertIn("def gross(", neu)
        self.assertNotIn("def gross(", rest)
        self.assertIn("def bleibt(", rest)


class UnbekannteNamenTest(BasisTest):

    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="umbau_namen_"))
        self.addCleanup(shutil.rmtree, self.ordner, True)

    def datei(self, name, inhalt):
        pfad = self.ordner / name
        pfad.write_text(inhalt, encoding="utf-8")
        return pfad

    def test_findet_undeklarierten_namen(self):
        pfad = self.datei("modul.js",
                          "export function x() { return ss.wert; }\n")
        self.assertIn("ss", umbau.Modulnamen(pfad).unbekannt())

    def test_browser_globale_sind_kein_befund(self):
        u"""`getComputedStyle`, `PerformanceObserver` und `Option` wurden
        gemeldet — drei Fehlalarme in drei Dateien."""
        pfad = self.datei("global.js",
                          "export function x() {\n"
                          "    new PerformanceObserver(() => {});\n"
                          "    const o = new Option('a', 'b');\n"
                          "    return getComputedStyle(document.body).color + o;\n"
                          "}\n")
        self.assertEqual(umbau.Modulnamen(pfad).unbekannt(), [])
