# -*- coding: utf-8 -*-
u"""Re-Export-Marker: was zählt, was nicht — und wie weit er reicht."""
import ast
import unittest

from djangobase.umbau.reexport import Reexporte


class ReexportMarkerTest(unittest.TestCase):

    def test_f401_und_nacktes_noqa_zaehlen(self):
        for zeile in (u"from .x import y  # noqa: F401",
                      u"from .x import y  # noqa",
                      u"from .x import y  # NOQA: F401",
                      u"from .x import y  # noqa:F401,E501",
                      u"from .x import y  # noqa: E501, F401"):
            self.assertTrue(Reexporte.ist_marker(zeile), zeile)

    def test_ein_anderer_code_zaehlt_nicht(self):
        u"""Sonst verschwände ein echter Befund hinter einer langen Zeile."""
        for zeile in (u"from .x import y  # noqa: E501",
                      u"from .x import y  # noqa: E402",
                      u"from .x import y",
                      u"from .x import y  # nur ein Kommentar"):
            self.assertFalse(Reexporte.ist_marker(zeile), zeile)

    def test_leer_und_none_werfen_nicht(self):
        self.assertFalse(Reexporte.ist_marker(u""))
        self.assertFalse(Reexporte.ist_marker(None))


class ReexportZeilenTest(unittest.TestCase):

    def _zeilen(self, quelle):
        return Reexporte.zeilen(ast.parse(quelle), quelle.splitlines())

    def test_der_ganze_umbrochene_import_zaehlt(self):
        u"""Der Marker steht in Zeile 1, pyright meldet auch Zeile 2."""
        quelle = (u"from .basis import (A, B,   # noqa: F401\n"
                  u"                    C, D)\n"
                  u"x = 1\n")
        self.assertEqual(self._zeilen(quelle), {1, 2})

    def test_ohne_marker_faellt_nichts(self):
        quelle = u"from .basis import A\nimport os\n"
        self.assertEqual(self._zeilen(quelle), set())

    def test_nur_der_markierte_import_faellt(self):
        quelle = (u"import os            # noqa: F401\n"
                  u"import sys\n")
        self.assertEqual(self._zeilen(quelle), {1})

    def test_ein_marker_an_etwas_anderem_zaehlt_nicht(self):
        quelle = (u"import os\n"
                  u"x = irgendwas()      # noqa: F401\n")
        self.assertEqual(self._zeilen(quelle), set())


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
