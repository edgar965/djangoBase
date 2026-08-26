# -*- coding: utf-8 -*-
u"""Die Lehren stehen in einer Tabelle — mit eigenen, verschiebbaren Nummern.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „mach die Lehren auch in einer veränderbaren Tabelle mit veränderbaren
     Nummern"

Es war die DRITTE Stelle auf dieser Seite mit derselben Schwäche — nach
den zwei Kriterien-Kästen und den Fix-Werkzeugen: eine Liste von Blöcken
ohne Rang, ohne Sortierung, ohne Spalten.

Der Bereich ging dabei nicht verloren, er wurde eine Spalte — und ist
damit sortierbar, was er als Zwischenüberschrift nicht war.

DREI LISTEN, DREI ABLAGEN
=========================
``skills_rang.json``, ``fixer_rang.json``, ``lehren_rang.json``. Ein Rang
ist die Position in SEINER Liste; gemeinsam nummeriert würde das
Verschieben einer Lehre die Nummer eines Prüfers ändern.
"""
import tempfile
from pathlib import Path

from djangobase.skills import fixer, werkzeuge
from djangobase.skills.lehren_review import LEHREN, Lehrenstand
from djangobase.skills.rangliste import (Lehrenrangliste, fixerrangliste,
                                         lehrenrangliste, rangliste)
from djangobase.views.skills import SkillsView

from ..base import BasisTest


class DieLehrenStehenInEinerTabelle(BasisTest):

    def _tabelle(self):
        return SkillsView()._lehrentabelle()

    def test_jede_lehre_hat_eine_zeile(self):
        self.assertEqual(len(self._tabelle()['zeilen']), len(LEHREN))

    def test_die_spalten_stehen_fest(self):
        namen = [s['label'] for s in self._tabelle()['spalten']]
        self.assertEqual(namen[1:], ['Rang', 'Bereich', 'Lehre',
                                     'Regel und Begründung', 'Prüfung'])
        self.assertIn('checkbox', namen[0])

    def test_die_raenge_laufen_luekenlos_ab_eins(self):
        raenge = [z['zellen'][1]['sort'] for z in self._tabelle()['zeilen']]
        self.assertEqual(raenge, list(range(1, len(raenge) + 1)))

    def test_jede_zeile_traegt_ein_verschiebefeld(self):
        for z in self._tabelle()['zeilen']:
            html = z['zellen'][1]['html']
            self.assertIn('value="lehrenrang"', html)
            self.assertIn('name="rang_slug"', html)

    def test_das_haekchen_bleibt(self):
        u"""Es bedeutet weiterhin „gilt für dieses Projekt"."""
        for z in self._tabelle()['zeilen']:
            self.assertIn('name="lehre"', z['zellen'][0]['html'])

    def test_der_bereich_ist_jetzt_eine_spalte(self):
        bereiche = {z['zellen'][2]['sort'] for z in self._tabelle()['zeilen']}
        self.assertEqual(bereiche, {l.bereich for l in LEHREN})


class DieSpaltePruefungSagtAuchWennEsKEINEGibt(BasisTest):

    def test_wer_ein_werkzeug_hat_zeigt_die_nummer(self):
        mit = [l.slug for l in LEHREN if l.werkzeuge]
        self.assertTrue(mit)
        zeilen = {z['zellen'][3]['sort']: z for z in
                  SkillsView()._lehrentabelle()['zeilen']}
        for l in LEHREN:
            if l.werkzeuge:
                with self.subTest(lehre=l.slug):
                    self.assertIn('Nr. ', zeilen[l.titel]['zellen'][5]['html'])

    def test_ohne_werkzeug_steht_es_ausdruecklich_da(self):
        u"""Keine Prüfung ist eine AUSSAGE, keine fehlende Angabe."""
        ohne = [l for l in LEHREN if not l.werkzeuge]
        self.assertTrue(ohne)
        zeilen = {z['zellen'][3]['sort']: z for z in
                  SkillsView()._lehrentabelle()['zeilen']}
        for l in ohne:
            with self.subTest(lehre=l.slug):
                self.assertIn('kein Werkzeug',
                              zeilen[l.titel]['zellen'][5]['html'])


class DreiListenDreiAblagen(BasisTest):

    def test_alle_drei_ablagen_sind_verschieden(self):
        pfade = {str(rangliste().pfad), str(fixerrangliste().pfad),
                 str(lehrenrangliste().pfad)}
        self.assertEqual(len(pfade), 3, pfade)

    def test_verschieben_ordnet_die_lehren_um(self):
        ordner = Path(tempfile.mkdtemp(prefix='lrang_'))
        r = Lehrenrangliste(ordner / 'lehren_rang.json')
        alle = list(LEHREN)
        vorher = r.reihenfolge(alle)
        self.assertTrue(r.verschieben(vorher[-1], 1, alle))
        nachher = Lehrenrangliste(ordner / 'lehren_rang.json').reihenfolge(alle)
        self.assertEqual(nachher[0], vorher[-1])
        self.assertEqual(sorted(nachher), sorted(vorher))

    def test_pruefer_und_fixer_bleiben_unberuehrt(self):
        vorher_w = rangliste().reihenfolge(list(werkzeuge()))
        vorher_f = fixerrangliste().reihenfolge(list(fixer()))
        ordner = Path(tempfile.mkdtemp(prefix='lrang2_'))
        r = Lehrenrangliste(ordner / 'lehren_rang.json')
        alle = list(LEHREN)
        r.verschieben(r.reihenfolge(alle)[-1], 1, alle)
        self.assertEqual(rangliste().reihenfolge(list(werkzeuge())), vorher_w)
        self.assertEqual(fixerrangliste().reihenfolge(list(fixer())), vorher_f)


class DieGrundordnungIstNICHTDasAlphabet(BasisTest):
    u"""``Rangliste.grundordnung`` sortiert nach Kennung — für Lehren falsch.

    Sie haben kein Kriterium; nach Kennung sortiert stünde
    ``aequivalenz-beweisen`` vor ``bincount-statt-add-at``, eine
    Reihenfolge nach Alphabet, die niemand so gemeint hat.
    """

    def test_die_erklaerte_reihenfolge_gilt(self):
        ordner = Path(tempfile.mkdtemp(prefix='lrang3_'))
        r = Lehrenrangliste(ordner / 'leer.json')
        self.assertEqual(r.reihenfolge(list(LEHREN)),
                         [l.slug for l in LEHREN])

    def test_das_alphabet_waere_etwas_anderes(self):
        u"""Gegenprobe: Sonst prüft der Test darüber nichts."""
        erklaert = [l.slug for l in LEHREN]
        self.assertNotEqual(erklaert, sorted(erklaert))


class KeineListeMehrNebenDerTabelle(BasisTest):

    def test_die_lehre_bloecke_sind_weg(self):
        from django.template.loader import get_template

        from djangobase.tests.konform.test_statik import ohne_kommentare
        markup = ohne_kommentare(
            Path(get_template('djangobase/hilfe/skills.html').origin.name
                 ).read_text(encoding='utf-8'))
        self.assertNotIn('class="sk-lehre"', markup)
        self.assertIn('tabelle=lehrentabelle', markup)

    def test_der_ankreuzstand_wird_weiter_gespeichert(self):
        u"""Die Tabelle darf das Häkchen nicht zur Zierde machen."""
        self.assertTrue(hasattr(Lehrenstand, 'speichern'))
        stand = Lehrenstand.laden()
        self.assertIsInstance(stand, dict)
