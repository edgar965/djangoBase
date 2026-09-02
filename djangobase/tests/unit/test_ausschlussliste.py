# -*- coding: utf-8 -*-
u"""Ausschlussliste: deuten, lesen, schreiben — und was sie ablehnt."""
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.ausschlussliste import Ausschlussliste


class AusschlusslisteTest(unittest.TestCase):

    def _liste(self, ordner, inhalt=None):
        if inhalt is not None:
            (Path(ordner) / Ausschlussliste.DATEI).write_text(inhalt, encoding="utf-8")
        return Ausschlussliste(ordner)

    def test_ohne_datei_ist_alles_leer_und_das_feld_zeigt_die_vorlage(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d)
            self.assertFalse(liste.vorhanden())
            self.assertEqual(liste.muster(), [])
            self.assertEqual(liste.namen(), [])
            self.assertIn("# Ausschlussliste", liste.text())

    def test_nackter_name_gilt_in_jeder_tiefe_pfad_ab_der_wurzel(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d, u"# Kommentar\n\nsicherung\n"
                                   u"werkzeug/netz_*.py\n**/*.min.js\n")
            self.assertEqual(liste.muster(),
                             ["**/sicherung", "werkzeug/netz_*.py", "**/*.min.js"])
            self.assertEqual(liste.namen(), ["sicherung"],
                             u"Globs kann Werkzeug.ausgeschlossen() nicht deuten")

    def test_schraegstriche_und_schluss_werden_vereinheitlicht(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d, u"werkzeug\\sicherung\\\n./brain/alt/\n")
            self.assertEqual(liste.muster(), ["werkzeug/sicherung", "brain/alt"])

    def test_absolut_und_doppelpunkt_werden_abgelehnt_bleiben_aber_sichtbar(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d, u"C:/Windows\n/etc/passwd\n../nachbar\nbrain\n")
            self.assertEqual(liste.muster(), ["**/brain"])
            gruende = [g for _nr, _roh, g in liste.fehler()]
            self.assertEqual(len(gruende), 3)
            self.assertIn(u"absoluter Pfad", gruende[0])
            self.assertIn(u"aus dem Projekt", gruende[2])
            self.assertEqual([nr for nr, _r, _g in liste.fehler()], [1, 2, 3],
                             u"die Zeilennummer der Datei, nicht die des Musters")

    def test_speichern_liest_sich_zurueck_und_der_merker_faellt(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d, u"alt\n")
            self.assertEqual(liste.muster(), ["**/alt"])
            anzahl, fehler = liste.speichern(u"neu\r\nzweitens\r\n\r\n")
            self.assertEqual((anzahl, fehler), (2, []))
            self.assertEqual(liste.muster(), ["**/neu", "**/zweitens"])
            roh = (Path(d) / Ausschlussliste.DATEI).read_bytes()
            self.assertNotIn(b"\r", roh, u"LF, damit die Datei im Repo gleich aussieht")
            self.assertTrue(roh.endswith(b"\n"))

    def test_deckel_gegen_ein_eingefuegtes_protokoll(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d)
            liste.speichern(u"\n".join(u"ordner%d" % i for i in range(600)))
            self.assertEqual(len(liste.muster()), Ausschlussliste.HOECHSTENS)

    def test_abdruck_haengt_am_inhalt(self):
        with tempfile.TemporaryDirectory() as d:
            liste = self._liste(d, u"eins\n")
            vorher = liste.abdruck()
            liste.speichern(u"eins\nzwei\n")
            self.assertNotEqual(vorher, liste.abdruck())
            liste.speichern(u"# nur ein Kommentar\neins\n")
            self.assertEqual(vorher, liste.abdruck(),
                             u"Kommentare zaehlen nicht zum Ergebnis")
