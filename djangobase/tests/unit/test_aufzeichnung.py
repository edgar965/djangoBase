# -*- coding: utf-8 -*-
u"""Die Testcase-Aufzeichnung: Bestand, Steuerung und der erzeugte Testfall.

AUFTRAG (Edgar, 20.08.2026): „mach in djangoBase auf /hilfe/tests/ einen neuen
Tab: Testcase aufzeichnen … Ziel ist es, dass du aus diesen Aufzeichnungen echte
Tests erstellen kannst."

WAS HIER GEPRUEFT WIRD - UND WARUM GERADE DAS
=============================================
Die Aufzeichnung schreibt eine Datei im Projekt und erzeugt daraus spaeter
Quelltext. Beides muss verlaesslich sein, sonst entsteht ein Test, der etwas
anderes prueft als aufgenommen wurde. Die Faelle decken die Stellen ab, an denen
das schiefgehen kann:

  * nur EINE Aufnahme gleichzeitig (zwei haetten dieselben Ereignisse in beiden)
  * eine BEENDETE nimmt nichts mehr an (Nachzuegler aus einem offenen Tab)
  * unbekannte Ereignisarten werden verworfen - der Browser darf hier keine
    beliebigen Strukturen ablegen, aus denen spaeter Code wird
  * der erzeugte Quelltext ist gueltiges Python UND faehrt keine
    Schreibzugriffe nach
"""
import ast
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.aufzeichnung import Aufzeichnungen
from djangobase.aufzeichnung_steuerung import Steuerung
from djangobase.aufzeichnung_testfall import Testfall


class AufzeichnungTest(SimpleTestCase):
    u"""Bestand und Steuerung - auf einer Wegwerf-Datei, nie im Projekt."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bestand = Aufzeichnungen(Path(self._tmp.name) / "auf.json")
        self.s = Steuerung(self.bestand)

    def tearDown(self):
        self._tmp.cleanup()

    def test_start_vergibt_namen_und_id(self):
        a, neu = self.s.starten(seite="/dax-handel/")
        self.assertTrue(neu)
        self.assertTrue(a.id.startswith("auf_"))
        self.assertIn("Aufzeichnung", a.name)      # Default-Name wie gefordert
        self.assertTrue(a.laeuft)
        self.assertEqual(a.seite, "/dax-handel/")

    def test_nur_eine_laeuft_gleichzeitig(self):
        u"""Ein zweiter Start liefert die LAUFENDE zurueck, statt eine zweite zu
        beginnen - sonst saehen beide dieselben Ereignisse."""
        erste, _ = self.s.starten()
        zweite, neu = self.s.starten()
        self.assertFalse(neu)
        self.assertEqual(zweite.id, erste.id)
        self.assertEqual(len([a for a in self.bestand.alle() if a.laeuft]), 1)

    def test_unbekannte_art_wird_verworfen(self):
        a, _ = self.s.starten()
        n = self.s.anhaengen(a.id, [
            {"t": 1, "art": "klick", "ziel": "#x"},
            {"t": 2, "art": "beliebig", "ziel": "#y"},      # nicht in ARTEN
            "kein Dictionary",
        ])
        self.assertEqual(n, 1)
        self.assertEqual(len(self.bestand.holen(a.id).schritte), 1)

    def test_beendete_nimmt_nichts_mehr_an(self):
        a, _ = self.s.starten()
        self.s.anhaengen(a.id, [{"t": 1, "art": "klick", "ziel": "#x"}])
        self.s.beenden(a.id)
        self.assertEqual(self.s.anhaengen(a.id, [{"t": 9, "art": "klick", "ziel": "#z"}]), 0)
        self.assertEqual(len(self.bestand.holen(a.id).schritte), 1)

    def test_umbenennen_und_loeschen(self):
        a, _ = self.s.starten()
        self.assertIsNotNone(self.s.umbenennen(a.id, "Mein Weg"))
        self.assertEqual(self.bestand.holen(a.id).name, "Mein Weg")
        self.assertIsNone(self.s.umbenennen(a.id, "   "))      # leer gilt nicht
        self.assertTrue(self.s.loeschen(a.id))
        self.assertIsNone(self.bestand.holen(a.id))
        self.assertFalse(self.s.loeschen(a.id))                # zweimal geht nicht


class TestfallTest(SimpleTestCase):
    u"""Der erzeugte Quelltext."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bestand = Aufzeichnungen(Path(self._tmp.name) / "auf.json")
        self.s = Steuerung(self.bestand)
        a, _ = self.s.starten(name="Depot ansehen", seite="/depot/")
        self.s.anhaengen(a.id, [
            {"t": 0.0, "art": "seite", "seite": "/depot/"},
            {"t": 0.5, "art": "klick", "ziel": "#knopf", "text": "Aktualisieren"},
            {"t": 1.0, "art": "abruf", "methode": "GET", "pfad": "/api/depot/", "status": 200},
            {"t": 1.5, "art": "abruf", "methode": "GET", "pfad": "/api/depot/", "status": 200},
            {"t": 2.0, "art": "abruf", "methode": "POST", "pfad": "/api/order/", "status": 201},
        ])
        self.a = self.s.beenden(a.id, logs=[
            {"zeit": "2026-08-20 18:00:00", "stufe": "ERROR", "logger": "x", "text": "kaputt"}])

    def tearDown(self):
        self._tmp.cleanup()

    def test_quelltext_ist_gueltiges_python(self):
        ast.parse(Testfall(self.a).quelltext())

    def test_get_abrufe_ohne_doppelte(self):
        self.assertEqual(Testfall(self.a).abrufe(),
                         [{"pfad": "/api/depot/", "status": 200}])

    def test_schreibzugriff_wird_nicht_nachgefahren(self):
        u"""Ein aufgezeichnetes POST loeste damals eine Wirkung aus - beim
        Testlauf wuerde es sie erneut ausloesen. Es darf nur als Kommentar
        auftauchen, nie als Aufruf."""
        fall = Testfall(self.a)
        quelltext = fall.quelltext()
        self.assertEqual([s["pfad"] for s in fall.schreibende()], ["/api/order/"])
        for zeile in quelltext.splitlines():
            if "/api/order/" in zeile:
                self.assertTrue(zeile.strip().startswith("#"),
                                "Schreibzugriff steht als Code: %r" % zeile)

    def test_fehlerzeilen_stehen_im_kopf(self):
        self.assertIn("kaputt", Testfall(self.a).quelltext())

    def test_namen_sind_gueltige_bezeichner(self):
        fall = Testfall(self.a)
        self.assertTrue(fall.klassenname().isidentifier())
        self.assertTrue(fall.dateiname().startswith("test_"))
        self.assertTrue(fall.dateiname().endswith(".py"))
