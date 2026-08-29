# -*- coding: utf-8 -*-
u"""JsSchnitt - wo lässt sich eine zu große JS-Datei ohne Zirkel teilen?

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
Richtung Abhaengigkeit besteht. Von 44 zu großen Dateien im shortlongx-Review
waren 13 so schneidbar - die übrigen 31 brauchen einen anderen Zugriff
(Vererbung, oder gar keinen).

WAS ES NICHT SAGT
=================
Ob der Schnitt inhaltlich Sinn ergibt. „Beide Haelften unter 200" ist eine
Buchhaltung; ob die neue Datei eine eigene FRAGE beantwortet, sieht nur ein
Mensch. Das Werkzeug nennt die Stelle, nicht den Grund.
"""
import re

from .anlassfall import Anlassfall
from .dateigroesse import Dateigroesse
from .jszirkel import Zirkelkarte
from .werkzeug import Ergebnis, Werkzeug


class JsSchnitt(Werkzeug):
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
    dauer = "unter 1 s"
    kriterium = 3

    #: DIESELBE ZAHL WIE `dateigroesse` (28.08.2026).
    #:
    #: Hier stand 200, dort 300 — zwei Zahlen fuer dieselbe Regel. Am
    #: 22.08.2026 war `dateigroesse.GRENZE_JS` ausdruecklich auf
    #: `GRENZE_DATEI` gezogen worden, mit der Begruendung: „Die Projektregel
    #: kennt aber nur EINE Zahl fuer eine Datei … und sie unterscheidet nicht
    #: nach Sprache" (Ansage Edgar). Dieses Werkzeug hat den Schritt nicht
    #: mitgemacht.
    #:
    #: Die Folge war ein Werkzeugkasten, der sich selbst widerspricht: In
    #: 3DTools meldete `dateigroesse` NULL Befunde und `jsschnitt` 46 — alle
    #: 46 Dateien lagen zwischen 201 und 297 Zeilen, also innerhalb der
    #: Regel. Wer die Liste abarbeitet, zerschneidet 46 Dateien, die in
    #: Ordnung sind; wer sie stehen laesst, gewoehnt sich an eine rote Zahl.
    #: Beides ist schlechter als eine Zahl, die stimmt.
    GRENZE = Dateigroesse.GRENZE_JS

    #: Naeher als so viele Zeilen an den Rand wird nicht geschnitten.
    RAND = 40

    #: Eine JS-Datei ueber der Grenze, aufgebaut aus zwei klar trennbaren
    #: Haelften - so muss eine Trennlinie zu finden sein.
    #:
    #: DIE GROESSE HAENGT AN DER GRENZE, nicht an einer festen Zahl. Das ist
    #: hier schon zweimal schiefgegangen: Der erste Versuch hatte 122 Zeilen
    #: und lag unter der damaligen Grenze von 200; der zweite hatte 242 und
    #: lag unter der Grenze von 300, als sie am 28.08.2026 an `dateigroesse`
    #: angeglichen wurde. Beide Male meldete der Check „blind", obwohl das
    #: Werkzeug recht hatte. Jetzt rechnet die Vorlage mit.
    HAELFTE = GRENZE          # zwei davon liegen sicher darueber

    anlassfall = Anlassfall(
        {"gross.js": "const A = 1;\n"
                     + "".join("export function ersteHaelfte%d() { return A + %d; }\n"
                               % (i, i) for i in range(HAELFTE))
                     + "const B = 2;\n"
                     + "".join("export function zweiteHaelfte%d() { return B + %d; }\n"
                               % (i, i) for i in range(HAELFTE))},
        erwartet_in="gross.js",
        warum="Kriterium 3: JS-Module unter der Dateigroessen-Grenze halten")

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
            karte = Zirkelkarte(quellzeilen)
            beste = self._beste(quellzeilen, karte)
            zeilen.append({
                "datei": pfad.name, "zeilen": len(quellzeilen),
                "schnitt bei": beste + 1 if beste is not None else "—",
                "hälften": ("%d / %d" % (beste, len(quellzeilen) - beste)
                            if beste is not None else "—"),
                "abhängigkeit": (karte.richtung(beste)
                                 if beste is not None else "—"),
                "bewertung": ("schneidbar" if beste is not None
                              else "kein zirkelfreier Punkt"),
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

    def _beste(self, quellzeilen, karte):
        """Die mittigste Trennlinie, an der beide Hälften passen — oder None.

        Die Zirkelfrage kommt aus `karte` und kostet hier eine Feldabfrage.
        Bis zum 29.08.2026 rechnete jede Trennlinie sie neu; am eigenen
        Anlassfall (602 Zeilen, 521 Trennlinien) waren das 186,9 s statt
        0,006 s — bei gleicher Antwort, nachgerechnet über 896 Trennlinien
        in 425 echten Dateien."""
        anzahl = len(quellzeilen)
        mitte = anzahl / 2
        gute = [b for b, z in enumerate(quellzeilen)
                if self.RAND < b < anzahl - self.RAND
                and b <= self.GRENZE and anzahl - b <= self.GRENZE
                and re.match(r"^(?:export )?(?:async )?(?:function|class) \w+", z)
                and not karte.zirkel(b)]
        return min(gute, key=lambda b: abs(b - mitte)) if gute else None
