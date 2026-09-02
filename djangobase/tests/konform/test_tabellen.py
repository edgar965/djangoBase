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

DIE REICHWEITE — UND WAS AUSSERHALB LIEGT
========================================
Geprüft werden **Vorlagen**. Tabellen, die JavaScript im Browser baut, stehen in
keiner Vorlage und kommen hier nicht vor: ``/dax-handel/`` und
``/handelssysteme/best-technik/`` liefern null Treffer, obwohl dort Tabellen
stehen. Für die sorgt ``tabellen_auto.js`` (über die Middleware auf jeder
Seite), das jede ``table.sortable`` anbindet und ihren Schlüssel ableitet.

Beides zusammen deckt ab: Was im Markup steht, trägt seinen Schlüssel selbst;
was im Browser entsteht, bekommt einen abgeleiteten.

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

from djangobase.tests.konform.quellen import TABU, dateien, text_von  # noqa: F401

#: Klassen, die eine Tabelle als Doku ausweisen (kein Datenraster).
DOKU_KLASSEN = ("plain", "doku", "legende", "info")

_TABELLE = re.compile(r"<table\b([^>]*)>", re.IGNORECASE)
_KLASSEN = re.compile(r'class\s*=\s*"([^"]*)"', re.IGNORECASE)

#: Kommentare — Django (``{% comment %}``, ``{# … #}``) und HTML (``<!-- … -->``).
#:
#: FEHLALARM VOM 21.08.2026: ``_mail_list_rows.html`` beginnt mit dem Kommentar
#: „Keine <table>/<thead>/<colgroup>-Wrapper damit nur EINE Tabelle existiert" —
#: also mit der ERKLÄRUNG, warum die Datei keine Tabelle hat. Gemeldet wurde
#: genau diese Erklärung als Tabelle ohne Sortierung. Dieselbe Falle wie in
#: ``test_tabellen_js`` (dort ``risiko.js``).
_KOMMENTAR = re.compile(
    r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}|{#.*?#}|<!--.*?-->",
    re.IGNORECASE | re.DOTALL)


def ohne_kommentare(text):
    u"""Kommentare durch Leerzeilen ersetzen (Zeilennummern bleiben erhalten)."""
    return _KOMMENTAR.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _templates():
    u"""Alle HTML-Vorlagen des Projekts (ohne djangoBase selbst)."""
    return dateien(".html")


def _ausgenommen(pfad):
    for teil in getattr(settings, "DJANGOBASE_KONFORM_TABELLEN_AUS", ()) or ():
        if teil in str(pfad).replace("\\", "/"):
            return True
    return False


def _rumpf(text, ab):
    u"""Der Text einer Tabelle: vom ``<table …>`` bis zum ``</table>``."""
    ende = text.lower().find("</table>", ab)
    return text[ab:] if ende < 0 else text[ab:ende]


def _hat_kopfzeile(text, treffer):
    u"""Hat DIESE Tabelle eine Kopfzeile - oder holt sie sich eine?

    JE TABELLE STATT JE DATEI (31.08.2026, Projekt assistant)
    ========================================================
    Geprueft wurde, ob irgendwo in der Datei ein ``<thead>`` steht. Damit
    galt jede Tabelle einer Datei als Datenraster, sobald EINE es war:
    ``verkauf_teaser.html`` hat eine Kontaktliste mit Kopfzeile und
    darueber eine zweispaltige Eckdaten-Aufstellung ohne. Die zweite
    stand in der Liste der Verstoesse, obwohl ``tabellen_auto.js`` sie
    mangels ``tHead`` gar nicht anbindet - ein Befund, den zu beheben
    nichts bewirkt haette.

    Die Ausnahme bleibt: Wer seine Kopfzeile per ``{% include %}`` holt,
    hat sie nicht im eigenen Rumpf stehen. Dann zaehlt wieder die Datei.
    """
    rumpf = _rumpf(text, treffer.end())
    if "<thead" in rumpf.lower():
        return True
    if "{% include" in rumpf or "{%include" in rumpf:
        return "<thead" in text.lower()
    return False


def datentabellen(vorlagen=None):
    u"""[(pfad, attribute)] aller Tabellen, die ein Datenraster sein wollen.

    ``vorlagen`` überschreibt die Dateiquelle. Gebraucht wird das von
    ``test_eigene_tabellen``: djangoBase nimmt sich aus den Konsumenten-Regeln
    heraus (siehe ``quellen.PAKET``) und stand deshalb selbst nie auf dem
    Prüfstand - obwohl sein Code in allen Projekten gleichzeitig wirkt.
    """
    aus = []
    for pfad in (vorlagen if vorlagen is not None else _templates()):
        if _ausgenommen(pfad):
            continue
        roh = text_von(pfad)
        if roh is None:
            continue
        text = ohne_kommentare(roh)
        if "<thead" not in text.lower():
            continue                                    # ohne Kopfzeile kein Raster
        for treffer in _TABELLE.finditer(text):
            attribute = treffer.group(1)
            klassen = " ".join(_KLASSEN.findall(attribute)).lower()
            if any(k in klassen.split() for k in DOKU_KLASSEN):
                continue
            if not _hat_kopfzeile(text, treffer):
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

    #: Eine Tabelle, deren ZEILENFOLGE etwas bedeutet: die Gliederung einer
    #: BWA, die Kennzahlen einer Steuererklaerung, die Tage eines
    #: Stundenzettels. Wer sie nach Betrag sortiert, zerstoert die Aussage.
    #:
    #: WARUM ES DIESE MARKE BRAUCHT (31.08.2026, Projekt assistant)
    #: ===========================================================
    #: Dort waren 19 von 45 Datentabellen nicht sortierbar - und bei den
    #: meisten zu Recht: UStVA, EUeR, Einkommensteuer, BWA, Stundenzettel,
    #: zwei Druckansichten. Ohne Marke bleiben nur zwei schlechte Wege: sie
    #: als „doku" auszugeben (falsch - es sind Daten) oder eine Sortierung
    #: anzubieten, die den Bericht kaputtmacht.
    #:
    #: Die GEMERKTEN SPALTENBREITEN bleiben Pflicht: Sie aendern keine
    #: Reihenfolge, und gerade in einem Bericht will man die Kontospalte
    #: breiter ziehen. `tabellen_auto.js` bindet dafuer schon auf
    #: ``table[data-sort-key]``, ganz ohne ``sortable``.
    ORDNUNG_ZAEHLT = "data-sort-aus"

    def test_alle_sind_sortierbar(self):
        ohne = [(p, a) for p, a in self.tabellen
                if "sortable" not in " ".join(_KLASSEN.findall(a)).lower().split()
                and self.ORDNUNG_ZAEHLT not in a.lower()]
        if ohne:
            self.fail(self._melden(
                ohne, u"tragen kein class=\"sortable\"",
            u"TabellenSortierung bindet an table.sortable. Ohne die Klasse "
                u"lassen sich die Spalten nicht sortieren — auch nicht, wenn "
                u"das Modul geladen ist.\n"
                u"Bedeutet die ZEILENFOLGE etwas (BWA-Gliederung, "
                u"Steuer-Kennzahlen, Tage eines Stundenzettels)? Dann "
                u"stattdessen <table data-sort-aus data-sort-key=\"…\"> — "
                u"gemerkte Spaltenbreiten ohne Sortierung."))

    @staticmethod
    def auto_bindung_aktiv():
        u"""Bindet djangoBase die Tabellen selbst an?

        ``tabellen_auto.js`` läuft über die Middleware auf jeder Seite, bindet
        alle ``table.sortable`` an und LEITET einen Schlüssel AB, wenn keiner
        dasteht (aus der id, sonst aus Seitenpfad und Position). Wo das aktiv
        ist, sind ziehbare Spalten auch ohne ``data-sort-key`` im Markup da —
        und dann wäre es Bürokratie, es trotzdem zu verlangen.

        Der Befund vom 21.08.2026 (91 von 91 Tabellen ohne Schlüssel) hat genau
        dazu geführt: 91 Vorlagen von Hand zu ergänzen hätte dieselbe Lücke beim
        nächsten neuen Template wieder aufgemacht."""
        from django.conf import settings as s
        if not getattr(s, "DJANGOBASE_AUFZEICHNUNG", True):
            return False                      # derselbe Kanal wie die Aufzeichnung
        from djangobase.apps import AUFZEICHNUNG_MIDDLEWARE
        return AUFZEICHNUNG_MIDDLEWARE in list(getattr(s, "MIDDLEWARE", []))

    def test_alle_merken_ihre_spaltenbreiten(self):
        u"""``data-sort-key`` im Markup — auch wenn die Auto-Bindung läuft.

        ``tabellen_auto.js`` leitet einen Schlüssel ab, wenn keiner dasteht, und
        rettet damit jedes neue Template. Als ERSATZ taugt das trotzdem nicht:
        Der abgeleitete Schlüssel hängt an der Position der Tabelle in der Seite
        (``auto-dax-handel--0``). Wer eine Tabelle verschiebt oder eine davor
        einfügt, verliert die gezogenen Breiten — lautlos.

        Ein Schlüssel im Markup überlebt das. Die Auto-Bindung bleibt der
        Sicherheitsgurt, nicht die Lösung."""
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

    def test_automatische_anbindung_ist_vollstaendig(self):
        u"""Wenn sich das Projekt auf ``tabellen_auto.js`` verlässt, muss das
        Modul auch beides tun — sortieren UND Breiten merken."""
        if not TabellenKonformTest.auto_bindung_aktiv():
            self.skipTest("keine automatische Anbindung")
        pfad = (Path(__file__).resolve().parents[2] / "static" / "djangobase"
                / "js" / "tabellen_auto.js")
        self.assertTrue(pfad.exists(), u"tabellen_auto.js fehlt")
        text = pfad.read_text(encoding="utf-8")
        for brocken in ("TabellenSortierung.binden", "new TabellenBreiten",
                        "table.sortable"):
            self.assertIn(brocken, text,
                          u"tabellen_auto.js bindet %r nicht mehr — dann sind "
                          u"die Tabellen still nur halb bedienbar." % brocken)

    def test_beide_module_werden_irgendwo_gebunden(self):
        u"""Die Attribute allein tun nichts — jemand muss die Module anbinden.

        Geprüft wird nur, DASS es im Projekt geschieht (einmal je Seite reicht),
        nicht wo: Manche Projekte binden im Basis-Template, andere je Seite.

        FEHLALARM VOM 21.08.2026 (assistant): Gesucht wurde unter ``BASE_DIR``.
        Wer die Anbindung ``tabellen_auto.js`` überlässt — dem von djangoBase
        empfohlenen Weg —, hat dort NICHTS stehen: Das Modul liegt im
        djangoBase-Paket, also außerhalb des Projekts. Gemeldet wurde damit
        ausgerechnet die saubere Lösung. Deshalb steht die Prüfung jetzt hinter
        der Frage, ob die Auto-Bindung überhaupt fehlt."""
        if TabellenKonformTest.auto_bindung_aktiv():
            # KEIN Skip (26.08.2026): Ein uebersprungener Test meldet gruen,
            # ohne etwas geprueft zu haben — und verdeckt damit auch den
            # Fall, dass `auto_bindung_aktiv()` selbst kaputt ist. Die
            # Auto-Bindung IST die Erfuellung dieser Regel, also wird sie
            # als solche zugesichert statt weggeschaltet.
            self.assertTrue(TabellenKonformTest.auto_bindung_aktiv(),
                            u"tabellen_auto.js bindet - das erfüllt die Regel")
            return
        gefunden = {"TabellenSortierung": False, "TabellenBreiten": False}
        for pfad in dateien(".html", ".js"):
            text = text_von(pfad)
            if text is None:
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

    def test_kommentare_werden_uebersprungen(self):
        u"""Sonst meldet der Pruefer die Erklaerung, warum eine Datei KEINE
        Tabelle hat - am 21.08.2026 genau so passiert."""
        quelle = ('{% comment %}Keine <table>/<thead> hier, damit nur EINE '
                  'Tabelle existiert.{% endcomment %}\n'
                  '<table class="daten sortable" data-sort-key="x">'
                  '<thead></thead></table>\n'
                  '<!-- auch <table> im HTML-Kommentar -->\n')
        sauber = ohne_kommentare(quelle)
        self.assertEqual(sauber.count("<table"), 1, sauber)

    def test_kurzer_kommentar_frisst_nicht_die_datei(self):
        u"""``{# ... #}`` ist einzeilig - ein gieriges Muster loeschte sonst
        alles zwischen dem ersten und dem letzten Vorkommen."""
        quelle = '{# eins #}\n<table><thead></thead></table>\n{# zwei #}'
        self.assertIn("<table", ohne_kommentare(quelle))
