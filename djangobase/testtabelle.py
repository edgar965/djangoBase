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

from .sortierschluessel import Sortierschluessel
from .zeitformat import dauer_text

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
        {"label": "", "key": "wahl", "sortAus": True,
         "titel": "auswählen — „Ausgewählte ausführen“ fährt sie in EINEM Lauf"},
        # Der PLATZ in der Tabelle, änderbar (Ansage 17.08.2026). Nicht
        # sortierbar über die Überschrift: Die Zeilen stehen ohnehin in dieser
        # Reihenfolge, ein Sortierpfeil daneben wäre eine zweite Wahrheit.
        {"label": "Nr.", "key": "nummer", "sortAus": True, "num": True,
         "titel": "Platz in der Tabelle — Zahl ändern verschiebt die Zeile "
                  "(gilt innerhalb ihres Bereichs)"},
        # Die Kategorie (unit, component, …) — der ORDNER der Testdatei. Sie
        # stand bis 17.08.2026 als „Verschieben" ganz rechts; sie gehört nach
        # vorn zu der anderen Einteilung, mit der man arbeitet.
        {"label": "Kategorie", "key": "kategorie", "sortAus": True,
         "titel": "Kategorie des Falls — die Auswahl verschiebt seine "
                  "Testdatei in den Ordner der Zielkategorie; weitere Fälle in "
                  "derselben Datei gehen mit"},
        # Die ZWEITE Einteilung neben der Kategorie (Ansage 17.08.2026:
        # „einmal Kategorien (unit, usw.), einmal Bereich (wie Chat usw.)").
        # Sie steht vorn, weil die Zeilen danach vorsortiert sind — eine
        # Gruppierung, die man rechts sucht, ist keine.
        {"label": "Bereich", "key": "bereich",
         "titel": "Was getestet wird — vom Projekt angegeben "
                  "(Einstellungen → djangoBase → Test-Bereiche). Die Auswahl "
                  "verschiebt die Testdatei; weitere Fälle darin gehen mit"},
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
        {"label": "", "key": "run", "sortAus": True},
    )

    #: Wie der Run-Knopf gebaut wird. „link" laedt die Seite mit ``?run=…`` neu
    #: (Hilfe → Tests). „knopf" rendert einen ``<button data-run="…">`` — fuer
    #: Projektseiten mit eigenem Runner, der den Lauf per AJAX faehrt und die
    #: Zeile live fortschreibt (assistant: ``/tests/<bereich>/<art>/``). Ohne
    #: diese Wahl muesste so eine Seite ihre Tabelle wieder selbst bauen, und
    #: genau das war der Fehler, den „warum gibt es kein Test Seiten template"
    #: gemeldet hat.
    RUN_MODI = ("link", "knopf")

    def __init__(self, historie, aktiver_slug="", tab="", run_modus="link"):
        self.historie = historie
        self.aktiver_slug = aktiver_slug or ""
        self.tab = tab or ""
        self.run_modus = run_modus if run_modus in self.RUN_MODI else "link"
        # EIN Verschieber fuer die ganze Seite: Er sucht die Datei zu jeder
        # Test-ID auf der Platte. Je Zeile ein neuer waere derselbe Weg 173-mal.
        from .testverschieben import Verschieber
        self.verschieber = Verschieber()
        # Dasselbe fuer die Bereiche: Die Zuordnung kommt aus den Einstellungen
        # und ist fuer alle Zeilen dieselbe.
        from .testbereiche import Bereiche
        self.bereiche = Bereiche.aus_einstellungen()
        # Die vom Nutzer gesetzten Plaetze (Spalte „Nr."). Einmal geladen, fuer
        # alle Zeilen der Seite.
        from .testreihenfolge import Reihenfolge
        self.reihenfolge = Reihenfolge()

    # ------------------------------------------------------------- Umformer

    def aus_tests(self, kategorie, tab=None, key=None):
        u"""Tabelle für die Einzeltests einer Kategorie (Unit, Component, …).

        ``key`` ist der Speicher-Schluessel (Sortierung, Spaltenbreiten). Er ist
        uebergebbar, weil dieselben Testfaelle an ZWEI Stellen stehen: im Reiter
        der Kategorie und im Reiter „Alle". Zwei Tabellen mit demselben
        Schluessel wuerden sich die Sortierung gegenseitig ueberschreiben.
        """
        return self.tabelle(
            [Eintrag.aus_test(t) for t in kategorie.get("tests", [])],
            key=key or "tests-%s" % (kategorie.get("typ") or "alle").lower(),
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
        u"""Die Tabelle einer Kategorie — Zeilen nach Bereich vorsortiert.

        EINE Tabelle je Kategorie, nicht eine je Bereich (Ansage 17.08.2026).
        Getrennte Tabellen haetten je eigene Sortierung, eigene Spaltenbreiten
        und eine eigene Auswahl gehabt; „alle Component anhaken" waere damit
        unmoeglich geworden.
        """
        # Bereich zuerst, darin der vom Nutzer gesetzte Platz („Nr."), dann die
        # Kennung. Wer keine Nummer vergeben hat, behaelt die Grundordnung —
        # `Reihenfolge.OHNE` sortiert solche Faelle hinter die numerierten.
        eintraege = sorted(
            eintraege,
            key=lambda e: (self.bereiche.platz(
                               self.bereiche.slug_von(e.ziel or e.kennung)),
                           self.reihenfolge.platz(e.kennung), e.kennung))
        zeilen = self._nummerieren(self._mit_gruppen(
            [self._zeile(e, tab, unter) for e in eintraege]))
        for z in zeilen:
            z["html"] = self._zellen_html(z["zellen"])
        # Dictionary gewollt: geht unveraendert in `_tabelle.html`.
        return {"key": key, "spalten": [dict(s) for s in self.SPALTEN],
                "zeilen": zeilen, "leer": leer, "anzahl": len(zeilen)}

    #: Die Zellen einer Zeile als fertige ``<td>``-Kette zusammensetzen.
    #: Gemessen am 18.08.2026: Der Seitenaufbau steckte zu drei Vierteln in der
    #: Vorlage — 120.898 Variablen-Aufloesungen (`_resolve_lookup`, 1,9 s), weil
    #: JEDE der rund 30.000 Zellen ein Dictionary mit vier optionalen
    #: Schluesseln war und die Vorlage sie einzeln abfragte. Der Inhalt steht
    #: hier ohnehin schon fest; ihn hier zu setzen kostet nichts.
    @staticmethod
    def _zellen_html(zellen):
        stuecke = []
        for z in zellen:
            teile = ["<td"]
            if z.get("klasse"):
                teile.append(' class="%s"' % z["klasse"])
            if z.get("colspan"):
                teile.append(' colspan="%d"' % z["colspan"])
            sortwert = z.get("sort")
            if sortwert is not None:
                # NICHT `str()` (05.09.2026): Eine Dauer von 0,379 s stand
                # als `data-sort="0.379"` da, und die Sortierung las
                # deutsch — der Punkt galt als Tausenderzeichen, aus 0,379
                # wurde 379. Der schnellste Lauf der Seite galt damit als
                # der langsamste.
                teile.append(' data-sort="%s"'
                             % escape(Sortierschluessel.aus(sortwert)))
            if z.get("titel"):
                teile.append(' title="%s"' % escape(str(z["titel"])))
            teile.append(">")
            teile.append(z.get("html") or "")
            teile.append("</td>")
            stuecke.append("".join(teile))
        return "".join(stuecke)

    def _mit_gruppen(self, zeilen):
        u"""Vor jedem neuen Bereich eine Abschnittszeile einziehen.

            „ausführen pro Teil-bereich möglich (also mach eine leere Zeile wenn
            tests zu einem neuen Bereich kommen, mit Button für Mehrauswahl und
            Button zum Batch ausführen NUR der tests in dem Bereich)"
            (Edgar, 17.08.2026)

        Die Zeile traegt den Bereichsnamen, die Anzahl und die zwei Knoepfe. Sie
        ist als ``gruppe`` markiert: Beim Umsortieren nach einer anderen Spalte
        stimmt die Gliederung nicht mehr, deshalb nimmt ``tests_bereiche.js``
        die Zeilen dann heraus und setzt sie zurueck, sobald wieder nach Bereich
        sortiert wird.
        """
        aus, vorher = [], None
        for z in zeilen:
            jetzt = z.get("bereich")
            if jetzt != vorher:
                aus.append(self._gruppenzeile(jetzt, z.get("bereich_name", "")))
                vorher = jetzt
            aus.append(z)
        # Zaehler nachtragen: erst jetzt ist bekannt, wie viele Faelle folgen.
        offen = None
        for z in aus:
            if z.get("gruppe"):
                offen = z
                offen["anzahl"] = 0
            elif offen is not None:
                offen["anzahl"] += 1
        for z in aus:
            if z.get("gruppe"):
                z["zellen"][0]["html"] = z["zellen"][0]["html"].replace(
                    "{{anzahl}}", str(z.get("anzahl") or 0))
        return aus

    @staticmethod
    def _nummerieren(zeilen):
        u"""Die Spalte „Nr." fuellen - je Bereichsabschnitt ab 1.

        Angezeigt wird der PLATZ, nicht der gespeicherte Wert: Nach einem
        Verschieben stehen sonst Luecken und Doppelungen in der Spalte („3, 3,
        7"), und niemand weiss mehr, welche Zahl er eintippen soll. Der Server
        speichert beim Aendern ohnehin die ganze Gruppe neu durch.
        """
        platz = 0
        for z in zeilen:
            if z.get("gruppe"):
                platz = 0
                continue
            platz += 1
            zelle = z["zellen"][1]
            zelle["html"] = zelle["html"].replace("{{nr}}", str(platz))
            zelle["sort"] = platz
        return zeilen

    def _gruppenzeile(self, slug, name):
        u"""Die Abschnittszeile eines Bereichs - Name, Anzahl, zwei Knoepfe."""
        knoepfe = (
            '<button type="button" class="ts-ber-wahl" data-bereich="%(s)s" '
            'title="alle Fälle dieses Bereichs an-/abhaken">'
            '<i class="bi bi-check2-square"></i> Auswählen</button>'
            '<button type="button" class="ts-ber-run" data-bereich="%(s)s" '
            'title="nur diesen Bereich fahren — in EINEM Lauf">'
            '<i class="bi bi-play-fill"></i> Bereich ausführen</button>'
        ) % {"s": escape(slug or "")}
        return {
            "klasse": "ts-gruppe", "gruppe": True, "bereich": slug,
            "zellen": [{"html": '<span class="ts-gruppe-name">%s</span>'
                                '<span class="ts-count">{{anzahl}}</span>%s'
                                % (escape(name or slug or "—"), knoepfe),
                        "colspan": len(self.SPALTEN)}],
        }

    def _zeile(self, e, tab, unter):
        laeufe = (self.historie.suitenlaeufe(e.kennung) if e.ist_suite
                  else self.historie.laeufe(e.kennung))
        letzte = laeufe[0]["dauer"] if laeufe else None
        schnitt = self._schnitt(laeufe)
        trendtext, trendklasse = ("", "") if e.ist_suite \
            else self.historie.trend(e.kennung)
        b_slug, b_name = self.bereiche.zu(e.ziel or e.kennung)
        return {
            "klasse": "aktiv" if self.aktiver_slug == e.kennung else "",
            "bereich": b_slug, "bereich_name": b_name,
            # EINMAL je Zeile (30.08.2026). Vorher trug jedes Bedienelement die
            # Kennung selbst: Nummernfeld, Kategorie-Box, Bereichs-Box. Bei 742
            # Zeilen und 80 Zeichen je Kennung sind das 178 KB Verdrahtung in
            # einer Seite von 1,66 MB - fuer dieselbe Zeichenkette, dreimal in
            # derselben <tr>. `tests_nummer.js` und `tests_verschieben.js`
            # lesen sie jetzt ueber `closest('tr').dataset.id`.
            "id": e.kennung,
            "zellen": [
                {"html": '<input type="checkbox" class="ts-wahl" value="%s" '
                         'aria-label="auswählen">' % escape(e.kennung),
                 "sort": 0, "klasse": "ts-wahl-zelle"},
                # Die Nummer - der Platz in der Tabelle, aenderbar. `{{nr}}`
                # setzt `_nummerieren` ein, sobald die Zeilen stehen (vorher ist
                # der Platz nicht bekannt, weil die Abschnittszeilen dazwischen
                # neu bei 1 beginnen).
                {"html": '<input type="number" class="ts-nr" min="1" '
                         'value="{{nr}}" aria-label="Platz in der Tabelle">',
                 "klasse": "ts-nr-zelle"},
                {"html": self._kategorie(e)},
                # Der Bereich - als Combo-Box, wo er wechselbar ist (Ansage
                # 17.08.2026: „der Bereich und die Kategorie können bei jedem
                # test in der Tabelle per Combo Box geändert werden"). Sortiert
                # wird nach dem NAMEN, nicht nach dem Auswahlfeld.
                {"html": self._bereich(e, b_slug, b_name),
                 "sort": self.bereiche.platz(b_slug)[1],
                 "klasse": "ts-bereich-zelle"},
                # Im Knopf-Modus faehrt der Lauf per AJAX: Dann braucht die
                # Zeile einen Platz, an den der Runner „läuft …“ / ✓ / ✗
                # schreibt. Im Link-Modus laedt die Seite neu, dort waere das
                # ein leeres Element ohne Zweck.
                {"html": '<i class="bi bi-dot"></i> %s%s'
                         % (escape(e.name),
                            ' <span class="ts-status" data-status></span>'
                            if self.run_modus == "knopf" else ""),
                 "titel": e.titel},
                # Titel dazu: Die Spalten sind gleich breit, der Modulpfad wird
                # abgeschnitten — vollständig steht er im Tooltip.
                {"html": escape(e.ziel), "klasse": "ts-ziel", "titel": e.ziel},
                {"html": self._sekunden(letzte), "sort": letzte, "klasse": "num"},
                {"html": self._sekunden(schnitt), "sort": schnitt, "klasse": "num"},
                {"html": ('<span class="ts-trend %s">%s</span>'
                          % (trendklasse, escape(trendtext))) if trendtext else "",
                 "sort": self._trendwert(trendtext), "klasse": "num"},
                {"html": self._laufliste(laeufe, mit_status=e.ist_suite),
                 "sort": len(laeufe)},
                {"html": self._knopf(e.kennung,
                                     self.tab if tab is None else tab, unter)},
            ],
        }

    def _bereich(self, e, slug, name):
        u"""Die Combo-Box „Bereich" - oder nur die Marke.

        Wechselbar ist der Bereich unter denselben Bedingungen wie die
        Kategorie: einzelner Python-Testfall, Datei in einem ``tests``-Baum,
        und es muss Zielbereiche MIT Modulpraefix geben. Suiten, UI-Faelle und
        djangoBase-eigene Tests zeigen ihn nur an.
        """
        from .testverschieben import Verschieber
        marke = ('<span class="ts-bereich" data-bereich="%s">%s</span>'
                 % (escape(slug), escape(name)))
        if e.ist_suite or Verschieber.aus_djangobase(e.kennung):
            return marke
        _slug, datei = self.verschieber.bereich_moeglich(e.kennung)
        if datei is None:
            return marke
        # Kennung: siehe `data-id` auf der Zeile. Tooltip: nur das, was sich
        # je Zeile unterscheidet - was die Spalte tut, steht im Spaltenkopf.
        return ('<select class="ts-ber ts-lazy" data-bereich="%s" '
                'data-liste="ts-ber-optionen" '
                'title="%s — weitere Fälle darin gehen mit">'
                '<option value="%s" selected>%s</option></select>'
                % (escape(slug), escape(datei.name), escape(slug), escape(name)))

    def _kategorie(self, e, kategorie_name=""):
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
        # Faelle, die djangoBase selbst mitbringt, tragen die Kategorie
        # „DjangoBase" (Ansage 17.08.2026). Sie gehoeren der Bibliothek und sind
        # nicht verschiebbar — vorher stand dort ein nacktes „—", das wie ein
        # Fehler aussah.
        if Verschieber.aus_djangobase(e.kennung):
            return ('<span class="ts-kat-fest ts-kat-fremd" title="Testfall aus '
                    'djangoBase selbst — gehört der Bibliothek, nicht diesem '
                    'Projekt. Ein-/ausblenden über Einstellungen → djangoBase → '
                    '„djangoBase-Testcases sichtbar“.">%s</span>'
                    % escape(Verschieber.EIGENE_KATEGORIE))
        art, datei = self.verschieber.moeglich(e.kennung)
        wahl = Verschieber.auswahl(art, datei is not None)
        if datei is None:
            return ('<span class="ts-kat-fest" title="nicht verschiebbar — die '
                    'Datei liegt nicht in einem tests/&lt;art&gt;/-Ordner">%s</span>'
                    % escape(kategorie_name or wahl[0][1]))
        # NUR die aktuelle Option (Ansage: der Aufbau war langsam). Die
        # restlichen holt `tests_combo.js` beim Aufklappen aus EINER Liste im
        # DOM. Gemessen am 18.08.2026: 2.750 Zeilen x 21 Optionen sind rund
        # 58.000 `<option>` und damit über die Hälfte der 4,4 MB, die die Seite
        # wog — für Auswahlfelder, von denen man eines benutzt.
        return ('<select class="ts-kat ts-lazy" data-art="%s" '
                'data-liste="ts-kat-optionen" '
                'title="%s — weitere Fälle darin gehen mit">'
                '<option value="%s" selected>%s</option></select>'
                % (escape(art), escape(datei.name), escape(art),
                   escape(Verschieber.NAMEN.get(art, art))))

    def optionen(self):
        u"""Die vollstaendigen Auswahllisten - EINMAL je Seite.

        Sie gehen als JSON ins DOM; `tests_combo.js` fuellt damit die Combo-Box,
        die gerade aufgeklappt wird. Vorher stand jede Liste in JEDER Zeile.
        """
        from .testverschieben import Verschieber
        # Dictionary gewollt: geht als json_script in die Vorlage.
        return {
            "kategorie": [{"wert": a, "name": Verschieber.NAMEN.get(a, a)}
                          for a, _n, _g in Verschieber.auswahl("", True)],
            "bereich": [{"wert": w, "name": n}
                        for w, n, _g in self.bereiche.auswahl("", True)],
        }

    @staticmethod
    def _schnitt(laeufe):
        if not laeufe:
            return None
        return round(sum(x["dauer"] for x in laeufe) / len(laeufe), 3)

    # ------------------------------------------------------------ Bausteine

    @staticmethod
    def _sekunden(wert, stellen=2):
        u"""Laufzeit lesbar — Regel in :func:`.zeitformat.dauer_text`.

        Hier steht nur noch der Sonderfall der Tabelle: „nie gelaufen" ist ein
        graues Zeichen, kein leerer Text.
        """
        if wert is None:
            return '<span class="ts-nie">—</span>'
        return dauer_text(wert, stellen)

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
        if self.run_modus == "knopf":
            return ('<button type="button" class="ts-run" data-run="%s" '
                    'title="Diesen Test ausführen">'
                    '<i class="bi bi-play-fill"></i> Run</button>'
                    % escape(kennung))
        felder = {"run": kennung, "tab": tab or ""}
        if unter:
            felder["unter"] = unter
        return ('<a class="ts-run" href="?%s" title="Diesen Test ausführen">'
                '<i class="bi bi-play-fill"></i> Run</a>'
                % escape(urlencode(felder)))
