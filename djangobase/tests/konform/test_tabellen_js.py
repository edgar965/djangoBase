# -*- coding: utf-8 -*-
u"""Bauen auch die JavaScript-Module djangoBase-Tabellen?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „javascript soll auch diese Tabellen mit dem djangoBase tabellen Template
     bauen"

DIE LÜCKE, DIE DAS SCHLIESST
============================
``test_tabellen.py`` prüft Vorlagen. Tabellen, die JavaScript im Browser baut,
stehen in keiner Vorlage — ``/dax-handel/`` und ``/handelssysteme/best-technik/``
lieferten dort null Treffer, obwohl beide Seiten voller Tabellen sind. In
ShortLongX bauen **18 Module** ihr Tabellen-Markup selbst, jedes mit eigener
Schreibweise: ``class="stats sortable db-rahmen"``, ``class="results
bucket-tbl"``, manche ganz ohne. Was in der einen Tabelle geht, fehlt in der
nächsten.

Seit dem 21.08.2026 gibt es dafür ``tabelle_bauen.js`` — dasselbe Markup wie
``_tabelle.html``, aus denselben Angaben. Diese Datei prüft, dass die Module es
auch benutzen.

WAS EIN VERSTOSS IST — UND WAS NICHT
====================================
Gemeldet wird ein Modul, das eine ``<table>`` mit ``<thead>`` selbst
zusammensetzt, ohne den Bauer zu nehmen und ohne die Pflichtstücke
(``sortable`` und ``data-sort-key``) zu schreiben.

NICHT gemeldet wird:

    * ``tabelle_bauen.js`` selbst und ``tabellen_auto.js`` (sie sind das Werkzeug)
    * ein Modul, das die Tabelle nur FINDET (``querySelector('table')``)
    * Tabellen ohne ``<thead>`` — dieselbe Grenze wie bei den Vorlagen: ohne
      Kopfzeile ist es kein Datenraster
    * Doku-Klassen aus ``DOKU_KLASSEN``
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

PAKET = Path(__file__).resolve().parents[2]
JS_DJANGOBASE = PAKET / "static" / "djangobase" / "js"

TABU = {"node_modules", "__pycache__", "venv", "pythonVENV", ".git",
        "site-packages", "migrations"}

#: Werkzeuge, die naturgemäß Tabellen-Markup enthalten.
WERKZEUG = ("tabelle_bauen.js", "tabellen_auto.js", "tabellen_sortierung.js",
            "tabellen_breiten.js", "aufzeichner_liste.js")

DOKU_KLASSEN = ("plain", "doku", "legende", "info")

#: Ein ``<table …>`` in einer Zeichenkette — mit oder ohne Attribute.
_TABELLE = re.compile(r"<table\b([^>]*)>", re.IGNORECASE)
_KLASSEN = re.compile(r"""class\s*=\s*\\?["']([^"'\\]*)""", re.IGNORECASE)


#: Block- und Zeilenkommentare - ohne sie meldet der Prüfer seine eigene
#: Dokumentation. Genau das passierte am 21.08.2026: Ein Kommentar in
#: ``risiko.js``, der den Befund ERKLÄRTE („`<thead>` in derselben Datei wie das
#: `<table>`"), wurde als Tabelle ohne Sortierung gemeldet.
_KOMMENTAR = re.compile(r"/\*.*?\*/|(?<![:\w])//[^\n]*", re.DOTALL)


def ohne_kommentare(text):
    u"""Kommentare durch Leerzeilen ersetzen (Zeilennummern bleiben erhalten)."""
    return _KOMMENTAR.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _module():
    u"""JS-Dateien des Projekts, ohne djangoBase und ohne Spiegelungen."""
    wurzel = Path(getattr(settings, "BASE_DIR", "."))
    for pfad in wurzel.rglob("*.js"):
        if TABU & set(pfad.parts):
            continue
        if JS_DJANGOBASE in pfad.parents or pfad.name in WERKZEUG:
            continue
        # Testspiegel (tests_app/js/_web/) sind Kopien - sie zweimal zu melden
        # verdoppelt jeden Befund.
        if "_web" in pfad.parts:
            continue
        yield pfad


def _ausgenommen(pfad):
    for teil in getattr(settings, "DJANGOBASE_KONFORM_TABELLEN_AUS", ()) or ():
        if teil in str(pfad).replace("\\", "/"):
            return True
    return False


def bauende_module():
    u"""[(pfad, attribute)] jeder selbstgebauten Datentabelle."""
    aus = []
    for pfad in _module():
        if _ausgenommen(pfad):
            continue
        try:
            text = ohne_kommentare(pfad.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        # KEINE ``<thead>``-BEDINGUNG MEHR (Korrektur 21.08.2026): Sie hat
        # ``risiko.js`` übersehen. Dort steht das ``<table>``, die Kopfzeile baut
        # ``risiko_tabellen.js`` — zwei Dateien, eine Tabelle. Neun echte
        # Datentabellen (eine je Asset) blieben deshalb ohne Sortierung und
        # ohne gemerkte Breiten, und der Prüfer meldete nichts.
        #
        # Dafür braucht es jetzt Ausnahmen: Module, die Erklärtabellen in
        # Hilfe-Popups bauen (``param_info.js``), tragen dieselben Klassen wie
        # Datenraster. Sie stehen in DJANGOBASE_KONFORM_TABELLEN_AUS — eine
        # Entscheidung, die man sieht, statt einer Regel, die niemand einhält.
        for treffer in _TABELLE.finditer(text):
            attribute = treffer.group(1)
            klassen = " ".join(_KLASSEN.findall(attribute)).lower().split()
            if any(k in klassen for k in DOKU_KLASSEN):
                continue
            aus.append((pfad, attribute))
    return aus


class WerkzeugTest(SimpleTestCase):
    u"""Gibt es den Bauer, und kann er, was die Vorlage kann?"""

    databases = []

    def test_bauer_existiert(self):
        self.assertTrue((JS_DJANGOBASE / "tabelle_bauen.js").exists(),
                        u"tabelle_bauen.js fehlt — dann haben die JS-Module "
                        u"nichts, worauf sie umsteigen könnten.")

    def test_bauer_erzeugt_dieselben_marken_wie_die_vorlage(self):
        u"""Sonst sähe eine gebaute Tabelle anders aus als eine gerenderte, und
        Stile wie Module griffen nur bei einer von beiden."""
        text = (JS_DJANGOBASE / "tabelle_bauen.js").read_text(encoding="utf-8")
        for marke in ("db-tabelle", "sortable", "data-sort-key",
                      "db-tabelle-rahmen", "data-sort", "data-key"):
            self.assertIn(marke, text,
                          u"tabelle_bauen.js schreibt %r nicht — die Vorlage "
                          u"_tabelle.html tut es." % marke)

    def test_bauer_verlangt_einen_schluessel(self):
        u"""Ein stiller Rückfall wäre die schlimmere Lösung: Die Tabelle merkte
        sich nichts, und es fiele erst auf, wenn jemand vergeblich eine Spalte
        zieht."""
        text = (JS_DJANGOBASE / "tabelle_bauen.js").read_text(encoding="utf-8")
        self.assertIn("throw new Error", text,
                      u"dbTabelle muss ohne „key“ werfen.")


class ModuleNutzenDenBauerTest(SimpleTestCase):
    u"""Die Module des Projekts."""

    databases = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gebaut = bauende_module()

    def _melden(self, treffer, was, rat):
        zeilen = "\n".join("    %s: <table %s>" % (p.name, a[:64].strip())
                           for p, a in treffer[:10])
        return u"%d von %d selbstgebauten Tabellen %s:\n%s%s\n\n%s" % (
            len(treffer), len(self.gebaut), was, zeilen,
            "\n    …" if len(treffer) > 10 else "", rat)

    def test_gebaute_tabellen_sind_sortierbar(self):
        ohne = [(p, a) for p, a in self.gebaut
                if "sortable" not in " ".join(_KLASSEN.findall(a)).lower().split()]
        if ohne:
            self.fail(self._melden(
                ohne, u"tragen kein class=\"sortable\"",
                u"Nimm den Bauer, dann kommt es von selbst:\n"
                u"    import { dbTabelle } from "
                u"'/static/djangobase/js/tabelle_bauen.js';\n"
                u"    el.innerHTML = dbTabelle({key: '…', spalten: […], "
                u"zeilen: […]});"))

    def test_gebaute_tabellen_merken_ihre_breiten(self):
        u"""Ohne ``data-sort-key`` leitet ``tabellen_auto.js`` einen aus der
        Position ab — das rettet die Tabelle, hält aber nur, solange niemand
        etwas davor einfügt."""
        ohne = [(p, a) for p, a in self.gebaut if "data-sort-key" not in a.lower()]
        if ohne:
            self.fail(self._melden(
                ohne, u"tragen kein data-sort-key",
                u"Der Bauer verlangt den Schlüssel als Pflichtangabe — genau "
                u"deshalb. Er muss projektweit eindeutig sein."))

    def test_es_wurde_wirklich_gesucht(self):
        u"""Findet der Sucher nichts, ist „0 Verstöße" bedeutungslos."""
        anzahl = sum(1 for _ in _module())
        self.assertTrue(anzahl > 5,
                        u"Nur %d JS-Module gefunden — stimmt BASE_DIR?" % anzahl)


class GegenprobeTest(SimpleTestCase):
    u"""Trifft die Erkennung, was sie treffen soll?"""

    databases = []

    def test_tabelle_in_zeichenkette_wird_gefunden(self):
        for probe in ('`<table class="stats sortable">`',
                      "'<table>' + kopf",
                      '"<table class=\\"x\\" data-sort-key=\\"y\\">"'):
            with self.subTest(probe=probe):
                self.assertTrue(_TABELLE.search(probe), probe)

    def test_klassen_werden_auch_maskiert_gelesen(self):
        u"""In JS steht die Klasse oft in einer maskierten Zeichenkette
        (``class=\\"stats\\"``). Ohne das würde jede davon als „ohne Klasse"
        gemeldet — ein Fehlalarm auf korrekten Code."""
        self.assertIn("stats", _KLASSEN.findall('<table class=\\"stats\\">'))
        self.assertIn("stats", _KLASSEN.findall('<table class="stats">'))

    def test_kommentare_werden_uebersprungen(self):
        u"""Sonst meldet der Prüfer seine eigene Dokumentation — am 21.08.2026
        genau so passiert."""
        quelle = ('/* erklärt das <table> hier */\n'
                  'const h = `<table class="data sortable" data-sort-key="x">`;\n'
                  '// auch <table> im Zeilenkommentar\n')
        sauber = ohne_kommentare(quelle)
        self.assertEqual(sauber.count("<table"), 1,
                         u"Genau EIN echtes <table> sollte übrig bleiben: %r"
                         % sauber)

    def test_urls_bleiben_heil(self):
        u"""``//`` steht auch in ``https://…`` — ein zu gieriges Muster fräße
        den halben Import."""
        quelle = "import x from 'https://cdn.example/a.js';"
        self.assertIn("cdn.example", ohne_kommentare(quelle))

    def test_werkzeuge_bleiben_draussen(self):
        u"""Sonst meldete der Prüfer den Bauer selbst."""
        self.assertIn("tabelle_bauen.js", WERKZEUG)
        self.assertIn("aufzeichner_liste.js", WERKZEUG)
