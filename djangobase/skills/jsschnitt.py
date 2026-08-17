# -*- coding: utf-8 -*-
u"""JsSchnitt - wo laesst sich eine zu grosse JS-Datei ohne Zirkel teilen?

DIE FRAGE, DIE VOR DEM UMBAU KOMMT (16.08.2026)
===============================================
„JS-Module von hoechstens ~200 Zeilen" klingt nach einer Zeilenzahl, ist aber
eine Frage nach ABHAENGIGKEIT: Ein Block, den man herausloest, darf nicht
zurueckrufen, was ihn selbst braucht.

    dax_stock3_tabelle.js   13 Funktionen liessen sich schneiden - aber vier
                            davon rufen ``renderS3Table`` aus dem Rest, und der
                            Rest ruft alle dreizehn. Zirkel, kein Schnitt.

Dieses Werkzeug probiert je Datei JEDE Funktionsgrenze durch und meldet die
beste: die, bei der beide Haelften unter der Grenze bleiben und hoechstens EINE
Richtung Abhaengigkeit besteht. Von 44 zu grossen Dateien im shortlongx-Review
waren 13 so schneidbar - die uebrigen 31 brauchen einen anderen Zugriff
(Vererbung, oder gar keinen).

WAS ES NICHT SAGT
=================
Ob der Schnitt inhaltlich Sinn ergibt. „Beide Haelften unter 200" ist eine
Buchhaltung; ob die neue Datei eine eigene FRAGE beantwortet, sieht nur ein
Mensch. Das Werkzeug nennt die Stelle, nicht den Grund.
"""
import re

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2


class Schnittstelle:
    """Eine moegliche Trennlinie in einer Datei - und was sie kosten wuerde."""

    def __init__(self, zeilen, bei, grenze):
        self.zeilen = zeilen
        self.bei = bei                     # 0-basiert
        self.grenze = grenze
        self.oben = "\n".join(zeilen[:bei])
        self.unten = "\n".join(zeilen[bei:])

    @staticmethod
    def _namen(text):
        return set(re.findall(
            r"^(?:export )?(?:async )?(?:function|class|const) (\w+)", text, re.M))

    @staticmethod
    def _benutzt(wer, namen):
        return {n for n in namen if re.search(r"(?<![.\w])%s\b" % re.escape(n), wer)}

    @property
    def unten_braucht_oben(self):
        return self._benutzt(self.unten, self._namen(self.oben))

    @property
    def oben_braucht_unten(self):
        return self._benutzt(self.oben, self._namen(self.unten))

    @property
    def zirkel(self):
        return bool(self.unten_braucht_oben) and bool(self.oben_braucht_unten)

    @property
    def haelften(self):
        return self.bei, len(self.zeilen) - self.bei

    @property
    def gut(self):
        a, b = self.haelften
        return not self.zirkel and a <= self.grenze and b <= self.grenze

    @property
    def richtung(self):
        if not (self.unten_braucht_oben or self.oben_braucht_unten):
            return "keine"
        return "unten←oben" if not self.oben_braucht_unten else "oben←unten"


class JsSchnitt(Werkzeug2):
    slug = "jsschnitt"
    titel = "Wo lässt sich eine JS-Datei teilen?"
    zweck = ("Für jede JS-Datei über der Grenze: die beste Trennlinie, bei der "
             "beide Hälften darunter bleiben und kein Zirkelbezug entsteht.")
    befund = ("Von 44 zu großen Dateien waren 13 zirkelfrei schneidbar. Die "
              "übrigen 31 haben keinen solchen Punkt — dort hilft nur Vererbung "
              "oder gar nichts.")
    abhilfe = ("An der genannten Zeile schneiden. Die herausgelöste Hälfte "
               "beantwortet eine eigene Frage — sonst ist der Schnitt nur "
               "Buchhaltung.")
    dauer = "2–6 s"
    kriterium = 3

    GRENZE = 200
    #: Naeher als so viele Zeilen an den Rand wird nicht geschnitten.
    RAND = 40

    #: Eine JS-Datei ueber der Grenze, aufgebaut aus zwei klar trennbaren
    #: Haelften - so muss eine Trennlinie zu finden sein. Je 120 Funktionen:
    #: Der erste Versuch hatte 122 Zeilen und lag damit UNTER der Grenze von
    #: 200 - der Check meldete „blind", obwohl das Werkzeug recht hatte.
    anlassfall = Anlassfall(
        {"gross.js": "const A = 1;\n"
                     + "".join("export function ersteHaelfte%d() { return A + %d; }\n"
                               % (i, i) for i in range(120))
                     + "const B = 2;\n"
                     + "".join("export function zweiteHaelfte%d() { return B + %d; }\n"
                               % (i, i) for i in range(120))},
        erwartet_in="gross.js",
        warum="Kriterium 3: JS-Module unter 200 Zeilen halten")

    def laufen(self):
        zeilen = []
        # `frontendquellen()` statt `dateien(".js")`: Sonst steht das gebaute
        # Vite-Buendel in der Liste — `theatre-app.js`, 7.163 Zeilen, „kein
        # zirkelfreier Punkt". Erzeugten Code teilt niemand, und die Quelle
        # daneben wird sowieso schon geprueft (17.08.2026, 3DTools).
        for pfad, kurz in self.frontendquellen().paare(".js"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            quellzeilen = text.split("\n")
            if len(quellzeilen) <= self.GRENZE:
                continue
            beste = self._beste(quellzeilen)
            a, b = beste.haelften if beste else (len(quellzeilen), 0)
            zeilen.append({
                "datei": pfad.name, "zeilen": len(quellzeilen),
                "schnitt bei": beste.bei + 1 if beste else "—",
                "hälften": "%d / %d" % (a, b) if beste else "—",
                "abhängigkeit": beste.richtung if beste else "—",
                "bewertung": "schneidbar" if beste else "kein zirkelfreier Punkt",
            })
        zeilen.sort(key=lambda z: (z["bewertung"] != "schneidbar", -z["zeilen"]))
        gut = [z for z in zeilen if z["bewertung"] == "schneidbar"]
        return Ergebnis(
            ["datei", "zeilen", "schnitt bei", "hälften", "abhängigkeit", "bewertung"],
            zeilen,
            "%d Dateien über %d Zeilen, davon %d zirkelfrei schneidbar"
            % (len(zeilen), self.GRENZE, len(gut)),
            "Die Zeilenzahl ist nicht das Problem — der Zirkelbezug ist es. Wo "
            "keine Trennlinie steht, hilft Vererbung: die herausgelöste Hälfte "
            "wird Basisklasse, dann wandert kein Aufrufer mit.")

    def _beste(self, quellzeilen):
        mitte = len(quellzeilen) / 2
        grenzen = [i for i, z in enumerate(quellzeilen)
                   if re.match(r"^(?:export )?(?:async )?(?:function|class) \w+", z)]
        kandidaten = [Schnittstelle(quellzeilen, b, self.GRENZE) for b in grenzen
                      if self.RAND < b < len(quellzeilen) - self.RAND]
        gute = [k for k in kandidaten if k.gut]
        return min(gute, key=lambda k: abs(k.bei - mitte)) if gute else None
