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
import threading
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
            cpu_vorher = cls._cpu()
            argumente = cls._argumente(kwargs)
            # Eigener Prozess (Aufgabenplaner, Konsole) oder ``call_command``
            # aus einem Thread des Servers? Die Jobs-Seite zeigt unter
            # „Nacht-Aufgabe" nur die eigenstaendigen Laeufe.
            eigenstaendig = threading.current_thread() is threading.main_thread()
            try:
                ergebnis = original(befehl, *args, **kwargs)
            except BaseException as fehler:
                # Auch Abbruch per Strg+C gehoert in den Verlauf - sonst
                # steht der Lauf fuer immer als "laeuft noch" da.
                cls._notieren(kennung, time.monotonic() - begonnen, False,
                              '%s: %s' % (type(fehler).__name__, fehler),
                              cls._cpu() - cpu_vorher, argumente, eigenstaendig)
                raise
            cls._notieren(kennung, time.monotonic() - begonnen, True, '',
                          cls._cpu() - cpu_vorher, argumente, eigenstaendig)
            return ergebnis

        setattr(gemessen, cls.MERKER, True)
        return gemessen

    # ------------------------------------------------------------ Innerei
    @staticmethod
    def _cpu():
        u"""Verbrauchte CPU-Sekunden - des Prozesses oder nur dieses Threads.

        CPU NEBEN DER DAUER (02.09.2026, shortlongx: „evaluiere, was mich
        diese Jobs an CPU Performance kosten"). Die Wanduhr-Dauer sagt
        nicht, ob ein Job rechnet oder wartet: ``ib_assets_laden`` braucht
        17 Minuten und schlaeft davon 16, der stock3-Import brauchte 15
        Minuten und rechnete jede davon.

        Laeuft der Befehl als EIGENER Prozess (Hauptthread), zaehlt der
        ganze Prozess - samt seiner Hilfsthreads. Laeuft er IM Server
        (``call_command`` aus einem Runner-Thread), zaehlt nur dieser
        Thread - sonst stuenden die anderen Runner mit auf der Rechnung.
        """
        if threading.current_thread() is threading.main_thread():
            return time.process_time()
        return time.thread_time()

    #: Optionen, die jeder Django-Befehl traegt - sie sagen nichts ueber den
    #: Lauf und bleiben deshalb draussen.
    STANDARD_OPTIONEN = frozenset((
        'verbosity', 'settings', 'pythonpath', 'traceback', 'no_color',
        'force_color', 'skip_checks', 'stdout', 'stderr'))

    @classmethod
    def _argumente(cls, optionen):
        u"""Die Optionen, die diesen Lauf von einem anderen unterscheiden.

        ``duka_history --reihe ESTX50`` und ``duka_history`` ohne Reihe sind
        zwei verschiedene Jobs derselben Kennung; ``ib_history_fdax`` laeuft
        mit 30-Sekunden- und mit 1-Sekunden-Bars. Ohne die Argumente koennte
        die Jobs-Seite ihre Zeilen nicht dem richtigen Lauf zuordnen.
        Nur gesetzte Werte, kurz gehalten - der Verlauf ist eine Zeile je
        Lauf, kein Protokoll."""
        raus = {}
        try:
            for name, wert in (optionen or {}).items():
                if name in cls.STANDARD_OPTIONEN or wert in (None, False, '', [], ()):
                    continue
                raus[name] = str(wert)[:40]
        except Exception:
            logger.debug('Jobaufzeichnung._argumente: uebersprungen', exc_info=True)
        return raus

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
    def _notieren(kennung, dauer_s, erfolg, fehler, cpu_s=None, argumente=None,
                  eigenstaendig=True):
        try:
            from .jobverlauf import Jobverlauf

            Jobverlauf().notieren(kennung, dauer_s, erfolg, fehler,
                                  cpu_s=cpu_s, argumente=argumente,
                                  eigenstaendig=eigenstaendig)
        except Exception:
            logger.exception('Jobaufzeichnung._notieren: Exception gefangen')
