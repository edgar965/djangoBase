# -*- coding: utf-8 -*-
u"""Die Fix-Werkzeuge stehen in einer Tabelle — mit eigenen Nummern.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „ordne den Bereich Fix-Werkzeuge · schreiben Code — Diff-Vorschau
     zuerst auch in einer tabelle, mit veränderbaren nummern"

Vorher war es eine Liste von ``sk1-fixzeile``-Blöcken: keine Nummer, keine
Sortierung, keine Spalten. Dieselbe Sorte Sonderfall wie die zwei Kästen,
die am selben Tag weggefallen sind — was nebeneinander gehört, gehört in
dieselbe Tabelle.

ZWEI LISTEN, ZWEI ABLAGEN
=========================
Ein Rang ist die POSITION in seiner Liste. 52 Prüfer und 7 Fixer gemeinsam
zu nummerieren hieße, dass das Verschieben eines Fixers die Nummer eines
Prüfers ändert. Deshalb ``fixer_rang.json`` neben ``skills_rang.json`` —
dieselbe Klasse, ein anderer Pfad.
"""
import tempfile
from pathlib import Path

from djangobase.skills import fixer, werkzeuge
from djangobase.skills.rangliste import Rangliste, fixerrangliste, rangliste
from djangobase.views.skills import SkillsView

from ..base import BasisTest


class DieFixerStehenInEinerTabelle(BasisTest):

    def _tabelle(self, fix=None):
        return SkillsView()._fixtabelle(fix)

    def test_jeder_fixer_hat_eine_zeile(self):
        self.assertEqual(len(self._tabelle()['zeilen']), len(list(fixer())))

    def test_die_spalten_stehen_fest(self):
        namen = [s['label'] for s in self._tabelle()['spalten']]
        self.assertEqual(namen, ['Rang', 'Fix-Werkzeug', 'Behebt',
                                 'Was es tut', 'Grenzen', 'Aktion'])

    def test_die_raenge_laufen_luekenlos_ab_eins(self):
        raenge = [z['zellen'][0]['sort'] for z in self._tabelle()['zeilen']]
        self.assertEqual(raenge, list(range(1, len(raenge) + 1)))

    def test_jede_zeile_traegt_ein_verschiebefeld(self):
        for z in self._tabelle()['zeilen']:
            html = z['zellen'][0]['html']
            self.assertIn('name="rang_ziel"', html)
            self.assertIn('value="fixrang"', html)
            self.assertIn('name="rang_slug"', html)

    def test_die_spalte_behebt_zeigt_die_nummer_der_pruefung(self):
        for z in self._tabelle()['zeilen']:
            with self.subTest(zeile=z['zellen'][1]['sort']):
                self.assertIn('Nr. ', z['zellen'][2]['html'])


class DerAnwendenKnopfBrauchtEineVorschau(BasisTest):
    u"""Ein Knopf, der ohne Vorschau schreibt, wäre die Falle, gegen die es
    die Vorschau gibt."""

    def test_ohne_vorschau_nur_der_vorschau_knopf(self):
        for z in SkillsView()._fixtabelle(None)['zeilen']:
            self.assertIn('vorschau:', z['zellen'][5]['html'])
            self.assertNotIn('anwenden:', z['zellen'][5]['html'])

    def test_nach_einer_vorschau_mit_treffern_erscheint_anwenden(self):
        erster = list(fixer())[0]
        fix = {'slug': erster.slug, 'modus': 'vorschau', 'n': 3, 'bereich': ''}
        zeilen = SkillsView()._fixtabelle(fix)['zeilen']
        passend = [z for z in zeilen
                   if 'anwenden:%s' % erster.slug in z['zellen'][5]['html']]
        self.assertEqual(len(passend), 1)
        self.assertIn('(3)', passend[0]['zellen'][5]['html'])

    def test_eine_vorschau_ohne_treffer_bietet_kein_anwenden(self):
        erster = list(fixer())[0]
        fix = {'slug': erster.slug, 'modus': 'vorschau', 'n': 0, 'bereich': ''}
        for z in SkillsView()._fixtabelle(fix)['zeilen']:
            self.assertNotIn('anwenden:', z['zellen'][5]['html'])

    def test_nur_der_gefragte_fixer_bekommt_den_knopf(self):
        erster = list(fixer())[0]
        fix = {'slug': erster.slug, 'modus': 'vorschau', 'n': 2, 'bereich': ''}
        mit = [z for z in SkillsView()._fixtabelle(fix)['zeilen']
               if 'anwenden:' in z['zellen'][5]['html']]
        self.assertEqual(len(mit), 1)


class ZweiListenZweiAblagen(BasisTest):
    u"""Das Verschieben eines Fixers darf keine Prüfer-Nummer ändern."""

    def test_die_ablagen_sind_verschieden(self):
        self.assertNotEqual(str(rangliste().pfad), str(fixerrangliste().pfad))

    def test_verschieben_ordnet_die_fixer_um(self):
        ordner = Path(tempfile.mkdtemp(prefix='fixrang_'))
        r = Rangliste(ordner / 'fixer_rang.json')
        alle = list(fixer())
        vorher = r.reihenfolge(alle)
        self.assertTrue(r.verschieben(vorher[-1], 1, alle))
        nachher = Rangliste(ordner / 'fixer_rang.json').reihenfolge(alle)
        self.assertEqual(nachher[0], vorher[-1])
        self.assertEqual(sorted(nachher), sorted(vorher),
                         'Beim Verschieben darf keiner verschwinden.')

    def test_die_pruefer_bleiben_dabei_unberuehrt(self):
        vorher = rangliste().reihenfolge(list(werkzeuge()))
        ordner = Path(tempfile.mkdtemp(prefix='fixrang2_'))
        r = Rangliste(ordner / 'fixer_rang.json')
        alle = list(fixer())
        r.verschieben(r.reihenfolge(alle)[-1], 1, alle)
        self.assertEqual(rangliste().reihenfolge(list(werkzeuge())), vorher)


class KeineListeMehrNebenDerTabelle(BasisTest):
    u"""Der Rückfall, gegen den diese Datei geschrieben ist."""

    def test_die_fixzeilen_sind_weg(self):
        from django.template.loader import get_template

        from djangobase.tests.konform.test_statik import ohne_kommentare
        markup = ohne_kommentare(
            Path(get_template('djangobase/hilfe/skills.html').origin.name
                 ).read_text(encoding='utf-8'))
        # EINE bleibt: das Umbau-Netz ist kein Fixer und hat keinen Rang.
        self.assertEqual(
            markup.count('class="sk1-fixzeile"'), 1,
            'Neben der Tabelle steht wieder eine Liste — dann gibt es zwei '
            'Darstellungen derselben Sache, und die zweite kann weniger.')

    def test_die_tabelle_ist_eingebunden(self):
        from django.template.loader import get_template
        markup = Path(get_template('djangobase/hilfe/skills.html').origin.name
                      ).read_text(encoding='utf-8')
        self.assertIn('tabelle=fixtabelle', markup)
