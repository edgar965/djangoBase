# -*- coding: utf-8 -*-
u"""Dateigroesse - Dateien und Funktionen, die zu groß geworden sind.

WAS ES IM REVIEW GEFUNDEN HAT (shortlongx, August 2026)
=======================================================
``views.py`` mit 12.223 Zeilen, ``test_runner.py`` mit 3.324, dazu Hilfe-Seiten
mit 1.027 und 855 Zeilen und zwei Browser-Module mit 478 und 427. Keine davon
war „falsch" - sie waren nur nicht mehr zu ueberblicken, und genau darin steckten
die Fehler, die niemand sah: eine Methode, die zweimal existierte; ein Block, der
beim Herausschneiden mitging.

DIE ZAHL IST KEIN SELBSTZWECK
=============================
300 Zeilen sind eine Faustregel, keine Wahrheit. Was zählt, ist die Frage, die
sie erzwingt: Welche ZUSTAENDIGKEITEN stecken hier drin? Beim Aufteilen von
``best_technik.js`` (478 Zeilen) kamen vier heraus - Laden/Status, die beiden
Kreuztabellen, der Veraltet-Hinweis und die Verdrahtung. Erst danach war zu
sehen, dass der Lade-Pfad seinen Zustand in Modul-Variablen hielt.

ZUM AUFTEILEN GEHOERT EINE GEGENPROBE
=====================================
Beim Aufteilen von ``modus_sicht.js`` wurde eine Methode (``_hinweis``)
mitgeloescht, weil sie zwischen zwei ausgeschnittenen Bloecken lag. Kein Test sah
es. Deshalb: Methodenliste VORHER und NACHHER vergleichen (siehe die Lehre
„Aufteilen mit Netz").
"""
import ast

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug


class Dateigroesse(Werkzeug):
    slug = "dateigroesse"
    titel = "Zu große Dateien und Funktionen"
    zweck = ("Dateien über 300 Zeilen, Klassen über 300 und Funktionen über 60 — "
             "je mit der Zahl der Zuständigkeiten, die drinstecken.")
    befund = ("Eine views.py mit 12.223 Zeilen und zwei Browser-Module mit 478 "
              "und 427. Beim Aufteilen fielen mehrere Fehler auf, die vorher "
              "niemand sehen konnte.")
    abhilfe = ("Nach Zuständigkeiten schneiden, nicht nach Zeilenzahl. Vor und "
               "nach dem Schnitt die Liste der Methoden vergleichen.")
    dauer = "3–10 s"
    kriterium = 2

    GRENZE_DATEI = 300
    GRENZE_KLASSE = 300
    GRENZE_FUNKTION = 60

    #: JS-Module hatten bis zum 22.08.2026 eine eigene, strengere Grenze
    #: (200). Die Projektregel kennt aber nur EINE Zahl fuer eine Datei —
    #: „ca. 200-300 Zeilen, was darueber hinauswaechst, wird aufgeteilt" —
    #: und sie unterscheidet nicht nach Sprache. Zwei Zahlen fuer dieselbe
    #: Regel hiessen: ein 250-Zeilen-Modul ist als .py in Ordnung und als
    #: .js ein Befund. Jetzt gilt fuer beide GRENZE_DATEI (Ansage Edgar).
    GRENZE_JS = GRENZE_DATEI

    #: Eine Funktion mit 70 Zeilen (Grenze 60). Der Rumpf wird erzeugt statt
    #: ausgeschrieben - eine Grenze prueft man mit Zaehlen, nicht mit Tippen.
    anlassfall = Anlassfall(
        {"lang.py": "def viel_zu_lang(werte):\n    aus = []\n"
                    + "".join("    aus.append(werte[%d])\n" % i
                              for i in range(70))
                    + "    return aus\n"},
        erwartet_in="viel_zu_lang",
        warum="Kriterium 2: Dateien 200–300 Zeilen, Funktionen unter 60")

    def laufen(self):
        zeilen = []
        doku = 0
        for d in self.dateien():
            if d.codezeilen > self.GRENZE_DATEI:
                zeilen.append(self._zeile(d, 1, "Datei", d.pfad.name,
                                          d.codezeilen, d.zeilen,
                                          self.GRENZE_DATEI))
            elif d.zeilen > self.GRENZE_DATEI:
                doku += 1                     # nur die Herleitung ist lang
            if d.baum is None:
                continue
            for k in d.knoten(ast.ClassDef):
                n, ganz = self._laenge(d, k)
                if n > self.GRENZE_KLASSE:
                    zeilen.append(self._zeile(d, k.lineno, "Klasse", k.name,
                                              n, ganz, self.GRENZE_KLASSE))
                elif ganz > self.GRENZE_KLASSE:
                    doku += 1
            for k in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                n, ganz = self._laenge(d, k)
                if n > self.GRENZE_FUNKTION:
                    zeilen.append(self._zeile(d, k.lineno, "Funktion", k.name,
                                              n, ganz, self.GRENZE_FUNKTION))
                elif ganz > self.GRENZE_FUNKTION:
                    doku += 1
        zeilen.sort(key=lambda z: -z["code"])
        # Auch die JS-Module: Sie wachsen genauso, werden aber von keinem
        # Python-Werkzeug gesehen.
        #
        # `frontendquellen()` statt `dateien(".js")`: Sonst steht ein Vite-Buendel
        # mit 7.163 Zeilen als Spitzenbefund ganz oben — erzeugter Code, den
        # niemand aufteilen kann, und er verdeckt die echten 300-Zeilen-Module
        # (3DTools, 17.08.2026).
        for p, kurz in self.frontendquellen().paare(".js"):
            if p.stat().st_size == 0:
                continue
            n = p.read_text(encoding="utf-8", errors="replace").count("\n") + 1
            if n > self.GRENZE_JS:
                # JS wird weiter nach Gesamtzeilen gemessen: Fuer .js gibt es
                # hier keinen Syntaxbaum, aus dem sich Doku sicher abziehen
                # liesse - und geraten wird nicht.
                zeilen.append({"datei": kurz, "zeile": 1, "art": "JS-Modul",
                               "name": p.name, "code": n, "gesamt": n,
                               "grenze": self.GRENZE_JS})
        kopf = "%d Stellen über der Faustregel" % len(zeilen)
        if doku:
            kopf += " · %d nur durch Doku über der Grenze (nicht gelistet)" % doku
        return Ergebnis(
            ["datei", "zeile", "art", "name", "code", "gesamt", "grenze"], zeilen,
            kopf,
            "Gemessen werden CODE-Zeilen; „gesamt“ steht daneben. Die Grenzen "
            "sind Faustregeln. Der Wert steckt in der Frage, die sie erzwingen: "
            "Wie viele Zuständigkeiten stecken hier drin?")

    @staticmethod
    def _zeile(datei, zeile, art, name, code, gesamt, grenze):
        # Dictionary gewollt: geht unveraendert als Tabellenzeile hinaus.
        return {"datei": datei.name, "zeile": zeile, "art": art, "name": name,
                "code": code, "gesamt": gesamt, "grenze": grenze}

    @staticmethod
    def _laenge(datei, knoten):
        u"""``(Code-Zeilen, Zeilen gesamt)`` eines Knotens."""
        ende = getattr(knoten, "end_lineno", None) or knoten.lineno
        return (datei.codezeilen_zwischen(knoten.lineno, ende),
                ende - knoten.lineno + 1)
