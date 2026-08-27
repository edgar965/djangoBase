# -*- coding: utf-8 -*-
u"""Pruefcode — findet er JEDE Pruefung, und nur Pruefungen?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „die andere Session sagte mir, BDD würde nur nach einem festen Muster
     suchen, nicht allgemein, im ganzen Code"
    „schaust du nach, ob BDD alle tests checkt? sollen alle Tests von der
     Testklasse erben? dann brauchen wir auch einen testcase dafür"

Zwei Fragen, zwei Antworten — beide gemessen:

    findet es alle?     Ja. Der Dateiname-Filter uebersah 73 Pruefmethoden
                        in djangoBase, die Vererbungsregel keine.
    muessen alle erben? Ja, und alle tun es. Eine Pruefklasse OHNE Basis
                        fuehrt `unittest` stillschweigend NIE aus — sie
                        ist rot und niemand sieht es.

Die letzte Klasse hier ist der Waechter dafuer. Sie ist heute gruen; genau
darum gehoert sie hin: Sie haelt die Eigenschaft fest, statt sie zu
entdecken.

Diese Pruefungen gehoeren zu Kriterium 19 („Abnahme und Beispiele").
"""
import ast
from pathlib import Path

from django.conf import settings

from djangobase.skills.pruefcode import WURZELBASEN, Pruefcode

from ..base import BasisTest


def _baum(quelle):
    return ast.parse(quelle)


def _pruefcode(*quellen):
    return Pruefcode().lesen([(Path('x%d.py' % i), _baum(q))
                              for i, q in enumerate(quellen)])


class EineKlasseMitTestBasisIstEinePruefung(BasisTest):
    u"""Der einfache Fall — und die Schreibweise darf egal sein."""

    def test_die_direkte_basis_wird_erkannt(self):
        pc = _pruefcode('class A(TestCase):\n    def test_x(self):\n        pass\n')
        knoten = _baum('class A(TestCase):\n    def test_x(self):\n'
                       '        pass\n').body[0]
        self.assertTrue(pc.ist_pruefklasse(knoten))

    def test_der_punkt_davor_aendert_nichts(self):
        u"""``unittest.TestCase`` ist dasselbe wie ``TestCase``."""
        quelle = ('class A(unittest.TestCase):\n'
                  '    def test_x(self):\n        pass\n')
        pc = _pruefcode(quelle)
        self.assertTrue(pc.ist_pruefklasse(_baum(quelle).body[0]))


class EineEigeneBasisWirdUEBERMEHREREStufenErkannt(BasisTest):
    u"""Der Fall, an dem eine feste Namensliste scheitert.

    In diesen Projekten erbt kaum etwas direkt von ``TestCase``:
    TestCase <- BasisTest <- JobsSeiteBasis <- die eigentliche Prüfung.
    """

    QUELLE = ('class BasisTest(TestCase):\n    pass\n\n\n'
              'class Zwischenbasis(BasisTest):\n    pass\n\n\n'
              'class Eigentliche(Zwischenbasis):\n'
              '    def test_etwas_geht_gut(self):\n        pass\n')

    def test_die_klasse_am_ende_der_kette_zaehlt(self):
        pc = _pruefcode(self.QUELLE)
        letzte = [k for k in _baum(self.QUELLE).body
                  if isinstance(k, ast.ClassDef)][-1]
        self.assertTrue(pc.ist_pruefklasse(letzte))

    def test_die_zwischenbasen_gelten_als_pruefbasis(self):
        pc = _pruefcode(self.QUELLE)
        self.assertIn('Zwischenbasis', pc.pruefbasen)
        self.assertIn('BasisTest', pc.pruefbasen)


class EineKlasseOhneBasisIstKeinePruefung(BasisTest):
    u"""Die Gegenrichtung — sonst waere die Regel wertlos.

    ``ConnectionTester.test_http_snapshot(ip, port, …)`` probiert
    Schnappschuss-Pfade an einer Kamera durch. Sie heißt nur so, und der
    frühere Dateiname-Filter brauchte eine Extrawurst für sie.
    """

    QUELLE = ('class ConnectionTester:\n'
              '    def test_http_snapshot(self, ip, port):\n'
              '        return 1\n')

    def test_eine_ansicht_faellt_von_selbst_heraus(self):
        pc = _pruefcode(self.QUELLE)
        self.assertFalse(pc.ist_pruefklasse(_baum(self.QUELLE).body[0]))

    def test_und_taucht_in_keiner_pruefklassenliste_auf(self):
        pc = _pruefcode(self.QUELLE)
        self.assertEqual(pc.pruefklassen(_baum(self.QUELLE)), [])


class DerDateinameEntscheidetNICHTS(BasisTest):
    u"""Die eigentliche Korrektur vom 27.08.2026.

    ``grundtests.py``, ``befundgrenzen.py``, ``endpunkttests.py`` und
    ``leistungstests.py`` heißen nicht ``test_*`` — und trugen zusammen 73
    Prüfmethoden, die niemand prüfte.
    """

    def test_eine_pruefung_in_grundtests_py_zaehlt_mit(self):
        quelle = ('class GrundtestUrls(SimpleTestCase):\n'
                  '    def test_jede_route_laesst_sich_aufloesen(self):\n'
                  '        pass\n')
        pc = Pruefcode().lesen([(Path('grundtests.py'), _baum(quelle))])
        self.assertEqual(len(pc.pruefklassen(_baum(quelle))), 1)


class NurWasDerTestlaeuferAusfuehrt(BasisTest):
    u"""Eine Hilfsmethode ist keine Prüfung."""

    QUELLE = ('class A(TestCase):\n'
              '    def test_eins(self):\n        pass\n'
              '    def _hilfe(self):\n        pass\n'
              '    def aufraeumen(self):\n        pass\n')

    def test_nur_die_test_methoden_kommen_mit(self):
        pc = _pruefcode(self.QUELLE)
        namen = [m.name for m in pc.pruefmethoden(_baum(self.QUELLE).body[0])]
        self.assertEqual(namen, ['test_eins'])


class JedePruefungErbtVonEinerTestBasis(BasisTest):
    u"""DER WÄCHTER — heute grün, und genau darum hier.

        „sollen alle Tests von der Testklasse erben? dann brauchen wir
         auch einen testcase dafür"

    Eine Klasse mit ``test_``-Methoden, die von KEINER Test-Basis erbt,
    wird von `unittest` nicht eingesammelt. Sie läuft nie — und meldet
    deshalb auch nie rot. Das ist die stillste Art, eine Prüfung zu
    verlieren: Sie steht da, sie sieht richtig aus, sie zählt in keiner
    Statistik.

    Geprüft wird nur unterhalb der Prüf-Ordner. Außerhalb gibt es
    Klassen, die zu Recht ``test_`` heißen und keine Prüfungen sind —
    ``ConnectionTester`` in einer Ansicht ist der bekannte Fall.
    """

    #: Ordner, in denen NUR Prüfungen stehen dürfen.
    ORTE = ('tests',)
    AUS = ('__pycache__', 'migrations', 'node_modules', 'venv')

    def _dateien(self):
        wurzel = Path(settings.BASE_DIR)
        for pfad in wurzel.rglob('*.py'):
            if any(t in self.AUS for t in pfad.parts):
                continue
            if not any(t in self.ORTE for t in pfad.parts):
                continue
            try:
                yield pfad, ast.parse(pfad.read_text(encoding='utf-8'))
            except (SyntaxError, OSError, UnicodeDecodeError):
                continue

    def test_keine_pruefklasse_bleibt_ohne_basis(self):
        dateien = list(self._dateien())
        self.assertTrue(dateien, 'Keine Prüfdateien gefunden — der Wächter '
                                 'wäre sonst grün, ohne etwas zu prüfen.')
        pruefcode = Pruefcode().lesen(dateien)
        verwaist = []
        for pfad, baum in dateien:
            for knoten in ast.walk(baum):
                if not isinstance(knoten, ast.ClassDef):
                    continue
                if not pruefcode.pruefmethoden(knoten):
                    continue
                if not pruefcode.ist_pruefklasse(knoten):
                    verwaist.append('%s:%d %s' % (pfad.name, knoten.lineno,
                                                  knoten.name))
        self.assertEqual(verwaist, [],
                         'Diese Klassen tragen test_-Methoden, erben aber '
                         'von keiner Test-Basis. unittest führt sie NIE '
                         'aus: %s' % verwaist)

    def test_es_gibt_ueberhaupt_pruefungen_zu_finden(self):
        u"""Gegenprobe: Sonst wäre der Wächter oben trivial grün."""
        dateien = list(self._dateien())
        pruefcode = Pruefcode().lesen(dateien)
        gefunden = sum(len(m) for _p, baum in dateien
                       for _k, m in pruefcode.pruefklassen(baum))
        self.assertGreater(gefunden, 100)

    def test_die_wurzelbasen_sind_die_von_unittest(self):
        u"""Wer hier etwas einträgt, das keine Testbasis ist, macht den
        Wächter blind."""
        self.assertIn('TestCase', WURZELBASEN)
        self.assertIn('SimpleTestCase', WURZELBASEN)
