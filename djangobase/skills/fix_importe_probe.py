# -*- coding: utf-8 -*-
u"""Gegenprobe zum Import-Fixer: schneidet er noch, und schneidet er zu viel?

WARUM ES DIESE PROBE GIBT (25.08.2026)
======================================
Der Fixer hat im Projekt assistant die Anwendung startunfaehig gemacht.
In ``mail/sync/MailboxSyncer/kern.py`` stand::

    from .basis import SyncFolderResult

- im Modul selbst nirgends benutzt, nach allen damaligen Regeln tot.
Daneben lag aber::

    # mail/sync/MailboxSyncer/__init__.py
    from .kern import MailboxSyncer, SyncFolderResult  # noqa: F401

Nach dem Schnitt: ``ImportError: cannot import name 'SyncFolderResult'
from 'mail.sync.MailboxSyncer.kern'``.

KEINE der vier damaligen Sicherungen greift dort:

* ``__init__.py`` ist geschuetzt - aber die Datei, aus der es holt, war
  es nicht.
* Das ``# noqa`` steht in der ANDEREN Datei.
* ``__all__`` fuehrt den Namen nicht.
* Das Netz (``pruefen``) sieht nichts: die geschnittene Datei
  kompiliert weiter tadellos. Ein gebrochener Re-Export faellt erst
  beim IMPORT von aussen auf.

Ein Modul kann also ein Durchgangstor sein, ohne ``__init__.py`` zu
heissen. Die fuenfte Sicherung ``_wird_weitergereicht`` schliesst das;
diese Probe haelt sie fest.

WARUM ALS PROBE UND NICHT NUR ALS KOMMENTAR
===========================================
Eine Verschaerfung ohne Gegenprobe ist keine Verbesserung, sondern eine
Vermutung. Und eine, die man nur zu schnell wieder zurueckdreht, weil
sie ein paar Befunde weniger meldet. Hier steht daneben, was WEITERHIN
geschnitten werden muss - sonst waere die einfachste Art, diese Probe
gruen zu bekommen, den Fixer ganz abzuschalten.
"""
import ast
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

__all__ = ["FixImporteProbe"]

#: Der Vorfall: ``kern`` reicht ``SyncFolderResult`` an ``__init__`` weiter.
WEITERGEREICHT = {
    'kern.py': (
        'from __future__ import annotations\n'
        'from .basis import SyncFolderResult\n'
        '\n'
        'class MailboxSyncer:\n'
        '    pass\n'
    ),
    '__init__.py': (
        'from .kern import MailboxSyncer, SyncFolderResult  # noqa: F401\n'
    ),
    'basis.py': (
        'class SyncFolderResult:\n'
        '    pass\n'
    ),
}

#: Dasselbe Bild OHNE Weiterreichung - hier MUSS geschnitten werden.
WIRKLICH_TOT = {
    'kern.py': (
        'from __future__ import annotations\n'
        'from .basis import SyncFolderResult\n'
        '\n'
        'class MailboxSyncer:\n'
        '    pass\n'
    ),
    '__init__.py': (
        'from .kern import MailboxSyncer  # noqa: F401\n'
    ),
    'basis.py': (
        'class SyncFolderResult:\n'
        '    pass\n'
    ),
}


class FixImporteProbe(SimpleTestCase):
    u"""Der Fixer laesst Durchgangstore stehen - und schneidet sonst weiter."""

    def _vorschlag(self, dateien):
        u"""``{Datei: entfernte Zeilen}`` fuer ein gebautes Paket."""
        from .fix_importe import ImportFixer

        with tempfile.TemporaryDirectory() as ordner:
            paket = Path(ordner) / 'paket'
            paket.mkdir()
            for name, inhalt in dateien.items():
                (paket / name).write_text(inhalt, encoding='utf-8')

            fixer = ImportFixer()
            fixer.pfade = lambda muster='*.py': list(paket.rglob('*.py'))
            fixer._geholt = None
            raus = {}
            for aenderung in fixer.vorschau().aenderungen:
                alt = aenderung.pfad.read_text(encoding='utf-8').splitlines()
                neu = aenderung.neuer_text.splitlines()
                raus[aenderung.pfad.name] = [z for z in alt if z not in neu]
            return raus

    def test_weitergereichter_name_bleibt(self):
        u"""Der Vorfall vom 25.08.2026 - darf nie wieder geschnitten werden."""
        vorschlag = self._vorschlag(WEITERGEREICHT)
        geschnitten = vorschlag.get('kern.py', [])
        self.assertNotIn(
            'from .basis import SyncFolderResult', geschnitten,
            "Der Fixer will einen Namen entfernen, den __init__.py aus "
            "genau dieser Datei holt. Nach dem Schnitt ist die Anwendung "
            "nicht mehr startbar - und das Netz merkt es nicht, weil die "
            "Datei weiter kompiliert. Siehe _wird_weitergereicht.")

    def test_wirklich_toter_import_faellt_weiter(self):
        u"""Gegenrichtung: die Sicherung darf den Fixer nicht abschalten."""
        vorschlag = self._vorschlag(WIRKLICH_TOT)
        geschnitten = vorschlag.get('kern.py', [])
        self.assertIn(
            'from .basis import SyncFolderResult', geschnitten,
            "Hier holt NIEMAND den Namen aus kern.py - er ist wirklich "
            "tot und muss fallen. Faellt er nicht, ist die fuenfte "
            "Sicherung zu grob und der Fixer tut nichts mehr.")
