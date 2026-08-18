# -*- coding: utf-8 -*-
u"""Dateigroesse - Dateien und Funktionen, die zu gross geworden sind.

WAS ES IM REVIEW GEFUNDEN HAT (shortlongx, August 2026)
=======================================================
``views.py`` mit 12.223 Zeilen, ``test_runner.py`` mit 3.324, dazu Hilfe-Seiten
mit 1.027 und 855 Zeilen und zwei Browser-Module mit 478 und 427. Keine davon
war „falsch" - sie waren nur nicht mehr zu ueberblicken, und genau darin steckten
die Fehler, die niemand sah: eine Methode, die zweimal existierte; ein Block, der
beim Herausschneiden mitging.

DIE ZAHL IST KEIN SELBSTZWECK
=============================
300 Zeilen sind eine Faustregel, keine Wahrheit. Was zaehlt, ist die Frage, die
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
        for d in self.dateien():
            if d.zeilen > self.GRENZE_DATEI:
                zeilen.append({"datei": d.name, "zeile": 1, "art": "Datei",
                               "name": d.pfad.name, "groesse": d.zeilen,
                               "grenze": self.GRENZE_DATEI})
            if d.baum is None:
                continue
            for k in d.knoten(ast.ClassDef):
                n = self._laenge(k)
                if n > self.GRENZE_KLASSE:
                    zeilen.append({"datei": d.name, "zeile": k.lineno, "art": "Klasse",
                                   "name": k.name, "groesse": n,
                                   "grenze": self.GRENZE_KLASSE})
            for k in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                n = self._laenge(k)
                if n > self.GRENZE_FUNKTION:
                    zeilen.append({"datei": d.name, "zeile": k.lineno, "art": "Funktion",
                                   "name": k.name, "groesse": n,
                                   "grenze": self.GRENZE_FUNKTION})
        zeilen.sort(key=lambda z: -z["groesse"])
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
            if n > 200:
                zeilen.append({"datei": kurz, "zeile": 1, "art": "JS-Modul",
                               "name": p.name, "groesse": n, "grenze": 200})
        return Ergebnis(
            ["datei", "zeile", "art", "name", "groesse", "grenze"], zeilen,
            "%d Stellen über der Faustregel" % len(zeilen),
            "Die Grenzen sind Faustregeln. Der Wert steckt in der Frage, die sie "
            "erzwingen: Wie viele Zuständigkeiten stecken hier drin?")

    @staticmethod
    def _laenge(knoten):
        ende = getattr(knoten, "end_lineno", None) or knoten.lineno
        return ende - knoten.lineno + 1
