# -*- coding: utf-8 -*-
u"""Die Sperrklinke muss auch rot werden können.

DIE FRAGE (Edgar, 26.08.2026)
============================
    „wie kann es sein, dass die Code-Review-Tests alles grün melden, und du
     noch hunderte freier Funktionen hast usw??"

Weil niemand hinsah: Elf von dreizehn Skills-Prüfmodulen fahren gegen
gestellte Fälle, die zwei übrigen gegen ein leeres `MiniProjekt()`, und
kein Grundtest fuhr überhaupt ein Prüfwerkzeug. „Grün" hiess *die
Werkzeuge funktionieren*, nicht *das Projekt ist sauber*.

`GrundtestBefundgrenzen` schliesst die Lücke. Diese Datei prüft die
Sperrklinke selbst — denn eine Prüfung, die nur grün kann, wäre genau
derselbe Fehler noch einmal.
"""
from unittest import mock

from django.test import SimpleTestCase, override_settings

#: DAS MODUL, NICHT DIE KLASSE (26.08.2026)
#: =======================================
#: ``from djangobase.befundgrenzen import GrundtestBefundgrenzen`` holt die
#: Klasse in DIESEN Namensraum — und Djangos Test-Sammler nimmt jede
#: ``TestCase``-Klasse, die er hier findet. Der echte Grundtest lief damit
#: ein zweites Mal mit: aus elf Pruefungen wurden zwoelf, und die 19
#: Sekunden von `code-qualitaet` fielen doppelt an.
from djangobase import befundgrenzen as _grenzen

_zahl = _grenzen._zahl


def _klinke():
    u"""Die Sperrklinke als Exemplar — NICHT als Modulname.

    Auch ``X = modul.Grundtest...`` legt die Klasse wieder in diesen
    Namensraum, und der Sammler nimmt sie. Erst der Aufruf hier hält sie
    heraus.
    """
    return _grenzen.GrundtestBefundgrenzen(
        'test_kein_werkzeug_ueberschreitet_seine_grenze')


class _Befund:
    def __init__(self, gewicht):
        self.gewicht = gewicht


class _Satz:
    def __init__(self, befunde):
        self.befunde = befunde


class _NeuesWerkzeug:
    u"""Bauart ``BefundWerkzeug``: meldet über ``pruefen()``."""

    def __init__(self, gewichte):
        self._gewichte = gewichte

    def pruefen(self, **_a):
        return _Satz([_Befund(g) for g in self._gewichte])


class _AeltererTyp:
    u"""Bauart ``Werkzeug``: meldet über ``laufen()`` — kein ``pruefen``."""

    def __init__(self, zeilen):
        self._zeilen = zeilen

    def laufen(self, **_a):
        return mock.Mock(zeilen=self._zeilen)


def _lauf(grenzen, werkzeuge):
    u"""Die Sperrklinke mit gestellten Werkzeugen fahren.

    Liefert die Fehlermeldung — oder ``''``, wenn sie durchging.
    """
    fall = _klinke()
    with override_settings(DJANGOBASE={'befundgrenzen': grenzen}), \
            mock.patch('djangobase.skills.werkzeug_finden',
                       side_effect=lambda s: werkzeuge.get(s)):
        try:
            fall.test_kein_werkzeug_ueberschreitet_seine_grenze()
        except AssertionError as fehler:
            return str(fehler)
    return ''


class BeideBauartenWerdenGezaehlt(SimpleTestCase):
    u"""Ein Fixer heißt nicht ``laufen`` — dieselbe Falle wie zweimal zuvor."""

    def test_ein_befundwerkzeug_ueber_pruefen(self):
        gesamt, je = _zahl(_NeuesWerkzeug(['fehler', 'warnung', 'warnung']))
        self.assertEqual(gesamt, 3)
        self.assertEqual(je, {'fehler': 1, 'warnung': 2})

    def test_ein_aelteres_ueber_laufen(self):
        gesamt, je = _zahl(_AeltererTyp([{}, {}, {}, {}]))
        self.assertEqual(gesamt, 4)
        self.assertEqual(je, {})


class SieWirdRot(SimpleTestCase):

    def test_eine_zahl_darueber_ist_rot(self):
        meldung = _lauf({'x': 2}, {'x': _NeuesWerkzeug(['hinweis'] * 3)})
        self.assertIn('3 Befunde, erlaubt 2', meldung)

    def test_genau_auf_der_grenze_ist_gruen(self):
        self.assertEqual(
            _lauf({'x': 3}, {'x': _NeuesWerkzeug(['hinweis'] * 3)}), '')

    def test_darunter_ist_gruen(self):
        self.assertEqual(
            _lauf({'x': 9}, {'x': _NeuesWerkzeug(['hinweis'] * 3)}), '')

    def test_null_heisst_null(self):
        u"""`altlast` steht auf 0 — ein einziger Befund muss reichen."""
        meldung = _lauf({'altlast': 0}, {'altlast': _AeltererTyp([{}])})
        self.assertIn('1 Befunde, erlaubt 0', meldung)


class GrenzenJeGewicht(SimpleTestCase):
    u"""219 Hinweise sind bei `code-qualität` fast alle Rang C — rot
    werden soll es bei den schweren."""

    WERKZEUG = {'q': _NeuesWerkzeug(['fehler'] * 2 + ['warnung'] * 5
                                    + ['hinweis'] * 200)}

    def test_zu_viele_fehler_sind_rot(self):
        meldung = _lauf({'q': {'fehler': 1}}, self.WERKZEUG)
        self.assertIn('2 fehler, erlaubt 1', meldung)

    def test_die_hinweise_zaehlen_dann_nicht_mit(self):
        u"""Zweihundert Hinweise, aber die Grenze gilt den Fehlern."""
        self.assertEqual(
            _lauf({'q': {'fehler': 2, 'warnung': 5}}, self.WERKZEUG), '')

    def test_jedes_gewicht_wird_einzeln_geprueft(self):
        meldung = _lauf({'q': {'fehler': 2, 'warnung': 4}}, self.WERKZEUG)
        self.assertIn('5 warnung, erlaubt 4', meldung)


class WasSchiefgehenKann(SimpleTestCase):

    def test_ein_verschwundenes_werkzeug_ist_rot(self):
        u"""Sonst fällt eine Grenze still weg, sobald jemand ein Werkzeug
        umbenennt — und niemand merkt, dass nichts mehr geprüft wird."""
        meldung = _lauf({'gibtsnicht': 0}, {})
        self.assertIn('gibt es nicht', meldung)

    def test_ohne_grenzen_wird_uebersprungen_nicht_bestanden(self):
        u"""Ein übersprungener Test soll nie grün melden — er steht gelb.

        Grün hiesse hier „geprüft und sauber", und genau diese Verwechslung
        hat die Lücke überhaupt erst entstehen lassen.
        """
        fall = _klinke()
        with override_settings(DJANGOBASE={}):
            with self.assertRaises(Exception) as gefangen:
                fall.test_kein_werkzeug_ueberschreitet_seine_grenze()
        self.assertIn('SkipTest', type(gefangen.exception).__name__)
