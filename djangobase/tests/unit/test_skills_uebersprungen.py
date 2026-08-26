# -*- coding: utf-8 -*-
u"""Übersprungen — findet es die Abkürzungen, und meldet es nichts Falsches?

DIE ANSAGE (Edgar, mehrfach)
============================
    „kein Skip test" / „ein übersprungener Test soll nie grün melden"

Die Prüfungen hier decken beide Richtungen ab: Ein Werkzeug, das blind
ist, taugt nichts — eines, das Fehlalarme streut, wird ignoriert und
nimmt den echten Fund mit.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund

from ..base import BasisTest


def _lauf(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='ue_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    werkzeug = werkzeug_finden('uebersprungen')
    werkzeug.wurzel = lambda: ordner
    return werkzeug.pruefen()


def _gewichte(satz):
    raus = {}
    for b in satz.befunde:
        raus[b.gewicht] = raus.get(b.gewicht, 0) + 1
    return raus


KOPF = 'import os\nimport unittest\n\n\n'


class EsFindetDieAbkuerzungen(BasisTest):

    def test_umgebungsschalter_ohne_vorgabe_ist_ein_fehler(self):
        u"""Der Fall aus CamTrack: sechs Prüfungen, die NIE liefen."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      "@unittest.skipUnless(os.environ.get('ECHT'), 'nur mit ECHT')\n"
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(_gewichte(satz).get(Befund.FEHLER), 1,
                         [b.was for b in satz.befunde])

    def test_skiptest_im_rumpf_ist_eine_warnung(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      "        self.skipTest('nichts gefunden')\n"})
        self.assertEqual(_gewichte(satz).get(Befund.WARNUNG), 1)

    def test_dauerhaft_stillgelegt_ist_ein_hinweis(self):
        u"""``@skip`` ohne Bedingung ist wenigstens sichtbar."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      "@unittest.skip('spaeter')\n"
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(_gewichte(satz).get(Befund.HINWEIS), 1)

    def test_der_grund_steht_im_befund(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      "        self.skipTest('keine Aufnahmen auf der Platte')\n"})
        self.assertIn('keine Aufnahmen', satz.befunde[0].warum)

    def test_die_stelle_wird_benannt(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class Abc(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      "        self.skipTest('x')\n"})
        self.assertIn('Abc.test_x', satz.befunde[0].was)


class EinAusschalterIstKeinBefund(BasisTest):
    u"""DER FEHLALARM AUS DEM ERSTEN WURF (26.08.2026).

    Mein erster Entwurf meldete ``CAMTRACK_RUN_GPU_TESTS`` als FEHLER.
    Nachgemessen mit gesetztem Schalter: Die drei Fälle dahinter laufen
    und bestehen in 33 s — die Vorgabe schaltet sie EIN.

        os.environ.get('SMART_SEARCH_INTEGRATION')            läuft nie
        os.environ.get('CAMTRACK_RUN_GPU_TESTS', '1') == '1'  läuft immer

    Der zweite Wert im ``get``-Aufruf ist der ganze Unterschied. Ein
    Werkzeug, das beide gleich meldet, wird ignoriert — und mit ihm der
    echte Fall daneben.
    """

    def test_mit_vorgabe_ist_es_kein_fehler(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      "@unittest.skipUnless(os.environ.get('GPU', '1') == '1', 'aus')\n"
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertIsNone(_gewichte(satz).get(Befund.FEHLER),
                          'Ein Ausschalter mit Vorgabe „an" laeuft von '
                          'selbst — das ist kein stillgelegter Test.')

    def test_gemeldet_wird_er_trotzdem(self):
        u"""Nicht verschweigen: Wer ihn auf 0 setzt, soll wissen, was ausfällt."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      "@unittest.skipUnless(os.environ.get('GPU', '1') == '1', 'aus')\n"
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(len(satz.befunde), 1)


class EsMeldetNichtsFalsches(BasisTest):

    def test_eine_saubere_pruefdatei_ergibt_nichts(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(satz.befunde, [])

    def test_ausserhalb_der_pruefungen_wird_nicht_gesucht(self):
        u"""``warteschlange.skip()`` in Anwendungscode ist kein Test-Skip."""
        satz = _lauf({'app/dienst.py':
                      'def arbeiten(schlange):\n'
                      '    schlange.skip()\n'})
        self.assertEqual(satz.befunde, [])

    def test_ein_fremdes_skip_im_pruefcode_zaehlt_nicht(self):
        u"""Nur ``skipTest`` oder ``pytest.skip`` — nicht jedes ``.skip()``."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        schlange = object()\n'
                      '        schlange.skip()\n'})
        self.assertEqual(satz.befunde, [])

    def test_pytest_skip_zaehlt_schon(self):
        satz = _lauf({'tests/test_a.py':
                      'import pytest\n\n\n'
                      'def test_x():\n'
                      "    pytest.skip('nicht heute')\n"})
        self.assertEqual(len(satz.befunde), 1)


class DerKopfSagtWieVieleEsSind(BasisTest):

    def test_ohne_befund_steht_es_ausdruecklich_da(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertTrue(any('Keine' in z for z in satz.kopf), satz.kopf)

    def test_die_schweren_werden_getrennt_gezaehlt(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      "@unittest.skipUnless(os.environ.get('ECHT'), 'x')\n"
                      'class A(unittest.TestCase):\n'
                      '    def test_x(self):\n'
                      "        self.skipTest('y')\n"})
        self.assertTrue(any('Umgebungsvariablen' in z for z in satz.kopf),
                        satz.kopf)
