# -*- coding: utf-8 -*-
u"""Szenarien — findet es stumme Prüfungen, und lässt es gute in Ruhe?

DIE FRAGE DAHINTER (Edgar, 26.08.2026)
======================================
    „Macht es sinn, dass ich BDD anwende?"

Die teuerste Sorte Prüfung ist die, die nichts zusichert: Sie meldet
grün, egal was der Code tut, und täuscht damit Sicherheit vor. Genau
zwei solche fanden sich im Ursprungsprojekt — beide mit der Absicht
„darf nicht werfen", beide ohne eine Zeile, die das festhält.

DER FEHLALARM AUS DEM ERSTEN WURF
=================================
Er nahm auch ``*_test.py`` als Prüf-Code und meldete prompt zwei
Verstösse in ``app/views/cameras/connection_test.py`` — einer ANSICHT.
``ConnectionTester.test_http_snapshot(ip, port, …)`` probiert
Schnappschuss-Pfade an einer Kamera durch; sie heisst nur so.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund

from ..base import BasisTest

KOPF = 'import unittest\n\n\nclass A(unittest.TestCase):\n'


def _lauf(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='sz_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    werkzeug = werkzeug_finden('szenarien')
    werkzeug.wurzel = lambda: ordner
    return werkzeug.pruefen()


def _gewichte(satz):
    aus = {}
    for b in satz.befunde:
        aus[b.gewicht] = aus.get(b.gewicht, 0) + 1
    return aus


class EineStummePruefungIstEinFehler(BasisTest):

    def test_ohne_zusicherung_wird_gemeldet(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        x = 1\n'
                      '        print(x)\n'})
        self.assertEqual(_gewichte(satz).get(Befund.FEHLER), 1)

    def test_der_grund_nennt_die_folge(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        x = 1\n'
                      '        print(x)\n'})
        self.assertIn('gruen', satz.befunde[0].warum)

    def test_ein_nacktes_assert_zaehlt(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        assert 1 == 1\n'})
        self.assertEqual(satz.befunde, [])

    def test_assertraises_zaehlt(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_wird_nicht_geloescht(self):\n'
                      '        with self.assertRaises(ValueError):\n'
                      '            int("x")\n'})
        self.assertEqual(satz.befunde, [])

    def test_eine_eigene_hilfsmethode_zaehlt(self):
        u"""`self._pruefe_dass(...)` sichert vielleicht zu — lieber ein
        Befund weniger als ein falscher."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        self._pruefe_dass(1)\n'})
        self.assertEqual(satz.befunde, [])


class EinNameSollDasVerhaltenNennen(BasisTest):

    def test_zu_kurzer_name_wird_gemeldet(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_grid(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(_gewichte(satz).get(Befund.HINWEIS), 1)

    def test_nichtssagender_name_wird_auch_gemeldet(self):
        u"""``test_basic`` ist lang genug und sagt trotzdem nichts."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_basic(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(_gewichte(satz).get(Befund.HINWEIS), 1)

    def test_ein_satz_als_name_ist_in_ordnung(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_nach_merge_erhalten(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertEqual(satz.befunde, [])

    def test_ein_stummer_test_mit_gutem_namen_wiegt_schwerer(self):
        u"""Der Name ist ein Hinweis, die fehlende Zusicherung ein Fehler."""
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_nach_merge_erhalten(self):\n'
                      '        pass\n'})
        self.assertEqual(_gewichte(satz), {Befund.FEHLER: 1})


class ProduktivcodeIstKeinePruefung(BasisTest):
    u"""Der Fehlalarm aus dem ersten Wurf, als Prüfung festgehalten."""

    ANSICHT = ('class ConnectionTester:\n'
               '    @classmethod\n'
               '    def test_http_snapshot(cls, ip, port):\n'
               '        return ip, port\n')

    def test_eine_ansicht_namens_connection_test_zaehlt_nicht(self):
        satz = _lauf({'app/views/connection_test.py': self.ANSICHT})
        self.assertEqual(satz.befunde, [],
                         'Eine Ansicht, deren Methoden test_ heissen, ist '
                         'keine Pruefung — sie heisst nur so.')

    def test_dieselbe_datei_unter_tests_zaehlt_schon(self):
        u"""Gegenprobe: Sonst prüft der Test darüber nur den Dateinamen."""
        satz = _lauf({'tests/connection_test.py': self.ANSICHT})
        self.assertEqual(_gewichte(satz).get(Befund.FEHLER), 1)


class DerKopfSagtDenAnteil(BasisTest):

    def test_ohne_befund_steht_es_ausdruecklich_da(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        self.assertTrue(True)\n'})
        self.assertTrue(any('Keine' in z for z in satz.kopf), satz.kopf)

    def test_die_zahl_der_stummen_steht_im_kopf(self):
        satz = _lauf({'tests/test_a.py': KOPF +
                      '    def test_person_bleibt_erhalten(self):\n'
                      '        pass\n'})
        self.assertTrue(any('ohne jede Zusicherung' in z for z in satz.kopf),
                        satz.kopf)


class JedesWerkzeugHatEinBeispielOderEinenGrund(BasisTest):
    u"""Die erste der drei BDD-Zusicherungen — als Prüfung, nicht als
    Vorsatz.

    ``anlassfall-check`` fährt die Beispiele; diese Prüfung hält fest,
    dass es überhaupt für jedes eines gibt. Am 26.08.2026 stand genau
    eines schweigend da — und ein Schweigen sieht aus wie Vergessen.
    """

    def test_keines_schweigt(self):
        from djangobase.skills import fixer, werkzeuge
        stumm = [w.slug for w in list(werkzeuge()) + list(fixer())
                 if getattr(w, 'anlassfall', None) is None
                 and not getattr(w, 'ohne_anlassfall_weil', '')]
        self.assertEqual(stumm, [],
                         'Diese Werkzeuge haben weder ein Beispiel noch einen '
                         'Grund, warum nicht: %s' % stumm)

    def test_die_gruende_sind_keine_leerformeln(self):
        from djangobase.skills import fixer, werkzeuge
        for w in list(werkzeuge()) + list(fixer()):
            grund = getattr(w, 'ohne_anlassfall_weil', '')
            if grund:
                with self.subTest(werkzeug=w.slug):
                    self.assertGreater(
                        len(grund), 30,
                        'Ein Grund in drei Worten ist keiner: %r' % grund)
