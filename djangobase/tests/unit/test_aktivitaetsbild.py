# -*- coding: utf-8 -*-
u"""Aktivitaetsbild — ist die Schrift neben den Bloecken lesbar?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „mach mir die grafische Ausgabe von vorher, kein Quelltext, aber
     sowas in der Richtung des Screenshots"
    „mach die schriften noch lesbar (neben den Blöcken)"

Der erste Wurf sah aus wie die Vorlage und war trotzdem unbrauchbar:
``[not os.path.isdir(…)]`` lag mitten auf der Raute, ``[sonst]`` auf dem
Pfeil, und die Zeilennummer ``166`` klebte an beiden.

Ein Bild, dessen Beschriftung man nicht lesen kann, beantwortet die
Frage nicht, um die es geht. Diese Pruefungen halten die vier
Korrekturen fest — sie sind alle GEOMETRIE, also nachrechenbar:

    Hof        weisser Rand unter der Schrift, damit Linien sie nicht
               durchschneiden
    Platz      eine Marke wird auf die verfuegbare Breite gekuerzt
    Vollstand  der volle Text bleibt als Tooltip erhalten
    Abstand    Zeilennummern stehen links, nie an der Achse

Sie gehoeren zu Kriterium 20 („Dokumentation").
"""
import ast
import re

from djangobase.umbau.ablauf import Ablauf
from djangobase.umbau.aktivitaetsbild import KASTEN_B, SPUR, Aktivitaetsbild
from djangobase.umbau.beschriftung import Beschriftung

from ..base import BasisTest


class _Bezug:
    def __init__(self, quelle):
        self.knoten = ast.parse(quelle).body[0]
        self.anzeige = 'A.f'
        self.modul = 'probe'
        self.zeile = 1


def _bild(quelle):
    lauf = Ablauf(_Bezug(quelle)).lesen()
    return Aktivitaetsbild(lauf, lambda k: Beschriftung.fuer(k))


VERZWEIGT = ('def f(self):\n'
             '    if not os.path.isdir(self.zwischenlager_pfad_lang):\n'
             '        return 0\n'
             '    self.aufraeumen()\n')


class JedeBeschriftungHatEinenWeissenHof(BasisTest):
    u"""Ohne ihn schneidet jede Linie die Schrift, die ueber ihr liegt."""

    def test_marken_und_nummern_tragen_einen_rand(self):
        svg = _bild(VERZWEIGT).svg()
        self.assertIn('paint-order:stroke', svg)
        self.assertIn('stroke:#fff', svg)


class EineMarkePasstInDenPlatzDenSieHat(BasisTest):
    u"""``[not os.path.isdir(self.zwischenlager_pfad_lang)]`` ist laenger
    als die Spur breit ist. Ungekuerzt lief sie ueber die Raute."""

    def setUp(self):
        self.svg = _bild(VERZWEIGT).svg()
        self.marken = re.findall(
            r'<text class="ak-m"[^>]*>(?:<title>[^<]*</title>)?([^<]*)</text>',
            self.svg)

    def test_es_gibt_ueberhaupt_eine_marke(self):
        self.assertTrue(self.marken, 'Ohne Marke sagt die Raute nicht, '
                                     'wofuer sie sich entscheidet.')

    def test_keine_marke_ist_breiter_als_die_spur(self):
        u"""Grob gerechnet 6 Punkte je Zeichen bei 11er Schrift."""
        for marke in self.marken:
            self.assertLessEqual(len(marke) * 6, SPUR,
                                 'zu lang: %r' % marke)

    def test_der_volle_text_bleibt_als_tooltip(self):
        u"""Kuerzen ist noetig — die Bedingung ganz zu verlieren waere zu
        teuer. Wer genau wissen will, was geprueft wird, faehrt drueber."""
        self.assertIn('<title>', self.svg)
        self.assertIn('isdir', self.svg)


class DieZeilennummerStehtLinks(BasisTest):
    u"""Rechts lag sie genau auf der Achse und der naechsten Raute."""

    def test_die_nummer_sitzt_in_der_linken_haelfte_des_kastens(self):
        bild = _bild(VERZWEIGT).anordnen()
        svg = bild.svg()
        kasten = [t for t in bild.teile if t.art in ('kasten', 'ausgang')][0]
        stelle = re.search(r'<text class="ak-z" x="(\d+)"', svg)
        self.assertIsNotNone(stelle)
        self.assertLess(int(stelle.group(1)), kasten.x,
                        'Die Nummer steht rechts und damit an der Achse.')


class ZwischenNebenspurUndAchseIstPlatz(BasisTest):
    u"""Die Marke steht in dieser Luecke — sie darf nicht null sein."""

    def test_die_luecke_traegt_mehr_als_ein_paar_zeichen(self):
        luecke = SPUR - KASTEN_B / 2.0 - 22
        self.assertGreater(luecke, 100,
                           'Bei 43 Punkten stand „[ja]" als '
                           'Buchstabensalat zwischen Kasten und Raute.')


class DasBildBringtSeinenGrundMit(BasisTest):
    u"""Als STIL, nicht als Attribut: Ein ``fill="…"`` verliert gegen jede
    CSS-Regel des Wirtsprojekts, und die Flaeche blieb dunkel."""

    def test_ein_weisses_rechteck_deckt_das_ganze_bild(self):
        bild = _bild(VERZWEIGT).anordnen()
        svg = bild.svg()
        treffer = re.search(
            r'<rect x="0" y="0" width="(\d+)" height="(\d+)" '
            r'style="fill:#ffffff"', svg)
        self.assertIsNotNone(treffer, 'Kein weisser Grund im Bild.')
        self.assertEqual(int(treffer.group(1)), bild.breite)
        self.assertEqual(int(treffer.group(2)), bild.hoehe)


class DerTextIstProsaUndKeinQuelltext(BasisTest):
    u"""Der eigentliche Unterschied zur Workflow-Seite."""

    def test_aus_einem_methodennamen_werden_woerter(self):
        self.assertEqual(Beschriftung('_install_signal_handlers').satz(),
                         'install signal handlers')

    def test_eine_abkuerzung_bleibt_ein_wort(self):
        u"""Sonst wurde aus ``SUCCESS`` ein „S U C C E S S"."""
        self.assertEqual(Beschriftung('SUCCESS').satz(), 'SUCCESS')

    def test_der_empfaenger_steht_als_gegenstand_davor(self):
        self.assertEqual(Beschriftung('prepare', None, 'service').satz(),
                         'service: prepare')

    def test_self_ist_kein_gegenstand(self):
        u"""``self`` steht in jedem zweiten Kasten und waere Rauschen."""
        self.assertEqual(Beschriftung('tun', None, 'self').satz(), 'tun')

    def test_ein_docstring_schlaegt_den_namen(self):
        quelle = ('def helfen(self):\n'
                  '    """Raeumt die Zwischenablage auf."""\n'
                  '    pass\n')

        class Bezug:
            knoten = ast.parse(quelle).body[0]
        self.assertEqual(Beschriftung('helfen', Bezug()).satz(),
                         'Raeumt die Zwischenablage auf')

    def test_ein_docstring_der_mit_einer_ueberschrift_anfaengt_zaehlt_nicht(self):
        u"""``>>>`` oder ``===`` beschreiben keine Handlung."""
        quelle = ('def helfen(self):\n'
                  '    """>>> helfen()"""\n'
                  '    pass\n')

        class Bezug:
            knoten = ast.parse(quelle).body[0]
        self.assertEqual(Beschriftung('helfen', Bezug()).satz(), 'helfen')


class AusgabeIstKeineHandlung(BasisTest):
    u"""Im ersten Bild stand neunmal „stdout: write"."""

    def test_eine_schreibzeile_erzeugt_keinen_kasten(self):
        lauf = Ablauf(_Bezug(
            'def f(self):\n'
            "    self.stdout.write(self.style.SUCCESS('fertig'))\n"
            '    self.arbeiten()\n')).lesen()
        self.assertEqual([k.aufruf for k in lauf.knoten], ['arbeiten'])
