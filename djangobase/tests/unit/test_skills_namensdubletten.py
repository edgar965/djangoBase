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
3. Ein PRIVATER Name in zwei Dateien ist nur dann ein Befund, wenn die
   Parameterlisten abweichen (31.08.2026, siehe unten).

DER ZWEITE ANLASS (31.08.2026, 3DTools)
=======================================
Hier stand ``knoten.name.startswith('_')`` als blindes ``continue``.
Damit blieb ``_push_outside_body`` unsichtbar, das in VIER Dateien mit
DREI verschiedenen Parameterlisten stand — derselbe sprechende Name für
drei verschiedene Rechnungen, und Aufrufer holten ihn mal aus dem einen,
mal aus dem anderen Modul.

Der Filter war nicht falsch, nur zu grob: ``_parse`` und ``_key`` heissen
überall gleich, und das ist keine Dublette. Gemeldet wird deshalb nur die
gefährliche Hälfte — gleicher Name, ABWEICHENDE Signatur.
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

    # --- Private Namen (31.08.2026) --------------------------------------

    #: Zwei Dateien, ein privater Name, DIESELBE Parameterliste.
    GLEICHE_SIGNATUR = {
        'eins.py': 'def _schieben(punkte, koerper, abstand):\n    return punkte\n',
        'zwei.py': 'def _schieben(punkte, koerper, abstand):\n    return koerper\n',
    }

    #: Dieselben zwei Dateien, aber die zweite meint etwas anderes.
    ANDERE_SIGNATUR = {
        'eins.py': 'def _schieben(punkte, koerper, abstand):\n    return punkte\n',
        'zwei.py': 'def _schieben(verts, ziel, marge, normalen):\n    return verts\n',
    }

    def test_privatname_mit_gleicher_signatur_bleibt_still(self):
        u"""`_parse` in zwanzig Modulen ist keine Dublette, sondern ein kurzer Name.

        Und wo der Rumpf wirklich doppelt steht, melden es `doppelcode`
        und `doppelrumpf` — die vergleichen den Rumpf statt den Namen.
        """
        satz = self._lauf(self.GLEICHE_SIGNATUR)
        self.assertNotIn('_schieben', self._text(satz))

    def test_privatname_mit_anderer_signatur_wird_gemeldet(self):
        u"""Derselbe Name für zwei verschiedene Rechnungen — der eigentliche Fall."""
        satz = self._lauf(self.ANDERE_SIGNATUR)
        self.assertIn('_schieben', self._text(satz))

    def test_der_befund_nennt_beide_signaturen(self):
        u"""Ohne die Parameterlisten muss man beide Dateien aufschlagen."""
        text = self._text(self._lauf(self.ANDERE_SIGNATUR))
        self.assertIn('punkte, koerper, abstand', text)
        self.assertIn('verts, ziel, marge, normalen', text)

    def test_ein_einzelner_privatname_ist_nie_ein_befund(self):
        satz = self._lauf({
            'eins.py': 'def _schieben(punkte, koerper, abstand):\n    return punkte\n',
        })
        self.assertNotIn('_schieben', self._text(satz))

    def test_private_klassen_bleiben_aussen_vor(self):
        u"""Eine Klasse hat keine Parameterliste, an der man sie unterscheiden könnte."""
        satz = self._lauf({
            'eins.py': 'class _Puffer:\n    pass\n',
            'zwei.py': 'class _Puffer:\n    def lesen(self):\n        return 1\n',
        })
        self.assertNotIn('_Puffer', self._text(satz))
