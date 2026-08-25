# -*- coding: utf-8 -*-
u"""Rangliste und Werkzeugwahl - die stillen Wege.

DER AUFTRAG (25.08.2026, Edgar)
===============================
    „mach Nummern für jeden Testcase … wenn die Nummer eines Testcases
     verändert wird, dann rutscht er in den neuen Bereich, die anderen Nummern
     ändern sich"
    „Überlege, ob wir nicht alle Testcases ändern sollen und gleich die
     Werkzeuge … anbiete, damit nicht jede andere Session sich eigene
     Fix-Werkzeuge baut"

WAS HIER FESTGENAGELT WIRD
==========================
Beide Klassen können auf dieselbe Art still versagen: Sie liefern etwas, das
plausibel aussieht, und niemand merkt, dass es falsch ist.

  * Eine Rangliste mit einer doppelten oder übersprungenen Nummer sieht in der
    Tabelle normal aus - bis jemand verschiebt und ein Eintrag verschwindet.
  * Eine Werkzeug-Empfehlung, die das naheliegende Werkzeug WEGLÄSST, ist
    schlimmer als keine: Sie sieht vollständig aus. Genau das passierte beim
    ersten Lauf - „tote-importe" empfahl vier Nachbarn, aber nicht sich selbst.

Beide Fälle sind hier abgedeckt. Ohne Datenbank, ohne Netz: reine Logik gegen
erfundene Werkzeuge - nicht gegen den echten Bestand, denn der ändert sich, und
ein Test, der mit dem Bestand kippt, prüft den Bestand statt die Logik.
"""
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.rangliste import BEREICHE, Rangliste
from djangobase.skills.werkzeugwahl import Werkzeugwahl


class Attrappe:
    u"""Ein Werkzeug, so weit die beiden Klassen es anfassen."""

    def __init__(self, slug, kriterium=0, titel="", zweck="", tut="", behebt=()):
        self.slug = slug
        self.kriterium = kriterium
        self.titel = titel or slug
        self.zweck = zweck
        self.tut = tut
        self.behebt = behebt


class RanglisteTest(SimpleTestCase):
    databases = []

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.pfad = Path(self.ordner.name) / "rang.json"
        # Je Bereich zwei Werkzeuge, damit Verschiebungen über Grenzen gehen.
        self.werkzeuge = []
        for n, b in enumerate(BEREICHE):
            k = b["kriterien"][0]
            self.werkzeuge += [Attrappe("w%d_%s" % (n, i), kriterium=k)
                               for i in ("a", "b")]

    def tearDown(self):
        self.ordner.cleanup()

    def _liste(self):
        return Rangliste(self.pfad)

    # ------------------------------------------------------------ Grundlage
    def test_grundordnung_folgt_den_bereichen(self):
        u"""Ohne Ablage bestimmt das Kriterium die Reihenfolge."""
        folge = self._liste().reihenfolge(self.werkzeuge)
        self.assertEqual(folge[0], "w0_a", "erster Bereich zuerst")
        self.assertEqual(len(folge), len(self.werkzeuge))

    def test_jede_nummer_genau_einmal(self):
        u"""Der Kern der Ansage: EINE eindeutige Nummer je Eintrag.

        Der Rang ist die Position in der Liste - eine Dublette kann es damit
        gar nicht geben. Der Test hält das fest, weil eine spätere Umstellung
        auf gespeicherte Nummern genau hier brechen würde.
        """
        r = self._liste()
        raenge = [r.rang_von(w.slug, self.werkzeuge) for w in self.werkzeuge]
        self.assertEqual(sorted(raenge), list(range(1, len(self.werkzeuge) + 1)))

    # ---------------------------------------------------------- Verschieben
    def test_verschieben_laesst_andere_rutschen(self):
        r = self._liste()
        letzter = self.werkzeuge[-1].slug
        vorher_erster = r.reihenfolge(self.werkzeuge)[0]
        r.verschieben(letzter, 1, self.werkzeuge)
        neu = Rangliste(self.pfad)
        self.assertEqual(neu.rang_von(letzter, self.werkzeuge), 1)
        self.assertEqual(neu.rang_von(vorher_erster, self.werkzeuge), 2,
                         "der vorher Erste muss auf 2 rutschen")

    def test_verschieben_wechselt_den_bereich(self):
        u"""Die Ansage wörtlich: „dann rutscht er in den neuen Bereich".

        Der Bereich hängt an der POSITION, nicht am Kriterium - sonst bliebe
        ein auf Rang 1 gesetztes Werkzeug in seinem alten Abschnitt stehen,
        und die Nummer wäre folgenlos.
        """
        r = self._liste()
        letzter = self.werkzeuge[-1].slug
        r.verschieben(letzter, 1, self.werkzeuge)
        abschnitte = Rangliste(self.pfad).abschnitte(self.werkzeuge)
        oben = [w.slug for _n, w in abschnitte[0]["eintraege"]]
        self.assertIn(letzter, oben, "muss im ERSTEN Bereich stehen")

    def test_bereichsgroessen_bleiben(self):
        u"""Ein Bereich wächst nicht - das letzte Werkzeug fällt hinaus.

        Der ehrliche Preis der Positions-Regel. Ohne ihn wäre der erste Bereich
        nach zehn Verschiebungen die halbe Liste, und die Rangfolge wieder eine
        Kategorie.
        """
        r = self._liste()
        vorher = [len(a["eintraege"]) for a in r.abschnitte(self.werkzeuge)]
        r.verschieben(self.werkzeuge[-1].slug, 1, self.werkzeuge)
        nachher = [len(a["eintraege"])
                   for a in Rangliste(self.pfad).abschnitte(self.werkzeuge)]
        self.assertEqual(vorher, nachher)

    def test_zurueck_auf_grundordnung_loescht_die_datei(self):
        u"""Eine Ablage, die nur wiederholt was der Code sagt, legt ihn still."""
        r = self._liste()
        letzter = self.werkzeuge[-1].slug
        alt = r.rang_von(letzter, self.werkzeuge)
        r.verschieben(letzter, 1, self.werkzeuge)
        self.assertTrue(self.pfad.exists())
        Rangliste(self.pfad).verschieben(letzter, alt, self.werkzeuge)
        self.assertFalse(self.pfad.exists(), "Datei muss verschwinden")

    def test_neues_werkzeug_landet_an_seiner_stelle(self):
        u"""Nicht hinten anhängen - dort sucht es niemand."""
        r = self._liste()
        r.verschieben(self.werkzeuge[-1].slug, 1, self.werkzeuge)
        neu = Attrappe("frisch", kriterium=BEREICHE[0]["kriterien"][0])
        alle = self.werkzeuge + [neu]
        folge = Rangliste(self.pfad).reihenfolge(alle)
        self.assertIn("frisch", folge)
        self.assertLess(folge.index("frisch"), len(folge) - 1,
                        "darf nicht am Ende kleben")

    def test_kaputte_datei_wirft_nicht(self):
        u"""Lieber die Grundordnung als eine tote Seite."""
        self.pfad.write_text("{kein json", encoding="utf-8")
        self.assertEqual(len(Rangliste(self.pfad).reihenfolge(self.werkzeuge)),
                         len(self.werkzeuge))

    def test_ziel_ausserhalb_wird_begrenzt(self):
        u"""0 oder 999 ist ein Vertipper, kein Wunsch nach einer Lücke."""
        r = self._liste()
        r.verschieben(self.werkzeuge[-1].slug, 999, self.werkzeuge)
        raenge = [Rangliste(self.pfad).rang_von(w.slug, self.werkzeuge)
                  for w in self.werkzeuge]
        self.assertEqual(sorted(raenge), list(range(1, len(self.werkzeuge) + 1)))


class WerkzeugwahlTest(SimpleTestCase):
    databases = []

    def setUp(self):
        self.w = [
            Attrappe("tote-importe", 5, "Tote Importe", zweck="findet sie"),
            Attrappe("altlast", 5, "Alter Code", zweck="findet Altlasten"),
            Attrappe("doppelcode", 6, "Doppelter Code", zweck="findet Dubletten"),
            Attrappe("fix-vermerk", 11, "Vermerk setzen", tut="setzt Vermerke",
                     behebt=("dict-versprechen",)),
        ]
        self.f = [Attrappe("fix-importe", 5, "Importe entfernen",
                           tut="entfernt tote Importe")]
        self.wahl = Werkzeugwahl(self.w, self.f)

    def test_ausdrueckliche_nennung_gewinnt(self):
        fund = self.wahl.fuer("dict-versprechen", kriterium=0)
        self.assertEqual([x.slug for x in fund["sicher"]], ["fix-vermerk"])

    def test_naechster_treffer_steht_oben(self):
        u"""Der Fehler des ersten Laufs: „tote-importe" empfahl alles AUSSER
        sich selbst, weil die Kriteriums-Geschwister unsortiert kamen."""
        fund = self.wahl.fuer("tote-importe", kriterium=5)
        self.assertEqual(fund["sicher"][0].slug, "tote-importe")

    def test_fixer_und_pruefer_beide_dabei(self):
        u"""Finden und Beheben sind zwei Werkzeuge - beide gehören genannt."""
        slugs = [x.slug for x in self.wahl.fuer("tote-importe", 5)["sicher"]]
        self.assertIn("fix-importe", slugs)

    def test_fremdes_erbt_nichts(self):
        self.assertEqual(self.wahl.fuer("voellig-anderes", 0),
                         {"sicher": [], "vermutlich": []})

    def test_zeilen_leer_wenn_nichts_gefunden(self):
        u"""Keine Überschrift ohne Inhalt - das stünde unter jedem Fehlschlag."""
        self.assertEqual(self.wahl.zeilen("voellig-anderes", 0), [])

    def test_zeilen_nennen_die_art(self):
        u"""``tote-importe`` gibt es als Prüfer UND als Fixer."""
        text = "\n".join(self.wahl.zeilen("tote-importe", 5))
        self.assertIn("[findet]", text)
        self.assertIn("[behebt]", text)

    # ------------------------------------------------ aus einem Testlauf
    def test_slug_im_testnamen_ist_sicher(self):
        u"""``test_tote_importe`` enthält den Slug - das ist kein Raten.

        Ohne diese Ebene landete der exakte Treffer unter „Vermutlich
        verwandt", während der Testname ihn wörtlich enthielt.
        """
        fund = self.wahl.fuer("test_tote_importe", kriterium=0)
        self.assertIn("tote-importe", [x.slug for x in fund["sicher"]])

    def test_teilwort_trifft_nicht(self):
        u"""Auf Wortgrenzen: „reimportest" enthält kein ``tote-importe``."""
        fund = self.wahl.fuer("test_reimportest_xy", kriterium=0)
        self.assertEqual(fund["sicher"], [])

    def test_ausgabe_findet_fehlschlaege(self):
        text = ("FAIL: test_tote_importe (a.b.C.test_tote_importe)\n"
                "ERROR: test_doppelcode (a.b.C.test_doppelcode)\n")
        block = self.wahl.zu_ausgabe(text)
        self.assertIn("tote-importe", block)
        self.assertIn("doppelcode", block)

    def test_gruener_lauf_bekommt_nichts(self):
        u"""Eine Werkzeugliste unter einem erfolgreichen Lauf wäre genau das
        Rauschen, das den Katalog vorher unlesbar gemacht hat."""
        self.assertEqual(self.wahl.zu_ausgabe("Ran 116 tests\nOK"), "")

    def test_ausgabe_deckelt_bei_drei(self):
        u"""Vierzig rote Tests heißt nicht vierzig Empfehlungsblöcke."""
        text = "".join("FAIL: test_tote_importe_%d (a.b.C.t)\n" % n
                       for n in range(9))
        self.assertLessEqual(self.wahl.zu_ausgabe(text).count("Dafür gibt es"), 3)
