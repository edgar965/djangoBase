# -*- coding: utf-8 -*-
u"""Der Prüfer für ``data-sort``-Werte muss die Fälle vom 01.09.2026 finden.

WARUM ES IHN GIBT
=================
Auf ``/hilfe/ki-modelle/`` sortierte die Spalte „Parameter" sichtbar falsch:
Ein Modell mit **137 Millionen** Parametern stand über einem mit **122
Milliarden**, und ein 70,6-Milliarden-Modell galt als das größte überhaupt -
vor 550B. Zwei Ursachen, beide im Attribut:

    data-sort="137M"    ->  die Einheit faellt weg, es bleibt 137
    data-sort="20.9B"   ->  der Punkt gilt als Tausenderzeichen, es wird 209

Dazu die dritte Sorte: ``data-sort="{{ x|default:'' }}"`` mit ``x = 0``.
Django haelt 0 fuer falsy, macht daraus einen Leerstring - und die Spalte
sortiert gar nicht mehr (Befund GPU-Bedarf, dort ist jeder Wert 0).

WARUM DIE VORHANDENEN WERKZEUGE NICHTS FANDEN
=============================================
* Die **Tabellen-Konformitaet** prueft ``class="sortable"`` und
  ``data-sort-key`` - beides Attribute an der ``<table>``. Die Zellwerte sieht
  sie nie an; die Seite war nach ihrer Definition konform.
* **Doppelcode** sucht Wiederholungen ab 6 Zeilen. Die wiederholten
  Tabellenbloecke dort sind 3-5 Zeilen lang - gemessen: mindestens=6 liefert
  0 Befunde, mindestens=3 liefert 3.

Ein falscher Sortierwert ist die stille Sorte Fehler: Die Zeilen stehen in
EINER Reihenfolge, nur nicht in der richtigen. Nichts wirft, nichts loggt.

BDD - GEGEBEN / DANN
====================
    EinheitImSchluessel   ... gemeldet (137M, 20.9B, "3 GB")
    DezimalpunktImWert    ... gemeldet (20.9 -> 209)
    LeerBeiGefuellterZelle... gemeldet (der |default-Fall)
    LeerBeiLeererZelle    ... KEIN Befund
    SauberDeutsch         ... KEIN Befund (0,137 / 550 / 1.234,5)
    DatumUndText          ... KEIN Befund (ISO-Datum, Note, Bruch)
"""
from django.test import SimpleTestCase

from djangobase.skills.sortierwerte import Sortierwert, ZELLE


class SortierwertLesart(SimpleTestCase):
    u"""``zahl()`` muss lesen wie ``tabellen_sortierung._zahl`` im Browser."""

    databases = []

    def test_deutsche_zahlen(self):
        self.assertEqual(Sortierwert.zahl("0,137"), 0.137)
        self.assertEqual(Sortierwert.zahl("550"), 550.0)
        self.assertEqual(Sortierwert.zahl("1.234,5"), 1234.5)
        self.assertEqual(Sortierwert.zahl("−1.234,5 €"), -1234.5)

    def test_punkt_gilt_als_tausenderzeichen(self):
        u"""DER KERN DES FEHLERS: „20.9" wird im Browser zu 209, nicht zu 20,9."""
        self.assertEqual(Sortierwert.zahl("20.9"), 209.0,
                         u"wenn das hier 20.9 ergibt, weicht der Pruefer vom JS ab")

    def test_einheit_wird_ignoriert(self):
        u"""„137M" liest das JS als 137 - die Einheit ist weg."""
        self.assertEqual(Sortierwert.zahl("137M"), 137.0)
        self.assertEqual(Sortierwert.zahl("20.9B"), 209.0)

    def test_bruch_nach_wert(self):
        self.assertAlmostEqual(Sortierwert.zahl("3/4"), 0.75)

    def test_kein_zahlenwert(self):
        self.assertIsNone(Sortierwert.zahl(""))
        self.assertIsNone(Sortierwert.zahl("2026-08-11"))
        self.assertIsNone(Sortierwert.zahl(None))


class SortierwertBefunde(SimpleTestCase):
    u"""Welche Zellen gemeldet werden - und welche ausdruecklich nicht."""

    databases = []

    def _befund(self, attribut, text):
        return Sortierwert(attribut, text).befund()

    # ------------------------------------------------------------ meldet

    def test_einheit_im_schluessel(self):
        u"""DER ECHTE FALL: data-sort=\"137M\" neben der Anzeige „137M\"."""
        b = self._befund("137M", "137M")
        self.assertIsNotNone(b, u"der Fall vom 01.09.2026 wird NICHT gemeldet")
        self.assertIn("Einheit", b)

    def test_dezimalpunkt_im_schluessel(self):
        b = self._befund("20.9", "20,9 GB")
        self.assertIsNotNone(b)
        self.assertIn("Dezimalpunkt", b)

    def test_leerer_schluessel_bei_gefuellter_zelle(self):
        u"""Der ``|default``-Fall: Zelle zeigt 0,0 GB, data-sort ist leer."""
        b = self._befund("", "0,0 GB")
        self.assertIsNotNone(b, u"eine Zahl in der Zelle ohne Sortierwert ist ein Fehler")
        self.assertIn("default_if_none", b)

    def test_text_im_schluessel_bei_zahl_in_der_zelle(self):
        b = self._befund("k.A.", "17,4 GB")
        self.assertIsNotNone(b)

    # ------------------------------------------------------ meldet NICHT

    def test_leerer_schluessel_bei_leerer_zelle(self):
        u"""GEGENPROBE: „kein Wert" ist voellig in Ordnung.

        Ohne diese Ausnahme meldete der Pruefer jede „—"-Zelle und waere die
        Fehlalarm-Maschine, vor der `~/.claude/rules/analysewerkzeuge.md` warnt."""
        self.assertIsNone(self._befund("", "—"))
        self.assertIsNone(self._befund("", ""))
        self.assertIsNone(self._befund("", "k.A."))

    def test_saubere_deutsche_werte(self):
        self.assertIsNone(self._befund("0,137", "137M"))
        self.assertIsNone(self._befund("550", "550B"))
        self.assertIsNone(self._befund("1.234,5", "1.234,5 €"))

    def test_prozent_bleibt_erlaubt(self):
        u"""„15 %" ist ein gewachsenes Anzeigeformat, kein Befund."""
        self.assertIsNone(self._befund("15", "15 %"))

    def test_datum_und_text_sind_erlaubt(self):
        u"""Nicht jede Spalte ist numerisch - ISO-Datum sortiert als Text korrekt."""
        self.assertIsNone(self._befund("2026-08-11", "11.08.2026"))
        self.assertIsNone(self._befund("A", "A"))


class ZellenErkennung(SimpleTestCase):
    u"""Findet der Ausdruck die Zellen im echten Markup?"""

    databases = []

    def test_td_und_th_mit_und_ohne_klasse(self):
        html = ('<tr><td class="num" data-sort="0,137">137M</td>'
                '<th data-sort="5">fünf</th>'
                '<td>ohne Attribut</td></tr>')
        treffer = ZELLE.findall(html)
        self.assertEqual(len(treffer), 2, u"td UND th, Zellen ohne data-sort nicht")
        self.assertEqual(treffer[0], ("0,137", "137M"))

    def test_markup_in_der_zelle_wird_entfernt(self):
        u"""Der sichtbare Text zaehlt, nicht das Markup drumherum."""
        w = Sortierwert("", '<span class="klein">0,0</span> GB')
        self.assertEqual(w.text, "0,0  GB")
        self.assertIsNotNone(w.befund(), u"die Zahl steckte im span und wurde uebersehen")
