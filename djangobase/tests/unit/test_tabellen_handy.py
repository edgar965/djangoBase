# -*- coding: utf-8 -*-
"""`TabellenHandy.vorbereiten` über `TabellenDaten` — Handy-Karten nur, wenn eine Spalte eine Rolle hat.

Anlass (21.11.2026): Die Heizung (StayNestor) zeigt Tabellen mit bis zu 16 Spalten; auf dem Handy
wird jede Zeile eine Karte. Die Vorlage schreibt `label`/`handy` als `data-label`/`data-handy` an die
Zellen. Geprüft wird auch, was UNVERÄNDERT bleiben muss: Tabellen ohne Rolle (alle bisherigen
Aufrufer) und geteilte Zellen-Objekte."""

from django.test import SimpleTestCase

from djangobase.tabellen_daten import TabellenDaten
from djangobase.tabellen_handy import TabellenHandy

sp, z, tab = TabellenDaten.spalte, TabellenDaten.zelle, TabellenDaten.tabelle


class TabellenHandyTest(SimpleTestCase):
    def test_ohne_rolle_unveraendert(self):
        spalten = [sp("Name", "name"), sp("Ist", "ist", num=True)]
        zeilen = [{"zellen": [z("Bad"), z("21,0")]}]
        t = tab("x", spalten, zeilen)
        self.assertNotIn("klasse", t)
        self.assertNotIn("handy", spalten[0])
        self.assertEqual(set(t["zeilen"][0]["zellen"][0]), {"html"})

    def test_rollen_und_beschriftung(self):
        spalten = [
            sp("<b>Name</b>", "name", handy="titel"),
            sp("Ist", "ist", handy="kopf"),
            sp("Gerät", "typ"),
        ]
        t = tab("x", spalten, [{"zellen": [z("Bad"), z("21,0"), z("HmIP-eTRV")]}])
        zellen = t["zeilen"][0]["zellen"]
        self.assertEqual(t["klasse"], TabellenHandy.KLASSE)
        self.assertEqual([c["handy"] for c in zellen], ["titel", "kopf", "mehr"])  # ohne Rolle -> mehr
        self.assertEqual(zellen[0]["label"], "Name")  # ohne HTML

    def test_geteilte_zelle_wird_kopiert(self):
        leer = z("–")
        spalten = [sp("A", "a", handy="karte"), sp("B", "b", handy="mehr")]
        t = tab("x", spalten, [{"zellen": [leer, leer]}])
        a, b = t["zeilen"][0]["zellen"]
        self.assertEqual((a["label"], b["label"]), ("A", "B"))
        self.assertNotIn("label", leer)

    def test_colspan_rueckt_weiter(self):
        spalten = [sp("A", "a", handy="titel"), sp("B", "b", handy="karte"), sp("C", "c", handy="mehr")]
        t = tab("x", spalten, [{"zellen": [{"html": "ab", "colspan": 2}, z("c")]}])
        self.assertEqual([c["label"] for c in t["zeilen"][0]["zellen"]], ["A", "C"])

    def test_fertige_kette_und_gruppe_bleiben(self):
        spalten = [sp("A", "a", handy="titel")]
        zeilen = [{"html": "<td>x</td>"}, {"gruppe": True, "zellen": [z("Abschnitt")]}]
        tab("x", spalten, zeilen)
        self.assertNotIn("zellen", zeilen[0])
        self.assertNotIn("label", zeilen[1]["zellen"][0])

    def test_unbekannte_rolle(self):
        with self.assertRaises(ValueError):
            tab("x", [sp("A", "a", handy="oben")], [])
