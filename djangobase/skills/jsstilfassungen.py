# -*- coding: utf-8 -*-
u"""JsStilfassungen - welche Inline-Stile lohnen eine CSS-Klasse?

DER BEFUND (3DTools, 16.08.2026)
================================
1.266 statische `style="…"` in den Vorlagen — aber nur 485 verschiedene
Fassungen. Eine davon stand 78-mal da, eine weitere 61-mal. Das ist der
Unterschied zwischen „viele Inline-Stile" (Meinung) und „78-mal dieselbe Zeile"
(Arbeitsauftrag).

Diese Pruefung gruppiert nach Fassung statt nach Vorkommen. Damit sieht man in
einer Zeile, was sich zusammenfassen laesst — und `djangobase.umbau.stilklassen`
macht daraus Klassen.

WAS SIE NICHT MELDET: Werte mit `{{ }}`, `{% %}` oder `${ }`. Die stehen erst
zur Laufzeit fest und koennen keine Klasse werden.

ACHTUNG BEIM UMSTELLEN: Eine CSS-Klasse (0,0,1,0) hat eine niedrigere
Spezifitaet als ein Inline-Stil. Zwei Regressionen sind auf genau diesem Weg
entstanden — Abschnittstitel verloren ihre Akzentfarbe, Farbfelder ihre Groesse.
Deshalb schreibt das Umbau-Werkzeug den Klassennamen dreifach in den Selektor
und die Aenderung wird im Browser gegengemessen
(`static/djangobase/js/stilmessung.js`).
"""
import re
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["JsStilfassungen"]

STIL = re.compile(r'style\s*=\s*"([^"]*)"')
#: Werte mit diesen Zeichen stehen erst zur Laufzeit fest.
DYNAMISCH = ("{{", "{%", "${", '" +', "' +")


class JsStilfassungen(Werkzeug2):
    slug = "jsstilfassungen"
    titel = "Inline-Stile: gleiche Fassungen"
    zweck = ("Gruppiert `style=\"…\"` nach Inhalt: Welche Fassung steht wie oft "
             "da und lohnt damit eine CSS-Klasse?")
    befund = ("3DTools: 1.266 Inline-Stile in nur 485 Fassungen — die haeufigste "
              "78-mal, die zweithaeufigste 61-mal. Nach dem Zusammenfassen "
              "blieben 494 Einzelfaelle.")
    abhilfe = ("`python -m djangobase.umbau.stilklassen <vorlage.html> "
               "--schreiben` — und danach mit stilmessung.js im Browser "
               "gegenmessen, die Spezifitaet ist die Falle.")
    dauer = "unter 1 s"
    kriterium = 15

    NICHT_IM_PFAD = ("vendor", "theatre", "theatre-studio", "dist", "bundle",
                     "node_modules", "staticfiles")
    #: So viele Fassungen kommen in die Tabelle.
    OBEN = 25

    #: Dieselbe Inline-Fassung dreimal - der Fall, in dem sich eine CSS-Klasse
    #: lohnt. Beim naechsten Farbwechsel muss man sonst alle drei finden.
    anlassfall = Anlassfall(
        {"seite.html": '''<div style="display:flex;gap:.5rem;align-items:center">eins</div>
<div style="display:flex;gap:.5rem;align-items:center">zwei</div>
<div style="display:flex;gap:.5rem;align-items:center">drei</div>
'''},
        erwartet_in="display:flex",
        warum="Kriterium 6: dieselbe Inline-Fassung mehrfach statt einer Klasse")

    def laufen(self):
        fassungen = Counter()
        dateien = Counter()
        dynamisch = 0
        for pfad, kurz in self._quellen():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for wert in STIL.findall(text):
                gestrafft = " ".join(wert.split()).strip()
                if not gestrafft.strip(";"):
                    continue
                if any(marke in gestrafft for marke in DYNAMISCH):
                    dynamisch += 1
                    continue
                fassungen[gestrafft] += 1
                dateien[kurz] += 1

        zeilen = [{"anzahl": anzahl, "fassung": fassung[:110]}
                  for fassung, anzahl in fassungen.most_common(JsStilfassungen.OBEN)]
        for datei, anzahl in dateien.most_common(8):
            zeilen.append({"anzahl": anzahl, "fassung": "» Datei: " + datei})
        mehrfach = sum(n for n in fassungen.values() if n > 1)
        return Ergebnis(
            ["anzahl", "fassung"], zeilen,
            zusammenfassung="%d statische Inline-Stile in %d Fassungen; %d davon "
                            "stehen mehrfach. %d dynamische bleiben."
                            % (sum(fassungen.values()), len(fassungen),
                               mehrfach, dynamisch),
            hinweis="Oben die haeufigsten Fassungen, darunter die Dateien mit "
                    "den meisten Stellen. Was nur einmal vorkommt, lohnt keine "
                    "eigene Klasse.")

    def _quellen(self):
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for endung in ("*.html", "*.js"):
            for pfad in sorted(wurzel.rglob(endung)):
                if any(teil in raus for teil in pfad.parts):
                    continue
                if any(teil in JsStilfassungen.NICHT_IM_PFAD for teil in pfad.parts):
                    continue
                if ".min." in pfad.name:
                    continue
                yield pfad, pfad.relative_to(wurzel).as_posix()
