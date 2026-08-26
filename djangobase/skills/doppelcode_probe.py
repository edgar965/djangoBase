# -*- coding: utf-8 -*-
u"""Gegenprobe zur Block-Zusammenfassung im Doppelcode-Melder.

WARUM (25.08.2026, Projekt assistant)
=====================================
Gesucht wird mit einem GLEITENDEN Fenster. Ein zusammenhaengender
Duplikatblock von zwölf Zeilen erzeugt bei Fenstergroesse sechs sieben
Fenster - und damit sieben Befunde für EINE Stelle. Von 670 gemeldeten
Stellen blieben nach dem Zusammenfassen 446; in den ersten 200
angezeigten waren 112 blosse Folgezeilen.

Diese Probe hält beide Richtungen fest:

* Aneinandergrenzende Fenster werden zu EINEM Befund mit der ECHTEN
  Laenge - sonst blaeht sich die Liste wieder auf.
* Zwei GETRENNTE Duplikatstellen bleiben zwei Befunde - sonst wäre die
  einfachste Art, die Liste kurz zu bekommen, alles zusammenzuwerfen.
"""
from django.test import SimpleTestCase

__all__ = ["DoppelcodeProbe"]


class DoppelcodeProbe(SimpleTestCase):
    u"""Fenster zusammenfassen - aber nur die, die zusammengehoeren."""

    def _fassen(self, roh, fenster=6):
        from .doppelcode import Doppelcode

        return Doppelcode._zusammenfassen(roh, fenster)

    def test_angrenzende_fenster_werden_eins(self):
        u"""Drei Fenster, je eine Zeile weiter = ein Block von acht Zeilen."""
        roh = [['a.py:10', 'b.py:100'],
               ['a.py:11', 'b.py:101'],
               ['a.py:12', 'b.py:102']]
        ergebnis = self._fassen(roh)
        self.assertEqual(len(ergebnis), 1,
                         "Drei aneinandergrenzende Fenster sind EIN Block. "
                         "Werden sie einzeln gemeldet, steht dieselbe Stelle "
                         "dreimal in der Liste.")
        orte, laenge = ergebnis[0]
        self.assertEqual(orte, ['a.py:10', 'b.py:100'],
                         "Gemeldet wird der ANFANG des Blocks.")
        self.assertEqual(laenge, 8,
                         "Sechs Zeilen Fenster plus zwei Verschiebungen = "
                         "acht Zeilen echte Blocklaenge.")

    def test_leerzeile_im_block_bricht_nicht(self):
        u"""Der Melder überspringt Leerzeilen - die Nummern springen."""
        roh = [['a.py:10', 'b.py:100'],
               ['a.py:12', 'b.py:102']]
        self.assertEqual(len(self._fassen(roh)), 1,
                         "Beide Fundstellen ruecken um ZWEI weiter - das ist "
                         "derselbe Block mit einer Leerzeile darin. Verlangt "
                         "man genau +1, fasst man fast nichts zusammen.")

    def test_getrennte_stellen_bleiben_getrennt(self):
        u"""Ohne diese Richtung wäre das Zusammenfassen wertlos."""
        roh = [['a.py:10', 'b.py:100'],
               ['a.py:400', 'b.py:900']]
        self.assertEqual(len(self._fassen(roh)), 2,
                         "Zwei weit auseinanderliegende Stellen sind zwei "
                         "Befunde. Wer sie zusammenwirft, macht die Liste "
                         "kurz und nutzlos.")

    def test_andere_partnerdateien_bleiben_getrennt(self):
        u"""Gleiche Zeilenfolge, andere Dateien = anderer Block."""
        roh = [['a.py:10', 'b.py:100'],
               ['a.py:11', 'c.py:101']]
        self.assertEqual(len(self._fassen(roh)), 2,
                         "Der zweite Block steht in einer anderen Datei - "
                         "er rueckt nicht 'weiter', er ist ein anderer Fund.")
