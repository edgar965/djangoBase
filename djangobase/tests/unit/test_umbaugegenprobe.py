# -*- coding: utf-8 -*-
u"""Was hat ein Umbau an den Funktionsruempfen wirklich geaendert?

DER ANLASS (28.08.2026)
=======================
Beim Umbau freier Funktionen zu Klassen wurden im Projekt assistant zwei
Funktionsruempfe ERFUNDEN statt gelesen — Felder, die es am Modell gar
nicht gibt. Gefangen hat es ein vorhandener Test; bei einem Modul ohne
Test waere es durchgegangen.

WAS HIER GEPRUEFT WIRD
======================
Die Zerlegung und der Vergleich — ohne git. Die git-Aufrufe sind
umgelenkt: Ein Test, der ein echtes Repo anlegt und committet, pruefte
git, nicht dieses Werkzeug.

DIE WICHTIGSTE ZUSICHERUNG
==========================
Ein geaenderter Docstring ist KEINE Aenderung. Stuende er im Vergleich,
waere nach jedem Umbau jeder Rumpf verschieden — und die Meldung damit
wertlos.

BDD - GEGEBEN / DANN
====================
    EineDateiOhneAenderung     ... meldet nichts
    EinGeaenderterRumpf        ... genau der eine
    EinNeuerDocstring          ... ist keine Aenderung
    EinVerschwundenerRumpf     ... der gefaehrliche Fall
    EineKaputteFassung         ... meldet statt zu werfen
    KeinRepo                   ... sagt das, statt leer zu wirken
"""
import unittest
from unittest import mock

from djangobase.skills.umbaugegenprobe import Umbaugegenprobe


class _Probe(Umbaugegenprobe):
    u"""Eine Ableitung, deren git-Zugriffe aus einem Woerterbuch kommen."""

    def __init__(self, alt=None, neu=None, geaendert=(), geloescht=()):
        self._alt = alt or {}
        self._neu = neu or {}
        self._geaendert = list(geaendert)
        self._geloescht = list(geloescht)

    def _geaenderte_dateien(self):
        return self._geaendert, self._geloescht

    def _alter_stand(self, pfad):
        return self._alt.get(pfad)

    def wurzel(self):
        return _Wurzel(self._neu)


class _Wurzel:
    u"""Tut so, als laege der neue Stand auf der Platte."""

    def __init__(self, dateien):
        self._dateien = dateien

    def __truediv__(self, pfad):
        return _Datei(self._dateien.get(pfad))


class _Datei:
    def __init__(self, inhalt):
        self._inhalt = inhalt

    def read_text(self, encoding=None):
        if self._inhalt is None:
            raise OSError('gibt es nicht')
        return self._inhalt


_ALT = '''
def rechnen(a, b):
    """Alter Docstring."""
    return a + b


def zaehlen(x):
    return len(x)
'''


class EineDateiOhneAenderung(unittest.TestCase):
    u"""Gegeben: Die Datei steht in git wie auf der Platte."""

    def test_es_wird_nichts_gemeldet(self):
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': _ALT},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])

    def test_auch_bei_anderer_formatierung_nicht(self):
        u"""Der Vergleich laeuft ueber den Syntaxbaum. Zeilenumbrueche und
        Klammern aendern nichts am Rumpf — sonst meldete jeder
        PEP-8-Durchlauf das ganze Projekt."""
        neu = _ALT.replace('return a + b', 'return (\n        a\n        + b\n    )')
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])

    def test_und_bei_neuen_kommentaren_auch_nicht(self):
        neu = _ALT.replace('    return a + b',
                           '    # Erklaerung, die vorher fehlte\n    return a + b')
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])


class EinNeuerDocstring(unittest.TestCase):
    u"""Gegeben: Nur der Docstring wurde umgeschrieben.

    DIE WICHTIGSTE ZUSICHERUNG: Ein Umbau schreibt IMMER neue Docstrings.
    Zaehlten die mit, waere nach jedem Umbau jeder Rumpf verschieden und
    die Meldung wertlos.
    """

    def test_das_ist_keine_aenderung(self):
        neu = _ALT.replace('"""Alter Docstring."""',
                           '"""Ein ganz neuer, viel laengerer Text.\n\n    Mit Absatz.\n    """')
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])

    def test_ein_neu_hinzugekommener_ebenfalls_nicht(self):
        neu = _ALT.replace('def zaehlen(x):',
                           'def zaehlen(x):\n    """Vorher stand hier keiner."""')
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])

    def test_eine_funktion_die_NUR_einen_docstring_hat_wirft_nicht(self):
        u"""Ohne Ersatz-Rumpf waere die Liste leer und ``ast.unparse``
        bekaeme ein Modul ohne Koerper."""
        alt = 'def leer():\n    """Nur Text."""\n'
        neu = 'def leer():\n    """Anderer Text."""\n'
        erg = _Probe(alt={'m.py': alt}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])


class EinGeaenderterRumpf(unittest.TestCase):
    u"""Gegeben: Eine Funktion rechnet jetzt anders."""

    def setUp(self):
        neu = _ALT.replace('return a + b', 'return a * b')
        self.erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                          geaendert=['m.py']).laufen()

    def test_genau_eine_zeile(self):
        self.assertEqual(len(self.erg.zeilen), 1)

    def test_sie_nennt_die_funktion(self):
        self.assertEqual(self.erg.zeilen[0]['Rumpf'], 'rechnen')

    def test_und_die_neue_zeile(self):
        self.assertIn('a * b', self.erg.zeilen[0]['Was'])

    def test_die_unveraenderte_wird_nicht_gemeldet(self):
        self.assertNotIn('zaehlen',
                         [z['Rumpf'] for z in self.erg.zeilen])

    def test_auch_methoden_werden_erfasst(self):
        alt = 'class A:\n    def m(self):\n        return 1\n'
        neu = 'class A:\n    def m(self):\n        return 2\n'
        erg = _Probe(alt={'m.py': alt}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual([z['Rumpf'] for z in erg.zeilen], ['m'])


class EinVerschwundenerRumpf(unittest.TestCase):
    u"""Gegeben: Eine Funktion gibt es nach der Aenderung nicht mehr.

    DER GEFAEHRLICHE FALL: Entweder ist sie absichtlich in einer Klasse
    aufgegangen — dann steht sie unter neuem Namen da — oder sie ist
    verlorengegangen. Beides sieht in einem Diff gleich aus.
    """

    def setUp(self):
        neu = _ALT.replace('def zaehlen(x):\n    return len(x)\n', '')
        self.erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                          geaendert=['m.py']).laufen()

    def test_er_wird_gemeldet(self):
        self.assertEqual([z['Rumpf'] for z in self.erg.zeilen], ['zaehlen'])

    def test_mit_eigener_art(self):
        self.assertEqual(self.erg.zeilen[0]['Art'], 'verschwunden')

    def test_und_der_hinweis_nennt_die_zahl(self):
        self.assertIn('1 Ruempfe', self.erg.hinweis)

    def test_ohne_verschwundene_kein_hinweis(self):
        neu = _ALT.replace('return a + b', 'return a * b')
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': neu},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.hinweis, '')

    def test_eine_geloeschte_datei_steht_als_ganzes_da(self):
        erg = _Probe(geloescht=['weg.py']).laufen()
        self.assertEqual(erg.zeilen[0]['Art'], 'geloescht')
        self.assertEqual(erg.zeilen[0]['Rumpf'], '(ganze Datei)')


class EineNeueDatei(unittest.TestCase):
    u"""Gegeben: Die Datei gab es vorher nicht.

    Beim Umbau ist das der Normalfall — die Klasse kommt in eine neue
    Datei. Ein Vergleich ist da nicht moeglich und auch kein Befund.
    """

    def test_sie_wird_nicht_gemeldet(self):
        erg = _Probe(alt={}, neu={'neu.py': _ALT}, geaendert=['neu.py']).laufen()
        self.assertEqual(erg.zeilen, [])


class EineKaputteFassung(unittest.TestCase):
    u"""Gegeben: Eine der beiden Fassungen laesst sich nicht lesen."""

    def test_ein_syntaxfehler_wird_gemeldet_nicht_geworfen(self):
        erg = _Probe(alt={'m.py': _ALT}, neu={'m.py': 'def ('},
                     geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen[0]['Art'], 'unlesbar')

    def test_eine_fehlende_datei_auf_der_platte_wirft_nicht(self):
        u"""Sie kann zwischen git-Abfrage und Lesen verschwinden."""
        erg = _Probe(alt={'m.py': _ALT}, neu={}, geaendert=['m.py']).laufen()
        self.assertEqual(erg.zeilen, [])


class KeinRepo(unittest.TestCase):
    u"""Gegeben: git laeuft nicht, oder das Verzeichnis ist kein Repo.

    Ein leeres Ergebnis waere hier die falsche Antwort: Es saehe aus wie
    „nichts gefunden" und ist „nicht nachgesehen".
    """

    def test_das_wird_gesagt(self):
        with mock.patch.object(Umbaugegenprobe, '_git', return_value=None):
            erg = Umbaugegenprobe().laufen()
        self.assertIn('git', erg.zusammenfassung)
        self.assertTrue(erg.hinweis)

    def test_ein_sauberer_arbeitsbaum_sagt_etwas_anderes(self):
        erg = _Probe().laufen()
        self.assertIn('Keine geaenderte', erg.zusammenfassung)
        self.assertEqual(erg.hinweis, '')


class EinMassenumbau(unittest.TestCase):
    u"""Gegeben: Sehr viele geaenderte Dateien.

    Nach einem projektweiten Formatierungslauf ist die Liste kein Befund
    mehr, sondern Rauschen — und das Werkzeug liest dann Hunderte Dateien
    aus git.
    """

    def test_ab_einer_grenze_wird_abgewunken(self):
        viele = ['d%d.py' % i for i in range(Umbaugegenprobe.MAX_DATEIEN + 1)]
        erg = _Probe(geaendert=viele).laufen()
        self.assertEqual(erg.zeilen, [])
        self.assertIn('zu viele', erg.zusammenfassung)

    def test_knapp_darunter_noch_nicht(self):
        viele = ['d%d.py' % i for i in range(Umbaugegenprobe.MAX_DATEIEN)]
        erg = _Probe(geaendert=viele).laufen()
        self.assertNotIn('zu viele', erg.zusammenfassung)


class DasWerkzeugSelbst(unittest.TestCase):
    u"""Gegeben: Es steht im Werkzeugkasten."""

    def test_es_ist_registriert(self):
        from djangobase.skills import werkzeug_finden
        self.assertIsNotNone(werkzeug_finden('umbau-gegenprobe'))

    def test_es_sagt_warum_es_keinen_anlassfall_hat(self):
        u"""Ein Werkzeug ohne beides gilt als blind."""
        self.assertTrue(Umbaugegenprobe.ohne_anlassfall_weil)
        self.assertIsNone(Umbaugegenprobe.anlassfall)
