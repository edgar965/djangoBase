# -*- coding: utf-8 -*-
u"""Der Ausnahme-Vermerk von `lehren-treue` — und seine Grenzen.

WARUM ES DEN VERMERK GIBT (27.08.2026, 3DTools)
===============================================
Beide gemeldeten Verstoesse waren keine:

* `koerperhuelle.py` benutzt `np.add.at` MIT Messung daneben — unter numpy 2.4
  braucht `np.bincount` dort 31 ms gegen 29 ms und zusaetzlich ein `np.repeat`
  ueber alle Dreiecksecken. Die Lehre stammt aus einem anderen Zahlenbereich.
* `test_projekt_temp.py` ruft `gettempdir()`, um zu BEHAUPTEN, dass die Datei
  NICHT dort liegt. Gemeldet wurde also die Zusicherung, die die Lehre
  durchsetzt.

Eine Liste mit Dauergaesten liest niemand mehr — deshalb der Vermerk. Damit er
keine Hintertuer wird, gelten drei Grenzen, und die stehen hier als Test:

1. Er muss die Lehre BEIM NAMEN nennen.
2. Er gilt nur in der Funktion, in der er steht.
3. Die Kopfzeile nennt die Zahl der ausgenommenen Stellen.
"""

import ast

from django.test import SimpleTestCase

from djangobase.skills.lehrentreue import Regelsucher


def _verstoesse(quelle):
    sucher = Regelsucher('probe.py', quelle)
    sucher.visit(ast.parse(quelle))
    return sucher


ROH = '''import tempfile


def machen():
    return tempfile.mkdtemp()
'''

MIT_VERMERK = '''import tempfile


def machen():
    # Lehre gilt hier nicht ("keine-temp-dateien-im-system"): Der Pfad wird
    # nur verglichen, nicht beschrieben.
    return tempfile.mkdtemp()
'''

FALSCHE_LEHRE = '''import tempfile


def machen():
    # Lehre gilt hier nicht ("bincount-statt-add-at"): ganz andere Baustelle.
    return tempfile.mkdtemp()
'''

VERMERK_ANDERSWO = '''import tempfile


def erklaeren():
    # Lehre gilt hier nicht ("keine-temp-dateien-im-system") - hier steht
    # aber gar kein Aufruf.
    return 1


def machen():
    return tempfile.mkdtemp()
'''

WEITER_WEG = '''import tempfile


def machen():
    # Lehre gilt hier nicht ("keine-temp-dateien-im-system").
    # Gemessen am 27.08.2026: eine ausfuehrliche Begruendung braucht
    # Platz, und zwischen ihr und der Stelle steht oft noch Code.
    # Zeile vier der Begruendung.
    # Zeile fuenf der Begruendung.
    # Zeile sechs der Begruendung.
    # Zeile sieben der Begruendung.
    ordner = None
    if ordner is None:
        pass
    return tempfile.mkdtemp()
'''


class VermerkTest(SimpleTestCase):

    def test_ohne_vermerk_ist_es_ein_verstoss(self):
        u"""DIE GEGENPROBE: Ohne Vermerk muss der Waechter anschlagen."""
        sucher = _verstoesse(ROH)
        self.assertEqual(len(sucher.verstoesse), 1)
        self.assertEqual(sucher.ausgenommen, 0)

    def test_mit_vermerk_ist_es_keiner(self):
        sucher = _verstoesse(MIT_VERMERK)
        self.assertEqual(sucher.verstoesse, [])
        self.assertEqual(sucher.ausgenommen, 1)

    def test_vermerk_fuer_eine_ANDERE_lehre_zaehlt_nicht(self):
        u"""Sonst waere ein einziger Vermerk ein Freibrief fuer alles."""
        sucher = _verstoesse(FALSCHE_LEHRE)
        self.assertEqual(len(sucher.verstoesse), 1)
        self.assertEqual(sucher.ausgenommen, 0)

    def test_vermerk_in_einer_anderen_funktion_zaehlt_nicht(self):
        sucher = _verstoesse(VERMERK_ANDERSWO)
        self.assertEqual(len(sucher.verstoesse), 1)

    def test_vermerk_gilt_in_der_ganzen_funktion(self):
        u"""DER FALL AUS `koerperhuelle.py`: sieben Zeilen Messwerte dazwischen."""
        sucher = _verstoesse(WEITER_WEG)
        self.assertEqual(sucher.verstoesse, [])
        self.assertEqual(sucher.ausgenommen, 1)
