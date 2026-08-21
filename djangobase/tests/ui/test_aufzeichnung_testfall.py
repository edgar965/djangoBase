# -*- coding: utf-8 -*-
u"""Aus einer Aufzeichnung wird ein Testfall — per Knopf, mit eindeutigen Zielen.

DIE DREI PUNKTE (Edgar, 21.08.2026, „mach 1 und 2" … „auch 3 und 4")
====================================================================

1. **Testfall per Klick.** Vorher ging das nur über
   ``manage.py testfall_aus_aufzeichnung --ziel …``. Der Kommentar dort
   begründete das mit: „ein Knopf … würde dazu einladen, ihn nebenbei zu
   drücken und die Datei nie anzusehen." Das Argument bleibt richtig, deshalb
   nennt die Antwort Pfad und Zahl der geprüften Abrufe — und überschreibt
   niemals eine vorhandene Datei, die von Hand ergänzte Zusicherungen tragen
   könnte.

2. **Der Abspieler prüft.** Er fuhr Klicks nach und meldete höchstens „nicht
   gefunden"; die aufgezeichneten Abrufe (Pfad + Status) lagen ungenutzt
   daneben, obwohl genau sie die Zusicherung tragen, die aus einer Aufnahme
   folgt.

3. **Eindeutige Kennungen.** ``button.dax-tab`` gibt es viermal. Aufgelöst
   wurde über den sichtbaren Text — bei gleichem Text nahm der Abspieler den
   ersten Treffer und klickte den falschen Knopf, ohne dass es auffiel.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from djangobase.aufzeichnung import Aufzeichnungen
from djangobase.aufzeichnung_ablage import TestfallAblage
from djangobase.aufzeichnung_steuerung import Steuerung
from djangobase.aufzeichnung_testfall import Testfall

PAKET = Path(__file__).resolve().parents[2]
JS = PAKET / "static" / "djangobase" / "js"


class AblageTest(SimpleTestCase):
    u"""Punkt 1: Wohin die Datei geht — und wann NICHT."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self._tmp.name)
        bestand = Aufzeichnungen(self.ordner / "auf.json")
        s = Steuerung(bestand)
        a, _ = s.starten(name="Weg über zwei Seiten", seite="/dax-handel/")
        s.anhaengen(a.id, [
            {"art": "seite", "seite": "/dax-handel/", "t": 0.5},
            {"art": "abruf", "methode": "GET", "pfad": "/api/kurse/",
             "status": 200, "t": 1.0},
            {"art": "klick", "ziel": "#los", "text": "Los", "t": 2.0},
        ])
        self.fall = Testfall(s.beenden(a.id))

    def tearDown(self):
        self._tmp.cleanup()

    def test_datei_wird_geschrieben(self):
        pfad, meldung = TestfallAblage(self.ordner).ablegen(self.fall)
        self.assertIsNotNone(pfad, meldung)
        self.assertTrue(pfad.exists())
        self.assertIn("Abrufe geprüft", meldung)
        self.assertIn("/api/kurse/", pfad.read_text(encoding="utf-8"))

    def test_vorhandene_datei_wird_nicht_ueberschrieben(self):
        u"""Sie kann von Hand ergänzte Zusicherungen tragen — genau die, die
        eine Aufnahme nicht kennt."""
        pfad, _ = TestfallAblage(self.ordner).ablegen(self.fall)
        pfad.write_text("# von Hand ergänzt\n", encoding="utf-8")
        zweiter, meldung = TestfallAblage(self.ordner).ablegen(self.fall)
        self.assertIsNone(zweiter)
        self.assertIn("gibt schon", meldung)
        self.assertEqual(pfad.read_text(encoding="utf-8"), "# von Hand ergänzt\n")

    def test_ohne_ziel_klare_meldung_statt_geratenem_ort(self):
        u"""Eine Datei, die irgendwo landet, findet niemand wieder."""
        ablage = TestfallAblage(self.ordner / "gibtsnicht")
        pfad, meldung = ablage.ablegen(self.fall)
        self.assertIsNone(pfad)
        self.assertIn("DJANGOBASE_TESTFALL_ZIEL", meldung)

    def test_setting_hat_vorrang(self):
        with override_settings(DJANGOBASE_TESTFALL_ZIEL=str(self.ordner)):
            self.assertEqual(TestfallAblage().ziel(), self.ordner)

    def test_endpunkt_kennt_die_aktion(self):
        u"""Ohne die Aktion bliebe der Knopf ein Knopf ohne Wirkung."""
        from djangobase.views.aufzeichnung import AufzeichnungView
        self.assertTrue(hasattr(AufzeichnungView, "_testfall"))


class AbspielerPruefungTest(SimpleTestCase):
    u"""Punkt 2: Der Abspieler vergleicht die Abrufe."""

    def setUp(self):
        self.quelle = (JS / "aufzeichner_abspieler.js").read_text(encoding="utf-8")

    def test_abrufe_werden_verglichen_statt_uebersprungen(self):
        self.assertIn("abrufPruefen", self.quelle)
        self.assertNotIn("if (s.art === 'abruf') return true", self.quelle,
                         u"Abrufe dürfen nicht mehr kommentarlos übersprungen "
                         u"werden — sie sind die Zusicherung der Aufnahme")

    def test_abrufe_werden_nicht_nachgefahren(self):
        u"""Ein aufgezeichnetes POST würde seine Wirkung erneut auslösen.
        Beobachtet wird, was die nachgefahrenen Klicks von selbst auslösen."""
        pruefteil = self.quelle.split("abrufPruefen", 1)[1].split("\n}", 1)[0]
        for verboten in ("fetch(s.pfad", "location.href = s.pfad"):
            self.assertNotIn(verboten, pruefteil)

    def test_treffer_wird_verbraucht(self):
        u"""Sonst erfüllte EIN Abruf zwei gleiche Erwartungen."""
        self.assertIn("weg = true", self.quelle)

    def test_abweichungen_stehen_in_der_bilanz(self):
        self.assertIn("abweichungen", self.quelle)
        self.assertIn("abweichend", self.quelle)


class KennungTest(SimpleTestCase):
    u"""Punkt 3: Mehrdeutige Selektoren werden eindeutig gemacht."""

    def setUp(self):
        self.aufz = (JS / "aufzeichner.js").read_text(encoding="utf-8")
        self.absp = (JS / "aufzeichner_abspieler.js").read_text(encoding="utf-8")

    def test_aufzeichner_prueft_auf_eindeutigkeit(self):
        self.assertIn("_eindeutig", self.aufz)
        self.assertIn("querySelectorAll(einfach).length", self.aufz)

    def test_nummer_wird_mitgeschrieben(self):
        u"""Nur wenn der Selektor mehrdeutig blieb — sonst wäre sie eine
        weitere Stelle, die beim nächsten Umbau bricht."""
        self.assertIn("_nr(", self.aufz)
        self.assertIn("alle.length > 1 ? alle.indexOf(el) : -1", self.aufz)

    def test_abspieler_nimmt_die_nummer(self):
        self.assertIn("typeof s.nr === 'number'", self.absp)

    def test_abspieler_raet_nicht_mehr(self):
        u"""Weder Nummer noch eindeutiger Text: lieber ein gemeldeter
        Fehlschlag als ein falscher Klick, der als grün durchgeht."""
        finden = self.absp.split("static async finden(s)", 1)[1].split("\n  }", 1)[0]
        self.assertNotIn("|| treffer[0]", finden,
                         u"Der erste Treffer darf nicht mehr als Notlösung "
                         u"geklickt werden")
        self.assertIn("return null", finden)

    def test_server_reicht_die_nummer_durch(self):
        u"""Ohne dieses Feld käme der Abspieler auf ein anderes Element."""
        from djangobase.aufzeichnung_steuerung import Steuerung as St
        sauber = St._pruefen({"art": "klick", "ziel": "button.tab", "nr": 2, "t": 1})
        self.assertEqual(sauber.get("nr"), 2)

    def test_nummer_wird_begrenzt(self):
        u"""Was aus dem Browser kommt, ist Eingabe von außen."""
        from djangobase.aufzeichnung_steuerung import Steuerung as St
        self.assertEqual(
            St._pruefen({"art": "klick", "ziel": "b", "nr": 10 ** 9, "t": 1})["nr"],
            9999)
        self.assertNotIn(
            "nr", St._pruefen({"art": "klick", "ziel": "b", "nr": "hallo", "t": 1}))
