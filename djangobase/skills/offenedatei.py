# -*- coding: utf-8 -*-
u"""Offene Datei — ``open()`` ohne ``with`` und ohne ``close()``.

DAS MUSTER
==========
::

    lf = open(log_file, 'w')
    subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    # kein close(), kein with

Der Subprozess erbt den Deskriptor und schreibt weiter — die Ausgabe
landet also da, wo sie soll. Der aufrufende Prozess behaelt seinen aber
AUCH, bis die Speicherbereinigung ihn einsammelt. Jeder Start laesst
einen offenen Deskriptor zurueck; in einem langlebigen Serverprozess
sammeln sie sich.

Dass die Ausgabe stimmt, macht den Fehler unsichtbar: Es gibt nichts zu
sehen, bis das Betriebssystem keine Handles mehr vergibt.

WARUM NICHT EINFACH ``with``
============================
``with open(...) as f: Popen(..., stdout=f)`` schliesst die Datei beim
Verlassen des Blocks — das ist hier RICHTIG, weil der Subprozess seine
eigene Kopie hat. Wer es nicht glaubt, schreibt ``try/finally``. Beides
zaehlt fuer dieses Werkzeug als behoben.

DER BEFUND (assistant, 28./29.08.2026)
======================================
FUENF Stellen, alle nach demselben Schnittmuster — Audio-Laeufe,
ACE-Step-Dienst, ACE-Step-Worker, MIDI-Auftrag, Musik-Auftrag. Vier
davon waren Abschriften voneinander. Die fuenfte
(``indexer_job/prozessstart``) macht es richtig und war die Vorlage fuer
die Reparatur.

WAS GEMELDET WIRD
=================
Ein ``open(...)``, dessen Ergebnis an einen Namen geht, wenn in
DERSELBEN Funktion kein ``close()`` auf diesen Namen vorkommt.

WAS NICHT GEMELDET WIRD
=======================
* ``with open(...)`` — der Block schliesst selbst.
* Ein ``close()`` irgendwo in derselben Funktion (auch im ``finally``).
* Ein ``return`` des Namens: Dann gehoert die Datei dem Aufrufer, und
  ob DER sie schliesst, kann diese Pruefung nicht wissen.
* Tests.
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["OffeneDatei"]


class OffeneDatei(BefundWerkzeug):
    u"""``open()`` ohne ``with`` und ohne ``close()``."""

    slug = "offene-datei"
    titel = "Datei geoeffnet, nie geschlossen"
    zweck = ("Findet `f = open(...)` ohne `with` und ohne `close()` in "
             "derselben Funktion.")
    befund = ("Fuenfmal in assistant gefunden, viermal als Abschrift "
              "voneinander: Logdatei auf, an `Popen` weitergegeben, nie zu. "
              "Die Ausgabe stimmt trotzdem — deshalb faellt es nicht auf.")
    abhilfe = ("`with open(...) as f:` — oder `try/finally` mit `close()`. "
               "Der Subprozess hat seine eigene Kopie und schreibt weiter.")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"starter.py": (
            "import subprocess\n"
            "\n"
            "\n"
            "def starten(befehl, pfad):\n"
            "    protokoll = open(pfad, 'w')\n"
            "    subprocess.Popen(befehl, stdout=protokoll)\n"),
         "sauber.py": (
            "import subprocess\n"
            "\n"
            "\n"
            "def starten(befehl, pfad):\n"
            "    protokoll = open(pfad, 'w')\n"
            "    try:\n"
            "        subprocess.Popen(befehl, stdout=protokoll)\n"
            "    finally:\n"
            "        protokoll.close()\n"
            "\n"
            "\n"
            "def mit_block(befehl, pfad):\n"
            "    with open(pfad, 'w') as protokoll:\n"
            "        subprocess.Popen(befehl, stdout=protokoll)\n"
            "\n"
            "\n"
            "def gehoert_dem_aufrufer(pfad):\n"
            "    datei = open(pfad, 'w')\n"
            "    return datei\n")},
        mindestens=1, hoechstens=1, erwartet_in="starter.py",
        warum="Der Deskriptor bleibt im Serverprozess liegen, einer je "
              "Start. `sauber.py` haelt die drei Ausnahmen fest: "
              "`try/finally`, `with`, und die Datei, die dem Aufrufer "
              "gehoert — ohne sie meldete das Werkzeug jede Fabrikmethode.")

    #: Diese Datei beschreibt den Fehler, statt ihn zu machen.
    AUSNAHMEN = ("offenedatei.py",)

    def pruefen(self, **_argumente):
        befunde = []
        dateien = 0
        for pfad in self.projektdateien(".py"):
            if pfad.name in self.AUSNAHMEN or self._ist_test(pfad):
                continue
            baum = self._baum(pfad)
            if baum is None:
                continue
            dateien += 1
            befunde += self._aus_baum(baum, self.kurz(pfad))
        kopf = ["%d Python-Dateien gelesen" % dateien,
                "%d offene Dateien" % len(befunde)]
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _ist_test(pfad):
        return (pfad.name.startswith("test_")
                or "tests" in pfad.parts
                or "test" in pfad.parts)

    @staticmethod
    def _baum(pfad):
        try:
            return ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            return None

    def _aus_baum(self, baum, name):
        raus = []
        traeger = (ast.FunctionDef, ast.AsyncFunctionDef)
        for knoten in ast.walk(baum):
            if not isinstance(knoten, traeger):
                continue
            raus += self._aus_funktion(knoten, name)
        return raus

    def _aus_funktion(self, funktion, name):
        u"""Die Namen, die in dieser Funktion eine Datei bekommen."""
        geschlossen = self._geschlossene(funktion)
        zurueck = self._zurueckgegebene(funktion)
        raus = []
        for knoten in ast.walk(funktion):
            if not isinstance(knoten, ast.Assign):
                continue
            if not self._ist_open(knoten.value):
                continue
            for ziel in knoten.targets:
                if not isinstance(ziel, ast.Name):
                    continue
                if ziel.id in geschlossen or ziel.id in zurueck:
                    continue
                raus.append(Befund(
                    "%s:%d" % (name, knoten.lineno),
                    "`%s = open(...)` ohne `close()`" % ziel.id,
                    "Der Deskriptor bleibt im Prozess liegen — einer je "
                    "Aufruf. Die Ausgabe stimmt trotzdem, deshalb faellt "
                    "es nicht auf.",
                    Befund.WARNUNG))
        return raus

    @staticmethod
    def _ist_open(knoten):
        return (isinstance(knoten, ast.Call)
                and isinstance(knoten.func, ast.Name)
                and knoten.func.id == "open")

    @staticmethod
    def _geschlossene(funktion):
        u"""Namen, auf denen irgendwo ``close()`` gerufen wird."""
        namen = set()
        for knoten in ast.walk(funktion):
            if (isinstance(knoten, ast.Call)
                    and isinstance(knoten.func, ast.Attribute)
                    and knoten.func.attr == "close"
                    and isinstance(knoten.func.value, ast.Name)):
                namen.add(knoten.func.value.id)
            # Auch die Uebergabe an einen Helfer zaehlt: `self._zu(datei)`
            elif isinstance(knoten, ast.Call):
                for arg in knoten.args:
                    if (isinstance(arg, ast.Name)
                            and isinstance(knoten.func, ast.Attribute)
                            and "schliess" in knoten.func.attr.lower()):
                        namen.add(arg.id)
        return namen

    @staticmethod
    def _zurueckgegebene(funktion):
        u"""Namen, die zurueckgegeben werden — dann gehoert die Datei
        dem Aufrufer, und ob DER sie schliesst, ist hier nicht zu
        sehen."""
        namen = set()
        for knoten in ast.walk(funktion):
            if isinstance(knoten, ast.Return) and isinstance(knoten.value,
                                                             ast.Name):
                namen.add(knoten.value.id)
        return namen
