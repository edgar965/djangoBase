# -*- coding: utf-8 -*-
u"""Die Aufzeichnung: jeder Befehlslauf landet im Verlauf - und stoert nie.

BDD - GEGEBEN / DANN
====================
    EinBefehlDerDurchlaeuft
        ... wird im Verlauf notiert
        ... liefert sein Ergebnis unveraendert zurueck
    EinBefehlDerWirft
        ... wird als Fehlschlag notiert
        ... reicht die Ausnahme unveraendert weiter
    EinAbgebrochenerBefehl
        ... wird ebenfalls notiert
    EinAusgeschlossenerBefehl
        ... wird nicht notiert
    EineZweimalEingeschalteteAufzeichnung
        ... notiert jeden Lauf trotzdem nur einmal

DIE WICHTIGSTE ZUSICHERUNG
==========================
"reicht die Ausnahme unveraendert weiter". Diese Aufzeichnung legt sich
um JEDEN Management-Command in sechs Projekten. Verschluckte sie eine
Ausnahme, liefen Befehle scheinbar erfolgreich durch - und niemand
suchte den Fehler an dieser Stelle.
"""
from django.core.management.base import BaseCommand
from django.test import SimpleTestCase

from djangobase.jobaufzeichnung import Jobaufzeichnung
from djangobase.jobverlauf import Jobverlauf

from .jobwerkzeug import MitTempordner


class _Befehl(BaseCommand):
    u"""Ein Befehl, der tut, was der Test vorgibt."""

    def __init__(self, ergebnis=None, wirft=None):
        super().__init__()
        self._ergebnis = ergebnis
        self._wirft = wirft
        self.lief = False

    def execute(self, *args, **kwargs):
        self.lief = True
        if self._wirft:
            raise self._wirft
        return self._ergebnis


class AufzeichnungBasis(MitTempordner):
    u"""Haengt die Aufzeichnung um EINEN Befehl - nicht um BaseCommand.

    Die echte ``einschalten()`` patcht ``BaseCommand.execute`` fuer den
    ganzen Prozess. In einer Pruefung waere das ein Eingriff, der andere
    Pruefungen ueberlebt; hier wird deshalb nur die Umhuellung selbst
    geprueft - dieselbe Funktion, nur gezielt angewandt.
    """

    def setUp(self):
        super().setUp()
        self.verlauf = Jobverlauf(pfad=self.datei('joblaeufe.jsonl'))
        self._echt = Jobaufzeichnung._notieren
        Jobaufzeichnung._notieren = staticmethod(
            # ``*rest``: seit dem 02.09.2026 reicht die Umhuellung auch
            # CPU-Sekunden und Argumente durch - die Attrappe nimmt sie an
            # und laesst sie weg, geprueft wird hier nur der Lauf selbst.
            lambda kennung, dauer_s, erfolg, fehler, *rest:
            self.verlauf.notieren(kennung, dauer_s, erfolg, fehler))
        self.addCleanup(self._zuruecksetzen)

    def _zuruecksetzen(self):
        Jobaufzeichnung._notieren = self._echt

    def laufen_lassen(self, befehl, kennung='mail_sync'):
        u"""Den Befehl durch die Umhuellung schicken."""
        typ = type(befehl)
        alt = typ.__module__
        typ.__module__ = 'projekt.management.commands.' + kennung
        try:
            gemessen = Jobaufzeichnung._umhuellen(typ.execute)
            return gemessen(befehl)
        finally:
            typ.__module__ = alt


class EinBefehlDerDurchlaeuft(AufzeichnungBasis, SimpleTestCase):
    u"""Gegeben: Ein Befehl, der ohne Fehler endet."""

    def test_wird_im_verlauf_notiert(self):
        self.laufen_lassen(_Befehl(ergebnis='fertig'))
        self.assertIsNotNone(self.verlauf.letzter('mail_sync'))

    def test_gilt_als_erfolgreich(self):
        self.laufen_lassen(_Befehl(ergebnis='fertig'))
        self.assertTrue(self.verlauf.letzter('mail_sync')['erfolg'])

    def test_liefert_sein_ergebnis_unveraendert_zurueck(self):
        u"""Die Messung darf am Ergebnis des Befehls nichts aendern."""
        self.assertEqual(self.laufen_lassen(_Befehl(ergebnis='fertig')),
                         'fertig')

    def test_notiert_eine_dauer(self):
        self.laufen_lassen(_Befehl())
        self.assertIsNotNone(self.verlauf.letzter('mail_sync')['dauer_s'])


class EinBefehlDerWirft(AufzeichnungBasis, SimpleTestCase):
    u"""Gegeben: Ein Befehl, der mit einer Ausnahme endet."""

    def test_reicht_die_ausnahme_unveraendert_weiter(self):
        u"""Die wichtigste Zusicherung — siehe Modul-Doku."""
        with self.assertRaises(ValueError):
            self.laufen_lassen(_Befehl(wirft=ValueError('kaputt')))

    def test_wird_als_fehlschlag_notiert(self):
        with self.assertRaises(ValueError):
            self.laufen_lassen(_Befehl(wirft=ValueError('kaputt')))
        self.assertFalse(self.verlauf.letzter('mail_sync')['erfolg'])

    def test_notiert_den_fehlertext(self):
        with self.assertRaises(ValueError):
            self.laufen_lassen(_Befehl(wirft=ValueError('kaputt')))
        self.assertIn('ValueError', self.verlauf.letzter('mail_sync')['fehler'])


class EinAbgebrochenerBefehl(AufzeichnungBasis, SimpleTestCase):
    u"""Gegeben: Der Befehl wird mit Strg+C abgebrochen."""

    def test_wird_ebenfalls_notiert(self):
        u"""Sonst staende der Lauf fuer immer als unbeendet da."""
        with self.assertRaises(KeyboardInterrupt):
            self.laufen_lassen(_Befehl(wirft=KeyboardInterrupt()))
        self.assertIsNotNone(self.verlauf.letzter('mail_sync'))

    def test_gilt_nicht_als_erfolgreich(self):
        with self.assertRaises(KeyboardInterrupt):
            self.laufen_lassen(_Befehl(wirft=KeyboardInterrupt()))
        self.assertFalse(self.verlauf.letzter('mail_sync')['erfolg'])


class EinAusgeschlossenerBefehl(AufzeichnungBasis, SimpleTestCase):
    u"""Gegeben: ``runserver`` - ein Werkzeug, kein Ablauf des Projekts."""

    def test_wird_nicht_notiert(self):
        u"""``runserver`` liefe stundenlang und saehe aus wie ein Job."""
        self.laufen_lassen(_Befehl(), kennung='runserver')
        self.assertEqual(self.verlauf.laeufe(), [])

    def test_laeuft_trotzdem_durch(self):
        befehl = _Befehl(ergebnis='ok')
        self.assertEqual(self.laufen_lassen(befehl, kennung='runserver'), 'ok')
        self.assertTrue(befehl.lief)


class EinBefehlAusEinerFremdenApp(AufzeichnungBasis, SimpleTestCase):
    u"""Gegeben: Ein Befehl von djangoBase oder Django selbst.

    DER BEFUND (26.08.2026, beim ersten Aufruf der Seite sichtbar)
    =============================================================
    Die Aufzeichnung notierte `aktuell` (djangoBase) und
    `createcachetable` (Django). Die Erkennung kennt beide nicht - sie
    filtert fremde Apps heraus. Die Uebersicht meldete daraufhin
    "Nicht mehr im Bestand — geloescht oder umbenannt?" fuer zwei
    Befehle, die es sehr wohl gibt.

    Zwei Stellen mit derselben Frage muessen dieselbe Antwort geben.
    """

    def laufen_lassen_aus(self, app, kennung):
        befehl = _Befehl(ergebnis='ok')
        typ = type(befehl)
        alt = typ.__module__
        typ.__module__ = '%s.management.commands.%s' % (app, kennung)
        try:
            return Jobaufzeichnung._umhuellen(typ.execute)(befehl)
        finally:
            typ.__module__ = alt

    def test_aus_djangobase_wird_nicht_notiert(self):
        self.laufen_lassen_aus('djangobase', 'aktuell')
        self.assertEqual(self.verlauf.laeufe(), [])

    def test_aus_django_wird_nicht_notiert(self):
        self.laufen_lassen_aus('django.core', 'createcachetable')
        self.assertEqual(self.verlauf.laeufe(), [])

    def test_aus_einer_projekt_app_wird_notiert(self):
        u"""Die Gegenprobe: Der Filter darf nicht zu viel wegnehmen."""
        self.laufen_lassen_aus('mail', 'mail_sync')
        self.assertEqual(len(self.verlauf.laeufe()), 1)


class EineZweimalEingeschalteteAufzeichnung(SimpleTestCase):
    u"""Gegeben: ``einschalten()`` wird zweimal gerufen (zwei AppConfigs)."""

    def test_legt_sich_nicht_doppelt_um_den_befehl(self):
        u"""Sonst staende jeder Lauf zweimal im Verlauf."""
        Jobaufzeichnung.einschalten()
        einmal = BaseCommand.execute
        Jobaufzeichnung.einschalten()
        self.assertIs(BaseCommand.execute, einmal)

    def test_meldet_dass_sie_haengt(self):
        self.assertTrue(Jobaufzeichnung.einschalten())
