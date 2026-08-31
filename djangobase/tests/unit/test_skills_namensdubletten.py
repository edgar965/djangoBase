# -*- coding: utf-8 -*-
u"""Namens-Dubletten — und die Namen, die das Rahmenwerk vorschreibt.

DER ANLASS (30.08.2026, assistant)
==================================
Der Spitzenbefund der Liste lautete „Klasse ``Command`` existiert 56x".
``Command`` ist Djangos PFLICHTNAME: ``BaseCommand`` sucht in einem
Modul unter ``management/commands/`` genau diesen Namen. Wer dem Befund
folgt und umbenennt, nimmt dem Projekt seine Verwaltungskommandos.

Das ist dieselbe Klasse Fehlalarm, wegen der ``Meta`` und ``Migration``
schon in ``ERLAUBT`` standen — ``Command`` fehlte. Nachgetragen, und
damit es nicht wieder herausfaellt, steht es hier geprueft.

WAS HIER GEPRUEFT WIRD
======================
1. Ein Pflichtname des Rahmenwerks in zwei Dateien ist KEIN Befund.
2. Ein gewoehnlicher Name in zwei Dateien ist einer — der Prüfer ist
   also nicht einfach still geworden (die Gegenprobe).
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden

from ..base import BasisTest


class NamensdublettenTest(BasisTest):

    SLUG = 'namens-dubletten'

    #: Ein Verwaltungskommando, wie Django es verlangt.
    KOMMANDO = ('from django.core.management.base import BaseCommand\n\n\n'
                'class Command(BaseCommand):\n'
                '    def handle(self, *a, **k):\n'
                '        return None\n')

    def _lauf(self, dateien, **argumente):
        ordner = tempfile.TemporaryDirectory(prefix='dubletten_')
        self.addCleanup(ordner.cleanup)
        wurzel = Path(ordner.name)
        for name, inhalt in dateien.items():
            pfad = wurzel / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug, '%s ist nicht registriert' % self.SLUG)
        werkzeug.wurzel = lambda: wurzel
        return werkzeug.pruefen(**argumente)

    @staticmethod
    def _text(satz):
        return ' '.join(b.was + ' ' + b.warum for b in satz.befunde)

    def test_pflichtnamen_des_rahmenwerks_sind_keine_dublette(self):
        satz = self._lauf({
            'app/management/commands/eins.py': self.KOMMANDO,
            'app/management/commands/zwei.py': self.KOMMANDO,
        })
        self.assertNotIn('Command', self._text(satz))

    def test_ein_gewoehnlicher_name_wird_weiterhin_gemeldet(self):
        u"""Die Gegenprobe: Der Pruefer ist nicht einfach still geworden."""
        satz = self._lauf({
            'eins.py': 'class Auswertung:\n    pass\n',
            'zwei.py': 'class Auswertung:\n    pass\n',
        })
        self.assertIn('Auswertung', self._text(satz))
