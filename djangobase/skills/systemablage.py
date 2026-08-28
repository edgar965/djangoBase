# -*- coding: utf-8 -*-
u"""Systemablage — Zwischendateien, die auf der Systemplatte landen.

DIE VORGESCHICHTE
=================
``tempfile.mkstemp()``, ``NamedTemporaryFile()`` und
``TemporaryDirectory()`` schreiben OHNE ``dir=`` in den
System-Zwischenspeicher — unter Windows nach
``C:\\Users\\…\\AppData\\Local\\Temp``. Aus dieser Gewohnheit sind in
einem Projekt rund **100 GB Datenmuell auf C:** entstanden.

Seither lautet die Hausregel: Zwischendateien liegen im
Projektverzeichnis, auf derselben Platte wie die Daten, die sie
begleiten.

WARUM DAS AUFRAEUMEN NICHT REICHT
=================================
Fast jede solche Stelle raeumt im ``finally`` auf — solange der Prozess
lebt. Ein abgebrochener Lauf, ein harter Neustart, ein Absturz: dann
bleibt die Kopie liegen. Und es sind selten kleine Dateien; gefunden
wurden (assistant, 29.08.2026):

    jeder Mail-Anhang, einmal vollstaendig
    zwei Kopien je PDF-Variante beim Verkleinern
    jedes Mitglied eines Archiv-Anhangs
    ein WAV je Aufnahme beim Entrauschen und Diarisieren

WAS GEMELDET WIRD
=================
Ein Aufruf von ``mkstemp``, ``mkdtemp``, ``NamedTemporaryFile``,
``TemporaryFile``, ``SpooledTemporaryFile`` oder ``TemporaryDirectory``
OHNE ``dir=``-Angabe.

WAS NICHT GEMELDET WIRD
=======================
* **Tests.** Ein Wegwerf-Verzeichnis in einer Pruefung verschwindet mit
  ihr, und es geht um Beispieldaten, nicht um Nutzdaten.
* ``dir=`` vorhanden — egal, was drinsteht. Wohin genau, entscheidet
  das Projekt.
* Kommentare und Docstrings (der Syntaxbaum kennt sie nicht als Aufruf).
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Systemablage"]


class Systemablage(BefundWerkzeug):
    u"""Zwischendateien ohne ``dir=`` — sie landen auf der Systemplatte."""

    slug = "systemablage"
    titel = "Zwischendateien im System-Zwischenspeicher"
    zweck = ("Findet `tempfile.mkstemp()` und Verwandte ohne `dir=`. Sie "
             "schreiben unter Windows nach C:, nicht neben die Daten.")
    befund = ("Aus dieser Gewohnheit sind in einem Projekt rund 100 GB "
              "Datenmuell auf C: entstanden. Aufgeraeumt wird meist im "
              "`finally` — das hilft nur, solange der Prozess lebt.")
    abhilfe = ("`dir=` auf einen Ordner im Projekt setzen (etwa "
               "`BASE_DIR/tmp`, in `.gitignore`).")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"kopierer.py": (
            "import tempfile\n"
            "\n"
            "\n"
            "def kopieren(daten):\n"
            "    griff, pfad = tempfile.mkstemp(suffix='.pdf')\n"
            "    return pfad\n"),
         "sauber.py": (
            "import tempfile\n"
            "from django.conf import settings\n"
            "\n"
            "\n"
            "def kopieren(daten):\n"
            "    griff, pfad = tempfile.mkstemp(suffix='.pdf',\n"
            "                                   dir=settings.BASE_DIR)\n"
            "    return pfad\n")},
        mindestens=1, hoechstens=1, erwartet_in="kopierer.py",
        warum="Ohne `dir=` liegt die Kopie auf C:. `sauber.py` steht "
              "daneben, damit die Ausnahme (dir= vorhanden) nicht "
              "unbemerkt wegfaellt — sonst meldete das Werkzeug jede "
              "Zwischendatei, auch die richtig abgelegten.")

    #: Die Aufrufe, die einen Ort waehlen.
    ANLEGER = ("mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile",
               "SpooledTemporaryFile", "TemporaryDirectory")

    #: Diese Datei beschreibt den Fehler, statt ihn zu machen.
    AUSNAHMEN = ("systemablage.py",)

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
                "%d Zwischendateien ohne `dir=`" % len(befunde)]
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _ist_test(pfad):
        u"""Ein Wegwerf-Verzeichnis in einer Pruefung verschwindet mit ihr."""
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
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call):
                continue
            gerufen = self._name(knoten.func)
            if gerufen not in self.ANLEGER:
                continue
            if any(k.arg == "dir" for k in knoten.keywords):
                continue
            raus.append(Befund(
                "%s:%d" % (name, knoten.lineno),
                "`%s(...)` ohne `dir=`" % gerufen,
                "Die Datei landet im System-Zwischenspeicher, unter "
                "Windows auf C:. Aufgeraeumt wird meist im `finally` — "
                "das hilft nur, solange der Prozess lebt.",
                Befund.WARNUNG))
        return raus

    @staticmethod
    def _name(knoten):
        u"""Der gerufene Name — ``mkstemp`` wie ``tempfile.mkstemp``."""
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        if isinstance(knoten, ast.Name):
            return knoten.id
        return ""
