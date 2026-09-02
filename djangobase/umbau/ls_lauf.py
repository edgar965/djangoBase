# -*- coding: utf-8 -*-
u"""Der Lauf im Hintergrund — einer je Prozess, mit Zustand zum Abfragen.

WARUM NICHT IM REQUEST (Edgar, 02.09.2026: „Hintergrund thread")
==================================================================
Ein Lauf über rund 700 Dateien dauert einen halben bis ganzen Minute. Ein
Request, der so lange rechnet, hält seinen Thread, und der Watchdog des
Wirtsprojekts (TCP-Probe, 2 s) hält einen stillstehenden Server für tot und
startet ihn neu — der Lauf wäre weg, samt der Seite, die auf ihn wartet.

Deshalb: EIN Thread ``ls-lauf``, der Zustand liegt hier, die Seite fragt ihn
über ``languageserver/status/`` ab und lädt sich neu, wenn er ``fertig`` sagt.
Das Ergebnis geht über ``danach`` in die Ablage — dieser Baustein kennt keinen
Speicher und kein Django.
"""
import logging
import threading
import time

logger = logging.getLogger("djangobase.languageserver")

__all__ = ["LsLauf", "LAUF"]


class LsLauf:
    u"""Zustand und Steuerung des einen Hintergrund-Laufs."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self.status = "wartet"            # wartet | laeuft | fertig | fehler
        self.begonnen = None
        self.beendet = None
        self.werkzeug = ""
        self.fehler = ""
        self.befunde = None
        self.abdruck = ""

    def laeuft(self):
        return self._thread is not None and self._thread.is_alive()

    def starten(self, server, danach):
        u"""``True``, wenn gestartet; ``False``, wenn schon einer läuft.

        ``server`` ist ein ``LanguageServer`` (hat ``laufen()``), ``danach``
        bekommt das ``LsErgebnis`` und legt es ab."""
        with self._lock:
            if self.laeuft():
                return False
            self.status, self.fehler, self.befunde = "laeuft", "", None
            self.begonnen, self.beendet = time.time(), None
            self.werkzeug = server.konfig.werkzeug
            self.abdruck = server.konfig.abdruck()
            self._thread = threading.Thread(target=self._arbeit, args=(server, danach),
                                            name="ls-lauf", daemon=True)
            self._thread.start()
            return True

    def _arbeit(self, server, danach):
        try:
            ergebnis = server.laufen()
            self.werkzeug = ergebnis.werkzeug or self.werkzeug
            if ergebnis.fehlt:
                self.status, self.fehler = "fehler", ergebnis.fehlt
            else:
                self.status = "fertig"
            self.befunde = len(ergebnis.befunde)
            danach(ergebnis)
            logger.info("Language Server %s: %d Befunde in %.1f s%s", ergebnis.werkzeug,
                        len(ergebnis.befunde), ergebnis.dauer_s,
                        u" — " + ergebnis.fehlt if ergebnis.fehlt else "")
        except Exception as e:                            # noqa: BLE001
            logger.exception("Language-Server-Lauf gescheitert")
            self.status, self.fehler = "fehler", u"%s: %s" % (type(e).__name__, e)
        finally:
            self.beendet = time.time()

    def zustand(self):
        jetzt = time.time()
        return {
            "status": self.status if not self.laeuft() else "laeuft",
            "werkzeug": self.werkzeug,
            "sekunden": round((self.beendet or jetzt) - self.begonnen, 1) if self.begonnen else 0,
            "fehler": self.fehler,
            "befunde": self.befunde,
            "abdruck": self.abdruck,
        }


#: DER Lauf des Prozesses.
LAUF = LsLauf()
