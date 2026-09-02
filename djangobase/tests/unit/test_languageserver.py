# -*- coding: utf-8 -*-
u"""LanguageServer: Parser, fehlendes Programm, Konfigurationsdatei — ohne
einen echten Server zu starten. Der echte Lauf ist eine Gegenprobe auf der
Seite, kein Unit-Test."""
import json
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.languageserver import LanguageServer, LsErgebnis
from djangobase.umbau.ls_befunde import LsBefunde
from djangobase.umbau.ls_konfig import LsKonfig

AUSGABE = {
    "version": "1.19.0",
    "generalDiagnostics": [
        {"file": r"C:\p\brain\a.py", "severity": "error", "rule": "reportUndefinedVariable",
         "message": "\"_unveraendert\" is not defined",
         "range": {"start": {"line": 9, "character": 4}, "end": {"line": 9, "character": 17}}},
        {"file": r"C:\p\brain\b.py", "severity": "warning", "rule": "reportUnusedImport",
         "message": "Import \"os\" is not accessed",
         "range": {"start": {"line": 0, "character": 7}, "end": {"line": 0, "character": 9}}},
        {"file": r"C:\p\brain\b.py", "severity": "information", "rule": None,
         "message": "Hinweis", "range": {"start": {"line": 3, "character": 0}}},
    ],
    "summary": {"filesAnalyzed": 2, "errorCount": 1, "warningCount": 1,
                "informationCount": 1, "timeInSec": 0.4},
}


class ParserTest(unittest.TestCase):

    def test_parser_liefert_relative_pfade_und_1basierte_zeilen(self):
        befunde, dateien, version = LanguageServer._parsen(
            "Kopfzeile der Huelle\n" + json.dumps(AUSGABE), Path(r"C:\p"))
        self.assertEqual((dateien, version), (2, "1.19.0"))
        self.assertEqual(befunde[0]["datei"], "brain/a.py")
        self.assertEqual((befunde[0]["zeile"], befunde[0]["spalte"]), (10, 5))
        self.assertEqual(befunde[0]["stufe"], "error")
        self.assertEqual(befunde[2]["regel"], "")

    def test_parser_ohne_json_wirft(self):
        with self.assertRaises(ValueError):
            LanguageServer._parsen("nur Text", Path(r"C:\p"))


class LaufTest(unittest.TestCase):

    def test_fehlendes_programm_ergibt_hinweis_statt_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            k = LsKonfig({"werkzeug": "pyright", "python": str(Path(d) / "x" / "python.exe")})
            s = LanguageServer(k, d, Path(d) / "ablage")
            s._programm = lambda name: None              # nirgends installiert
            e = s.laufen()
            self.assertIn("nicht installiert", e.fehlt)
            self.assertIn("pip install pyright", e.fehlt)
            self.assertEqual(e.befunde, [])

    def test_konfigurationsdatei_liegt_im_ablageordner(self):
        with tempfile.TemporaryDirectory() as d:
            ordner = Path(d) / "ablage"
            s = LanguageServer(LsKonfig(), d, ordner)
            pfad = s.konfig_schreiben()
            self.assertEqual(pfad.parent, ordner)
            cfg = json.loads(pfad.read_text(encoding="utf-8"))
            # RELATIV zur Konfigurationsdatei (ablage/ liegt eine Ebene unter d):
            # pyright verwirft absolute include-Pfade, 02.09.2026 gemessen.
            self.assertEqual(cfg["include"], [".."])
            self.assertEqual(s.umgebung()["PYRIGHT_PYTHON_CACHE_DIR"],
                             str(ordner / "pyright-python"))


class BefundeTest(unittest.TestCase):

    def _ergebnis(self):
        e = LsErgebnis("basedpyright", "abc", "basic")
        e.befunde, e.dateien, e.version = LanguageServer._parsen(
            json.dumps(AUSGABE), Path(r"C:\p"))
        e.dauer_s = 0.4
        return e

    def test_kennzahlen_und_stufenfilter(self):
        b = LsBefunde(self._ergebnis(), LsKonfig({"stufe": "warning"}))
        k = b.kennzahlen()
        self.assertEqual((k["fehler"], k["warnungen"], k["hinweise"]), (1, 1, 1))
        self.assertEqual(k["gefiltert"], 2, "Hinweise liegen unter der Stufe")
        self.assertEqual(b.gefiltert()[0]["stufe"], "error", "Fehler zuerst")

    def test_tabelle_traegt_stelle_im_id_und_haelt_den_deckel(self):
        b = LsBefunde(self._ergebnis(), LsKonfig({"stufe": "information", "deckel": 10}))
        t = b.tabelle()
        self.assertEqual(len(t["zeilen"]), 3)
        self.assertEqual(t["zeilen"][0]["id"], "brain/a.py|10|5")
        self.assertEqual(t["zeilen"][0]["klasse"], "ls-error")
        b2 = LsBefunde(self._ergebnis(), LsKonfig({"stufe": "information", "deckel": 10}))
        b2.konfig.deckel = 1
        self.assertEqual(len(b2.tabelle()["zeilen"]), 1)

    def test_je_regel_zaehlt(self):
        b = LsBefunde(self._ergebnis(), LsKonfig())
        regeln = dict((r, n) for r, n, _s in b.je_regel())
        self.assertEqual(regeln["reportUndefinedVariable"], 1)
        self.assertEqual(b.je_datei()[0], ("brain/b.py", 2))


class DasEigenePaketIstAufloesbar(unittest.TestCase):
    u"""``extra_pfade()`` muss den Ordner ÜBER ``djangobase`` mitgeben.

    DER ANLASS (02.09.2026)
    =======================
    Alle sechs Konsumenten binden djangoBase als *editable install* ein.
    In ``site-packages`` liegt dann nur ein Verweis, und dem folgt der
    Language Server nicht. Erster Lauf über CamTrack: sieben
    ``reportMissingImports``, alle auf ``djangobase.*`` — kein einziger
    davon ein Fehler im Projekt.

    Sieben rote Zeilen, die nichts bedeuten, sind teurer als keine: Sie
    bringen den Leser dazu, auch die echten zu überblättern.
    """

    def _pfade(self):
        from djangobase.views.languageserver import extra_pfade
        return [Path(p).resolve() for p in extra_pfade()]

    def test_der_ordner_ueber_dem_paket_ist_dabei(self):
        import djangobase
        eigene = Path(djangobase.__file__).resolve().parent.parent
        self.assertIn(eigene, self._pfade(),
                      u"Ohne diesen Pfad meldet der Server jeden "
                      u"djangobase-Import als unauffindbar.")

    def test_und_er_enthaelt_das_paket_wirklich(self):
        u"""Sonst prüft die Zusage darüber einen Pfad ins Leere."""
        import djangobase
        eigene = Path(djangobase.__file__).resolve().parent.parent
        self.assertTrue((eigene / "djangobase" / "__init__.py").is_file(),
                        u"%s ist keine Import-Wurzel für djangobase" % eigene)

    def test_kein_pfad_kommt_doppelt(self):
        u"""``extraPaths`` wächst sonst bei jedem Lauf um dieselbe Zeile."""
        pfade = self._pfade()
        self.assertEqual(len(pfade), len(set(pfade)))
