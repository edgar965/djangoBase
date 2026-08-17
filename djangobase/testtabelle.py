# -*- coding: utf-8 -*-
u"""Testtabelle - Testcases als sortierbare djangoBase-Tabelle, mit Laufzeiten.

    „und alle Tabellen mit Testcases sollen erben von der djangoBase sortierbaren
    Tabelle" (Ansage Edgar, 17.08.2026)

Vorher war die Liste der Einzeltests eine Reihe von ``<div class="ts-item">``:
nicht sortierbar, keine Spaltenbreiten, keine Zahlen. Jetzt liefert diese Klasse
die Struktur, die ``djangobase/_tabelle.html`` erwartet - damit erben die
Testcase-Tabellen dieselbe Bedienung wie alle anderen Tabellen im Haus
(Pfeile immer sichtbar, Breiten ziehbar und gemerkt, Rohwerte zum Sortieren).

DIE ROHWERTE SIND WICHTIG
=========================
Angezeigt wird „1,23 s", sortiert wird nach ``data-sort="1.23"``. Ohne den
Rohwert wuerde die Tabelle die deutsche Zahl im Text lesen muessen; das kann das
Sortiermodul, aber bei „—" (nie gelaufen) waere die Reihenfolge Zufall. Leere
Zellen landen im Modul immer am Ende.
"""
from django.utils.html import escape

__all__ = ["Testtabelle"]


class Testtabelle:
    """Baut die Tabellen-Struktur fuer Einzeltests und fuer Suiten."""

    def __init__(self, historie, aktiver_slug="", tab=""):
        self.historie = historie
        self.aktiver_slug = aktiver_slug or ""
        self.tab = tab or ""

    # --------------------------------------------------------------- Einzeltests

    def einzeltests(self, kategorie):
        u"""Ein Testcase je Zeile: Name, Laufzeit, Mittel, Trend, letzte 4 Laeufe."""
        zeilen = []
        for t in kategorie.get("tests", []):
            laeufe = self.historie.laeufe(t["id"])
            letzte = self.historie.letzte(t["id"])
            schnitt = self.historie.schnitt(t["id"])
            trendtext, trendklasse = self.historie.trend(t["id"])
            zeilen.append({
                "klasse": "aktiv" if self.aktiver_slug == t["id"] else "",
                "zellen": [
                    {"html": '<i class="bi bi-dot"></i> %s' % escape(t["kurz"]),
                     "titel": t["id"]},
                    {"html": self._sekunden(letzte), "sort": letzte, "num": True,
                     "klasse": "num"},
                    {"html": self._sekunden(schnitt), "sort": schnitt,
                     "klasse": "num"},
                    {"html": ('<span class="ts-trend %s">%s</span>'
                              % (trendklasse, escape(trendtext))) if trendtext else "",
                     "sort": self._trendwert(trendtext), "klasse": "num"},
                    {"html": self._laufliste(laeufe),
                     "sort": len(laeufe)},
                    {"html": self._knopf(t["id"], kategorie.get("typ", ""))},
                ],
            })
        # Dictionary gewollt: geht unveraendert in `_tabelle.html`.
        return {
            "key": "tests-%s" % (kategorie.get("typ") or "alle").lower(),
            "spalten": [
                {"label": "Testcase", "key": "name"},
                {"label": "letzte", "key": "letzte", "num": True,
                 "titel": "Laufzeit des letzten Durchgangs"},
                {"label": "Ø", "key": "schnitt", "num": True,
                 "titel": "Mittel über die gespeicherten Läufe"},
                {"label": "Trend", "key": "trend", "num": True,
                 "titel": "letzter Lauf gegen das Mittel der vorigen — "
                          "erst ab 25 % Abweichung"},
                {"label": "letzte 4 Läufe", "key": "laeufe",
                 "titel": "Datum · Uhrzeit · Laufzeit, neuester zuerst"},
                {"label": "", "key": "run", "sortAus": True},
            ],
            "zeilen": zeilen,
            "leer": "Keine Tests gefunden — Labels in "
                    "DJANGOBASE[\"test_discover\"] prüfen.",
        }

    # -------------------------------------------------------------------- Suiten

    def suiten(self, befehle, name="Suiten"):
        u"""Eine Suite je Zeile - mit derselben Laufzeit-Historie."""
        zeilen = []
        for b in befehle:
            slug = b.get("slug") or ""
            laeufe = self.historie.suitenlaeufe(slug)
            letzte = laeufe[0]["dauer"] if laeufe else None
            zeilen.append({
                "klasse": "aktiv" if self.aktiver_slug == slug else "",
                "zellen": [
                    {"html": escape(b.get("name") or slug),
                     "titel": " ".join(str(x) for x in (b.get("cmd") or []))},
                    {"html": escape(b.get("ziel") or ""), "klasse": "ts-ziel"},
                    {"html": self._sekunden(letzte, stellen=1), "sort": letzte,
                     "klasse": "num"},
                    {"html": self._laufliste(laeufe, mit_status=True),
                     "sort": len(laeufe)},
                    {"html": self._knopf(slug, self.tab)},
                ],
            })
        return {
            "key": "test-suiten-%s" % name.lower().replace(" ", "-"),
            "spalten": [
                {"label": "Suite", "key": "name"},
                {"label": "Ziel", "key": "ziel"},
                {"label": "letzte", "key": "letzte", "num": True},
                {"label": "letzte 4 Läufe", "key": "laeufe"},
                {"label": "", "key": "run", "sortAus": True},
            ],
            "zeilen": zeilen,
            "leer": "Keine Suiten konfiguriert.",
        }

    # ------------------------------------------------------------------ Bausteine

    @staticmethod
    def _sekunden(wert, stellen=2):
        u"""Laufzeit lesbar - unter 10 ms in Millisekunden.

        „0,00 s" fuer drei Millisekunden sagt nichts; die Unit-Tests liegen fast
        alle dort. Sortiert wird ohnehin nach dem Rohwert (``data-sort``), die
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
        datum, uhr = teile
        return "%s %s" % (datum[:6], uhr[:5])

    @classmethod
    def _laufliste(cls, laeufe, mit_status=False):
        u"""Die letzten Laeufe als Kette „17.08. 16:55 · 1,23 s".

        Datum UND Uhrzeit, wie verlangt. Das Jahr faellt weg: Es steht in jeder
        Zeile gleich da und kostet nur Breite; im Tooltip ist es vollstaendig.
        """
        if not laeufe:
            return '<span class="ts-nie">noch nie gelaufen</span>'
        stuecke = []
        for lauf in laeufe:
            zeit = str(lauf.get("zeit") or "")
            kurz = cls._kurze_zeit(zeit)
            marke = ""
            if mit_status:
                marke = ('<i class="bi bi-check-circle-fill ts-ok"></i> '
                         if lauf.get("ok") else
                         '<i class="bi bi-x-circle-fill ts-fehler"></i> ')
            stuecke.append(
                '<span class="ts-lauf" title="%s">%s%s · %s</span>'
                % (escape(zeit), marke, escape(kurz),
                   cls._sekunden(lauf.get("dauer")).replace(
                       '<span class="ts-nie">—</span>', "—")))
        return " ".join(stuecke)

    def _knopf(self, slug, tab):
        from django.utils.http import urlencode
        ziel = "?" + urlencode({"run": slug, "tab": tab or ""})
        return ('<a class="ts-run" href="%s" title="Diesen Test ausführen">'
                '<i class="bi bi-play-fill"></i> Run</a>' % escape(ziel))
