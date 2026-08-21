# -*- coding: utf-8 -*-
u"""Sind die Tabellen dieses Projekts djangoBase-konform?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „Sind alle Tabellen im Projekt konform mit dem DjangoBase Tabellentemplate
     mit verschiebbaren Spalten, sortierbaren Spalten"

WAS EINE KONFORME TABELLE BRAUCHT
=================================
Zwei Dinge, und sie hängen an verschiedenen Stellen:

    class="sortable"        ``TabellenSortierung`` bindet an ``table.sortable``
    data-sort-key="…"       ``TabellenBreiten`` merkt Spaltenbreiten unter
                            diesem Schlüssel

Das Zweite wird gern vergessen, weil eine Tabelle ohne ihn völlig normal
aussieht — sie sortiert, sie zeigt Daten, nur die Spalten lassen sich nicht
ziehen und nichts wird gemerkt. Ein fehlendes ``data-sort-key`` ist damit die
stille Sorte Abweichung: nichts kaputt, nur die halbe Bedienung fehlt.

WELCHE TABELLEN GEMEINT SIND — UND WELCHE NICHT
===============================================
Nicht jede ``<table>`` ist eine Datentabelle. Die Hilfe-Seiten dieses Projekts
enthalten allein 181 Doku-Tabellen (``class="plain"``): feste Textinhalte,
Belegzahlen in Fließtext, drei Zeilen. Sie sortierbar zu machen wäre sinnlos,
und sie hier zu melden würde den Prüfer zur Fehlalarm-Maschine machen — die
teuerste Sorte Prüfung, weil sie die echten Befunde zudeckt.

Gemeldet wird deshalb nur, was nach Datentabelle aussieht:

    * hat einen ``<thead>``
    * trägt KEINE Klasse aus ``DOKU_KLASSEN``
    * steht nicht in einer Datei, die das Projekt ausdrücklich ausnimmt

AUSNAHMEN
=========
``DJANGOBASE_KONFORM_TABELLEN_AUS`` nimmt Dateien (Teilstrings des Pfads) aus.
Wer bewusst abweicht, trägt es dort ein — das ist eine Entscheidung, die man
sieht, statt einer Regel, die niemand einhält.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

#: Klassen, die eine Tabelle als Doku ausweisen (kein Datenraster).
DOKU_KLASSEN = ("plain", "doku", "legende", "info")

#: Verzeichnisse, die nie durchsucht werden.
TABU = {"node_modules", "__pycache__", "venv", "pythonVENV", ".git",
        "site-packages", "migrations"}

_TABELLE = re.compile(r"<table\b([^>]*)>", re.IGNORECASE)
_KLASSEN = re.compile(r'class\s*=\s*"([^"]*)"', re.IGNORECASE)


def _templates():
    u"""Alle HTML-Vorlagen des Projekts (ohne djangoBase selbst)."""
    wurzel = Path(getattr(settings, "BASE_DIR", "."))
    eigen = Path(__file__).resolve().parents[2]        # …/djangobase
    for pfad in wurzel.rglob("*.html"):
        if TABU & set(pfad.parts):
            continue
        try:
            if eigen in pfad.parents:
                continue                                # djangoBase prüft sich nicht selbst
        except Exception:                               # noqa: BLE001
            pass
        yield pfad


def _ausgenommen(pfad):
    for teil in getattr(settings, "DJANGOBASE_KONFORM_TABELLEN_AUS", ()) or ():
        if teil in str(pfad).replace("\\", "/"):
            return True
    return False


def datentabellen():
    u"""[(pfad, attribute)] aller Tabellen, die ein Datenraster sein wollen."""
    aus = []
    for pfad in _templates():
        if _ausgenommen(pfad):
            continue
        try:
            text = pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "<thead" not in text.lower():
            continue                                    # ohne Kopfzeile kein Raster
        for treffer in _TABELLE.finditer(text):
            attribute = treffer.group(1)
            klassen = " ".join(_KLASSEN.findall(attribute)).lower()
            if any(k in klassen.split() for k in DOKU_KLASSEN):
                continue
            aus.append((pfad, attribute))
    return aus


class TabellenKonformTest(SimpleTestCase):
    u"""Sortierbar UND in der Breite ziehbar."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tabellen = datentabellen()

    def _melden(self, treffer, was, rat):
        u"""Eine Fehlermeldung, mit der man arbeiten kann: Zahl, Beispiele, Rat."""
        beispiele = "\n".join(
            "    %s: <table %s>" % (Path(p).name, a[:70].strip())
            for p, a in treffer[:8])
        return (u"%d von %d Datentabellen %s.\n%s%s\n\n%s"
                % (len(treffer), len(self.tabellen), was, beispiele,
                   "\n    …" if len(treffer) > 8 else "", rat))

    def test_es_gibt_ueberhaupt_datentabellen(self):
        u"""Ohne Fund prüfen die beiden Regeln unten nichts — dann stimmt die
        Erkennung nicht, und das wäre schlimmer als ein Verstoß."""
        self.assertTrue(self.tabellen,
                        u"Keine einzige Datentabelle gefunden. Entweder hat das "
                        u"Projekt keine, oder DOKU_KLASSEN/das Suchmuster passt "
                        u"nicht mehr.")

    def test_alle_sind_sortierbar(self):
        ohne = [(p, a) for p, a in self.tabellen
                if "sortable" not in " ".join(_KLASSEN.findall(a)).lower().split()]
        if ohne:
            self.fail(self._melden(
                ohne, u"tragen kein class=\"sortable\"",
            u"TabellenSortierung bindet an table.sortable. Ohne die Klasse "
                u"lassen sich die Spalten nicht sortieren — auch nicht, wenn "
                u"das Modul geladen ist."))

    def test_alle_merken_ihre_spaltenbreiten(self):
        u"""Der Teil, der still fehlt: Ohne ``data-sort-key`` gibt es keine
        ziehbaren Spalten und nichts wird gemerkt."""
        ohne = [(p, a) for p, a in self.tabellen if "data-sort-key" not in a.lower()]
        if ohne:
            self.fail(self._melden(
                ohne, u"tragen kein data-sort-key",
            u"TabellenBreiten merkt Spaltenbreiten unter diesem Schlüssel. "
            u"Ohne ihn sieht die Tabelle normal aus, aber die Spalten lassen "
            u"sich nicht ziehen. Anschluss:\n"
            u"    <table class=\"db-tabelle sortable\" data-sort-key=\"meine-seite\">\n"
                u"    new TabellenBreiten([t], t.dataset.sortKey).binden();"))

    def test_schluessel_sind_eindeutig(self):
        u"""Zwei Tabellen mit demselben Schlüssel teilen sich die gemerkten
        Breiten — die schmale übernimmt die der breiten, und die Hälfte der
        Spalten liegt außerhalb (am 21.08.2026 im Aufzeichnungs-Popup passiert)."""
        gesehen = {}
        doppelt = []
        for pfad, attribute in self.tabellen:
            m = re.search(r'data-sort-key\s*=\s*"([^"]+)"', attribute, re.I)
            if not m or "{{" in m.group(1):
                continue                                # dynamisch = je Ort anders
            schluessel = m.group(1)
            if schluessel in gesehen and gesehen[schluessel] != pfad:
                doppelt.append((schluessel, gesehen[schluessel], pfad))
            gesehen.setdefault(schluessel, pfad)
        self.assertFalse(doppelt,
                         u"Mehrfach vergebene Sortier-Schlüssel: %s"
                         % "; ".join("%s (%s / %s)" % (s, Path(a).name, Path(b).name)
                                     for s, a, b in doppelt[:5]))


class TabellenModuleTest(SimpleTestCase):
    u"""Ein ``data-sort-key`` ohne gebundenes Modul bringt nichts."""

    def test_beide_module_werden_irgendwo_gebunden(self):
        u"""Die Attribute allein tun nichts — jemand muss die Module anbinden.

        Geprüft wird nur, DASS es im Projekt geschieht (einmal je Seite reicht),
        nicht wo: Manche Projekte binden im Basis-Template, andere je Seite."""
        wurzel = Path(getattr(settings, "BASE_DIR", "."))
        gefunden = {"TabellenSortierung": False, "TabellenBreiten": False}
        for muster in ("*.html", "*.js"):
            for pfad in wurzel.rglob(muster):
                if TABU & set(pfad.parts):
                    continue
                try:
                    text = pfad.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "TabellenSortierung.binden" in text:
                    gefunden["TabellenSortierung"] = True
                if "new TabellenBreiten" in text:
                    gefunden["TabellenBreiten"] = True
                if all(gefunden.values()):
                    return
        fehlend = [k for k, v in gefunden.items() if not v]
        self.assertFalse(fehlend,
                         u"Nirgends im Projekt gebunden: %s. Die Tabellen-"
                         u"Attribute allein bewirken nichts — siehe den Kopf "
                         u"von djangobase/_tabelle.html." % ", ".join(fehlend))


class GegenprobeTest(SimpleTestCase):
    u"""Erkennt die Regel überhaupt etwas — und lässt sie Doku in Ruhe?"""

    def test_doku_tabelle_wird_nicht_gemeldet(self):
        klassen = "plain"
        self.assertTrue(any(k in klassen.split() for k in DOKU_KLASSEN),
                        u"class=\"plain\" muss als Doku gelten, sonst meldet der "
                        u"Prüfer 181 Hilfe-Tabellen und wird abgeschaltet")

    def test_fehlendes_attribut_wird_erkannt(self):
        attribute = ' class="stats sortable db-rahmen"'
        self.assertNotIn("data-sort-key", attribute.lower(),
                         u"Diese Probe MUSS als Verstoß gelten")
        self.assertIn("sortable", " ".join(_KLASSEN.findall(attribute)).split())

    def test_muster_findet_eine_tabelle(self):
        self.assertTrue(_TABELLE.search('<table class="db-tabelle sortable">'))
        self.assertTrue(_TABELLE.search("<table\n  data-sort-key='x'>"))
