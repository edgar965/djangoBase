# -*- coding: utf-8 -*-
u"""Werkzeug fuer die Job-Pruefungen: Attrappen und ein eigener Ordner.

Angelegt am 26.08.2026 zusammen mit der Jobs-Uebersicht.

WARUM EINE ATTRAPPE STATT DER ECHTEN ERKENNUNG
==============================================
``Joberkennung.ermitteln()`` importiert jede Befehlsklasse des Projekts.
In einer Pruefung waere das dreierlei zugleich falsch: langsam (in
assistant 93 Importe), unvorhersehbar (der Bestand aendert sich mit jedem
neuen Befehl - die Pruefung wuerde von allein rot) und ungenau, denn
geprueft werden soll das MERKEN, nicht das Finden.

Die Attrappe zaehlt ihre Aufrufe. Damit laesst sich die eigentliche
Zusicherung ueberhaupt erst schreiben: "wird beim Lesen NICHT neu
ermittelt" ist eine Aussage ueber die Anzahl der Aufrufe.

WARUM EIN EIGENER ORDNER
========================
Die Klassen schreiben nach ``BASE_DIR/logs/``. Eine Pruefung, die dorthin
schreibt, veraendert die Ablage des laufenden Projekts - und zwei
Pruefungen nacheinander saehen die Datei der jeweils anderen. Jede
Pruefung bekommt deshalb ihren eigenen Ordner, der danach verschwindet.
"""
import shutil
import tempfile
from pathlib import Path

__all__ = ['ErkennungAttrappe', 'MitTempordner']


class ErkennungAttrappe(object):
    u"""Liefert einen festen Bestand und zaehlt, wie oft sie gefragt wurde."""

    def __init__(self, kennungen, art='befehl'):
        self.kennungen = list(kennungen)
        self.art = art
        #: Wie oft ``ermitteln`` gerufen wurde. Die Zusicherungen der
        #: Katalog-Pruefungen haengen an dieser Zahl.
        self.aufrufe = 0

    def ermitteln(self):
        self.aufrufe += 1
        return [{'kennung': k, 'name': k, 'app': 'test',
                 'art': self.art, 'hilfe': ''}
                for k in sorted(self.kennungen)]


class MitTempordner(object):
    u"""Gibt jeder Pruefung einen eigenen Ordner und raeumt ihn weg.

    Als Mixin VOR die Testklasse setzen::

        class EinBestandVonHeute(MitTempordner, SimpleTestCase):
    """

    def setUp(self):
        super().setUp()
        self.ordner = Path(tempfile.mkdtemp(prefix='djangobase_jobs_'))
        self.addCleanup(shutil.rmtree, str(self.ordner), True)

    def datei(self, name):
        u"""Ein Pfad in diesem Ordner - die Datei muss nicht existieren."""
        return self.ordner / name
