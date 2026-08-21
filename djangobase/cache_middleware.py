# -*- coding: utf-8 -*-
u"""Keine gecachten Seiten — und trotzdem gecachte Statik.

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „lege einen testcase an um das caching zu überprüfen - damit ich nicht
     gecachte versionen von seiten sehe!"

Ein Test allein meldet nur. Damit er in jedem Projekt grün werden KANN, liefert
djangoBase die Header gleich mit — wie bei der Testaufzeichnung über eine
Middleware, die sich selbst einträgt.

ZWEI GEGENLÄUFIGE ANFORDERUNGEN
===============================
Sie werden gern verwechselt, und dann ist eine von beiden kaputt:

    HTML-Seiten     dürfen NIE aus dem Cache kommen. Wer nach einem Deploy die
                    Seite von gestern sieht, sucht den Fehler im Code.
    Statik (JS/CSS) SOLL aus dem Cache kommen — sonst lädt jede Seite alles neu.
                    Dass eine geänderte Datei trotzdem ankommt, besorgt die
                    ``?v=``-Kennung: Neue Fassung, neue URL, neuer Eintrag.

Eine Middleware, die pauschal ``no-store`` auf alles setzt, macht die zweite
Hälfte kaputt — dann lädt der Browser bei jedem Seitenaufruf sämtliche Module
neu. Genau das tut die ``NoCacheMiddleware``, die in ShortLongX steht (Kommentar
dort: „during development"). Diese hier unterscheidet.

WAS GESETZT WIRD
================
    text/html                 Cache-Control: no-store, no-cache, must-revalidate
                              Pragma: no-cache        (für alte Zwischenspeicher)
                              Expires: 0
    Statik MIT ?v=            Cache-Control: public, max-age=31536000, immutable
    Statik OHNE ?v=           unangetastet — dort wäre langes Cachen gefährlich
    alles andere              unangetastet

AUSNAHMEN
=========
``DJANGOBASE_CACHE_HEADER = False`` schaltet die Middleware ab. Wer eine Seite
bewusst cachen lässt (öffentliche Landingpage), nimmt ihren Pfad über
``DJANGOBASE_CACHE_ERLAUBT`` aus.
"""
from django.conf import settings

#: Ein Jahr — die übliche Angabe für unveränderliche, versionierte Dateien.
EIN_JAHR = 60 * 60 * 24 * 365

SEITE = "no-store, no-cache, must-revalidate, max-age=0"
STATIK = "public, max-age=%d, immutable" % EIN_JAHR


class CacheHeaderMiddleware:
    u"""Setzt die Cache-Header — je nach Art der Antwort verschieden."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        antwort = self.get_response(request)
        try:
            self._setzen(request, antwort)
        except Exception:                                   # noqa: BLE001
            # Header sind Beiwerk; eine Ausnahme hier darf keine Seite kosten.
            pass
        return antwort

    # ----------------------------------------------------------------- intern
    @staticmethod
    def _erlaubt(pfad):
        for teil in getattr(settings, "DJANGOBASE_CACHE_ERLAUBT", ()) or ():
            if pfad.startswith(teil):
                return True
        return False

    def _setzen(self, request, antwort):
        if not getattr(settings, "DJANGOBASE_CACHE_HEADER", True):
            return
        pfad = request.path or ""
        if self._erlaubt(pfad):
            return

        typ = (antwort.get("Content-Type") or "").lower()
        statik = getattr(settings, "STATIC_URL", "/static/") or "/static/"

        if pfad.startswith(statik):
            # NUR MIT KENNUNG (das ist der Punkt): Ohne ``?v=`` wäre ein Jahr
            # Cache eine Falle — eine geänderte Datei käme nie mehr an.
            if request.GET.get("v"):
                antwort["Cache-Control"] = STATIK
            return

        if "text/html" in typ:
            antwort["Cache-Control"] = SEITE
            antwort["Pragma"] = "no-cache"          # HTTP/1.0-Zwischenspeicher
            antwort["Expires"] = "0"
