# -*- coding: utf-8 -*-
"""Wächter für Hilfe → Aktuell (rollierendes Fenster).

Geprüft wird, was an einem Feed schiefgehen kann, ohne dass es auffällt:

* **Das Fenster rollt wirklich.** Ein Feed, der nur wächst, ist kein Fenster,
  sondern eine Halde in einem Verzeichnis, das niemand beobachtet.
* **Eine kaputte Zeile macht die Seite nicht leer.** Wird beim Schreiben
  abgebrochen, steht eine halbe JSON-Zeile in der Datei — dann müssen die
  übrigen Einträge trotzdem erscheinen.
* **Kürzungen sind sichtbar.** Stillschweigend abschneiden lässt den Leser
  glauben, mehr sei nicht da gewesen.
* **Der Schreibweg ist der Verwaltungsbefehl, nicht HTTP.** Es darf keinen
  Endpunkt geben, über den eine fremde Webseite in den Feed schreibt.
"""
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from djangobase.aktuell import AktuellFeed
from djangobase.tests.base import BasisTest, StoreIsolationMixin


class AktuellFeedTest(BasisTest):
    def setUp(self):
        self.datei = Path(tempfile.mkdtemp(prefix="aktuell-")) / "aktuell.jsonl"
        self.feed = AktuellFeed(self.datei)

    def test_neueste_zuerst(self):
        self.feed.anhaengen("erster")
        self.feed.anhaengen("zweiter")
        titel = [e["titel"] for e in self.feed.lesen()]
        self.assertEqual(titel, ["zweiter", "erster"])

    def test_fenster_rollt(self):
        """Der Kern der Seite: Es bleiben die neuesten N, nicht alle.

        `LUFT = 0` gehört hier dazu: Gekürzt wird im Betrieb erst ab
        MAX + LUFT, damit das Kürzen ein seltener Vorgang ist (nur dabei können
        zwei Schreiber kollidieren). Die Zusage lautet deshalb „ungefähr MAX,
        höchstens MAX + LUFT" — nicht „genau MAX". Dieser Test prüft die
        Mechanik, `test_luft_erlaubt_ein_paar_zeilen_mehr` die Zusage."""
        self.feed.MAX_EINTRAEGE, self.feed.LUFT = 5, 0
        for i in range(12):
            self.feed.anhaengen("Eintrag %d" % i)
        eintraege = self.feed.lesen()
        self.assertEqual(len(eintraege), 5)
        self.assertEqual(eintraege[0]["titel"], "Eintrag 11")
        self.assertEqual(eintraege[-1]["titel"], "Eintrag 7")
        # Und die Datei selbst ist mitgeschrumpft, nicht nur die Anzeige.
        self.assertEqual(len(self.datei.read_text(encoding="utf-8").strip().split("\n")), 5)

    def test_luft_erlaubt_ein_paar_zeilen_mehr(self):
        """Die Zusage ist eine Größenordnung, keine Zeile — und das ist gewollt."""
        self.feed.MAX_EINTRAEGE, self.feed.LUFT = 5, 10
        for i in range(12):
            self.feed.anhaengen("Eintrag %d" % i)
        anzahl = len(self.feed.lesen())
        self.assertEqual(anzahl, 12, "vor MAX+LUFT darf nicht gekuerzt werden")
        for i in range(6):
            self.feed.anhaengen("noch %d" % i)
        # 18 geschrieben; beim 16. wurde auf 5 gekuerzt, danach kamen zwei dazu.
        # Die Zusage lautet „hoechstens MAX + LUFT" — nicht „genau MAX".
        anzahl = len(self.feed.lesen())
        self.assertLessEqual(anzahl, self.feed.MAX_EINTRAEGE + self.feed.LUFT,
                             "ab MAX+LUFT muss gekuerzt werden")
        self.assertLess(anzahl, 18, "es wurde gar nicht gekuerzt")
        self.assertEqual(self.feed.lesen()[0]["titel"], "noch 5", "neuester fehlt")

    def test_kuerzen_verliert_keinen_gleichzeitigen_eintrag(self):
        """DER FUND AUS DEM REVIEW DIESES WERKZEUGS (13.08.2026).

        Anhängen ist unteilbar, das Kürzen war es nicht: Wer die Datei liest,
        auf 200 Zeilen schneidet und ersetzt, überschreibt einen Eintrag, der
        zwischen Lesen und Ersetzen dazugekommen ist.

        Hier wird genau dieses Fenster nachgestellt: Während `_kuerzen` läuft,
        hängt ein zweiter Schreiber an. Danach muss dessen Eintrag noch da sein."""
        self.feed.MAX_EINTRAEGE, self.feed.LUFT = 5, 0
        for i in range(6):
            self.feed.anhaengen("alt %d" % i)

        echtes_lesen = AktuellFeed._datei_kuerzen
        dazwischen = {"getan": False}

        def kuerzen_mit_stoerung(selbst):
            if not dazwischen["getan"]:
                dazwischen["getan"] = True
                # Ein zweiter Schreiber, GENAU im kritischen Fenster.
                with open(selbst.pfad, "a", encoding="utf-8") as f:
                    f.write('{"zeit": "x", "titel": "dazwischen", "art": "notiz", '
                            '"quelle": "", "text": ""}\n')
            return echtes_lesen(selbst)

        with mock.patch.object(AktuellFeed, "_datei_kuerzen", kuerzen_mit_stoerung):
            self.feed.anhaengen("neu")

        titel = [e["titel"] for e in self.feed.lesen()]
        self.assertIn("dazwischen", titel,
                      "der gleichzeitige Eintrag wurde beim Kuerzen ueberschrieben")
        self.assertIn("neu", titel)

    def test_sperre_verhindert_gleichzeitiges_kuerzen(self):
        """Hält ein anderer Prozess die Sperre, wird nicht gekürzt — die Datei
        ist dann ein paar Zeilen zu lang, und das ist die richtige Wahl."""
        self.feed.MAX_EINTRAEGE, self.feed.LUFT = 3, 0
        for i in range(8):
            self.feed.anhaengen("e %d" % i)
        sperre = self.feed.pfad.with_suffix(self.feed.pfad.suffix + ".lock")
        sperre.write_text("", encoding="utf-8")     # fremder Prozess kürzt gerade
        try:
            self.feed.anhaengen("waehrend der Sperre")
            self.assertGreater(len(self.feed.lesen()), self.feed.MAX_EINTRAEGE,
                               "trotz fremder Sperre gekuerzt")
            self.assertEqual(self.feed.lesen()[0]["titel"], "waehrend der Sperre")
        finally:
            sperre.unlink()

    def test_kaputte_zeile_wird_uebersprungen(self):
        self.feed.anhaengen("gut 1")
        with open(self.datei, "a", encoding="utf-8") as f:
            f.write('{"titel": "halb geschrieben\n')      # abgebrochene Zeile
        self.feed.anhaengen("gut 2")
        titel = [e["titel"] for e in self.feed.lesen()]
        self.assertEqual(titel, ["gut 2", "gut 1"])

    def test_langer_text_wird_sichtbar_gekuerzt(self):
        self.feed.MAX_ZEICHEN = 100
        self.feed.anhaengen("lang", text="x" * 500)
        text = self.feed.lesen()[0]["text"]
        self.assertLess(len(text), 300)
        self.assertIn("gekuerzt", text)

    def test_filter_nach_art(self):
        self.feed.anhaengen("a", art="fix")
        self.feed.anhaengen("b", art="befund")
        self.assertEqual([e["titel"] for e in self.feed.lesen(art="fix")], ["a"])

    def test_leeren(self):
        self.feed.anhaengen("weg damit")
        self.feed.leeren()
        self.assertEqual(self.feed.lesen(), [])

    def test_zeile_ist_gueltiges_json(self):
        """Von Hand lesbar sein war der Grund für JSONL statt Datenbank."""
        self.feed.anhaengen("titel", text="zwei\nzeilen", art="messung", quelle="cli")
        d = json.loads(self.datei.read_text(encoding="utf-8").strip())
        self.assertEqual(d["titel"], "titel")
        self.assertEqual(d["text"], "zwei\nzeilen")
        self.assertEqual(d["quelle"], "cli")


class AktuellBefehlTest(BasisTest):
    """Der Schreibweg: `manage.py aktuell`."""

    def setUp(self):
        self.verzeichnis = Path(tempfile.mkdtemp(prefix="aktuell-cmd-"))
        self.datei = self.verzeichnis / "aktuell.jsonl"

    def test_befehl_schreibt_eintrag(self):
        with self.settings(DJANGOBASE={"aktuell_datei": str(self.datei)}):
            aus = StringIO()
            call_command("aktuell", "--titel", "Aus der CLI", "--art", "fix",
                         "--text", "56 Tests gruen", stdout=aus)
            self.assertIn("Aus der CLI", aus.getvalue())
            eintraege = AktuellFeed(self.datei).lesen()
        self.assertEqual(eintraege[0]["titel"], "Aus der CLI")
        self.assertEqual(eintraege[0]["art"], "fix")
        self.assertEqual(eintraege[0]["quelle"], "claude-cli")

    def test_befehl_ohne_titel_scheitert(self):
        from django.core.management.base import CommandError
        with self.settings(DJANGOBASE={"aktuell_datei": str(self.datei)}):
            with self.assertRaises(CommandError):
                call_command("aktuell", "--text", "ohne Titel", stdout=StringIO())

    def test_unbekannte_art_warnt_aber_schreibt(self):
        with self.settings(DJANGOBASE={"aktuell_datei": str(self.datei)}):
            aus = StringIO()
            call_command("aktuell", "--titel", "t", "--art", "quatsch", stdout=aus)
            self.assertIn("Unbekannte Art", aus.getvalue())
            self.assertEqual(len(AktuellFeed(self.datei).lesen()), 1)


class AktuellSeiteTest(BasisTest):
    def setUp(self):
        self.datei = Path(tempfile.mkdtemp(prefix="aktuell-seite-")) / "aktuell.jsonl"

    def test_seite_zeigt_eintraege(self):
        AktuellFeed(self.datei).anhaengen("Ein Befund", text="Zeile A", art="befund")
        with self.settings(DJANGOBASE={"zugriff": "staff", "aktuell_datei": str(self.datei)}):
            a = self.staff_client().get(reverse("djangobase:aktuell"))
        self.assertEqual(a.status_code, 200)
        self.assertContains(a, "Ein Befund")
        self.assertContains(a, "Zeile A")

    def test_leere_seite_erklaert_den_schreibweg(self):
        """Ohne Einträge muss die Seite sagen, wie man welche bekommt — sie
        erscheint in jedem Projekt, auch dort wo noch nie etwas geschrieben wurde."""
        with self.settings(DJANGOBASE={"zugriff": "staff", "aktuell_datei": str(self.datei)}):
            a = self.staff_client().get(reverse("djangobase:aktuell"))
        self.assertContains(a, "manage.py aktuell")

    def test_daten_endpunkt_liefert_json(self):
        AktuellFeed(self.datei).anhaengen("Per JSON")
        with self.settings(DJANGOBASE={"zugriff": "staff", "aktuell_datei": str(self.datei)}):
            a = self.staff_client().get(reverse("djangobase:aktuell_daten"))
        self.assertEqual(a.json()["eintraege"][0]["titel"], "Per JSON")

    def test_kein_schreib_endpunkt(self):
        """Geschrieben wird über den Verwaltungsbefehl. Ein POST auf die Seite
        darf nichts anlegen — sonst könnte eine fremde Webseite den Feed füllen."""
        with self.settings(DJANGOBASE={"zugriff": "staff", "aktuell_datei": str(self.datei)}):
            a = self.staff_client().post(reverse("djangobase:aktuell"),
                                         data={"titel": "geschmuggelt"})
            self.assertIn(a.status_code, (403, 405))
            self.assertEqual(AktuellFeed(self.datei).lesen(), [])


@override_settings(DJANGOBASE={"zugriff": "staff"})
class NavigationTest(BasisTest):
    """Beide neuen Seiten sollen in JEDEM Projekt im Menü stehen — ohne Schalter."""

    def test_menue_zeigt_aktuell_und_review_ohne_konfiguration(self):
        a = self.staff_client().get(reverse("djangobase:versionen"))
        self.assertContains(a, reverse("djangobase:aktuell"))
        self.assertContains(a, reverse("djangobase:review"))
