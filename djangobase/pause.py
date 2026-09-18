# -*- coding: utf-8 -*-
"""Pause — Warten als injizierbare Abhängigkeit, damit Wartezeit testbar und abbrechbar ist.

DER ANLASS (gunSlinger, 18.09.2026)
===================================
Ein Scraper hält zwischen zwei Abrufen 3–6 s und legt alle 20–40 Abrufe eine
Lesepause von 30–90 s ein. Zwei Dinge daran waren nicht in Ordnung:

1. Der Knopf „Abbrechen" wurde nur ZWISCHEN den Abrufen gesehen. Wer in einer
   58-s-Lesepause drückte, wartete 58 s — und hielt den Knopf für tot.
2. Die Pausen ließen sich nicht prüfen. Ein Test, der die Lesepause fahren
   will, wartet 90 s oder patcht ``time.sleep`` modulweit — und trifft damit
   auch das Warten, das er gar nicht meinte.

Beides löst dieselbe Bauform: Das Warten ist ein OBJEKT, das man hineinreicht.
In Produktion schläft es (``Pause()``), im Test läuft es sofort durch und
schreibt auf, was es hätte warten sollen (``Pause.sofort()``). Und weil es auf
einem ``threading.Event`` liegt, endet jede Pause augenblicklich, sobald
jemand ``abbrechen()`` ruft — auch die von 90 s. Gemessen: 0,0 s vom Klick bis
zum Ende des Laufs, vorher bis zu 90 s.

BENUTZUNG
=========
::

    class Abholer:
        def __init__(self, pause=None):
            self.pause = pause or Pause()

        def holen(self):
            for seite in self.seiten:
                if not self.pause.warten(3.0):      # False = abgebrochen
                    return
                ...

    # Produktion
    Abholer().holen()

    # Test: läuft in Millisekunden, die Wartezeiten stehen in ``gewartet``
    pause = Pause.sofort()
    Abholer(pause).holen()
    assert pause.gewartet == [3.0, 3.0, 3.0]

    # Abbruch aus einem anderen Thread (GUI-Knopf, Signal-Handler)
    pause.abbrechen()

Ein ``Pause``-Objekt darf von mehreren Stellen geteilt werden — dann bricht
EIN ``abbrechen()`` alle ab. Für einen neuen Lauf ``zuruecksetzen()``.
"""

import threading
import time


class Pause:
    """Wartet höchstens ``sekunden``; ``abbrechen()`` beendet jedes Warten sofort.

    :param schlaefer: was wirklich wartet — ``None`` = Event-Warten (abbrechbar).
        Ein eigener Schläfer (etwa ``lambda s: None``) macht das Warten
        unabbrechbar, aber er ist für Sonderfälle da; ``sofort()`` reicht meist.
    """

    def __init__(self, schlaefer=None):
        self._ereignis = threading.Event()
        self._schlaefer = schlaefer
        #: Jede angeforderte Wartezeit in Sekunden, in Reihenfolge.
        self.gewartet = []

    @classmethod
    def sofort(cls):
        """Eine Pause, die nie wartet — für Tests. ``gewartet`` zählt trotzdem mit."""
        return cls(schlaefer=lambda _sekunden: None)

    def warten(self, sekunden):
        """``True`` = Zeit ist durchgelaufen, ``False`` = abgebrochen (auch vorher schon).

        Negative oder Null-Sekunden warten nicht, prüfen aber den Abbruch.
        """
        self.gewartet.append(float(sekunden))
        if self._schlaefer is not None:
            if sekunden > 0:
                self._schlaefer(sekunden)
            return not self._ereignis.is_set()
        if sekunden <= 0:
            return not self._ereignis.is_set()
        return not self._ereignis.wait(sekunden)

    def abbrechen(self):
        """Beendet das laufende Warten und lässt jedes weitere sofort zurückkehren."""
        self._ereignis.set()

    @property
    def abgebrochen(self):
        return self._ereignis.is_set()

    def zuruecksetzen(self):
        """Für den nächsten Lauf: Abbruch aufheben, Aufzeichnung leeren."""
        self._ereignis.clear()
        self.gewartet = []

    @property
    def gesamt(self):
        """Summe aller angeforderten Wartezeiten — was der Lauf ohne ``sofort()`` gedauert hätte."""
        return sum(self.gewartet)

    @staticmethod
    def jetzt():
        """Monotone Uhr für Messungen rund um das Warten — nicht ``time.time()``, das springt."""
        return time.monotonic()
