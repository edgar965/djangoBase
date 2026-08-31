# -*- coding: utf-8 -*-
u"""Pruefdatei — ist diese Datei eine Pruefung?

WOZU (31.08.2026)
=================
Mehrere Werkzeuge muessen Pruefungen anders behandeln als Anwendungscode,
und jedes hatte begonnen, sich das selbst zu beantworten:

* ``systemablage`` nimmt selbstraeumende Wegwerf-Ordner in Pruefungen aus.
* ``leserzahl`` darf einen Prueffall NICHT als zweiten Leser zaehlen —
  sonst macht ein guter Test aus einem lokalen Zwischenergebnis einen
  „Datentyp mit zwei Lesern".

DER ANREIZ, DER DABEI ENTSTEHT, IST DAS EIGENTLICHE ARGUMENT: Wer einem
Werkzeug erlaubt, Pruefungen mitzuzaehlen, belohnt weniger Tests. Genau
das ist am 31.08.2026 passiert — ein neuer Prueffall zu
``_pipelines_verfuegbar`` liess das Woerterbuch von „ein Leser" auf „zwei
Leser" springen und erzeugte einen Befund, der ohne den Test nicht da
waere.

WORAN ERKANNT
=============
Am Dateinamen (``test_…``) oder am Ordner (``tests``/``test`` im Pfad).
Zwei Fassungen derselben Frage laufen auseinander; deshalb steht sie hier.
"""
from pathlib import Path

from .pfadteile import Pfadteile

__all__ = ["Pruefdatei"]


class Pruefdatei:
    u"""Beantwortet fuer einen Pfad: Pruefung oder Anwendungscode?"""

    #: Ordnernamen, unter denen Pruefungen liegen.
    ORDNER = ("tests", "test")

    #: Namensanfang einer Pruefdatei.
    ANFANG = "test_"

    @classmethod
    def ist_es(cls, pfad, wurzel=None):
        u"""Liegt die Datei in einer Pruefung?

        @param pfad   Pfad oder Zeichenkette
        @param wurzel Projektwurzel dieses Laufs; ohne sie gilt der ganze Pfad
        @returns {bool}

        GEGEN DIE TEILE UNTERHALB DER WURZEL (Befund CodeRabbit, 31.08.2026):
        Vorher wurde der ABSOLUTE Pfad geprueft. Liegt ein Projekt unter
        ``/tmp/tests/meinprojekt``, gilt damit JEDE Anwendungsdatei als
        Pruefung — ``systemablage`` unterdrueckt dann alle Befunde ausser
        ``mkdtemp``/``mkstemp``, und das Werkzeug meldet ein sauberes Projekt.
        Dieselbe Fehlerklasse wie in ``pfadteile.py``, nur an einer Stelle,
        die dort noch nicht mitgezogen war.
        """
        p = Path(pfad)
        if p.name.startswith(cls.ANFANG):
            return True
        return any(teil in cls.ORDNER for teil in Pfadteile.unter(p, wurzel))
