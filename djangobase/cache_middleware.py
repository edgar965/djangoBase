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
    Statik OHNE ?v=           Cache-Control: no-cache
    alles andere              unangetastet

WARUM ``no-cache`` UND NICHT „unangetastet" (05.09.2026)
========================================================
Bis dahin blieb Statik ohne Kennung ohne jeden ``Cache-Control``-Header —
in der Annahme, dass dann ``Last-Modified`` entscheidet. Das tut es nicht:
Ohne Angabe zur Frische darf der Browser selbst schaetzen, und er schaetzt
**10 % des Alters der Datei**. Eine drei Wochen alte Datei gilt damit zwei
Tage als frisch und wird ausgeliefert, OHNE zu fragen.

Was daraus wird, zeigt der Fall vom 05.09.2026 in 3DTools. Die
Viewer-Module sind ES-Module ohne Kennung in den Import-Adressen; nur die
Einstiegsdatei traegt ``?t=``. Nach einer Aenderung, die ein Modul um einen
Export erweiterte, holte der Browser die Einstiegsdatei frisch und ein
Geschwistermodul aus seinem Zwischenspeicher. Ergebnis im Browser:

    SyntaxError: The requested module './skinning.js' does not provide an
    export named 'skelettNachfuehren'

Kein Server sieht das, kein Test sieht das — die Seite antwortet mit 200 und
zeigt nichts. Nachgestellt mit einem Playwright-Lauf, der genau EIN Modul
aus der alten Fassung ausliefert: ``window.__viewer`` war danach nicht mehr
da, das Modell weg.

``no-cache`` heisst NICHT „nicht cachen" — es heisst „vor jeder Benutzung
nachfragen". Die Datei bleibt im Zwischenspeicher, und solange sie stimmt,
kostet sie ein 304 ohne Rumpf. Das ist genau das Verhalten, das der
Kommentar oben ohnehin schon behauptet hat.

IM DEV-SERVER GREIFT DAS NICHT — und das ist wichtig zu wissen
==============================================================
``runserver`` haengt ``StaticFilesHandler`` VOR die Middleware-Kette; ein
Treffer unter ``STATIC_URL`` wird dort beantwortet und kommt hier nie an.
Gemessen am laufenden Server (05.09.2026):

    GET /static/viewer/viewer/skinning.js       -> nur Last-Modified
    GET /static/viewer/viewer/skinning.js?v=7   -> nur Last-Modified
    GET /humanbody/scene-model/                 -> Cache-Control: no-store, …

Diese Regeln gelten also fuer Auslieferungen, die durch die Middleware
laufen (WhiteNoise, Reverse Proxy mit Django dahinter), nicht fuer
``runserver``. Wer sich im Entwicklungsbetrieb darauf verlaesst, verlaesst
sich auf nichts. Dort hilft nur, den Modulbaum so zu bauen, dass ein
einzelnes altes Modul ihn nicht abreisst — also keine neuen Pflicht-Importe
zwischen bestehenden Modulen, sondern der Weg ueber eine Registrierung, die
ein fehlendes Stueck vertraegt.

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
#: Statik ohne Kennung: liegen bleiben darf sie, aber nur mit Rueckfrage.
#: Siehe den Modulkopf — ohne diese Zeile schaetzt der Browser die Frische
#: selbst und liefert Tage alte Module aus, ohne zu fragen.
NACHFRAGEN = "no-cache"


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
            antwort["Cache-Control"] = (STATIK if request.GET.get("v")
                                        else NACHFRAGEN)
            return

        if "text/html" in typ:
            antwort["Cache-Control"] = SEITE
            antwort["Pragma"] = "no-cache"          # HTTP/1.0-Zwischenspeicher
            antwort["Expires"] = "0"
