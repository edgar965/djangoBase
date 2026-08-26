# -*- coding: utf-8 -*-
u"""Mitschrift - Laufzeiten aus einem FREMDEN Testlauf in dieselbe Historie.

:class:`~.testlauf.Testlauf` faehrt ein Kommando, wartet und schreibt die
Laufzeiten. Projekte haben aber eigene Runner: der assistant streamt seine
Testlaeufe zeilenweise ins Browserfenster (``/tests/<bereich>/<art>/``), damit
man beim Zuschauen sieht, wo es haengt. Dieser Runner soll die Zahlen in
DIESELBE Historie schreiben — sonst haette dieselbe Seite zwei Wahrheiten:
Laufzeiten unter Hilfe → Tests, keine unter /tests/.

    mit = Mitschrift()
    cmd = mit.option_setzen(cmd)          # --durations 0, wenn der Interpreter kann
    …                                     # Lauf des Projekts, Zeilen sammeln
    reihen = mit.aufnehmen("\\n".join(zeilen))
    # {test_id: [{"zeit","dauer"}, …]} - direkt zum Fortschreiben der Tabelle

Warum nicht je Testcase ein POST an ``/hilfe/tests/dauer/``: Bei 250 Faellen
waeren das 250 Anfragen fuer einen Lauf. Der Server hat die Ausgabe ohnehin in
der Hand — er liest sie einmal.
"""
import time

from .testdauern import Dauern
from .testhistorie import Testhistorie

__all__ = ["Mitschrift"]


class Mitschrift:
    """Nimmt die Ausgabe eines Testlaufs und trägt die Laufzeiten ein."""

    def __init__(self, historie=None):
        self.historie = historie or Testhistorie()

    @staticmethod
    def option_setzen(cmd):
        u"""``--durations 0`` ergänzen, wo der Interpreter es kann."""
        return Dauern.option_setzen(cmd)

    def aufnehmen(self, ausgabe, suite=None, zeit=None):
        u"""Laufzeiten eintragen und die betroffenen Reihen zurueckgeben.

        Leere Rueckgabe heisst: Der Lauf hatte keinen ``--durations``-Block
        (alter Interpreter, Abbruch vor dem Ende). Das ist kein Fehler und wird
        nicht geschrieben — eine erfundene Null waere schlimmer als eine Luecke.
        """
        dauern = Dauern.lesen(ausgabe or "")
        if not dauern and not suite:
            return {}
        self.historie.merken(zeit or time.strftime("%d.%m.%Y %H:%M:%S"),
                             dauern, suite)
        return {tid: self.historie.laeufe(tid) for tid in dauern}
