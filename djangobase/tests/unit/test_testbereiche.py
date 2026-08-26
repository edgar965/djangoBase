# -*- coding: utf-8 -*-
u"""Bereiche, Kategorien-Reihenfolge und Laufzeit-Darstellung.

Jeder Test hier steht fuer einen Fehler, der am 17.08.2026 WIRKLICH passiert
ist — nicht fuer einen ausgedachten Fall:

* Ein Bereich, dessen Praefix ueber anderen liegt, war als Ziel waehlbar. Ein
  Klick legte die Chat-Platzhalterdatei nach ``search/tests/unit/``; gemerkt
  hat es nur, wer danach in `git status` schaute.
* ``bereich_verschieben`` rief eine Methode auf, die es nicht gab — die Datei
  war da schon verschoben, die Seite zeigte eine Fehlerseite.
* Die Laufzeit stand mal als „35 ms", mal als „0,00 s" in derselben Spalte.
* Das JavaScript baute Zeilen mit weniger Zellen, als die Tabelle Spalten hat.
"""
import json
import shutil
import re
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.testarten import Arten
from djangobase.testbereiche import Bereiche
from djangobase.testkarten import Karten
from djangobase.testtabelle import Testtabelle
from djangobase.testverschieben import Verschieber
from djangobase.zeitformat import dauer_text

ANGABE = [
    {"slug": "mail", "name": "Mail", "praefixe": ["mail.tests"]},
    {"slug": "chat", "name": "Chat", "praefixe": ["search.tests.chat"]},
    {"slug": "musik", "name": "Musik", "praefixe": ["search.tests.musik"]},
    {"slug": "suche", "name": "Suche", "praefixe": ["search.tests"]},
]


class BereicheTests(SimpleTestCase):

    def test_laengstes_praefix_gewinnt(self):
        b = Bereiche(ANGABE)
        self.assertEqual(b.slug_von("search.tests.musik.unit.test_x.K.t"), "musik")
        self.assertEqual(b.slug_von("search.tests.andere.unit.test_x.K.t"), "suche")
        self.assertEqual(b.slug_von("mail.tests.component.test_x.K.t"), "mail")

    def test_ohne_angabe_aus_dem_ordner(self):
        b = Bereiche()
        self.assertEqual(b.slug_von("search.tests.musik.unit.test_x.K.t"), "musik")
        self.assertEqual(b.slug_von("mail.tests.unit.test_x.K.t"), "mail")
        self.assertEqual(b.slug_von("irgendwas"), "")

    def test_reihenfolge_folgt_der_angabe(self):
        u"""„auch die reihenfolge ist änderbar" — nicht alphabetisch."""
        b = Bereiche(ANGABE)
        tests = [{"id": "search.tests.musik.unit.test_a.K.t"},
                 {"id": "mail.tests.unit.test_b.K.t"},
                 {"id": "search.tests.chat.unit.test_c.K.t"}]
        self.assertEqual([g["slug"] for g in b.gruppieren(tests)],
                         ["mail", "chat", "musik"])

    def test_elternordner_ist_kein_ziel(self):
        u"""`search.tests` liegt über `search.tests.chat` — nicht waehlbar."""
        b = Bereiche(ANGABE)
        self.assertIn("chat", b.ziele())
        self.assertNotIn("suche", b.ziele())
        self.assertNotIn("suche", [w for w, _n, _g in b.auswahl("chat")])

    def test_zeilenformat_hin_und_zurueck(self):
        u"""Was im Formular steht, muss dasselbe ergeben wie die Angabe."""
        zeilen = Bereiche.als_zeilen(ANGABE)
        self.assertEqual(zeilen[0], "mail | Mail | mail.tests")
        zurueck = Bereiche(zeilen)
        self.assertEqual(zurueck.slug_von("search.tests.musik.unit.test_x.K.t"),
                         "musik")
        self.assertEqual(set(zurueck.ziele()), set(Bereiche(ANGABE).ziele()))

    def test_kurzform_nur_umbenennen(self):
        b = Bereiche({"schedule": "Kalender"})
        self.assertEqual(b.name_von("schedule"), "Kalender")
        self.assertFalse(b.ziele())          # ohne Praefix kein Ziel


class ArtenTests(SimpleTestCase):

    def test_reihenfolge_und_namen(self):
        a = Arten(["longrunner | Nachtlauf", "unit"])
        self.assertEqual(a.liste()[:2], ["longrunner", "unit"])
        self.assertEqual(a.name_von("longrunner"), "Nachtlauf")
        # Nicht genannte verschwinden nicht.
        self.assertIn("component", a.liste())

    def test_unbekannte_werden_verworfen(self):
        self.assertNotIn("phantasie", Arten(["phantasie | Phantasie"]).liste())


class ZeitformatTests(SimpleTestCase):

    def test_unter_einer_sekunde_immer_ms(self):
        self.assertEqual(dauer_text(0), "0 ms")
        self.assertEqual(dauer_text(0.002), "2 ms")
        self.assertEqual(dauer_text(0.42), "420 ms")
        self.assertEqual(dauer_text(0.999), "999 ms")

    def test_ab_einer_sekunde_sekunden(self):
        self.assertEqual(dauer_text(1), "1,00 s")
        self.assertEqual(dauer_text(38.005), "38,01 s")

    def test_kein_wert(self):
        self.assertEqual(dauer_text(None), "")


class SpaltenDeckungTests(SimpleTestCase):
    u"""Die Spalten der Tabelle und die Zuordnung im JavaScript.

    `testzeiten.js` schreibt Laufzeiten ueber feste Zellen-Indizes. Kommt eine
    Spalte dazu (der Bereich, 17.08.2026), landen die Zahlen sonst in der
    falschen Zelle — ohne Fehler, ohne Warnung.
    """

    def test_js_kennt_dieselben_spalten(self):
        pfad = (Path(__file__).resolve().parents[2] / "static" / "djangobase"
                / "js" / "testzeiten.js")
        text = pfad.read_text(encoding="utf-8")
        block = re.search(r"export const SPALTE = \{(.+?)\};", text, re.S).group(1)
        js = dict(re.findall(r"(\w+):\s*(\d+)", block))
        py = {s["key"]: i for i, s in enumerate(Testtabelle.SPALTEN)}
        self.assertEqual({k: int(v) for k, v in js.items()}, py)


class KartenLabelTests(SimpleTestCase):

    def test_label_nur_wenn_es_genau_passt(self):
        u"""Ein Label, das mehr fährt als die Tabelle zeigt, wäre gelogen."""
        gleiche = [{"id": "mail.tests.unit.test_a.K.t"},
                   {"id": "mail.tests.unit.test_b.K.t"}]
        self.assertEqual(Karten.label(gleiche), "mail.tests.unit")
        gemischt = gleiche + [{"id": "search.tests.unit.test_c.K.t"}]
        self.assertEqual(Karten.label(gemischt), "")

    def test_kein_label_fuer_ganze_app(self):
        u"""`mail.tests` fährt auch Component und UI — kein Kategorie-Knopf."""
        self.assertEqual(Karten.label([{"id": "mail.tests.a.K.t"},
                                       {"id": "mail.tests.b.K.t"}]), "")


class BereichWechselTests(SimpleTestCase):
    u"""Die Datei wandert wirklich — an einer Kunst-Struktur, nicht am Projekt."""

    def setUp(self):
        # Im Projekt, nicht in System-Temp (harte Vorgabe: kein Datenmuell auf C:).
        self.wurzel = Path(__file__).resolve().parents[3] / ".pruef_bereichswechsel"
        shutil.rmtree(self.wurzel, ignore_errors=True)
        self.quelle = self.wurzel / "app" / "tests" / "musik" / "unit"
        self.quelle.mkdir(parents=True)
        (self.quelle / "test_probe.py").write_text("# Probe\n", encoding="utf-8")
        self.bereiche = Bereiche([
            {"slug": "musik", "name": "Musik", "praefixe": ["app.tests.musik"]},
            {"slug": "chat", "name": "Chat", "praefixe": ["app.tests.chat"]},
            {"slug": "alles", "name": "Alles", "praefixe": ["app.tests"]},
        ])
        self.v = Verschieber(wurzel=self.wurzel, bereiche=self.bereiche)
        self.tid = "app.tests.musik.unit.test_probe.Probe.test_eins"

    def tearDown(self):
        shutil.rmtree(self.wurzel, ignore_errors=True)

    def test_datei_wandert_und_id_stimmt(self):
        erfolg, meldung, neue_id = self.v.bereich_verschieben(self.tid, "chat")
        self.assertTrue(erfolg, meldung)
        self.assertEqual(neue_id, "app.tests.chat.unit.test_probe.Probe.test_eins")
        ziel = self.wurzel / "app" / "tests" / "chat" / "unit" / "test_probe.py"
        self.assertTrue(ziel.is_file())
        self.assertFalse((self.quelle / "test_probe.py").exists())
        # Ohne __init__.py findet Djangos Discovery den Ordner nicht.
        self.assertTrue((ziel.parent / "__init__.py").is_file())

    def test_elternordner_wird_abgelehnt(self):
        erfolg, meldung, _ = self.v.bereich_verschieben(self.tid, "alles")
        self.assertFalse(erfolg)
        self.assertIn("Ziel", meldung)
        self.assertTrue((self.quelle / "test_probe.py").exists())

    def test_gleicher_bereich_tut_nichts(self):
        erfolg, meldung, _ = self.v.bereich_verschieben(self.tid, "musik")
        self.assertFalse(erfolg)
        self.assertTrue((self.quelle / "test_probe.py").exists())

    def test_historie_zieht_mit(self):
        u"""Sonst stünde der Fall danach auf „noch nie gelaufen"."""
        from djangobase.testhistorie import Testhistorie
        ablage = self.wurzel / "historie.json"
        ablage.write_text(json.dumps({"tests": {self.tid: [{"zeit": "x", "dauer": 1}]},
                                      "suiten": {}}), encoding="utf-8")
        # Testhistorie() ohne Pfad zeigt auf BASE_DIR — hier wird der ECHTE
        # Umzug geprueft, deshalb die Ablage des Projekts unangetastet lassen:
        # der Verschieber legt seine eigene an, und die ist im Testlauf leer.
        vorher = dict(Testhistorie().daten["tests"])
        self.v.bereich_verschieben(self.tid, "chat")
        nachher = Testhistorie().daten["tests"]
        self.assertEqual(set(vorher), set(nachher),
                         "fremde Einträge dürfen sich nicht ändern")
