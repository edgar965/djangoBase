# -*- coding: utf-8 -*-
u"""EigenesWerkzeug - Werkzeug2 mit den Ausschluessen, die jedes Projekt braucht.

WARUM DIESE ERGAENZUNG (belegt beim ersten Lauf, 17.08.2026)
============================================================
``Werkzeug2.ausgeschlossen`` kennt venv, Migrationen und Sicherungsordner - nicht
aber die Ablagen, die in gewachsenen Projekten danebenliegen: mitgelieferter
Fremdcode (``vendor``), Modellgewichte (``models``), Arbeitsreste (``tmp``),
uebersetzte Zwischenstaende (``unsloth_compiled_cache``).

Ohne sie meldete das Protokoll-Werkzeug beim ersten Lauf **3.017 Stellen**, die
allermeisten aus Fremdcode. Das ist die teuerste Sorte Fehlalarm: Sie verdeckt
die echten Befunde, statt nur danebenzuliegen.

Ergaenzbar bleibt es je Projekt ueber ``DJANGOBASE["skills2_ignorieren"]`` - die
Liste hier ist nur die Grundausstattung.
"""
from ..skills2.werkzeug import Werkzeug2

__all__ = ["EigenesWerkzeug", "ZUSATZ_RAUS"]

#: Ablagen, die kein eigener Quelltext sind - ueber Werkzeug2 hinaus.
ZUSATZ_RAUS = {"vendor", "models", "tmp", "temp", "unsloth_compiled_cache",
               "media", "logs", "output", "Output", "Datenbank", "fixtures",
               ".claude", "docs", "htmlcov", ".idea", ".vscode"}


class EigenesWerkzeug(Werkzeug2):
    """Basis der Skills1-eigenen Werkzeuge."""

    def ausgeschlossen(self):
        return super().ausgeschlossen() | ZUSATZ_RAUS
