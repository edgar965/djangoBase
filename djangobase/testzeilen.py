# -*- coding: utf-8 -*-
u"""Testzeilen - den Fortschritt aus der Ausgabe von ``manage.py test`` lesen.

Fuer den Live-Lauf (:mod:`.teststrom`): Waehrend die Tests laufen, soll in jeder
Tabellenzeile stehen, was mit ihr passiert ist. Dazu muss die Ausgabe von
``unittest`` mitgelesen werden — und die ist unangenehmer, als sie aussieht.

DREI FALLEN, ALLE GEMESSEN (17.08.2026, Projekt assistant)
==========================================================
1. **Name und Ergebnis stehen nicht in einer Zeile.** ``unittest`` schreibt bei
   ``-v 2`` erst den Namen OHNE Zeilenumbruch und haengt das Ergebnis spaeter an::

       test_x (paket.modul.Klasse.test_x) ... ok

   Wer die Ausgabe zeilenweise liest (und das muss man, um live zu berichten),
   bekommt beides getrennt, sobald irgendetwas dazwischen schreibt.

2. **Zeitstempel mitten in der Zeile.** Manche Projekte stempeln jede
   stdout-Zeile (im assistant ``mail.apps.install_stdout_timestamps``). Aus
   einer Zeile werden zwei, und der Stempel steht auch in der Mitte. Ein Muster
   mit ``^`` findet dort nichts; deshalb wird der Stempel GLOBAL entfernt.

3. **Statt des Namens steht die Beschreibung da.** Hat ein Test einen Docstring,
   zeigt ``-v 2`` dessen erste Zeile::

       Zeigt die Route ins Leere? Dann ist der Endpunkt tot. ... ok

   Der erste Fall jedes Laufs blieb deshalb auf „läuft …" stehen.

Dazu die Regel, ab wann NICHT mehr gelesen wird: Im ``--durations``-Block steht
jeder Test noch einmal mit Namen, und das abschliessende „OK" haette dem letzten
davon ein zweites Ergebnis verpasst.
"""
import re

__all__ = ["Testzeilen"]


class Testzeilen:
    """Zustandsbehafteter Leser: Zeile hinein, Fortschritts-Ereignis heraus."""

    #: Zeitstempel, den Projekte ihren stdout-Zeilen voranstellen - ueberall,
    #: nicht nur am Anfang (siehe Modulkopf, Falle 2).
    STEMPEL = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[.,]?\d*\s*")
    #: ``test_x (paket.Klasse.test_x)`` - mit oder ohne folgendes Ergebnis.
    KOPF = re.compile(r"(test_\w+)\s*\(([\w.]+)\)")
    ERGEBNIS = {"ok": "pass", "OK": "pass", "FAIL": "fail", "ERROR": "error",
                "skipped": "skip", "expected failure": "pass",
                "unexpected success": "fail"}
    #: Ab hier steht die Auswertung, nicht mehr der Fortschritt.
    SCHLUSS = ("Slowest test durations", "Ran ", "FAILED (", "OK (")

    def __init__(self):
        self.offen = None      # (name, voller Pfad) - wartet auf sein Ergebnis
        self.aus = False       # Auswertungsteil erreicht

    def lesen(self, zeile):
        u"""``{"test", "id", "status"}`` - oder ``None``, wenn nichts drinsteht."""
        rein = self.STEMPEL.sub("", str(zeile or "")).strip()
        if not rein or self.aus:
            return None
        if any(rein.startswith(x) for x in self.SCHLUSS):
            self.aus = True
            self.offen = None
            return None
        kopf = self.KOPF.search(rein)
        if kopf:
            self.offen = (kopf.group(1), kopf.group(2))
            rest = rein[kopf.end():].strip(" .")
            status = self.ERGEBNIS.get(rest)
            return self._fertig(status) if status else None
        if not self.offen:
            return None
        # Ergebnis ohne Kopf: eigene Zeile („ok") oder hinter der Beschreibung
        # („… ist der Endpunkt tot. ... ok").
        rest = rein.strip(" .")
        status = self.ERGEBNIS.get(rest)
        if status:
            return self._fertig(status)
        if " ... " in rein:
            status = self.ERGEBNIS.get(rein.rsplit(" ... ", 1)[-1].strip())
            if status:
                return self._fertig(status)
        return None

    def _fertig(self, status):
        name, pfad = self.offen
        self.offen = None
        # Dictionary gewollt: geht als JSON-Zeile an die Seite.
        return {"test": "%s (%s)" % (name, pfad), "id": pfad,
                "status": status, "detail": ""}
