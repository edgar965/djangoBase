# -*- coding: utf-8 -*-
u"""Der Job-Bestand: gemerkt, taeglich aufgefrischt, auf Knopfdruck neu.

BDD - JEDE KLASSE IST EIN "GEGEBEN", JEDE METHODE EIN "DANN"
============================================================
Die Klassennamen beschreiben die AUSGANGSLAGE ("ein Bestand von
gestern"), die Methodennamen das erwartete VERHALTEN ("wird beim Lesen
neu ermittelt"). Wer die Testliste liest, liest die Anforderung:

    EinNochNieErmittelterBestand
        ... gilt als veraltet
        ... wird beim ersten Lesen ermittelt
    EinBestandVonHeute
        ... gilt als frisch
        ... wird beim Lesen NICHT neu ermittelt
    EinBestandVonGestern
        ... gilt als veraltet
        ... wird beim Lesen neu ermittelt

Geprueft wird das VERHALTEN, nicht der Weg dorthin: Die Tests zaehlen,
wie oft die Erkennung lief - nicht, welche Methode sie dabei benutzt hat.
Deshalb ueberstehen sie einen Umbau im Inneren.
"""
import json
from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from djangobase.jobkatalog import Jobkatalog

from .jobwerkzeug import ErkennungAttrappe, MitTempordner


class EinNochNieErmittelterBestand(MitTempordner, SimpleTestCase):
    u"""Gegeben: Es gibt noch keine Katalogdatei."""

    def setUp(self):
        super().setUp()
        self.erkennung = ErkennungAttrappe(['mail_sync'])
        self.katalog = Jobkatalog(pfad=self.datei('jobkatalog.json'),
                                  erkennung=self.erkennung)

    def test_gilt_als_veraltet(self):
        self.assertTrue(self.katalog.veraltet())

    def test_kennt_keinen_ermittlungszeitpunkt(self):
        self.assertIsNone(self.katalog.ermittelt_am())

    def test_wird_beim_ersten_lesen_ermittelt(self):
        jobs = self.katalog.jobs()
        self.assertEqual([j['kennung'] for j in jobs], ['mail_sync'])
        self.assertEqual(self.erkennung.aufrufe, 1)

    def test_merkt_sich_das_ergebnis(self):
        self.katalog.jobs()
        self.assertTrue(self.katalog.pfad.exists())
        daten = json.loads(self.katalog.pfad.read_text(encoding='utf-8'))
        self.assertIn('ermittelt_am', daten)
        self.assertEqual(len(daten['jobs']), 1)


class EinBestandVonHeute(MitTempordner, SimpleTestCase):
    u"""Gegeben: Der Bestand wurde gerade eben ermittelt."""

    def setUp(self):
        super().setUp()
        self.erkennung = ErkennungAttrappe(['mail_sync', 'index_pdfs'])
        self.katalog = Jobkatalog(pfad=self.datei('jobkatalog.json'),
                                  erkennung=self.erkennung)
        self.katalog.aktualisieren()
        self.erkennung.aufrufe = 0        # ab hier zaehlen

    def test_gilt_als_frisch(self):
        self.assertFalse(self.katalog.veraltet())

    def test_wird_beim_lesen_nicht_neu_ermittelt(self):
        u"""Das ist der Sinn des Merkens: 93 Importe je Seitenaufruf sparen."""
        self.katalog.jobs()
        self.katalog.jobs()
        self.assertEqual(self.erkennung.aufrufe, 0)

    def test_liefert_die_gemerkten_jobs(self):
        jobs = self.katalog.jobs()
        self.assertEqual([j['kennung'] for j in jobs],
                         ['index_pdfs', 'mail_sync'])

    def test_wird_auf_knopfdruck_trotzdem_neu_ermittelt(self):
        u""""Jetzt aktualisieren" fragt nicht, wie alt der Bestand ist."""
        self.katalog.aktualisieren()
        self.assertEqual(self.erkennung.aufrufe, 1)


class EinBestandVonGestern(MitTempordner, SimpleTestCase):
    u"""Gegeben: Der Bestand ist gestern ermittelt worden."""

    def setUp(self):
        super().setUp()
        self.erkennung = ErkennungAttrappe(['mail_sync'])
        self.pfad = self.datei('jobkatalog.json')
        gestern = (datetime.now(timezone.utc) - timedelta(days=1, minutes=1))
        self.pfad.write_text(json.dumps({
            'ermittelt_am': gestern.isoformat(timespec='seconds'),
            'jobs': [{'kennung': 'alt', 'name': 'alt', 'app': '',
                      'art': 'befehl', 'hilfe': ''}],
        }), encoding='utf-8')
        self.katalog = Jobkatalog(pfad=self.pfad, erkennung=self.erkennung)

    def test_gilt_als_veraltet(self):
        self.assertTrue(self.katalog.veraltet())

    def test_wird_beim_lesen_neu_ermittelt(self):
        u"""Taegliche Auffrischung, ohne dass jemand einen Knopf druecken muss."""
        jobs = self.katalog.jobs()
        self.assertEqual(self.erkennung.aufrufe, 1)
        self.assertEqual([j['kennung'] for j in jobs], ['mail_sync'])


class EineBeschaedigteKatalogdatei(MitTempordner, SimpleTestCase):
    u"""Gegeben: Die Datei ist unlesbar (halb geschrieben, von Hand geaendert)."""

    def setUp(self):
        super().setUp()
        self.pfad = self.datei('jobkatalog.json')
        self.pfad.write_text('{kein json', encoding='utf-8')
        self.erkennung = ErkennungAttrappe(['mail_sync'])
        self.katalog = Jobkatalog(pfad=self.pfad, erkennung=self.erkennung)

    def test_stuerzt_nicht_ab_sondern_ermittelt_neu(self):
        u"""Eine kaputte Merkdatei darf die Seite nicht kosten."""
        jobs = self.katalog.jobs()
        self.assertEqual([j['kennung'] for j in jobs], ['mail_sync'])

    def test_gilt_als_veraltet(self):
        self.assertTrue(self.katalog.veraltet())
