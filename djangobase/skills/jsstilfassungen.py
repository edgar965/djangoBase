# -*- coding: utf-8 -*-
u"""JsStilfassungen - welche Inline-Stile lohnen eine CSS-Klasse?

DER BEFUND (3DTools, 16.08.2026)
================================
1.266 statische `style="…"` in den Vorlagen — aber nur 485 verschiedene
Fassungen. Eine davon stand 78-mal da, eine weitere 61-mal. Das ist der
Unterschied zwischen „viele Inline-Stile" (Meinung) und „78-mal dieselbe Zeile"
(Arbeitsauftrag).

Diese Prüfung gruppiert nach Fassung statt nach Vorkommen. Damit sieht man in
einer Zeile, was sich zusammenfassen lässt — und `djangobase.umbau.stilklassen`
macht daraus Klassen.

WAS SIE NICHT MELDET: Werte mit `{{ }}`, `{% %}` oder `${ }`. Die stehen erst
zur Laufzeit fest und können keine Klasse werden.

ACHTUNG BEIM UMSTELLEN: Eine CSS-Klasse (0,0,1,0) hat eine niedrigere
Spezifitaet als ein Inline-Stil. Zwei Regressionen sind auf genau diesem Weg
entstanden — Abschnittstitel verloren ihre Akzentfarbe, Farbfelder ihre Größe.
Deshalb schreibt das Umbau-Werkzeug den Klassennamen dreifach in den Selektor
und die Änderung wird im Browser gegengemessen
(`static/djangobase/js/stilmessung.js`).
"""
import re
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["JsStilfassungen"]

STIL = re.compile(r'style\s*=\s*"([^"]*)"')

#: Ein Blockkommentar — sein Inhalt ist Prosa, kein Markup.
KOMMENTAR = re.compile(r'/\*.*?\*/|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}'
                       r'|\{#.*?#\}|<!--.*?-->', re.S)


def kommentarfrei(text):
    """Derselbe Text ohne Blockkommentare."""
    return KOMMENTAR.sub(' ', text)
#: Werte mit diesen Zeichen stehen erst zur Laufzeit fest.
DYNAMISCH = ("{{", "{%", "${", '" +', "' +")


class JsStilfassungen(Werkzeug):
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
        #: Stellen in Blockkommentaren. Sie beschreiben den ALTEN Zustand und
        #: sind kein Inline-Stil (30.08.2026): Drei der letzten Meldungen in
        #: 3DTools standen in Aufraeum-Notizen — „dieselbe
        #: `style="width:100%;padding:4px;…"`-Kette teils". Wer so einen
        #: Befund behebt, loescht die Begruendung.
        kommentiert = 0
        for pfad, kurz in self._quellen():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            ohne_kommentar = kommentarfrei(text)
            for wert in STIL.findall(text):
                if wert not in ohne_kommentar:
                    kommentiert += 1
                    continue
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
                    "eigene Klasse. %d Stellen in Kommentaren uebergangen."
                    % kommentiert)

    #: Ausschlussliste und Suche stehen seit dem 17.08.2026 in
    #: ``Frontendquellen`` — vorher hatte sie jedes JS-Werkzeug einzeln,
    #: in vier verschiedenen Fassungen.
    def _quellen(self):
        return self.frontendquellen().paare(".html", ".js")
