# -*- coding: utf-8 -*-
u"""Cachekonzept als Befund-Werkzeug — Hilfe -> Skills und Hilfe -> Review.

Prueft dasselbe wie die Konformitaetspruefung ``tests/konform/test_cachekonzept.py``,
nur als Befundliste mit Ort und Grund: Vorlagen (Modul-Einstieg ueber
``{% static %}?t=``, Zeitstempel an Statik), JavaScript (Kennung in
Import-Adressen) und die Einstellungen (Middleware, Fassungspfad, ASGI-Huelle).
Die Regeln selbst stehen in ``djangobase/cachekonzept.py`` und auf
Hilfe -> Cache (06.09.2026).
"""
from ..cachekonzept import Cachekonzept as Regeln
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Cachekonzept"]


class Cachekonzept(BefundWerkzeug):
    """Haelt das Projekt das Cache-Konzept ein — auch bei ES-Modulen?"""

    slug = "cachekonzept"
    titel = "Cache-Konzept: Seiten, Statik und ES-Module"
    zweck = ("HTML nie aus dem Zwischenspeicher, Statik mit Fassung, ES-Module "
             "ueber den Fassungspfad, keine Kennung in Import-Adressen, keine "
             "pauschale NoCache-Middleware, Fassungspfad und StatikKopfzeilen "
             "eingehaengt. Erklaert auf Hilfe -> Cache.")
    befund = ("Ein Modul-Einstieg mit `{% static %}?t=` laesst die Geschwister-"
              "module aus dem Zwischenspeicher kommen: `SyntaxError: does not "
              "provide an export named …`, leere Seite bei HTTP 200 "
              "(3DTools, 05.09.2026).")

    def pruefen(self, **_argumente):
        befunde = []
        vorlagen = 0
        for pfad in self.projektdateien(".html"):
            vorlagen += 1
            befunde.extend(self._befunde(Regeln.vorlage(self.kurz(pfad), self._text(pfad))))
        skripte = 0
        for pfad in self.projektdateien(".js"):
            skripte += 1
            befunde.extend(self._befunde(Regeln.skript(self.kurz(pfad), self._text(pfad))))
        befunde.extend(self._befunde(Regeln.einstellungen()))
        kopf = u"%d Vorlagen und %d Skripte geprueft, dazu Middleware, urls.py und asgi.py" % (vorlagen, skripte)
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _text(pfad):
        try:
            return pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _befunde(roh):
        raus = []
        for b in roh:
            regel = Regeln.regel(b["regel"])
            raus.append(Befund(b["ort"], u"%s — %s" % (regel.titel if regel else b["regel"], b["was"]),
                               (regel.wie if regel else ""), Befund.WARNUNG))
        return raus
