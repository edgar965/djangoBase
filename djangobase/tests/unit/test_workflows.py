# -*- coding: utf-8 -*-
u"""Workflows — werden sie gefunden, richtig sortiert und gezeichnet?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „die workflows sollst du aber ermitteln, schau dir jede Seite durch
     und ermittle 20-50 Workflows"
    „ordne sie an nach Komplexität (Anzahl der beteiligten Klassen)"

Drei Zusagen stehen hier zur Pruefung:

    gefunden   Routen, Befehle und Faeden werden ohne Liste entdeckt
    sortiert   der Weg mit mehr beteiligten Klassen steht weiter oben
    gezeichnet aus jedem Weg wird ein SVG mit Kaesten und Kanten

Diese Pruefungen gehoeren zu Kriterium 20 („Dokumentation").
"""
import tempfile
from pathlib import Path

from djangobase.umbau.einstiege import Einstiegssucher
from djangobase.umbau.workflowbild import Workflowbild
from djangobase.umbau.workflows import Workflowliste

from ..base import BasisTest

#: Ein Miniatur-Projekt: eine Route, ein Befehl, ein Faden — und ein Weg,
#: der laenger ist als der andere.
ABZUG = {
    'urls.py':
        'from django.urls import path\n'
        'from . import views\n'
        '\n'
        'urlpatterns = [\n'
        "    path('gross/', views.gross, name='gross'),\n"
        "    path('klein/', views.klein, name='klein'),\n"
        ']\n',
    'views.py':
        'def gross(request):\n'
        '    Erst().eins()\n'
        '\n\n'
        'def klein(request):\n'
        '    return 1\n',
    'kette.py':
        'class Erst:\n'
        '    def eins(self):\n'
        '        self.x.zwei()\n'
        '\n\n'
        'class Zweit:\n'
        '    def zwei(self):\n'
        '        self.y.drei()\n'
        '\n\n'
        'class Dritt:\n'
        '    def drei(self):\n'
        '        self.z.vier()\n'
        '\n\n'
        'class Viert:\n'
        '    def vier(self):\n'
        '        self.w.fuenf()\n'
        '\n\n'
        'class Fuenft:\n'
        '    def fuenf(self):\n'
        '        return 5\n',
    'management/commands/machwas.py':
        'class Command:\n'
        '    def handle(self, *a, **k):\n'
        '        from ..kette import Erst\n'
        '        Erst().eins()\n',
    'live/schleife.py':
        'class Dauerlauf:\n'
        '    def run(self):\n'
        '        return 1\n',
}


def _abzug(dateien=None):
    ordner = Path(tempfile.mkdtemp(prefix='wf_'))
    for name, inhalt in (dateien or ABZUG).items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return ordner


class EinstiegeWerdenGefundenStattAufgeschrieben(BasisTest):
    u"""Eine Liste von Hand waere beim naechsten neuen Endpunkt falsch."""

    def setUp(self):
        self.alle = Einstiegssucher(_abzug()).alle()

    def test_eine_route_wird_gefunden(self):
        self.assertIn('gross/', [e.adresse for e in self.alle])

    def test_ein_management_befehl_wird_gefunden(self):
        self.assertIn('manage.py machwas', [e.adresse for e in self.alle])

    def test_eine_dauerschleife_wird_gefunden(self):
        u"""Der Teil, den man beim Lesen der Routen gerade NICHT findet."""
        self.assertIn('Dauerlauf.run', [e.adresse for e in self.alle])

    def test_die_route_kennt_ihre_stelle_im_quelltext(self):
        route = [e for e in self.alle if e.adresse == 'gross/'][0]
        self.assertTrue(str(route.datei).endswith('urls.py'))
        self.assertGreater(route.zeile, 0)


class DieListeIstNachKomplexitaetSortiert(BasisTest):
    u"""Nicht nach Name und nicht nach Adresse: nach der Zahl der
    beteiligten Klassen. Das ist das Mass dafuer, wie viel man verstehen
    muss, um diesen einen Vorgang zu aendern."""

    def setUp(self):
        # Grenze 0, damit AUCH der kuerzeste Weg in der Liste steht: Hier
        # wird die Reihenfolge geprueft, nicht das Aussieben.
        self.liste = Workflowliste(_abzug(), grenze=0).lesen()

    def test_der_weg_mit_den_meisten_klassen_steht_oben(self):
        zahlen = [len(w.klassen) for w in self.liste.wege]
        self.assertEqual(zahlen, sorted(zahlen, reverse=True))

    def test_die_lange_kette_steht_vor_der_kurzen(self):
        titel = [w.einstieg.titel for w in self.liste.wege]
        self.assertLess(titel.index('/gross/'), titel.index('/klein/'))


class EinHandgriffIstKeinWorkflow(BasisTest):
    u"""Eine Seite, die nur eine Vorlage ausliefert, erzaehlt nichts.
    Ohne diese Grenze stuenden dreihundert Eintraege in der Liste."""

    def test_die_kurze_route_faellt_unter_der_grenze_heraus(self):
        liste = Workflowliste(_abzug(), grenze=3).lesen()
        self.assertNotIn('/klein/', [w.einstieg.titel for w in liste.wege])

    def test_und_wird_als_verworfen_gezaehlt_statt_verschwiegen(self):
        liste = Workflowliste(_abzug(), grenze=3).lesen()
        self.assertGreater(liste.verworfen, 0)


class ZweiBefehleMitGleichemHandleBleibenZweiWorkflows(BasisTest):
    u"""Alle Management-Befehle heissen ``handle``.

    Wer danach entdoppelt, behaelt einen und wirft den Rest weg — genau so
    verschwand am 27.08.2026 die CamTrack-Aufnahmekette mit 35 beteiligten
    Klassen hinter ``process_faces``.
    """

    def test_beide_befehle_stehen_in_der_liste(self):
        dateien = dict(ABZUG)
        dateien['management/commands/nochwas.py'] = (
            'class Command:\n'
            '    def handle(self, *a, **k):\n'
            '        from ..kette import Erst\n'
            '        Erst().eins()\n')
        liste = Workflowliste(_abzug(dateien), grenze=1).lesen()
        titel = [w.einstieg.titel for w in liste.wege]
        self.assertIn('manage.py machwas', titel)
        self.assertIn('manage.py nochwas', titel)


class JederWegLaesstSichZeichnen(BasisTest):
    u"""Ein Weg ohne Bild waere eine Liste — davon gibt es genug."""

    def setUp(self):
        liste = Workflowliste(_abzug(), grenze=1).lesen()
        self.weg = liste.wege[0]
        self.bild = Workflowbild(self.weg)

    def test_es_kommt_ein_svg_heraus(self):
        svg = self.bild.svg()
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.rstrip().endswith('</svg>'))

    def test_jeder_schritt_bekommt_einen_kasten(self):
        self.bild.anordnen()
        self.assertEqual(len(self.bild.karten), len(self.weg.schritte))

    def test_das_bild_ist_breiter_als_hoch(self):
        u"""Ein Streifen von 966 mal 4214 Punkten war der erste Wurf —
        man scrollte senkrecht und sah nie zwei Spalten zugleich."""
        self.bild.anordnen()
        self.assertGreaterEqual(self.bild.breite, self.bild.hoehe)

    def test_der_einstieg_ist_im_bild_hervorgehoben(self):
        self.assertIn('wf-k-start', self.bild.svg())


class DieReiterVerteilenDieWegeVollstaendig(BasisTest):
    u"""Kein Weg darf beim Gliedern verlorengehen — sonst zeigt die Seite
    weniger, als die Kopfzeile behauptet."""

    def test_die_summe_der_reiter_ist_die_ganze_liste(self):
        liste = Workflowliste(_abzug(), grenze=1).lesen()
        verteilt = sum(len(wege) for _k, _t, wege in liste.reiter())
        self.assertEqual(verteilt, len(liste.wege))
