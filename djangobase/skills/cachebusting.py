# -*- coding: utf-8 -*-
u"""Cachebusting — jede Skript- und Stilzeile traegt eine Fassungsangabe.

DER FEHLER
==========
Ein ``<script src>`` ohne Fassungsangabe faellt niemandem auf: Die Seite laedt,
sie fuehrt nur eine ALTE Fassung aus. Sichtbar wird das als „die Aenderung
kommt nicht an" — und die naheliegende Antwort darauf ist „druecke mal
Strg+Shift+R". Damit ist der Fehler beim Entwickler weg und beim Benutzer noch
da. Beim naechsten Entwickler faengt es von vorn an.

DIE HAUSREGEL VON djangoBase
============================
``_shell.html`` haengt an jede eigene Stildatei
``?v={% firstof JS_VERSION STATIC_V djangobase.statik_v %}``. Das Werkzeug
prueft, ob die Vorlagen des PROJEKTS es genauso halten. In 3DTools steht die
Regel woertlich in ``CLAUDE.md``:

    KEIN Browser-Cache — ALLE Seiten! Zusaetzlich `?t={% now "U" %}` an ALLE
    JS/CSS/API-URLs in ALLEN Templates. Niemals „Ctrl+Shift+R" als Loesung
    vorschlagen — stattdessen IMMER Cache-Busting im Code sicherstellen.

WAS ALS FASSUNGSANGABE ZAEHLT
=============================
``?t=…`` (Zeitstempel) und ``?v=…`` (Versionsnummer) — beide Schreibweisen sind
in Gebrauch, ``?t={% now 'U' %}`` in den Vorlagen und ``?v=N`` in ES-Importen.

WAS NICHT GEMELDET WIRD
=======================
* **Fremde Adressen** (``https://cdn…``): Die liefern eine feste Fassung unter
  einer festen Adresse; ein Anhaengsel wuerde dort nur den Zwischenspeicher des
  Auslieferungsnetzes umgehen.
* **Importkarten** (``<script type="importmap">``): Sie enthalten keine
  Adresse, die der Browser sofort laedt — die Ziele darin werden einzeln
  geprueft.
* **``<link>`` ohne ``rel="stylesheet"``**: ``icon``, ``manifest``,
  ``preconnect`` laden nichts nach, was sich aendert. Der Favicon SOLL
  zwischengespeichert werden — sonst holt der Browser ihn bei jedem
  Seitenwechsel neu.
"""
import re

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Cachebusting"]


class Cachebusting(BefundWerkzeug):
    """Laedt der Browser wirklich die neue Fassung?"""

    slug = "cachebusting"
    titel = "Cache-Busting: Skript- und Stilzeilen ohne Fassungsangabe"
    zweck = ("Jede `<script src>`- und `<link rel=stylesheet>`-Zeile in den "
             "Vorlagen traegt `?t=` oder `?v=`. Ohne das fuehrt der Browser "
             "eine alte Fassung aus, ohne dass irgendwo ein Fehler steht.")
    befund = ("Projektregel in 3DTools seit dem ersten Tag: „Niemals "
              "Ctrl+Shift+R als Loesung vorschlagen.“ Wer eine Zeile ohne "
              "Fassungsangabe stehen laesst, erzeugt genau die Frage, auf die "
              "diese Antwort folgt.")
    abhilfe = ("`?t={% now \"U\" %}` an die Adresse haengen — bei ES-Importen "
               "`?v=N` und N erhoehen.")
    dauer = "unter 1 s"
    kriterium = 16

    anlassfall = Anlassfall(
        {"templates/alt.html": (
            '<script src="/static/app/x.js"></script>\n'
            '<link rel="stylesheet" href="/static/app/y.css">\n'),
         "templates/neu.html": (
            '<script src="/static/app/x.js?v=3"></script>\n'
            '<link rel="stylesheet" href="/static/app/y.css?t=1">\n'
            '<script src="https://cdn.example/lib.js"></script>\n'
            '<link rel="icon" href="/static/img/f.svg">\n')},
        mindestens=2, hoechstens=2, erwartet_in="alt.html",
        warum="Eine Seite ohne Fassungsangabe laedt und fuehrt eine ALTE "
              "Fassung aus — ohne Fehler. `neu.html` steht daneben, weil die "
              "drei Ausnahmen (Fassung vorhanden, fremde Adresse, Favicon) "
              "sonst unbemerkt wegfallen koennten.")

    #: Adressen, die keine Fassungsangabe brauchen.
    FREMD = ("http://", "https://", "//", "data:", "#")
    #: Was als Fassungsangabe gilt.
    FASSUNG = re.compile(r"\?(?:t|v)=")
    #: ``<script src="…">`` und ``<link … href="…">``, auch ueber Zeilenumbrueche.
    SKRIPT = re.compile(r"<script\b[^>]*?\bsrc\s*=\s*\"([^\"]+)\"", re.I | re.S)
    LINK = re.compile(r"<link\b[^>]*?\bhref\s*=\s*\"([^\"]+)\"", re.I | re.S)
    #: Importkarten werden gelesen, nicht geladen.
    IMPORTKARTE = re.compile(r"type\s*=\s*\"importmap\"", re.I)
    #: Nur ein Stylesheet laedt etwas nach, das sich aendern kann.
    NUR_STIL = re.compile(r"rel\s*=\s*\"stylesheet\"", re.I)

    def pruefen(self, **_argumente):
        befunde = []
        geprueft = 0
        for pfad in self.projektdateien(".html"):
            if "templates" not in pfad.parts:
                continue
            geprueft += 1
            text = pfad.read_text(encoding="utf-8", errors="replace")
            befunde += self._aus_datei(self.kurz(pfad), text)
        kopf = ["%d Vorlagen gelesen" % geprueft,
                "%d Zeilen ohne Fassungsangabe" % len(befunde)]
        return Befundsatz(self.titel, kopf, befunde)

    def _aus_datei(self, name, text):
        raus = []
        for treffer in self.SKRIPT.finditer(text):
            if self.IMPORTKARTE.search(treffer.group(0)):
                continue
            raus += self._pruefen_adresse(name, text, treffer, "script src")
        for treffer in self.LINK.finditer(text):
            if not self.NUR_STIL.search(treffer.group(0)):
                continue
            raus += self._pruefen_adresse(name, text, treffer, "link href")
        return raus

    def _pruefen_adresse(self, name, text, treffer, art):
        adresse = treffer.group(1).strip()
        if adresse.startswith(self.FREMD) or self.FASSUNG.search(adresse):
            return []
        zeile = text.count("\n", 0, treffer.start()) + 1
        return [Befund(
            "%s:%d" % (name, zeile),
            "%s ohne `?t=`/`?v=`: %s" % (art, adresse[:70]),
            "Der Browser darf die Datei aus seinem Zwischenspeicher nehmen. "
            "Die Seite laedt trotzdem — sie fuehrt nur eine alte Fassung aus.",
            Befund.WARNUNG)]
