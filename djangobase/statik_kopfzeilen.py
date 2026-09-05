# -*- coding: utf-8 -*-
u"""Cache-Kopfzeilen fuer die Statik — auch im Entwicklungsbetrieb.

WARUM DAS NICHT DIE MIDDLEWARE TUT (05.09.2026)
===============================================
``CacheHeaderMiddleware`` setzt die richtigen Kopfzeilen, sieht die Statik
aber nie: ``runserver`` haengt den ``StaticFilesHandler`` VOR die
Middleware-Kette, ein Treffer unter ``STATIC_URL`` wird dort beantwortet.
Gemessen am laufenden Server:

    GET /static/viewer/viewer/skinning.js    -> nur Last-Modified
    GET /humanbody/scene-model/              -> Cache-Control: no-store, …

Diese Schicht sitzt als ASGI-Huelle **um** den Statik-Handler und kommt
deshalb an jede Antwort heran.

WAS OHNE SIE PASSIERT — DER FALL VOM 05.09.2026
===============================================
Ohne ``Cache-Control`` schaetzt der Browser die Frische selbst: 10 % des
Dateialters. Eine drei Wochen alte Datei gilt zwei Tage als frisch und wird
ausgeliefert, OHNE zu fragen. Im Serverlog sieht man das daran, dass die
Datei gar nicht mehr angefragt wird:

    15:09:26 GET /humanbody/scene-model/            200
    15:09:27 GET /static/viewer/viewer/websocket.js 304
    15:09:28 GET /static/viewer/gemeinsam/netznachricht.js 304
    (kein Eintrag fuer skinning.js — aus dem Zwischenspeicher)

Die Viewer-Module sind ES-Module ohne Kennung in den Import-Adressen. Eine
frische Einstiegsdatei neben einem alten Geschwistermodul heisst im besten
Fall „die neue Funktion fehlt" und im schlechtesten

    SyntaxError: The requested module './skinning.js' does not provide an
    export named 'skelettNachfuehren'

— und damit eine leere Seite bei HTTP 200.

``no-cache`` heisst NICHT „nicht speichern", sondern „vor jeder Benutzung
nachfragen". Die Datei bleibt liegen; stimmt sie noch, kostet sie ein 304
ohne Rumpf. Versionierte Statik (``?v=``) bleibt ein Jahr gueltig.

EINHAENGEN
==========
In ``ui/asgi.py``, als aeusserste Schicht::

    from djangobase.statik_kopfzeilen import StatikKopfzeilen
    application = StatikKopfzeilen(ASGIStaticFilesHandler(...))

``DJANGOBASE_CACHE_HEADER = False`` schaltet sie mit der Middleware zusammen
ab.
"""
from django.conf import settings

from .cache_middleware import NACHFRAGEN, STATIK

__all__ = ['StatikKopfzeilen']


class StatikKopfzeilen:
    u"""ASGI-Huelle, die den Statik-Antworten ihre Cache-Kopfzeile gibt."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        u"""``scope``/``receive``/``send`` heissen hier NICHT deutsch.

        Daphne ruft die Anwendung mit Schluesselwoertern auf
        (``self.application(scope=…, receive=…, send=…)``, ``server.py``).
        Mit eigenen Namen endet jede einzelne Anfrage in

            TypeError: StatikKopfzeilen.__call__() got an unexpected
            keyword argument 'receive'

        — HTTP 500 auf der ganzen Seite. Das sind Vertragsnamen, keine
        frei gewaehlten (05.09.2026, so passiert).
        """
        if scope.get('type') != 'http' or not self._zustaendig(scope):
            await self.app(scope, receive, send)
            return

        kopfzeile = self._kopfzeile(scope)

        async def gesetzt(nachricht):
            if nachricht.get('type') == 'http.response.start':
                nachricht = dict(nachricht)
                nachricht['headers'] = self._ergaenzt(
                    nachricht.get('headers') or [], kopfzeile)
            await send(nachricht)

        await self.app(scope, receive, gesetzt)

    # ----------------------------------------------------------------- intern

    @staticmethod
    def _zustaendig(scope):
        if not getattr(settings, 'DJANGOBASE_CACHE_HEADER', True):
            return False
        statik = getattr(settings, 'STATIC_URL', '/static/') or '/static/'
        return (scope.get('path') or '').startswith(statik)

    @staticmethod
    def _kopfzeile(scope):
        u"""Mit ``?v=`` ein Jahr, ohne Kennung nachfragen.

        Die Abfrage kommt als Bytes; ein ``v`` ohne Wert (``?v=``) zaehlt
        nicht — sonst waere eine leere Kennung ein Jahr Cache.
        """
        roh = (scope.get('query_string') or b'').decode('latin-1')
        for teil in roh.split('&'):
            name, _, wert = teil.partition('=')
            if name == 'v' and wert:
                return STATIK
        return NACHFRAGEN

    @staticmethod
    def _ergaenzt(kopfzeilen, wert):
        u"""``Cache-Control`` setzen und ein vorhandenes ersetzen.

        Nicht bloss anhaengen: Zwei ``Cache-Control``-Zeilen werden vom
        Browser zusammengefasst, und aus ``no-cache`` plus ``max-age=…``
        wird dann etwas, das niemand gemeint hat.
        """
        behalten = [(k, w) for k, w in kopfzeilen
                    if k.lower() != b'cache-control']
        behalten.append((b'cache-control', wert.encode('latin-1')))
        return behalten
