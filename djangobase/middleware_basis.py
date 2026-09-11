# -*- coding: utf-8 -*-
u"""Eine Middleware, die BEIDE Betriebsarten kann — und warum das kein Luxus ist.

DER VORFALL (CamTrack, 11.09.2026)
==================================
    „server ist tot" / „server immer noch tot"

Der Web-Dienst nahm Verbindungen an und antwortete auf nichts mehr. Im
Stack-Abzug des laufenden Prozesses (``py-spy dump``):

    MainThread (Ereignisschleife)
        _wait_for_tstate_lock (threading.py)
        join / shutdown (concurrent.futures.thread)
        __aexit__ (asgiref/sync.py:148)          ThreadSensitiveContext
        __call__ (django/core/handlers/asgi.py:165)

    drei Arbeitsfäden
        run_until_future (asgiref/current_thread_executor.py:85)
        __call__ (asgiref/sync.py:291)           AsyncToSync
        __call__ (djangobase/cache_middleware.py:108)

Ein Ringschluss: Die Ereignisschleife wartet beim Aufräumen darauf, dass ihr
Faden-Pool leerläuft; die Fäden darin warten auf die Ereignisschleife. Aus dem
kommt der Dienst nicht mehr heraus, und ein einziger solcher Fall legt ALLE
Anfragen still — nicht nur die, die ihn ausgelöst hat.

WOHER DER RÜCKRUF KOMMT
=======================
Django baut die Middleware-Kette von innen nach aussen und passt an jeder
Stelle die Betriebsart an (``BaseHandler.adapt_method_mode``). Eine Middleware
gilt als NUR SYNCHRON, solange sie nichts anderes sagt::

    sync_capable  = True      (Vorgabe)
    async_capable = False     (Vorgabe!)

Unter ASGI ist der Handler aber asynchron. Trifft Django auf ein synchrones
Glied, wickelt es den Rest der Kette in ``async_to_sync`` — und GENAU DAS ist
der Rückruf: Die Middleware läuft in einem Arbeitsfaden, reicht die Anfrage
über die Ereignisschleife weiter und blockiert, bis die Antwort da ist.

Gemessen an CamTrack (11.09.2026), Kette von innen nach aussen:

    Ansicht (asynchron)
      -> async_to_sync   <-- Rückruf 1   CacheHeaderMiddleware (synchron)
                                         AufzeichnungMiddleware (synchron)
      -> sync_to_async                   AccountMiddleware … (beides)
      -> async_to_sync   <-- Rückruf 2   WhiteNoiseMiddleware (synchron)
      -> sync_to_async                   SecurityMiddleware (beides)

Zwei Rückrufe in einer Kette von elf Gliedern, verursacht von drei Modulen.
Sind alle Glieder beidseitig, baut Django die Kette durchgehend asynchron und
es gibt KEINEN einzigen Wechsel mehr. Synchrone Ansichten laufen weiterhin im
Faden-Pool — aber der Weg geht nur in eine Richtung, und ein Ring kann sich
nicht schliessen.

WAS DIESE KLASSE ABNIMMT
========================
Den immer gleichen Rahmen aus der Django-Anleitung: die zwei Zusagen, die
Erkennung der Betriebsart, ``markcoroutinefunction`` und die zweite Einstiegs-
methode ``__acall__``. Die Unterklasse schreibt nur noch, was sie tun will:

    vorbereiten(request)              vor der Weitergabe
    nachbereiten(request, antwort)    nach der Antwort

DIE DATENBANK-FALLE
===================
Im asynchronen Betrieb läuft beides AUF DER EREIGNISSCHLEIFE. Wer dort die
Datenbank anfasst — auch nur mittelbar über ``request.user`` —, bekommt
``SynchronousOnlyOperation``, und der ``except``-Block darunter verschluckt es.
Aus der Statistik wären damit still Nullen geworden.

Deshalb ``braucht_faden = True``: Dann gehen beide Haken durch
``sync_to_async``. Das ist derselbe Weg, den Django für synchrone Ansichten
nimmt, und er führt NICHT zurück in die Schleife.

WAS DIE UNTERKLASSE NICHT TUN DARF
==================================
Aus ``vorbereiten`` oder ``nachbereiten`` heraus ``async_to_sync`` aufrufen.
Das baut den Ring von Hand wieder auf, den diese Klasse gerade abschafft.

``djangobase/tests/konform/test_middleware_beidseitig.py`` hält jede Middleware
der eingestellten Kette gegen diese Zusage — auch die fremden.
"""
from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async


class ZweiwegMiddleware:
    u"""Middleware, die synchron UND asynchron laufen kann.

    Unterklassen überschreiben ``vorbereiten`` und/oder ``nachbereiten``.
    Beide geben nichts zurück; die Antwort wird an Ort und Stelle geändert.
    """

    #: Die zwei Zusagen an Django. Ohne die zweite wickelt es den Rest der
    #: Kette in ``async_to_sync`` — siehe Modulkopf.
    sync_capable = True
    async_capable = True

    #: Fasst einer der Haken die Datenbank an (auch über ``request.user``)?
    #: Dann laufen sie im Arbeitsfaden statt auf der Ereignisschleife.
    braucht_faden = False

    #: Fehler in den Haken verschlucken? Für Beiwerk (Kopfzeilen, Statistik,
    #: Einbettungen) ja — eine kaputte Zutat darf keine Seite kosten. Wer
    #: etwas Tragendes tut, setzt das auf False.
    fehler_schlucken = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.async_modus = iscoroutinefunction(get_response)
        if self.async_modus:
            # Ohne diese Zeile hält Django die Instanz für synchron — der
            # `__call__` unten gäbe dann eine Koroutine zurück, die niemand
            # erwartet, und die Antwort wäre ein Coroutine-Objekt.
            markcoroutinefunction(self)

    # ------------------------------------------------------------ Einstiege
    def __call__(self, request):
        if self.async_modus:
            return self.__acall__(request)
        self._schuetzen(self.vorbereiten, request)
        antwort = self.get_response(request)
        self._schuetzen(self.nachbereiten, request, antwort)
        return antwort

    async def __acall__(self, request):
        await self._schuetzen_async(self.vorbereiten, request)
        antwort = await self.get_response(request)
        await self._schuetzen_async(self.nachbereiten, request, antwort)
        return antwort

    # ---------------------------------------------------------------- Haken
    def vorbereiten(self, request):
        u"""Vor der Weitergabe. Vorgabe: nichts."""

    def nachbereiten(self, request, antwort):
        u"""Nach der Antwort, an Ort und Stelle. Vorgabe: nichts."""

    # --------------------------------------------------------------- intern
    def _schuetzen(self, haken, *args):
        if not self.fehler_schlucken:
            return haken(*args)
        try:
            return haken(*args)
        except Exception:                                   # noqa: BLE001
            return None

    async def _schuetzen_async(self, haken, *args):
        if self.braucht_faden:
            # `thread_sensitive=True` ist Absicht: derselbe Faden wie für
            # synchrone Ansichten, also dieselbe Datenbank-Verbindung und
            # dieselbe Transaktion.
            return await sync_to_async(self._schuetzen,
                                       thread_sensitive=True)(haken, *args)
        return self._schuetzen(haken, *args)
