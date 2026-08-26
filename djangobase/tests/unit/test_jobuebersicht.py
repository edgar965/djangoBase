# -*- coding: utf-8 -*-
u"""Die Zeilen der Jobs-Seite: Bestand und Verlauf zusammengefuehrt.

BDD - GEGEBEN / DANN
====================
    EinJobDerNieLief
        ... steht trotzdem in der Uebersicht
        ... ist als "nie gelaufen" gekennzeichnet
    EinJobMitErfolgreichemLauf
        ... zeigt Zeitpunkt und Dauer
    EinJobDerZuletztScheiterte
        ... steht ganz oben
        ... nennt den Fehlertext
    EinLaufOhnePassendenJobImBestand
        ... wird trotzdem gezeigt
    EineUebersichtMitVielenJobs
        ... zaehlt richtig
        ... ermittelt auf Knopfdruck neu

DIE ZWEI FAELLE, DIE MAN LEICHT UEBERSIEHT
==========================================
Ein Job im Bestand ohne Lauf (die Spalten bleiben leer) und ein Lauf ohne
Job im Bestand (jemand hat die Datei geloescht). Beide muessen sichtbar
sein - der zweite besonders, weil dort etwas laeuft, das niemand mehr
kennt.
"""
from django.test import SimpleTestCase

from djangobase.jobkatalog import Jobkatalog
from djangobase.jobuebersicht import Jobuebersicht
from djangobase.jobverlauf import Jobverlauf

from .jobwerkzeug import ErkennungAttrappe, MitTempordner


class JobsSeiteBasis(MitTempordner):
    u"""Baut eine Uebersicht auf eigenen Dateien - ohne das echte Projekt."""

    KENNUNGEN = ['mail_sync']

    def setUp(self):
        super().setUp()
        self.erkennung = ErkennungAttrappe(self.KENNUNGEN)
        self.katalog = Jobkatalog(pfad=self.datei('jobkatalog.json'),
                                  erkennung=self.erkennung)
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))
        self.uebersicht = Jobuebersicht(katalog=self.katalog,
                                        verlauf=self.verlauf)

    def zeile(self, kennung):
        for z in self.uebersicht.zeilen():
            if z['kennung'] == kennung:
                return z
        return None


class EinJobDerNieLief(JobsSeiteBasis, SimpleTestCase):
    u"""Gegeben: ``mail_sync`` steht im Bestand, lief aber noch nie."""

    def test_steht_trotzdem_in_der_uebersicht(self):
        u"""Sonst faende man nie heraus, dass es ihn ueberhaupt gibt."""
        self.assertIsNotNone(self.zeile('mail_sync'))

    def test_ist_als_nie_gelaufen_gekennzeichnet(self):
        self.assertTrue(self.zeile('mail_sync')['nie_gelaufen'])

    def test_hat_keinen_zeitpunkt(self):
        self.assertEqual(self.zeile('mail_sync')['lief_am'], '')

    def test_zaehlt_als_nie_gelaufen(self):
        self.assertEqual(self.uebersicht.zahlen()['nie'], 1)


class EinJobMitErfolgreichemLauf(JobsSeiteBasis, SimpleTestCase):
    u"""Gegeben: ``mail_sync`` lief erfolgreich, 12,5 Sekunden lang."""

    def setUp(self):
        super().setUp()
        self.verlauf.notieren('mail_sync', dauer_s=12.5, erfolg=True)

    def test_zeigt_die_dauer(self):
        self.assertEqual(self.zeile('mail_sync')['dauer_s'], 12.5)

    def test_zeigt_einen_zeitpunkt(self):
        self.assertNotEqual(self.zeile('mail_sync')['lief_am'], '')

    def test_liefert_den_zeitpunkt_auch_als_datum(self):
        u"""Als Text stuende auf der Seite UTC — also 21:11 statt 23:11.

        Genau so stand es beim ersten Aufruf am 26.08.2026 dort. Als
        ``datetime`` rechnet Django in die Zeitzone des Projekts um.
        """
        from datetime import datetime

        wann = self.zeile('mail_sync')['lief_am_zeit']
        self.assertIsInstance(wann, datetime)
        self.assertIsNotNone(wann.tzinfo)

    def test_gilt_als_erfolgreich(self):
        self.assertTrue(self.zeile('mail_sync')['erfolg'])

    def test_zaehlt_als_gelaufen(self):
        self.assertEqual(self.uebersicht.zahlen()['gelaufen'], 1)


class EinJobDerZuletztScheiterte(JobsSeiteBasis, SimpleTestCase):
    u"""Gegeben: Von zwei Jobs ist einer gescheitert."""

    KENNUNGEN = ['aaa_laeuft', 'zzz_scheitert']

    def setUp(self):
        super().setUp()
        self.verlauf.notieren('aaa_laeuft', dauer_s=1.0, erfolg=True)
        self.verlauf.notieren('zzz_scheitert', dauer_s=0.2, erfolg=False,
                              fehler='ValueError: kaputt')

    def test_steht_ganz_oben(self):
        u"""Wer die Seite oeffnet, sucht das Kaputte - trotz Z am Anfang."""
        self.assertEqual(self.uebersicht.zeilen()[0]['kennung'],
                         'zzz_scheitert')

    def test_nennt_den_fehlertext(self):
        self.assertIn('ValueError', self.zeile('zzz_scheitert')['fehler'])

    def test_wird_als_fehlerhaft_gezaehlt(self):
        self.assertEqual(self.uebersicht.zahlen()['fehlerhaft'], 1)


class EinLaufOhnePassendenJobImBestand(JobsSeiteBasis, SimpleTestCase):
    u"""Gegeben: Ein Lauf im Verlauf, dessen Befehl es nicht mehr gibt."""

    def setUp(self):
        super().setUp()
        self.verlauf.notieren('geloeschter_befehl', dauer_s=5.0, erfolg=True)

    def test_wird_trotzdem_gezeigt(self):
        u"""Sonst verschwaende ein noch laufender Ablauf lautlos aus der Sicht."""
        self.assertIsNotNone(self.zeile('geloeschter_befehl'))

    def test_ist_als_unbekannt_gekennzeichnet(self):
        self.assertEqual(self.zeile('geloeschter_befehl')['art'], 'unbekannt')

    def test_traegt_einen_hinweis(self):
        self.assertIn('Bestand', self.zeile('geloeschter_befehl')['hilfe'])


class EineUebersichtMitVielenJobs(JobsSeiteBasis, SimpleTestCase):
    u"""Gegeben: Drei Jobs im Bestand, einer davon gelaufen."""

    KENNUNGEN = ['eins', 'zwei', 'drei']

    def setUp(self):
        super().setUp()
        self.verlauf.notieren('eins', dauer_s=1.0, erfolg=True)

    def test_zaehlt_alle_jobs(self):
        self.assertEqual(self.uebersicht.zahlen()['gesamt'], 3)

    def test_zaehlt_den_gelaufenen(self):
        self.assertEqual(self.uebersicht.zahlen()['gelaufen'], 1)

    def test_ermittelt_auf_knopfdruck_neu(self):
        u"""Der Knopf "Jetzt aktualisieren" fragt nicht nach dem Alter."""
        self.uebersicht.zeilen()
        vorher = self.erkennung.aufrufe
        self.uebersicht.zeilen(neu=True)
        self.assertEqual(self.erkennung.aufrufe, vorher + 1)

    def test_ermittelt_ohne_knopfdruck_nicht_erneut(self):
        self.uebersicht.zeilen()
        vorher = self.erkennung.aufrufe
        self.uebersicht.zeilen()
        self.assertEqual(self.erkennung.aufrufe, vorher)
