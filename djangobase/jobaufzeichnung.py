# -*- coding: utf-8 -*-
u"""Jeden Lauf eines Management-Commands mitschreiben.

Angelegt am 26.08.2026. Die Uebersicht soll zeigen, "welcher Job wann
zuletzt lief, wie lange er brauchte und ob er Fehler warf" - dazu muss
jemand mitschreiben.

WARUM EIN EINGRIFF IN ``BaseCommand.execute``
=============================================
Django kennt kein Signal fuer "ein Befehl lief". Die Alternativen waeren:

1. Jeden Befehl anfassen (assistant: 93 Dateien, sechs Projekte). Wer
   einen vergisst, sieht ihn nie in der Uebersicht - und merkt nichts.
2. Eine gemeinsame Basisklasse vorschreiben. Aendert jeden Befehl und
   bricht die, die schon von einer eigenen Basis erben.
3. Hier: ``execute`` einmal umschliessen. Wirkt fuer alle Befehle
   sofort, auch fuer die, die es noch nicht gibt.

``execute`` ist der richtige Punkt und nicht ``handle``: Django ruft
``execute`` fuer JEDEN Befehl, auch wenn der Befehl ``handle``
ueberschreibt oder eine eigene Basisklasse hat.

WAS DIESER EINGRIFF NIEMALS TUN DARF
====================================
Einen Befehl scheitern lassen. Er misst nur. Jeder Fehler beim
Aufzeichnen wird protokolliert und verschluckt; die Ausnahme des Befehls
selbst wird unveraendert weitergereicht, nachdem sie notiert wurde.

ABSCHALTEN
==========
``DJANGOBASE_JOBAUFZEICHNUNG = False`` in der ``settings.py``.
"""
import logging
import time

logger = logging.getLogger(__name__)

__all__ = ['Jobaufzeichnung']


class Jobaufzeichnung(object):
    u"""Legt sich um ``BaseCommand.execute`` und schreibt in den Verlauf."""

    #: Merker am Original, damit ein zweiter Aufruf nichts doppelt legt.
    MERKER = '_djangobase_aufgezeichnet'

    @classmethod
    def einschalten(cls):
        u"""``True``, wenn die Aufzeichnung jetzt (oder schon) haengt."""
        from django.conf import settings

        if not getattr(settings, 'DJANGOBASE_JOBAUFZEICHNUNG', True):
            return False
        try:
            from django.core.management.base import BaseCommand
        except Exception:
            logger.exception('Jobaufzeichnung: BaseCommand nicht importierbar')
            return False

        if getattr(BaseCommand.execute, cls.MERKER, False):
            return True
        BaseCommand.execute = cls._umhuellen(BaseCommand.execute)
        return True

    @classmethod
    def _umhuellen(cls, original):
        from functools import wraps

        @wraps(original)
        def gemessen(befehl, *args, **kwargs):
            kennung = cls._kennung(befehl)
            if not kennung:
                return original(befehl, *args, **kwargs)

            begonnen = time.monotonic()
            try:
                ergebnis = original(befehl, *args, **kwargs)
            except BaseException as fehler:
                # Auch Abbruch per Strg+C gehoert in den Verlauf - sonst
                # steht der Lauf fuer immer als "laeuft noch" da.
                cls._notieren(kennung, time.monotonic() - begonnen, False,
                              '%s: %s' % (type(fehler).__name__, fehler))
                raise
            cls._notieren(kennung, time.monotonic() - begonnen, True, '')
            return ergebnis

        setattr(gemessen, cls.MERKER, True)
        return gemessen

    # ------------------------------------------------------------ Innerei
    @staticmethod
    def _kennung(befehl):
        u"""Der Befehlsname, oder ``''`` wenn dieser Lauf nicht zaehlt.

        Der Name steht nicht am Objekt - Django leitet ihn aus dem Modul
        ab (``mail.management.commands.mail_sync`` -> ``mail_sync``).
        """
        modul = getattr(type(befehl), '__module__', '') or ''
        name = modul.rsplit('.', 1)[-1]
        if not name or name.startswith('_'):
            return ''
        try:
            from .joberkennung import Joberkennung

            # DIESELBE Regel wie beim Ermitteln - sonst laufen die
            # beiden auseinander (Befund 26.08.2026, gleich beim ersten
            # Aufruf der Seite sichtbar): Die Aufzeichnung notierte
            # `aktuell` und `createcachetable`, die Erkennung kennt sie
            # nicht, und die Uebersicht meldete beide als "Nicht mehr im
            # Bestand — geloescht oder umbenannt?". Beides falsch: Der
            # eine gehoert djangoBase, der andere Django.
            #
            # Die App steht im Modulpfad davor:
            #   djangobase.management.commands.aktuell -> djangobase
            app = modul.split('.management.commands.')[0]
            if not Joberkennung().ist_job(name, app):
                return ''
        except Exception:
            logger.debug('Jobaufzeichnung._kennung: Ausschluss ungeprueft',
                         exc_info=True)
        return name

    @staticmethod
    def _notieren(kennung, dauer_s, erfolg, fehler):
        try:
            from .jobverlauf import Jobverlauf

            Jobverlauf().notieren(kennung, dauer_s, erfolg, fehler)
        except Exception:
            logger.exception('Jobaufzeichnung._notieren: Exception gefangen')
