# -*- coding: utf-8 -*-
u"""Karten - Titel, Sammelknopf und Tabelle einer Testcase-Liste.

    „Innerhalb von einer Kategorie, mehrere Untertabellen nach den Bereichen
    sortiert. EIne Tabelle je Kategorie, aber der Bereich ist nochmal extra
    markiert in der Tabelle" (Edgar, 17.08.2026)

Also EINE Karte je Kategorie. Die Gliederung nach Bereich steckt in der Tabelle
(Spalte „Bereich", Zeilen danach vorsortiert, Trennlinie beim Wechsel — siehe
:class:`~.testtabelle.Testtabelle`), nicht in getrennten Karten. Getrennte
Karten haetten je eigene Sortierung, eigene Spaltenbreiten und eine eigene
Auswahl gehabt; „alle Component anhaken" waere damit unmoeglich geworden.

    karten = Karten(tabellen)
    kategorie["karten"] = karten.je_kategorie(tests, titel="Component-Tests",
                                              key="tests-component",
                                              tab="Component")

Die Rueckgabe ist trotzdem eine LISTE. Die Vorlage schleift darueber, und damit
bleibt der Weg offen, eine Liste spaeter wieder aufzuteilen, ohne jedes Template
anzufassen.
"""
from .testbereiche import Bereiche
from .testtabelle import Eintrag

__all__ = ["Karten"]


class Karten:
    """Baut Kartenlisten (Titel + Sammelknopf + Tabelle) für die Tests-Seite."""

    #: Text fuer eine leere Liste. Er nennt BEIDE Gruende, denn der zweite hat
    #: schon einmal in die Irre gefuehrt (18.08.2026): Im assistant besteht die
    #: Kategorie „Automated" ausschliesslich aus djangoBase-Grundtests, und die
    #: sind per Vorgabe ausgeblendet. Die Tabelle stand leer da und die Meldung
    #: sagte „Labels pruefen" — die Labels waren in Ordnung.
    LEER = ("Keine Tests in dieser Liste. Entweder greifen die Labels in "
            "DJANGOBASE[\"test_discover\"] nicht — oder die gefundenen Fälle "
            "gehören djangoBase selbst und sind ausgeblendet (Einstellungen → "
            "djangoBase → „djangoBase-Testcases sichtbar“).")

    def __init__(self, tabellen, bereiche=None):
        #: :class:`~.testtabelle.Testtabelle` - die eine Tabellendefinition.
        self.tabellen = tabellen
        self.bereiche = bereiche or getattr(tabellen, "bereiche", None) \
            or Bereiche.aus_einstellungen()
        #: Jedes Label, das eine Karte als Sammellauf anbietet. Die View nimmt
        #: sie als erlaubte Laufziele — sie stammen aus ENTDECKTEN Test-IDs,
        #: nicht aus der Anfrage, und sind damit so sicher wie die IDs selbst.
        self.labels = set()

    def je_kategorie(self, tests, titel, key, tab, icon="bi-list-check",
                     leer=None):
        u"""[karte] - eine Karte mit allen Fällen der Kategorie."""
        return [self._karte(titel, tests, key, tab, icon, leer)]

    def _karte(self, titel, tests, key, tab, icon, leer):
        lauf = self.label(tests)
        if lauf:
            self.labels.add(lauf)
        gruppen = self.bereiche.gruppieren(tests)
        # Dictionary gewollt: geht unveraendert in `_testkarte.html`.
        return {"titel": titel, "anzahl": len(tests), "icon": icon,
                "lauf": lauf, "lauf_tab": tab or "",
                # „link" laedt die Seite mit ?run= neu, „knopf" ueberlaesst den
                # Lauf dem Runner der Projektseite - dieselbe Wahl wie in der
                # Tabelle, sonst zeigte eine Karte zwei Bedienarten.
                "lauf_modus": getattr(self.tabellen, "run_modus", "link"),
                # Fuer die Zeile unter dem Titel: „5 Bereiche: Chat, Mail, …"
                "bereiche": gruppen,
                "tabelle": self.tabellen.tabelle(
                    [Eintrag.aus_test(t) for t in tests], key=key, tab=tab,
                    leer=leer or self.LEER)}

    def eine(self, tabelle, titel, anzahl, icon="bi-collection-play"):
        """Eine einzelne Karte (Suiten) - ohne Sammelknopf und ohne Bereiche."""
        return [{"titel": titel, "anzahl": anzahl, "icon": icon,
                 "tabelle": tabelle}]

    @staticmethod
    def label(tests):
        u"""Ein ``manage.py test``-Label, das GENAU diese Faelle faehrt.

        Fuer den Knopf „Alle ausführen" im Kartenkopf. Ueber die Auswahl ginge
        es auch, aber dann stuenden hunderte Kennungen in der Anfrage statt
        eines Labels.

        Gebildet wird das laengste gemeinsame MODULPRAEFIX (die letzten zwei
        Segmente einer Test-ID sind Klasse und Methode). Deckt es mehr ab als
        die Tabelle zeigt, waere der Knopf eine Luege — deshalb gibt es ihn
        dann nicht: ``mail.tests`` unter „Unit" wuerde auch Component und UI
        mitfahren.
        """
        module = set()
        for t in tests:
            teile = str(t.get("id") or "").split(".")
            if len(teile) < 3:
                return ""
            module.add(tuple(teile[:-2]))
        if not module:
            return ""
        erstes = sorted(module)[0]
        gemein = []
        for i, teil in enumerate(erstes):
            if all(len(m) > i and m[i] == teil for m in module):
                gemein.append(teil)
            else:
                break
        # „app.tests" allein reicht nicht: Das faehrt alle Arten der App.
        if len(gemein) < 3 or "tests" not in gemein:
            return ""
        return ".".join(gemein)
