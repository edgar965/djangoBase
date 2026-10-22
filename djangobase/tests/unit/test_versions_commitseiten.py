# -*- coding: utf-8 -*-
"""Wächter für das seitenweise Holen der Commits (Hilfe → Versionen, `version_commits_alle`).

Die GitHub-Schnittstelle liefert je Aufruf höchstens 100 Commits; wer „alle" will, muss Seiten nachladen.
Attrappe statt `gh`: `Schnittstelle` antwortet auf `page=n` mit den passenden Commits einer Kunst-Historie.
"""

import json

from django.test import SimpleTestCase

from djangobase.views.versions_commitseiten import Commitseiten


class Schnittstelle:
    """`gh(args)` einer Historie aus `anzahl` Commits (neueste zuerst); `ausfall`: Seite, die scheitert."""

    def __init__(self, anzahl, ausfall=None):
        self.anzahl, self.ausfall, self.aufrufe = anzahl, ausfall, []

    def __call__(self, args):
        adresse = args[0]
        self.aufrufe.append(adresse)
        seite = int(adresse.split('&page=')[1]) if '&page=' in adresse else 1
        if seite == self.ausfall:
            return 1, '', 'Fehler'
        je = int(adresse.split('per_page=')[1].split('&')[0])
        von = (seite - 1) * je
        return 0, json.dumps([{'sha': 'c%d' % n} for n in range(von, min(von + je, self.anzahl))]), ''


class CommitseitenTest(SimpleTestCase):
    def test_ohne_alle_ein_einziger_aufruf_mit_den_letzten(self):
        gh = Schnittstelle(250)
        daten = Commitseiten.holen(gh, 'a/b', 100)
        self.assertEqual(len(daten), 100)
        self.assertEqual(len(gh.aufrufe), 1)
        self.assertNotIn('page=', gh.aufrufe[0])

    def test_alle_holt_jede_seite_bis_zur_kurzen(self):
        gh = Schnittstelle(237)
        daten = Commitseiten.holen(gh, 'a/b', 100, alle=True)
        self.assertEqual([c['sha'] for c in daten], ['c%d' % n for n in range(237)])
        self.assertEqual(len(gh.aufrufe), 3)

    def test_genau_volle_seiten_enden_mit_einer_leeren(self):
        gh = Schnittstelle(200)
        self.assertEqual(len(Commitseiten.holen(gh, 'a/b', 100, alle=True)), 200)
        self.assertEqual(len(gh.aufrufe), 3)

    def test_scheitert_die_erste_seite_ist_die_liste_leer(self):
        self.assertEqual(Commitseiten.holen(Schnittstelle(250, ausfall=1), 'a/b', 100, alle=True), [])
        self.assertEqual(Commitseiten.holen(Schnittstelle(250, ausfall=1), 'a/b', 100), [])

    def test_scheitert_eine_spaetere_seite_bleibt_das_bisherige(self):
        with self.assertLogs('djangobase.views.versions_commitseiten', level='WARNING'):
            daten = Commitseiten.holen(Schnittstelle(350, ausfall=3), 'a/b', 100, alle=True)
        self.assertEqual(len(daten), 200)

    def test_endlos_antwortende_schnittstelle_wird_bei_der_obergrenze_gestoppt(self):
        gh = Schnittstelle(10 ** 9)
        with self.assertLogs('djangobase.views.versions_commitseiten', level='WARNING'):
            daten = Commitseiten.holen(gh, 'a/b', 10, alle=True)
        self.assertEqual(len(gh.aufrufe), Commitseiten.SEITEN_MAX)
        self.assertEqual(len(daten), Commitseiten.SEITEN_MAX * 10)
