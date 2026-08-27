# -*- coding: utf-8 -*-
u"""Ablauf — steht im Bild dieselbe Reihenfolge wie im Quelltext?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „das ist auch nicht verständlich, ich brauche einen klaren Workflow,
     was in welcher Reihenfolge gemacht wird. Kannst du nicht sowas wie
     ein Ablaufdiagramm machen mit Entscheidungsbäumen?"

Berechtigt: Die Landkarte ordnet nach ENTFERNUNG vom Einstieg. Zwei
Kaesten nebeneinander sagen darin nicht, welcher zuerst kommt, und eine
Bedingung sieht aus wie ein Aufruf.

Diese Pruefungen halten fest, was ein Ablauf leisten muss:

    Reihenfolge   was oben steht, kommt zuerst
    Verzweigung   eine Frage traegt ihre beiden Zweige
    Ausgang       return und raise sind ein ENDE, kein Schritt
    Treue         nichts wird erfunden, nichts faellt still weg

Sie gehoeren zu Kriterium 20 („Dokumentation").
"""
import ast

from djangobase.umbau.ablauf import Ablauf
from djangobase.umbau.ablaufbild import Ablaufbild

from ..base import BasisTest


class _Bezug:
    u"""Ein Bezug ohne Verzeichnis — mehr braucht der Ablauf nicht."""

    def __init__(self, quelle, name='A.f'):
        self.knoten = ast.parse(quelle).body[0]
        self.anzeige = name
        self.modul = 'probe'
        self.zeile = 1


def _lauf(quelle):
    return Ablauf(_Bezug(quelle)).lesen()


def _arten(knoten):
    return [k.art for k in knoten]


class DieReihenfolgeIstDieDesQuelltextes(BasisTest):
    u"""Die Zusage, um die es geht."""

    QUELLE = ('def f(self):\n'
              '    self.eins()\n'
              '    self.zwei()\n'
              '    self.drei()\n')

    def test_die_schritte_stehen_in_der_reihenfolge_des_codes(self):
        lauf = _lauf(self.QUELLE)
        self.assertEqual([k.text for k in lauf.knoten],
                         ['self.eins()', 'self.zwei()', 'self.drei()'])

    def test_jeder_schritt_nennt_seine_zeile(self):
        u"""Ohne Zeilennummer waere der Kasten eine Behauptung."""
        lauf = _lauf(self.QUELLE)
        self.assertEqual([k.zeile for k in lauf.knoten], [2, 3, 4])


class EineFrageTraegtBeideZweige(BasisTest):
    u"""Der Entscheidungsbaum, nach dem gefragt war."""

    QUELLE = ('def f(self):\n'
              '    if self.geht():\n'
              '        self.weiter()\n'
              '    else:\n'
              '        self.abbrechen()\n')

    def test_aus_dem_if_wird_eine_frage(self):
        lauf = _lauf(self.QUELLE)
        self.assertEqual(_arten(lauf.knoten), ['frage'])

    def test_die_bedingung_steht_im_kasten(self):
        self.assertEqual(_lauf(self.QUELLE).knoten[0].text, 'self.geht()')

    def test_beide_zweige_haengen_daran(self):
        frage = _lauf(self.QUELLE).knoten[0]
        self.assertEqual([k.text for k in frage.ja], ['self.weiter()'])
        self.assertEqual([k.text for k in frage.nein], ['self.abbrechen()'])


class EinAusgangIstKeinSchritt(BasisTest):
    u"""``return`` und ``raise`` beenden den Ablauf — sie tun nichts."""

    def test_return_wird_ein_ende(self):
        lauf = _lauf('def f(self):\n    return self.wert()\n')
        self.assertEqual(_arten(lauf.knoten), ['ende'])

    def test_raise_wird_auch_ein_ende(self):
        lauf = _lauf('def f(self):\n    raise Fehler("weg")\n')
        self.assertEqual(_arten(lauf.knoten), ['ende'])

    def test_ein_frueher_ausstieg_haengt_am_ja_zweig(self):
        u"""Das haeufigste Muster in echtem Code: pruefen, dann raus."""
        lauf = _lauf('def f(self):\n'
                     '    if not self.geht():\n'
                     '        return None\n'
                     '    self.arbeiten()\n')
        frage, danach = lauf.knoten
        self.assertEqual(_arten(frage.ja), ['ende'])
        self.assertEqual(danach.text, 'self.arbeiten()')


class SchleifeUndAbsicherungTragenIhrenRumpf(BasisTest):
    u"""Was mehrfach laeuft und was schiefgehen darf."""

    def test_aus_dem_for_wird_eine_schleife(self):
        lauf = _lauf('def f(self):\n'
                     '    for kamera in self.kameras():\n'
                     '        self.pruefen(kamera)\n')
        schleife = lauf.knoten[0]
        self.assertEqual(schleife.art, 'schleife')
        self.assertEqual([k.text for k in schleife.rumpf],
                         ['self.pruefen(kamera)'])

    def test_das_finally_steht_getrennt_vom_rumpf(self):
        u"""„danach immer" ist etwas anderes als „im Normalfall" — im Bild
        muss man das sehen."""
        lauf = _lauf('def f(self):\n'
                     '    try:\n'
                     '        self.arbeiten()\n'
                     '    finally:\n'
                     '        self.aufraeumen()\n')
        sicher = lauf.knoten[0]
        self.assertEqual(sicher.art, 'absicherung')
        self.assertEqual([k.text for k in sicher.rumpf], ['self.arbeiten()'])
        self.assertEqual([k.text for k in sicher.immer],
                         ['self.aufraeumen()'])


class NICHTSWirdErfunden(BasisTest):
    u"""Die Gegenrichtung — ein Ablauf, der mehr zeigt als dasteht, ist
    schlimmer als keiner."""

    def test_eine_zeile_ohne_aufruf_erzeugt_keinen_kasten(self):
        u"""``x = 1`` ist kein Ablaufschritt."""
        lauf = _lauf('def f(self):\n    x = 1\n    self.tun()\n')
        self.assertEqual([k.text for k in lauf.knoten], ['self.tun()'])

    def test_ein_leerer_rumpf_ergibt_nichts(self):
        self.assertEqual(_lauf('def f(self):\n    pass\n').knoten, [])


class AusJedemAblaufWirdEinBild(BasisTest):
    u"""Ein Ablauf ohne Bild waere wieder eine Liste."""

    QUELLE = ('def f(self):\n'
              '    if self.geht():\n'
              '        return self.wert()\n'
              '    self.tun()\n')

    def test_es_kommt_ein_svg_heraus(self):
        svg = Ablaufbild(_lauf(self.QUELLE)).svg()
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.rstrip().endswith('</svg>'))

    def test_die_frage_wird_als_raute_gezeichnet(self):
        u"""Rechteck und Raute sind im Bild der Unterschied zwischen
        „hier passiert etwas" und „hier entscheidet sich etwas"."""
        self.assertIn('<polygon', Ablaufbild(_lauf(self.QUELLE)).svg())

    def test_jeder_knoten_bekommt_genau_einen_kasten(self):
        bild = Ablaufbild(_lauf(self.QUELLE)).anordnen()
        self.assertEqual(len(bild.kaesten), 3)   # Frage, Ende, Schritt

    def test_der_ja_zweig_steht_eingerueckt(self):
        u"""Die Einrückung IST die Aussage: Was weiter rechts steht,
        gehört zur Frage darüber."""
        bild = Ablaufbild(_lauf(self.QUELLE)).anordnen()
        frage = [k for k in bild.kaesten if k.knoten.art == 'frage'][0]
        ende = [k for k in bild.kaesten if k.knoten.art == 'ende'][0]
        self.assertGreater(ende.x, frage.x)

    def test_und_der_schritt_danach_wieder_auf_hoehe_der_frage(self):
        u"""Die Zusammenführung: Nach dem Zweig geht es links weiter."""
        bild = Ablaufbild(_lauf(self.QUELLE)).anordnen()
        frage = [k for k in bild.kaesten if k.knoten.art == 'frage'][0]
        danach = [k for k in bild.kaesten if k.knoten.art == 'schritt'][0]
        self.assertEqual(danach.x, frage.x)
        self.assertGreater(danach.y, frage.y)
