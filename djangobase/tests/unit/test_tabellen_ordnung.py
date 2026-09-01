# -*- coding: utf-8 -*-
u"""`data-sort-aus`: eine Tabelle, deren Zeilenfolge etwas bedeutet.

DER FALL (31.08.2026, Projekt assistant)
========================================
19 von 45 Datentabellen trugen kein ``class="sortable"``. Bei den meisten
war das RICHTIG: UStVA, EUeR, Einkommensteuer, BWA, Stundenzettel und zwei
Druckansichten. Ihre Zeilenfolge ist die Aussage - eine BWA nach Betrag
sortiert ist keine BWA mehr.

Ohne eine Marke dafuer bleiben nur zwei schlechte Wege: die Tabellen als
``plain``/``doku`` auszugeben (falsch - es sind Daten, keine Erklaerung)
oder eine Sortierung anzubieten, die den Bericht zerstoert.

Die gemerkten SPALTENBREITEN bleiben Pflicht: Sie aendern keine
Reihenfolge, und gerade in einem Bericht will man die Kontospalte breiter
ziehen. ``tabellen_auto.js`` bindet dafuer auf ``table[data-sort-key]``,
ganz ohne ``sortable``.
"""
import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

# DAS MODUL, NICHT DIE KLASSE (31.08.2026): Ein importierter TestCase wird
# vom Testlaeufer im importierenden Modul NOCH EINMAL eingesammelt und
# gefahren - hier lief dadurch die ganze Konformitaetspruefung des Projekts
# in einem Unittest mit, samt ihrer Befunde.
from djangobase.tests.konform import test_tabellen

__all__ = ["OrdnungZaehltTest"]


#: Eine Vorlage mit genau einer Tabelle - Attribute werden eingesetzt.
VORLAGE = """<table %s>
<thead><tr><th>Konto</th><th>Betrag</th></tr></thead>
<tbody><tr><td>Umsatzerloese</td><td>1,00</td></tr></tbody>
</table>
"""


class OrdnungZaehltTest(SimpleTestCase):
    u"""Die Marke nimmt von der Sortier-Pflicht aus - und nur davon."""

    databases = []

    def _pruefen(self, attribute):
        u"""Eine Wegwerf-Vorlage bauen und die beiden Regeln darauf fahren.

        Liefert (fehlt_sortable, fehlt_schluessel) als Wahrheitswerte.
        """
        ordner = Path(tempfile.mkdtemp(prefix="djb_tabellen_"))
        self.addCleanup(shutil.rmtree, ordner, True)
        (ordner / "templates").mkdir()
        (ordner / "templates" / "seite.html").write_text(
            VORLAGE % attribute, encoding="utf-8")
        with override_settings(BASE_DIR=str(ordner),
                               DJANGOBASE_KONFORM_AUS=[],
                               DJANGOBASE_KONFORM_TABELLEN_AUS=[]):
            tabellen = test_tabellen.datentabellen()
        self.assertEqual(len(tabellen), 1, tabellen)
        _pfad, attr = tabellen[0]
        marke = test_tabellen.TabellenKonformTest.ORDNUNG_ZAEHLT
        ohne_sortierung = ("sortable" not in attr.lower()
                           and marke not in attr.lower())
        return ohne_sortierung, "data-sort-key" not in attr.lower()

    def test_ohne_alles_fehlt_beides(self):
        u"""Gegenprobe: Die Regeln greifen ueberhaupt."""
        self.assertEqual(self._pruefen('class="bwa-table"'), (True, True))

    def test_marke_nimmt_von_der_sortierung_aus(self):
        self.assertEqual(
            self._pruefen('class="bwa-table" data-sort-aus '
                          'data-sort-key="bwa"'),
            (False, False))

    def test_marke_ersetzt_den_schluessel_nicht(self):
        u"""Breiten bleiben Pflicht - sie aendern keine Reihenfolge."""
        self.assertEqual(self._pruefen('class="bwa-table" data-sort-aus'),
                         (False, True))

    def test_sortierbare_tabelle_braucht_die_marke_nicht(self):
        self.assertEqual(
            self._pruefen('class="mail-table sortable" '
                          'data-sort-key="mail-liste"'),
            (False, False))

    # ---------------------------------------------- Kopfzeile je Tabelle

    def _tabellen(self, quelle):
        u"""``datentabellen()`` auf einer Wegwerf-Vorlage mit `quelle`."""
        ordner = Path(tempfile.mkdtemp(prefix="djb_tabellen_"))
        self.addCleanup(shutil.rmtree, ordner, True)
        (ordner / "templates").mkdir()
        (ordner / "templates" / "seite.html").write_text(quelle,
                                                         encoding="utf-8")
        with override_settings(BASE_DIR=str(ordner),
                               DJANGOBASE_KONFORM_AUS=[],
                               DJANGOBASE_KONFORM_TABELLEN_AUS=[]):
            return test_tabellen.datentabellen()

    #: Eine Datei mit ZWEI Tabellen: eine Aufstellung ohne Kopfzeile und
    #: darunter ein echtes Raster - der Fall aus `verkauf_teaser.html`.
    ZWEI = ("""<table class="tz-eck">
<tr><td>Baujahr</td><td>1998</td></tr>
</table>
<table class="tz-kontakte sortable" data-sort-key="teaser-kontakte">
<thead><tr><th>Name</th><th>Kanal</th></tr></thead>
<tbody><tr><td>Maier</td><td>Telefon</td></tr></tbody>
</table>
""")

    def test_tabelle_ohne_eigene_kopfzeile_ist_kein_raster(self):
        orte = [a for _p, a in self._tabellen(self.ZWEI)]
        self.assertEqual(len(orte), 1, orte)
        self.assertIn("tz-kontakte", orte[0])

    def test_kopfzeile_aus_einem_include_zaehlt_weiter(self):
        u"""Gegenprobe: Wer seine Kopfzeile einbindet, faellt nicht heraus."""
        quelle = ("""<table class="raster">
{% include 'kopf.html' %}
<tbody><tr><td>1</td></tr></tbody>
</table>
<table class="anderes"><thead><tr><th>X</th></tr></thead></table>
""")
        klassen = " ".join(a for _p, a in self._tabellen(quelle))
        self.assertIn("raster", klassen)
