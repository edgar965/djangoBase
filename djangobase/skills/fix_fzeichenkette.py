# -*- coding: utf-8 -*-
u"""FixFZeichenkette — das ``f`` vor Zeichenketten ohne Platzhalter streichen.

DIE FRAGE (Edgar, 25.08.2026)
=============================
    „Hast du auch alle Werkzeuge in djangoBase für die Code-Qualität und
     für die Fixes der Code-Qualität usw?"

Nein, hatte ich nicht — und beim Nachsehen kam ein Fund gegen mich heraus:

    djangoBase hatte längst `ImportFixer` (Kriterium 5), mit Sicherung und
    Netz auf der `Fixer`-Basis. Ich habe daneben in CamTrack ein eigenes
    Skript `tools/wartung/pyflakes_fixen.py` gebaut, das dieselben toten
    Einfuhren entfernt — im falschen Projekt, ohne Sicherung, ohne Netz.
    `ImportFixer` achtet sogar schon auf ``# noqa``.

Übrig blieb genau EINE Fähigkeit, die es hier noch nicht gab: dieser Fixer.

WAS ER TUT
==========
``pyflakes`` meldet ``FStringMissingPlaceholders``::

    logger.info(f'fertig')          ->   logger.info('fertig')

Ein ``f`` ohne ``{}`` tut nichts. Es ist auch kein Tippfehler ohne Folgen:
Es liest sich wie eine Zeichenkette, die eingesetzte Werte enthält, und wer
sie später erweitert, verlässt sich darauf, dass die Klammern greifen —
bei einer Zeichenkette OHNE ``f`` tun sie es nicht. Gemessen an CamTrack:
16 Stellen, davon drei in `trt_warmup.py` und drei in `yolo_export_trt.py`.

WARUM ÜBER DEN AST
==================
Ein Muster wie ``f'`` trifft auch ``if x == 'auf'`` und jedes ``f`` am
Wortende vor einem Anführungszeichen. Der AST liefert die genaue Spalte des
``JoinedStr``-Knotens; dort steht das ``f``, und nur dort wird eines
gestrichen. Zusätzlich muss der Knoten NACHWEISLICH keinen
``FormattedValue`` enthalten — sonst wäre es kein leeres ``f``.
"""
import ast

from .anlassfall import Anlassfall
from .fixer import Aenderung, Fixer, Vorschau

__all__ = ['FixFZeichenkette']


class FixFZeichenkette(Fixer):

    slug = 'fix-fzeichenkette'
    titel = 'Leere f-Zeichenketten entschärfen'
    tut = ('Streicht das ``f`` vor Zeichenketten, die keinen Platzhalter '
           'enthalten.')
    warum = ('Ein ``f`` ohne ``{}`` tut nichts und behauptet das Gegenteil. '
             'Wer die Zeichenkette später um ``{wert}`` ergänzt, verlässt '
             'sich darauf, dass die Klammern greifen — ohne das ``f`` tun '
             'sie es nicht, und die Klammern stehen wörtlich in der '
             'Ausgabe. `pyflakes` meldet es als '
             '``FStringMissingPlaceholders``.')
    grenzen = ('Nur Knoten, die nachweislich keinen ``FormattedValue`` '
               'enthalten. Zeilen mit ``# noqa`` bleiben unberührt — das '
               'ist die ausdrückliche Ansage des Autors, dieselbe Regel wie '
               'bei ``ImportFixer``.')
    kriterium = 0
    dauer = 'wenige Sekunden'

    anlassfall = Anlassfall(
        {'melden.py': ("import logging\n\n\n"
                       "logger = logging.getLogger(__name__)\n\n\n"
                       "def melden(n):\n"
                       "    logger.info(f'fertig')\n"
                       "    logger.info(f'{n} Stück')\n")},
        mindestens=1, hoechstens=1, erwartet_in='melden.py',
        warum='Ein `f` ohne Klammern tut nichts — und die Zeile daneben '
              'zeigt, dass nicht jedes `f` gemeint ist')

    # ------------------------------------------------------------------
    def vorschau(self):
        aenderungen = []
        for pfad in self.pfade('*.py'):
            try:
                quelle = pfad.read_text(encoding='utf-8')
                baum = ast.parse(quelle)
            except (OSError, SyntaxError, ValueError):
                continue
            zeilen = quelle.splitlines(keepends=True)
            stellen = self._leere_f(baum, zeilen)
            if not stellen:
                continue
            # Von hinten, sonst verschieben sich die Spalten der frueheren
            # Treffer in derselben Zeile.
            for zeile, spalte in sorted(stellen, reverse=True):
                inhalt = zeilen[zeile - 1]
                zeilen[zeile - 1] = inhalt[:spalte] + inhalt[spalte + 1:]
            aenderungen.append(Aenderung(
                pfad, '%d leere f-Zeichenketten' % len(stellen),
                ''.join(zeilen)))
        return Vorschau(
            aenderungen,
            'Nur Knoten ohne jeden Platzhalter; Zeilen mit # noqa bleiben.')

    def pruefen(self, aenderung):
        u"""Netz: parst die Datei noch, und ist wirklich nichts übrig?"""
        try:
            quelle = aenderung.pfad.read_text(encoding='utf-8')
            baum = ast.parse(quelle)
        except SyntaxError as fehler:
            return ['kompiliert nicht mehr: %s' % fehler]
        except OSError as fehler:
            return ['nicht lesbar: %s' % fehler]
        uebrig = self._leere_f(baum, quelle.splitlines(keepends=True))
        if uebrig:
            return ['%d leere f-Zeichenketten stehen noch' % len(uebrig)]
        return []

    # ------------------------------------------------------------ intern
    @staticmethod
    def _leere_f(baum, zeilen):
        u"""``[(zeile, spalte)]`` — wo ein ``f`` steht, das nichts tut.

        Geprüft wird DREIFACH, weil hier ein Zeichen mitten im Quelltext
        verschwindet:

        1. Der Knoten ist ein ``JoinedStr`` (also eine f-Zeichenkette).
        2. Er enthält keinen einzigen ``FormattedValue``.
        3. An der gemeldeten Spalte steht tatsächlich ein ``f`` oder ``F``.

        Ohne (3) würde bei einer über mehrere Zeilen verketteten
        Zeichenkette (``f'a' 'b'``) an der falschen Stelle geschnitten —
        der AST nennt dort den Anfang der GANZEN Verkettung.
        """
        raus = []
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.JoinedStr):
                continue
            if any(isinstance(teil, ast.FormattedValue)
                   for teil in knoten.values):
                continue
            zeile = getattr(knoten, 'lineno', 0)
            spalte = getattr(knoten, 'col_offset', -1)
            if not 1 <= zeile <= len(zeilen) or spalte < 0:
                continue
            inhalt = zeilen[zeile - 1]
            if 'noqa' in inhalt.lower():
                continue            # ausdrueckliche Ansage des Autors
            if spalte < len(inhalt) and inhalt[spalte] in 'fF':
                raus.append((zeile, spalte))
        return raus
