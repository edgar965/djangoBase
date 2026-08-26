# -*- coding: utf-8 -*-
u"""Der Job-Verlauf: was lief wann, wie lange, mit welchem Ausgang.

BDD - GEGEBEN / DANN
====================
    EinLeererVerlauf
        ... kennt keinen letzten Lauf
        ... liefert eine leere Zusammenfassung
    EinVerlaufMitEinemErfolgreichenLauf
        ... nennt ihn als letzten Lauf
        ... nennt seine Dauer
        ... zaehlt keinen Fehler
    EinVerlaufMitMehrerenLaeufen
        ... nennt den juengsten zuerst
        ... zaehlt alle Laeufe des Jobs
        ... trennt die Jobs voneinander
    EinVerlaufMitEinemFehlschlag
        ... nennt den Fehlertext
        ... zaehlt ihn als Fehler
    EineBeschaedigteVerlaufsdatei
        ... ueberspringt die kaputte Zeile
    EinVerlaufAmSchreibenGehindert
        ... laesst den Job trotzdem durchlaufen

Die letzte Klasse ist die wichtigste: Der Verlauf ist eine BEOBACHTUNG.
Wenn er nicht schreiben kann, darf trotzdem kein Job scheitern.
"""
from django.test import SimpleTestCase

from djangobase.jobverlauf import Jobverlauf

from .jobwerkzeug import MitTempordner


class EinLeererVerlauf(MitTempordner, SimpleTestCase):
    u"""Gegeben: Es wurde noch nie ein Job ausgefuehrt."""

    def setUp(self):
        super().setUp()
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))

    def test_kennt_keinen_letzten_lauf(self):
        self.assertIsNone(self.verlauf.letzter('mail_sync'))

    def test_liefert_eine_leere_zusammenfassung(self):
        self.assertEqual(self.verlauf.zusammenfassung(), {})

    def test_liefert_eine_leere_liste(self):
        self.assertEqual(self.verlauf.laeufe(), [])


class EinVerlaufMitEinemErfolgreichenLauf(MitTempordner, SimpleTestCase):
    u"""Gegeben: ``mail_sync`` lief einmal und war erfolgreich."""

    def setUp(self):
        super().setUp()
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))
        self.verlauf.notieren('mail_sync', dauer_s=12.75, erfolg=True)

    def test_nennt_ihn_als_letzten_lauf(self):
        letzter = self.verlauf.letzter('mail_sync')
        self.assertIsNotNone(letzter)
        self.assertEqual(letzter['kennung'], 'mail_sync')

    def test_nennt_seine_dauer(self):
        self.assertEqual(self.verlauf.letzter('mail_sync')['dauer_s'], 12.75)

    def test_gilt_als_erfolgreich(self):
        self.assertTrue(self.verlauf.letzter('mail_sync')['erfolg'])

    def test_zaehlt_keinen_fehler(self):
        eintrag = self.verlauf.zusammenfassung()['mail_sync']
        self.assertEqual(eintrag['fehler'], 0)
        self.assertEqual(eintrag['laeufe'], 1)


class EinVerlaufMitMehrerenLaeufen(MitTempordner, SimpleTestCase):
    u"""Gegeben: Zwei Jobs sind mehrfach gelaufen."""

    def setUp(self):
        super().setUp()
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))
        self.verlauf.notieren('mail_sync', dauer_s=1.0, erfolg=True)
        self.verlauf.notieren('index_pdfs', dauer_s=40.0, erfolg=True)
        self.verlauf.notieren('mail_sync', dauer_s=3.0, erfolg=True)

    def test_nennt_den_juengsten_zuerst(self):
        u"""Wer auf die Seite sieht, will den letzten Stand, nicht den ersten."""
        self.assertEqual(self.verlauf.letzter('mail_sync')['dauer_s'], 3.0)

    def test_zaehlt_alle_laeufe_des_jobs(self):
        self.assertEqual(
            self.verlauf.zusammenfassung()['mail_sync']['laeufe'], 2)

    def test_trennt_die_jobs_voneinander(self):
        u"""Ein langer Indexlauf darf die Zahlen des Mail-Abrufs nicht faerben."""
        zusammen = self.verlauf.zusammenfassung()
        self.assertEqual(zusammen['index_pdfs']['laeufe'], 1)
        self.assertEqual(zusammen['mail_sync']['dauer_schnitt'], 2.0)

    def test_liefert_auf_wunsch_nur_die_letzten(self):
        self.assertEqual(len(self.verlauf.laeufe(hoechstens=2)), 2)


class EinVerlaufMitEinemFehlschlag(MitTempordner, SimpleTestCase):
    u"""Gegeben: Der letzte Lauf ist mit einer Ausnahme geendet."""

    def setUp(self):
        super().setUp()
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))
        self.verlauf.notieren('mail_sync', dauer_s=0.4, erfolg=False,
                              fehler='ConnectionError: kein Server')

    def test_nennt_den_fehlertext(self):
        u"""Ohne Text muesste man ins Log — die Seite soll es selbst sagen."""
        self.assertIn('ConnectionError',
                      self.verlauf.letzter('mail_sync')['fehler'])

    def test_gilt_nicht_als_erfolgreich(self):
        self.assertFalse(self.verlauf.letzter('mail_sync')['erfolg'])

    def test_zaehlt_ihn_als_fehler(self):
        self.assertEqual(
            self.verlauf.zusammenfassung()['mail_sync']['fehler'], 1)

    def test_kuerzt_sehr_lange_fehlertexte(self):
        u"""Ein Traceback mit 40 kB darf die Datei nicht sprengen."""
        self.verlauf.notieren('gross', dauer_s=0.1, erfolg=False,
                              fehler='x' * 5000)
        self.assertLessEqual(len(self.verlauf.letzter('gross')['fehler']), 500)


class EineBeschaedigteVerlaufsdatei(MitTempordner, SimpleTestCase):
    u"""Gegeben: Eine Zeile ist unvollstaendig (Absturz beim Schreiben)."""

    def setUp(self):
        super().setUp()
        self.pfad = self.datei('joblaeufe.jsonl')
        self.verlauf = Jobverlauf(pfad=self.pfad)
        self.verlauf.notieren('mail_sync', dauer_s=1.0, erfolg=True)
        with self.pfad.open('a', encoding='utf-8') as datei:
            datei.write('{"kennung": "abgeschni\n')
        self.verlauf.notieren('index_pdfs', dauer_s=2.0, erfolg=True)

    def test_ueberspringt_die_kaputte_zeile(self):
        u"""Eine halbe Zeile darf die Laeufe davor und danach nicht kosten."""
        kennungen = [s['kennung'] for s in self.verlauf.laeufe()]
        self.assertIn('mail_sync', kennungen)
        self.assertIn('index_pdfs', kennungen)


class EinVerlaufAmSchreibenGehindert(MitTempordner, SimpleTestCase):
    u"""Gegeben: Der Zielort ist nicht beschreibbar (Ordner ist eine Datei)."""

    def setUp(self):
        super().setUp()
        sperrig = self.datei('sperre')
        sperrig.write_text('kein Ordner', encoding='utf-8')
        self.verlauf = Jobverlauf(pfad=sperrig / 'joblaeufe.jsonl')

    def test_wirft_nicht(self):
        u"""Der Verlauf beobachtet nur — er darf nie einen Job scheitern lassen."""
        self.verlauf.notieren('mail_sync', dauer_s=1.0, erfolg=True)

    def test_liefert_danach_eine_leere_liste(self):
        self.verlauf.notieren('mail_sync', dauer_s=1.0, erfolg=True)
        self.assertEqual(self.verlauf.laeufe(), [])
