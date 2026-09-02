# -*- coding: utf-8 -*-
u"""JsPruefer: tsc-Zeilen lesen, jsconfig schreiben, fehlendes tsc melden."""
import json
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.ls_javascript import JsPruefer

AUSGABE = """static/app/js/seite.js(12,5): error TS2304: Cannot find name 'Chart'.
static/app/js/seite.js(40,19): error TS2554: Expected 2 arguments, but got 1.
Version 7.0.2
"""


class JsPrueferTest(unittest.TestCase):

    def test_parser_liest_zeile_spalte_regel(self):
        with tempfile.TemporaryDirectory() as d:
            b = JsPruefer._parsen(AUSGABE, d)
        self.assertEqual(len(b), 2)
        self.assertEqual(b[0]["datei"], "static/app/js/seite.js")
        self.assertEqual((b[0]["zeile"], b[0]["spalte"], b[0]["regel"]), (12, 5, "TS2304"))
        self.assertEqual(b[1]["text"], "Expected 2 arguments, but got 1.")
        self.assertEqual(b[0]["sprache"], "js")
        self.assertEqual(b[0]["stufe"], "error")

    def test_jsconfig_prueft_js_und_schliesst_vendor_aus(self):
        with tempfile.TemporaryDirectory() as d:
            p = JsPruefer(d, Path(d) / "ablage", pfade=["web"])
            cfg = json.loads(p.konfig_schreiben().read_text(encoding="utf-8"))
        self.assertTrue(cfg["compilerOptions"]["checkJs"])
        self.assertTrue(cfg["compilerOptions"]["noEmit"])
        self.assertTrue(cfg["include"][0].endswith("/web/**/*.js"))
        self.assertTrue(any(e.endswith("/**/*.min.js") for e in cfg["exclude"]))
        self.assertTrue(any(e.endswith("/**/node_modules") for e in cfg["exclude"]))

    def test_fehlendes_tsc_ergibt_hinweis(self):
        with tempfile.TemporaryDirectory() as d:
            p = JsPruefer(d, Path(d) / "ablage")
            p.finden = lambda: None
            befunde, dauer, fehlt = p.laufen()
        self.assertEqual(befunde, [])
        self.assertIn("npm install -g typescript", fehlt)
