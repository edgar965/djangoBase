# -*- coding: utf-8 -*-
u"""WhiteNoise, das auch asynchron kann.

WARUM DIESE DATEI ÜBERHAUPT EXISTIERT
=====================================
``whitenoise.middleware.WhiteNoiseMiddleware`` (6.12.0, geprüft am 11.09.2026)
sagt Django nicht, dass sie asynchron laufen kann::

    sync_capable  = True      (Vorgabe)
    async_capable = False     (Vorgabe)

Unter ASGI wickelt Django deshalb den gesamten Rest der Kette in
``async_to_sync`` — ein Rückruf aus einem Arbeitsfaden in die Ereignisschleife.
Am 11.09.2026 hat genau diese Bauart den CamTrack-Web-Dienst stillgelegt; die
Begründung mit dem Stack-Abzug steht in ``middleware_basis.py``.

Das Paket selbst kennt keine asynchrone Fassung: Es ist, wie seine eigene
Beschreibung sagt, „static file serving for WSGI applications".

WAS DIESE KLASSE ÄNDERT — UND WAS NICHT
=======================================
Geändert wird ausschliesslich der Weg, NICHT das Verhalten: Dieselbe Suche,
dieselbe Auslieferung, dieselben Kopfzeilen. Nur wird die Kette nicht mehr
nach synchron umgebogen.

Die Dateisuche und das Öffnen laufen im Faden-Pool
(``thread_sensitive=False``) statt auf der Ereignisschleife. Absicht: Das ist
reine Datei-Arbeit ohne Datenbank, sie braucht weder dieselbe Verbindung noch
dieselbe Transaktion wie eine Ansicht — und der eigene Pool kann nicht mit dem
empfindlichen Pool um Fäden streiten.

WANN SIE IM ERNSTFALL ETWAS AUSLIEFERT: SELTEN
==============================================
Steht ein Dateiserver davor (CamTrack: nginx auf 8000, ``location /static/``),
kommt unter ``/static/`` nie eine Anfrage hier an. Diese Middleware ist dann
der Rückfall für den Fall, dass der Anwendungsserver einmal allein läuft —
und bis zum 11.09.2026 war sie in genau dieser Rolle der zweite Ringschluss
in der Kette, ohne je eine Datei geliefert zu haben.

EINBAU
======
In ``MIDDLEWARE`` statt des Originals::

    "djangobase.statik_middleware.ZweiwegWhiteNoise",

Fehlt das Paket ``whitenoise``, ist der Import ein klarer ``ImportError`` beim
Start — kein stiller Rückfall. Wer die Middleware einträgt, will sie.
"""
from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from whitenoise.middleware import WhiteNoiseMiddleware


class ZweiwegWhiteNoise(WhiteNoiseMiddleware):
    u"""WhiteNoise mit den zwei Zusagen, die Django braucht."""

    sync_capable = True
    async_capable = True

    def __init__(self, get_response=None, *args, **kwargs):
        super().__init__(get_response, *args, **kwargs)
        self.async_modus = iscoroutinefunction(get_response)
        if self.async_modus:
            markcoroutinefunction(self)

    def __call__(self, request):
        if self.async_modus:
            return self.__acall__(request)
        return super().__call__(request)

    async def __acall__(self, request):
        datei = await sync_to_async(self._suchen,
                                    thread_sensitive=False)(request)
        if datei is not None:
            return await sync_to_async(self.serve,
                                       thread_sensitive=False)(datei, request)
        return await self.get_response(request)

    # --------------------------------------------------------------- intern
    def _suchen(self, request):
        u"""Die Suche aus ``WhiteNoiseMiddleware.__call__``, unverändert.

        Bewusst hier herausgezogen und nicht nachgebaut: Ändert das Paket
        eines Tages seine Logik, fällt der Unterschied hier auf — ein
        nachgebauter Zweig würde still veralten.
        """
        if self.autorefresh:
            return self.find_file(request.path_info)
        return self.files.get(request.path_info)
