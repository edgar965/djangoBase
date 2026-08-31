# -*- coding: utf-8 -*-
u"""Pfadteile — gegen welche Namen eine Ausschlussliste wirklich gilt.

DER BEFUND (31.08.2026)
=======================
Vier Stellen im Werkzeugkasten prueften die Ausschlussliste gegen
``pfad.parts`` — also gegen den ABSOLUTEN Pfad. Die Liste beschreibt aber
Verzeichnisse INNERHALB des Projekts (``node_modules``, ``migrations``,
``_wegwerf``, ``vendor``). Oberhalb der Wurzel ist derselbe Name kein
Argument: Wer sein Projekt unter ``…/node_modules/meinprojekt`` liegen hat,
findet damit keine einzige Datei mehr — und das Werkzeug sagt „keine
Befunde", was wie ein sauberes Projekt aussieht.

AUFGEFALLEN IST ES AN DEN PRUEFLAEUFEN. Seit die ``Ablageumleitung`` die
Wegwerfordner ins Projekt holt (``_wegwerf/system/…``), stand dieser Name
im absoluten Pfad JEDER Attrappe. Rund vierzig Prueffaelle meldeten „keine
Befunde" — einzeln gefahren war jeder gruen, weil sein Ordner dann noch im
System-Zwischenspeicher lag.

WARUM EIGENES MODUL
===================
Weil es VIER Aufrufer sind (``werkzeug.pfade``, zweimal
``frontendquellen._ueberspringen``, ``befund.projektdateien``). Vier
Fassungen derselben Regel laufen auseinander; genau das ist an der
Ausschlussliste schon einmal passiert (siehe ``befund.py``: eigene Suche,
eigene Liste, 183 Befunde aus ``vendor/``).
"""
from pathlib import Path

__all__ = ["Pfadteile"]


class Pfadteile:
    u"""Die Namen eines Pfades, gegen die eine Ausschlussliste gilt."""

    @staticmethod
    def unter(pfad, wurzel):
        u"""Die Teile UNTERHALB der Wurzel — sonst der ganze Pfad.

        @param pfad   die gefundene Datei
        @param wurzel die Projektwurzel dieses Laufs
        @returns {tuple} die Namen, gegen die geprueft werden darf

        Liegt der Pfad ausserhalb der Wurzel, gilt er ganz: Dann hat der
        Aufrufer ihn absichtlich von woanders geholt, und die Liste ist die
        einzige Handhabe, die bleibt.
        """
        try:
            return Path(pfad).relative_to(wurzel).parts
        except (ValueError, TypeError):
            return Path(pfad).parts

    @classmethod
    def trifft(cls, pfad, wurzel, namen):
        u"""Steht einer der `namen` unterhalb der Wurzel im Pfad?

        @param namen Menge der ausgeschlossenen Verzeichnisnamen
        """
        if not namen:
            return False
        return any(teil in namen for teil in cls.unter(pfad, wurzel))
