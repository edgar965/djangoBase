# -*- coding: utf-8 -*-
u"""Testtabelle - EINE Tabelle für alles, was man auf der Tests-Seite starten kann.

    „warum gibt es kein Test Seiten template, wo du das nur einmal änderst??"
    (Edgar, 17.08.2026)

Berechtigte Frage, und sie zeigt den Fehler des ersten Wurfs: Die Tests-Seite
hatte VIER Listen mit derselben Aufgabe — Reiter „Alle" je Kategorie, Einzeltests
je Typ, Suiten je Gruppe, UI-Tests. Jede war eigenes Markup. Beim Umbau auf die
sortierbare Tabelle habe ich drei erwischt und die vierte übersehen; gemeldet
wurde sie über ``?tab=Alle&unter=unit``.

Deshalb jetzt EIN Weg:

    Ansicht  ->  Testtabelle.tabelle(eintraege, …)  ->  djangobase/_testkarte.html

``eintraege`` sind normalisierte Zeilen (``Eintrag``); woher sie kommen — aus der
Test-Discovery oder aus ``test_befehle`` — entscheiden zwei kleine Umformer. Wer
etwas an Spalten, Laufzeiten oder Bedienung ändert, ändert es an einer Stelle.

WAS DIE TABELLE ZEIGT
=====================
Name · Ziel · letzte · Ø · Trend · letzte 4 Läufe · Run. Sortiert wird nach
ROHWERTEN (``data-sort``), angezeigt in deutscher Schreibweise; unter 10 ms in
Millisekunden. Der Trend erscheint erst ab 25 % Abweichung vom Mittel der
vorigen Läufe — darunter ist es Rauschen.
"""
from django.utils.html import escape
from django.utils.http import urlencode

__all__ = ["Eintrag", "Testtabelle"]


class Eintrag:
    """Eine startbare Zeile: ein einzelner Testcase ODER eine ganze Suite."""

    __slots__ = ("name", "ziel", "kennung", "ist_suite", "titel")

    def __init__(self, name, ziel, kennung, ist_suite=False, titel=""):
        #: Anzeigename (kurz).
        self.name = name
        #: Was gefahren wird - Test-ID bzw. Test-Labels.
        self.ziel = ziel
        #: Womit der Lauf ausgeloest wird (``?run=…``).
        self.kennung = kennung
        #: Suiten haben eine eigene Historie (mit Ergebnis), Tests eine je Fall.
        self.ist_suite = ist_suite
        #: Tooltip - meist das vollständige Kommando.
        self.titel = titel or ziel

    @classmethod
    def aus_test(cls, test):
        """Aus der Discovery: ``{"id": "app.tests.unit.X.test_y", "kurz": …}``."""
        return cls(test["kurz"], test["id"], test["id"])

    @classmethod
    def aus_befehl(cls, befehl):
        """Aus ``DJANGOBASE["test_befehle"]`` bzw. einem abgeleiteten Sammler."""
        return cls(befehl.get("name") or befehl.get("slug") or "",
                   befehl.get("ziel") or "",
                   befehl.get("slug") or "",
                   ist_suite=True,
                   titel=" ".join(str(x) for x in (befehl.get("cmd") or [])))


class Testtabelle:
    """Baut die Tabellen-Struktur, die ``djangobase/_tabelle.html`` erwartet."""

    SPALTEN = (
        {"label": "Testcase", "key": "name"},
        {"label": "Ziel", "key": "ziel"},
        {"label": "letzte", "key": "letzte", "num": True,
         "titel": "Laufzeit des letzten Durchgangs"},
        {"label": "Ø", "key": "schnitt", "num": True,
         "titel": "Mittel über die gespeicherten Läufe"},
        {"label": "Trend", "key": "trend", "num": True,
         "titel": "letzter Lauf gegen das Mittel der vorigen — erst ab 25 % "
                  "Abweichung"},
        {"label": "letzte 4 Läufe", "key": "laeufe",
         "titel": "Datum · Uhrzeit · Laufzeit, neuester zuerst"},
        {"label": "Verschieben", "key": "kategorie", "sortAus": True,
         "titel": "Kategorie des Falls — Auswahl verschiebt seine Testdatei in "
                  "den Ordner der Zielkategorie"},
        {"label": "", "key": "run", "sortAus": True},
    )

    def __init__(self, historie, aktiver_slug="", tab=""):
        self.historie = historie
        self.aktiver_slug = aktiver_slug or ""
        self.tab = tab or ""
        # EIN Verschieber fuer die ganze Seite: Er sucht die Datei zu jeder
        # Test-ID auf der Platte. Je Zeile ein neuer waere derselbe Weg 173-mal.
        from .testverschieben import Verschieber
        self.verschieber = Verschieber()

    # ------------------------------------------------------------- Umformer

    def aus_tests(self, kategorie, tab=None):
        """Tabelle für die Einzeltests einer Kategorie (Unit, Component, …)."""
        return self.tabelle(
            [Eintrag.aus_test(t) for t in kategorie.get("tests", [])],
            key="tests-%s" % (kategorie.get("typ") or "alle").lower(),
            tab=kategorie.get("typ") if tab is None else tab,
            leer="Keine Tests gefunden — Labels in "
                 "DJANGOBASE[\"test_discover\"] prüfen.")

    def aus_befehlen(self, befehle, key, tab=None, unter=""):
        """Tabelle für Suiten (Batch-Kommandos) — Gruppe oder Kategorie."""
        return self.tabelle([Eintrag.aus_befehl(b) for b in befehle],
                            key=key, tab=tab, unter=unter,
                            leer="Keine Suiten konfiguriert.")

    # -------------------------------------------------------------- Tabelle

    def tabelle(self, eintraege, key, tab=None, unter="", leer="keine Einträge"):
        zeilen = [self._zeile(e, tab, unter) for e in eintraege]
        # Dictionary gewollt: geht unveraendert in `_tabelle.html`.
        return {"key": key, "spalten": [dict(s) for s in self.SPALTEN],
                "zeilen": zeilen, "leer": leer, "anzahl": len(zeilen)}

    def _zeile(self, e, tab, unter):
        laeufe = (self.historie.suitenlaeufe(e.kennung) if e.ist_suite
                  else self.historie.laeufe(e.kennung))
        letzte = laeufe[0]["dauer"] if laeufe else None
        schnitt = self._schnitt(laeufe)
        trendtext, trendklasse = ("", "") if e.ist_suite \
            else self.historie.trend(e.kennung)
        return {
            "klasse": "aktiv" if self.aktiver_slug == e.kennung else "",
            "zellen": [
                {"html": '<i class="bi bi-dot"></i> %s' % escape(e.name),
                 "titel": e.titel},
                {"html": escape(e.ziel), "klasse": "ts-ziel"},
                {"html": self._sekunden(letzte), "sort": letzte, "klasse": "num"},
                {"html": self._sekunden(schnitt), "sort": schnitt, "klasse": "num"},
                {"html": ('<span class="ts-trend %s">%s</span>'
                          % (trendklasse, escape(trendtext))) if trendtext else "",
                 "sort": self._trendwert(trendtext), "klasse": "num"},
                {"html": self._laufliste(laeufe, mit_status=e.ist_suite),
                 "sort": len(laeufe)},
                {"html": self._kategorie(e)},
                {"html": self._knopf(e.kennung,
                                     self.tab if tab is None else tab, unter)},
            ],
        }

    def _kategorie(self, e):
        u"""Die Combo-Box „Verschieben" - oder nur der Name der Kategorie.

        Aenderbar ist sie fuer einzelne Python-Testfaelle: Dort ist die Kategorie
        der ORDNER, und die Auswahl haengt die Testdatei um (siehe
        ``testverschieben``). Suiten und die Faelle aus einer ``testcases.js``
        bzw. hinter einem Projekt-Endpunkt tragen ihre Kategorie anderswo — die
        Spalte zeigt sie dort nur an, statt einen Klick anzubieten, der nichts tut.
        """
        from .testverschieben import Verschieber
        if e.ist_suite:
            art = Verschieber.art_von(e.ziel) or Verschieber.art_von(e.kennung)
            return ('<span class="ts-kat-fest" title="Kategorie steht im Ziel '
                    'der Suite">%s</span>'
                    % escape(Verschieber.NAMEN.get(art, art or "—")))
        art, datei = self.verschieber.moeglich(e.kennung)
        wahl = Verschieber.auswahl(art, datei is not None)
        if datei is None:
            return ('<span class="ts-kat-fest" title="nicht verschiebbar — die '
                    'Datei liegt nicht in einem tests/&lt;art&gt;/-Ordner">%s</span>'
                    % escape(wahl[0][1]))
        felder = "".join(
            '<option value="%s"%s>%s</option>'
            % (escape(wert), " selected" if gesetzt else "", escape(name))
            for wert, name, gesetzt in wahl)
        return ('<select class="ts-kat" data-test-id="%s" data-art="%s" '
                'title="verschiebt %s in den Ordner der gewählten Kategorie — '
                'weitere Fälle in derselben Datei gehen mit">%s</select>'
                % (escape(e.kennung), escape(art), escape(datei.name), felder))

    @staticmethod
    def _schnitt(laeufe):
        if not laeufe:
            return None
        return round(sum(x["dauer"] for x in laeufe) / len(laeufe), 3)

    # ------------------------------------------------------------ Bausteine

    @staticmethod
    def _sekunden(wert, stellen=2):
        u"""Laufzeit lesbar - unter 10 ms in Millisekunden.

        „0,00 s" fuer drei Millisekunden sagt nichts, und dort liegen fast alle
        Unit-Tests. Sortiert wird ohnehin nach dem Rohwert (``data-sort``), die
        Anzeige darf also die passende Einheit nehmen.
        """
        if wert is None:
            return '<span class="ts-nie">—</span>'
        if 0 < wert < 0.01:
            return "%d ms" % round(wert * 1000)
        return "%s s" % ("%.*f" % (stellen, wert)).replace(".", ",")

    @staticmethod
    def _trendwert(text):
        """Rohwert zum Sortieren aus „+38 %" - ohne ihn sortiert die Spalte Text."""
        if not text:
            return None
        try:
            return float(text.replace("%", "").replace(" ", "").replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _kurze_zeit(zeit):
        u"""„17.08.2026 17:02:32" -> „17.08. 17:02".

        Das Jahr steht in jeder Zeile gleich da und kostet nur Breite (im Tooltip
        ist es vollstaendig), die Sekunden interessieren beim Datum nicht. Der
        erste Wurf schnitt mit ``replace(zeit[6:11], "")`` und machte daraus
        „17.08.17:02:32" — Datum und Uhrzeit klebten zusammen.
        """
        teile = zeit.split()
        if len(teile) != 2:
            return zeit
        return "%s %s" % (teile[0][:6], teile[1][:5])

    @classmethod
    def _laufliste(cls, laeufe, mit_status=False):
        u"""Die letzten Laeufe als Kette „17.08. 16:55 · 1,23 s"."""
        if not laeufe:
            return '<span class="ts-nie">noch nie gelaufen</span>'
        stuecke = []
        for lauf in laeufe:
            zeit = str(lauf.get("zeit") or "")
            marke = ""
            if mit_status:
                marke = ('<i class="bi bi-check-circle-fill ts-ok"></i> '
                         if lauf.get("ok") else
                         '<i class="bi bi-x-circle-fill ts-fehler"></i> ')
            dauer = lauf.get("dauer")
            stuecke.append(
                '<span class="ts-lauf" title="%s">%s%s · %s</span>'
                % (escape(zeit), marke, escape(cls._kurze_zeit(zeit)),
                   "—" if dauer is None else cls._sekunden(dauer)))
        return " ".join(stuecke)

    def _knopf(self, kennung, tab, unter=""):
        felder = {"run": kennung, "tab": tab or ""}
        if unter:
            felder["unter"] = unter
        return ('<a class="ts-run" href="?%s" title="Diesen Test ausführen">'
                '<i class="bi bi-play-fill"></i> Run</a>'
                % escape(urlencode(felder)))
