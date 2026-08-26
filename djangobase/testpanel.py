# -*- coding: utf-8 -*-
u"""Panel - der Inhalt EINES Reiters der Tests-Seite.

    „der aufbau der testseiten ist langsam" (Edgar, 18.08.2026)

Gemessen wurde vor der Aenderung: 2,92 MB HTML, 1.513 Tabellenzeilen und rund
0,6 s allein fuer den Aufbau — fuer sechs Reiter, von denen man einen sieht.
Diese Klasse baut deshalb nur den Inhalt, der wirklich angezeigt wird; die
uebrigen Reiter holt ``tests_tabs.js`` beim ersten Klick nach
(``?tab=…&teil=1``).

WAS EIN PANEL IST
=================
    „Alle"        die Sammellaeufe je Kategorie plus ihre Testfaelle
    <Kategorie>   die Faelle dieser Kategorie (Unit, Component, …)
    „UI"          die Browser-Tests (Zeilen baut ``tests_ui.js``)
    „Suiten"      die konfigurierten Batch-Kommandos, je Gruppe eine Karte

Die REITERLEISTE braucht das nicht: Ihre Zaehler stehen in ``kategorien`` und
``kat.arten``, und die kommen aus der (gecachten) Discovery.
"""
from django.urls import reverse

from .testkategorien import Kategorien

__all__ = ["Panel"]


class Panel:
    """Baut die Karten eines einzelnen Reiters."""

    def __init__(self, kat, kategorien, gruppen, karten, tabellen, ui, historie):
        self.kat = kat
        self.kategorien = kategorien
        self.gruppen = gruppen
        self.karten = karten
        self.tabellen = tabellen
        self.ui = ui
        self.historie = historie

    # ------------------------------------------------------------- Auswahl

    def name(self, gewuenscht):
        u"""Welcher Reiter gezeigt wird - gepruefter Name, nie etwas Fremdes."""
        moeglich = self.namen()
        if gewuenscht in moeglich:
            return gewuenscht
        return moeglich[0] if moeglich else ""

    def namen(self):
        aus = []
        if self.kat.alles:
            aus.append("Alle")
        aus.extend(k["typ"] for k in self.kategorien)
        if self.ui:
            aus.append("UI")
        if self.kat.suiten:
            aus.append("Suiten")
        # AUFZEICHNEN steht IMMER zur Verfuegung (Auftrag Edgar, 20.08.2026):
        # Er haengt an keiner Testkonfiguration - was er sammelt, sind die
        # Aktionen des Nutzers. Am Ende der Reihe, weil er kein Testlauf ist,
        # sondern der Weg zu einem neuen Testfall.
        aus.append("Aufzeichnen")
        return aus

    # --------------------------------------------------------------- Bauen

    def bauen(self, name):
        u"""Der Inhalt des Reiters ``name`` - für ``_testpanel.html``."""
        if name == "Alle":
            return {"alles": self.kat.alles, "arten": self._arten()}
        if name == "UI":
            return {"ui": True, "ui_karte": self._ui_karte(),
                    "ui_config": self._ui_config(),
                    "ui_historie": self._ui_historie()}
        if name == "Aufzeichnen":
            # Der Reiter hat keinen Server-Inhalt: Zustand und Liste holt
            # ``aufzeichnung.js`` beim Oeffnen, weil sich beides waehrend einer
            # laufenden Aufnahme sekuendlich aendert. Eine serverseitig
            # gerenderte Liste waere ab dem ersten Klick veraltet.
            return {"aufzeichnen": True}
        if name == "Suiten":
            return {"karten": [k for g in self._suiten() for k in g["karten"]]}
        for k in self.kategorien:
            if k["typ"] == name:
                return {"karten": self.karten.je_kategorie(
                    k.get("tests") or [], titel="%s-Tests" % k["typ"],
                    key="tests-%s" % Kategorien.schluessel(k["typ"]),
                    tab=k["typ"])}
        # Dictionary gewollt: leeres Panel statt Ausnahme - ein unbekannter
        # Reitername kommt aus der Adresszeile, nicht aus dem Code.
        return {"karten": []}

    # ---------------------------------------------------------- Bausteine

    def _arten(self):
        u"""Reiter „Alle": je Kategorie ihre TESTFAELLE, nicht ihre Suiten.

        Gemeldet am 17.08.2026 („die Alle Seite enthält nicht alle tests!"):
        Dort standen die Suiten, also ganze Ordner — und eine Suite hat keine
        verschiebbare Datei, weshalb auch die Combo-Box fehlte.
        """
        nach_typ = {k["typ"]: k for k in self.kategorien}
        for a in self.kat.arten:
            faelle = nach_typ.get(a["kurz"])
            if faelle is None:
                # „Nach App" ist keine Art, sondern der Rest: Eintraege ohne
                # erkennbare Kategorie. Dafuer gibt es keine Einzelfall-Liste.
                a["karten"] = self.karten.eine(
                    self.tabellen.aus_befehlen(a["befehle"],
                                               key="test-alle-%s" % a["art"],
                                               tab="Alle"),
                    titel="%s — Suiten" % a["kurz"], anzahl=len(a["befehle"]))
                continue
            a["karten"] = self.karten.je_kategorie(
                faelle.get("tests") or [],
                titel="%s — Testfälle" % a["kurz"],
                key="test-alle-%s" % a["art"], tab="Alle")
        return self.kat.arten

    def _suiten(self):
        for g in self.gruppen:
            g["karten"] = self.karten.eine(
                self.tabellen.aus_befehlen(
                    g["befehle"],
                    key="test-suiten-%s" % Kategorien.schluessel(g["name"]),
                    tab="Suiten"),
                titel=g["name"], anzahl=len(g["befehle"]))
        return self.gruppen

    def _ui_karte(self):
        # Die Zeilen baut `tests_ui.js` aus der testcases.js des Projekts; von
        # hier kommen nur die Kopfzeile (dieselben Spalten wie ueberall) und
        # die bisherigen Laufzeiten.
        return {"titel": "UI-Tests", "icon": "bi-window",
                "hinweis": "laufen im Browser (Iframe)",
                "tabelle": self.tabellen.tabelle([], key="tests-ui-browser",
                                                 tab="UI",
                                                 leer="Lade Test-Liste …")}

    def _ui_config(self):
        ui = self.ui or {}
        # Dictionary gewollt: geht als json_script ins DOM, damit das Skript
        # eine eigene Datei bleiben kann.
        return {"runner": ui.get("runner", ""), "cases": ui.get("cases", ""),
                "seiten": ui.get("seiten", {}),
                "dauerUrl": reverse("djangobase:tests_dauer")}

    def _ui_historie(self):
        return {k: v for k, v in self.historie.daten["tests"].items()
                if k.startswith("ui:")}
