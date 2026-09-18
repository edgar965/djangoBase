# -*- coding: utf-8 -*-
"""Re-Export-Marker: was zählt, was nicht — und wie weit er reicht."""

import ast
import unittest

from djangobase.umbau.reexport import Reexporte


class ReexportMarkerTest(unittest.TestCase):
    def test_f401_und_nacktes_noqa_zaehlen(self):
        for zeile in (
            "from .x import y  # noqa: F401",
            "from .x import y  # noqa",
            "from .x import y  # NOQA: F401",
            "from .x import y  # noqa:F401,E501",
            "from .x import y  # noqa: E501, F401",
        ):
            self.assertTrue(Reexporte.ist_marker(zeile), zeile)

    def test_ein_anderer_code_zaehlt_nicht(self):
        """Sonst verschwände ein echter Befund hinter einer langen Zeile."""
        for zeile in (
            "from .x import y  # noqa: E501",
            "from .x import y  # noqa: E402",
            "from .x import y",
            "from .x import y  # nur ein Kommentar",
        ):
            self.assertFalse(Reexporte.ist_marker(zeile), zeile)

    def test_leer_und_none_werfen_nicht(self):
        self.assertFalse(Reexporte.ist_marker(""))
        self.assertFalse(Reexporte.ist_marker(None))


class ReexportZeilenTest(unittest.TestCase):
    def _zeilen(self, quelle):
        return Reexporte.zeilen(ast.parse(quelle), quelle.splitlines())

    def test_der_ganze_umbrochene_import_zaehlt(self):
        """Der Marker steht in Zeile 1, pyright meldet auch Zeile 2."""
        quelle = "from .basis import (A, B,   # noqa: F401\n                    C, D)\nx = 1\n"
        self.assertEqual(self._zeilen(quelle), {1, 2})

    def test_ohne_marker_faellt_nichts(self):
        quelle = "from .basis import A\nimport os\n"
        self.assertEqual(self._zeilen(quelle), set())

    def test_nur_der_markierte_import_faellt(self):
        quelle = "import os            # noqa: F401\nimport sys\n"
        self.assertEqual(self._zeilen(quelle), {1})

    def test_ein_marker_an_etwas_anderem_zaehlt_nicht(self):
        quelle = "import os\nx = irgendwas()      # noqa: F401\n"
        self.assertEqual(self._zeilen(quelle), set())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
