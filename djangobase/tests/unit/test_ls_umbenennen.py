# -*- coding: utf-8 -*-
u"""Umbenennung: Vorschau, Anwenden mit Sicherung, Kompilier-Netz, Zeilenenden."""
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.ls_sitzung import uri
from djangobase.umbau.ls_umbenennen import Umbenennung


def _edit(pfad, stellen):
    u"""WorkspaceEdit in der ``changes``-Form: stellen = [(zeile0, s0, s1, neu)]."""
    return {"changes": {uri(pfad): [
        {"range": {"start": {"line": z, "character": a}, "end": {"line": z, "character": b}},
         "newText": neu} for z, a, b, neu in stellen]}}


class UmbenennungTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        self.datei = self.wurzel / "modul.py"
        self.datei.write_bytes(b"def alt():\r\n    return 1\r\n\r\nx = alt()\r\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_vorschau_zeigt_jede_stelle(self):
        u = Umbenennung(_edit(self.datei, [(0, 4, 7, "neu"), (3, 4, 7, "neu")]),
                        self.wurzel, self.wurzel / "sicherung")
        v = u.vorschau()
        self.assertEqual([(x["zeile"], x["alt"], x["neu"]) for x in v],
                         [(1, "alt", "neu"), (4, "alt", "neu")])
        self.assertEqual(v[0]["datei"], "modul.py")

    def test_anwenden_schreibt_mit_sicherung_und_behaelt_crlf(self):
        u = Umbenennung(_edit(self.datei, [(0, 4, 7, "neu"), (3, 4, 7, "neu")]),
                        self.wurzel, self.wurzel / "sicherung")
        b = u.anwenden()
        self.assertEqual((b["dateien"], b["stellen"], b["fehler"]), (1, 2, []))
        self.assertEqual(self.datei.read_bytes(),
                         b"def neu():\r\n    return 1\r\n\r\nx = neu()\r\n")
        gesichert = list((self.wurzel / "sicherung").rglob("modul.py"))
        self.assertEqual(len(gesichert), 1)
        self.assertIn(b"def alt()", gesichert[0].read_bytes())

    def test_netz_faengt_kaputten_umbau(self):
        # Ein Name, der das Modul nicht mehr kompilieren laesst.
        u = Umbenennung(_edit(self.datei, [(0, 4, 7, "1 2")]),
                        self.wurzel, self.wurzel / "sicherung")
        b = u.anwenden()
        self.assertEqual(b["dateien"], 0)
        self.assertIn("nicht mehr kompilierbar", b["fehler"][0])
        self.assertIn(b"def alt()", self.datei.read_bytes(), "unveraendert")

    def test_document_changes_form(self):
        edit = {"documentChanges": [{"textDocument": {"uri": uri(self.datei), "version": 1},
                                     "edits": [{"range": {"start": {"line": 3, "character": 4},
                                                          "end": {"line": 3, "character": 7}},
                                                "newText": "neu"}]}]}
        u = Umbenennung(edit, self.wurzel, self.wurzel / "sicherung")
        self.assertEqual(u.vorschau()[0]["zeile"], 4)
