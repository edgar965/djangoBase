# -*- coding: utf-8 -*-
u"""JsFunktionen - zu lange Funktionen in Browser-Modulen.

DER BEFUND (3DTools, 16.08.2026)
================================
Der Auftrag verlangte ES-Module von etwa 200 Zeilen. Die Dateigroesse allein
trifft aber nicht den Kern: ``viewer/cloth.js`` hatte 339 Zeilen, davon 245 in
EINER Funktion (``loadClothUI``), die vier Bedienbereiche hintereinander
aufbaute. Nach der Aufteilung waren es fuenf Klassen mit je unter 120 Zeilen -
und dabei fielen drei doppelte Bloecke auf, die in der langen Funktion niemand
gesehen hatte.

Verlauf im Ursprungsprojekt: 46 Funktionen ab 90 Zeilen zu Beginn, 12 am Ende.

WIE GEZAEHLT WIRD
=================
Ueber die Klammerbilanz ab der Funktionszeile - kein JS-Parser. Klammern in
Zeichenketten zaehlen mit; fuer die Frage „welche Funktion ist zu lang" reicht
das und es braucht keine Abhaengigkeit. Die Zahl kann bei Dateien mit vielen
Template-Strings etwas zu hoch liegen.

Die Grenze steht in ``DJANGOBASE["skills2_funktionsgrenze"]`` (Vorgabe 90).
"""
import re

from django.conf import settings

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["JsFunktionen"]

#: `function name(`, `async name(` und Methoden `name(...) {`
MUSTER = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"
                    r"|^\s*(?:export\s+)?(?:static\s+)?(?:async\s+)?(\w+)"
                    r"\s*\([^)]*\)\s*\{")


class JsFunktionen(Werkzeug):
    slug = "jsfunktionen"
    titel = "Browser-Module: zu lange Funktionen"
    zweck = ("Findet Funktionen und Methoden ab einer Zeilengrenze - die "
             "dicken FUNKTIONEN, nicht die dicken Dateien.")
    befund = ("3DTools: `loadClothUI` hatte 245 Zeilen in einer Datei von 339. "
              "Beim Aufteilen fielen drei doppelte Bloecke auf, die vorher "
              "niemand gesehen hatte. 46 solcher Funktionen zu Beginn, 12 am "
              "Ende des Durchgangs.")
    abhilfe = ("Aufteilen: Was die Funktion NACHEINANDER tut, wird je eine "
               "Methode. Wiederholte Bloecke mit anderen Werten werden eine "
               "Methode mit Tabelle.")
    dauer = "unter 1 s"
    kriterium = 2

    VORGABE_GRENZE = 90

    def grenze(self):
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get(
            "skills2_funktionsgrenze")
        try:
            return int(eigen)
        except (TypeError, ValueError):
            return JsFunktionen.VORGABE_GRENZE

    #: Eine Funktion mit 100 Zeilen (Vorgabe-Grenze 90), erzeugt statt getippt.
    anlassfall = Anlassfall(
        {"lang.js": "export function vielZuLang(werte) {\n  const aus = [];\n"
                    + "".join("  aus.push(werte[%d]);\n" % i for i in range(100))
                    + "  return aus;\n}\n"},
        erwartet_in="vielZuLang",
        warum="Kriterium 3: die dicken Funktionen, nicht die dicken Dateien")

    def laufen(self):
        grenze = self.grenze()
        gefunden = []
        for pfad, kurz in self._quellen():
            zeilen = pfad.read_text(encoding="utf-8",
                                    errors="replace").split("\n")
            gefunden.extend(self._in_datei(kurz, zeilen, grenze))
        gefunden.sort(key=lambda e: -e[0])
        zeilen_aus = [{"zeilen": laenge, "ort": "%s:%d" % (ort, nummer),
                       "name": name + "()"}
                      for laenge, ort, name, nummer in gefunden]
        return Ergebnis(
            ["zeilen", "ort", "name"], zeilen_aus,
            zusammenfassung="%d Funktionen ab %d Zeilen"
                            % (len(gefunden), grenze),
            hinweis="Gezaehlt ueber die Klammerbilanz; bei vielen "
                    "Template-Strings kann die Zahl etwas zu hoch liegen.")

    @staticmethod
    def _in_datei(kurz, zeilen, grenze):
        gefunden = []
        i = 0
        while i < len(zeilen):
            treffer = MUSTER.match(zeilen[i])
            if not treffer or "{" not in zeilen[i]:
                i += 1
                continue
            name = treffer.group(1) or treffer.group(2)
            tiefe = 0
            j = i
            while j < len(zeilen):
                tiefe += zeilen[j].count("{") - zeilen[j].count("}")
                if tiefe <= 0 and j > i:
                    break
                j += 1
            laenge = j - i + 1
            if laenge >= grenze:
                gefunden.append((laenge, kurz, name, i + 1))
            i = j + 1
        return gefunden

    #: Ausschlussliste und Suche stehen seit dem 17.08.2026 in
    #: ``Frontendquellen`` — vorher hatte sie jedes JS-Werkzeug einzeln,
    #: in vier verschiedenen Fassungen.
    def _quellen(self):
        return self.frontendquellen().paare(".js")
