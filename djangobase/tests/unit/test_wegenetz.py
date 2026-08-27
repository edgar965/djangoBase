# -*- coding: utf-8 -*-
u"""Wegenetz — loest es Aufrufe auf, ohne zu raten?

DIE FRAGE DAHINTER (Edgar, 27.08.2026)
======================================
    „das bild soll aber nach durchlesen des Codes gezeichnet werden"

Ein Bild aus dem Code ist nur dann etwas wert, wenn jede Kante darin
belegbar ist. Diese Pruefungen halten genau das fest — und zwar von
BEIDEN Seiten: Was belegbar ist, MUSS verbunden werden; was mehrdeutig
ist, DARF NICHT verbunden werden.

Die zweite Haelfte ist die wichtigere. Ein Werkzeug, das im Zweifel raet,
liefert ein Bild, das genauso aussieht wie ein richtiges.

Diese Pruefungen gehoeren zu Kriterium 20 („Dokumentation").
"""
import tempfile
from pathlib import Path

from djangobase.umbau.einstiege import Einstieg
from djangobase.umbau.wegenetz import Verzeichnis, Wegsucher

from ..base import BasisTest


def _abzug(dateien):
    u"""Ein kleines Projekt auf der Platte, damit der AST etwas zu lesen hat."""
    ordner = Path(tempfile.mkdtemp(prefix='wn_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return ordner


def _weg(dateien, klasse, methode, tiefe=5):
    ordner = _abzug(dateien)
    verzeichnis = Verzeichnis(ordner).lesen()
    start = verzeichnis.in_klasse(klasse, methode)
    einstieg = Einstieg('probe', 'befehl', methode, ordner / 'a.py', 1)
    return Wegsucher(verzeichnis, tiefe=tiefe).verfolgen(einstieg, start)


class EinEindeutigerMethodennameWirdVerbunden(BasisTest):
    u"""Traegt im ganzen Projekt genau eine Klasse den Namen, ist klar,
    wer gemeint ist — auch ohne Typangabe."""

    QUELLE = {'a.py':
              'class Lager:\n'
              '    def einlagern(self):\n'
              '        return 1\n'
              '\n\n'
              'class Dienst:\n'
              '    def arbeiten(self):\n'
              '        self.irgendwas.einlagern()\n'}

    def test_der_weg_erreicht_die_gemeinte_klasse(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertIn('Lager', weg.klassen)

    def test_und_meldet_dafuer_kein_offenes_ende(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertNotIn('einlagern', weg.offen)


class EinMehRDEUTIGERNameWirdNichtVerbunden(BasisTest):
    u"""Die Kernzusage: Im Zweifel lieber eine Luecke als eine erfundene
    Kante. Zwei Klassen tragen ``start`` — welche gemeint ist, steht
    nirgends, also wird nichts verbunden."""

    QUELLE = {'a.py':
              'class Motor:\n'
              '    def start(self):\n'
              '        return 1\n'
              '\n\n'
              'class Pumpe:\n'
              '    def start(self):\n'
              '        return 2\n'
              '\n\n'
              'class Dienst:\n'
              '    def arbeiten(self):\n'
              '        self.dings.start()\n'}

    def test_keine_der_beiden_klassen_landet_im_weg(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertNotIn('Motor', weg.klassen)
        self.assertNotIn('Pumpe', weg.klassen)

    def test_die_luecke_wird_gemeldet_statt_verschwiegen(self):
        u"""Sonst sieht ein unvollstaendiges Bild aus wie ein vollstaendiges."""
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertIn('start', weg.offen)


class EinFeldMitBekanntemTypLoestDenNamenDochAuf(BasisTest):
    u"""``self.motor = Motor()`` steht im Code — damit ist ``self.motor.
    start()`` eindeutig, obwohl der Name ``start`` es nicht ist.

    Ohne diesen Schritt fehlte in CamTrack die Aufnahme-Kette: Sie
    besteht fast nur aus solchen Weitergaben.
    """

    QUELLE = {'a.py':
              'class Motor:\n'
              '    def start(self):\n'
              '        return 1\n'
              '\n\n'
              'class Pumpe:\n'
              '    def start(self):\n'
              '        return 2\n'
              '\n\n'
              'class Dienst:\n'
              '    def __init__(self):\n'
              '        self.motor = Motor()\n'
              '\n'
              '    def arbeiten(self):\n'
              '        self.motor.start()\n'}

    def test_der_weg_erreicht_die_klasse_aus_dem_feld(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertIn('Motor', weg.klassen)

    def test_und_nicht_die_andere_mit_gleichem_methodennamen(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertNotIn('Pumpe', weg.klassen)


class EineOertlicheZuweisungZaehltGenauso(BasisTest):
    u"""``p = Pumpe()`` im selben Rumpf ist derselbe Beleg wie ein Feld."""

    QUELLE = {'a.py':
              'class Pumpe:\n'
              '    def start(self):\n'
              '        return 2\n'
              '\n\n'
              'class Motor:\n'
              '    def start(self):\n'
              '        return 1\n'
              '\n\n'
              'class Dienst:\n'
              '    def arbeiten(self):\n'
              '        p = Pumpe()\n'
              '        p.start()\n'}

    def test_der_weg_erreicht_die_oertlich_erzeugte_klasse(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertIn('Pumpe', weg.klassen)


class PruefcodeGehoertNichtInEinenWeg(BasisTest):
    u"""Ein Doppelgaenger aus dem Pruefordner traegt oft einen eindeutigen
    Namen — gerufen wird er trotzdem nie von einem Dienst.

    Gemessen am 27.08.2026 endete die CamTrack-Aufnahmekette bei sechs
    Methoden von ``_FakeCv2`` aus ``tests/unit/test_motion_gate.py``.
    """

    QUELLE = {'a.py':
              'class Dienst:\n'
              '    def arbeiten(self):\n'
              '        self.x.weichzeichnen()\n',
              'tests/test_b.py':
              'class FalscherCv2:\n'
              '    def weichzeichnen(self):\n'
              '        return 1\n'}

    def test_der_doppelgaenger_aus_tests_bleibt_draussen(self):
        weg = _weg(self.QUELLE, 'Dienst', 'arbeiten')
        self.assertNotIn('FalscherCv2', weg.klassen)


class DieTiefeBegrenztDenWeg(BasisTest):
    u"""Ohne Grenze laufen alle Wege bei den Hilfsfunktionen zusammen und
    jedes Bild sieht aus wie jedes andere."""

    QUELLE = {'a.py':
              'class A:\n'
              '    def eins(self):\n'
              '        self.x.zwei()\n'
              '\n\n'
              'class B:\n'
              '    def zwei(self):\n'
              '        self.y.drei()\n'
              '\n\n'
              'class C:\n'
              '    def drei(self):\n'
              '        self.z.vier()\n'
              '\n\n'
              'class D:\n'
              '    def vier(self):\n'
              '        return 4\n'}

    def test_bei_tiefe_eins_kommt_nur_der_erste_schritt_mit(self):
        weg = _weg(self.QUELLE, 'A', 'eins', tiefe=1)
        self.assertIn('B', weg.klassen)
        self.assertNotIn('C', weg.klassen)

    def test_bei_voller_tiefe_kommt_der_ganze_weg(self):
        weg = _weg(self.QUELLE, 'A', 'eins', tiefe=5)
        self.assertIn('D', weg.klassen)


class JederSchrittZeigtAufEineStelleImQuelltext(BasisTest):
    u"""Ohne Datei und Zeile waere der Kasten eine Behauptung."""

    def test_datei_und_zeile_stehen_an_jedem_schritt(self):
        weg = _weg({'a.py': 'class A:\n'
                            '    def eins(self):\n'
                            '        return 1\n'}, 'A', 'eins')
        for schritt in weg.schritte:
            self.assertTrue(schritt.bezug.datei.exists())
            self.assertGreater(schritt.bezug.zeile, 0)
