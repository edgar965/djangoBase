# -*- coding: utf-8 -*-
u"""Wer ruft wen — über das ganze Projekt, für Funktionen UND Klassen.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „mache alle Klassen in allen Tabs und alle Funktionen aus allen Tabs
     auch als Gliederung mit Knöpfen, so dass man sieht, wer sie nutzt, und
     welche andere Unterklassen / funktionen sie nutzen"

`Klassenmodell` beantwortet das für Klassen — aber nur über ``self.x =
Klasse()``, also über den BESITZ. Für eine freie Funktion gibt es keinen
Besitz; sie wird gerufen. Und genau davon gibt es 820 Stück auf
Modulebene, mehr als es Klassen gibt.

WAS GEZÄHLT WIRD
================
Jeder Aufruf beim Namen::

    def zeichne():
        daten = lade()          -> zeichne nutzt lade
        Bild(daten).malen()     -> zeichne nutzt Bild

    class Seite:
        def bauen(self):
            zeichne()           -> Seite nutzt zeichne

Der Rufer ist die umschliessende Definition: eine Funktion, eine Klasse
(nicht die einzelne Methode — im Bild ist die Klasse der Kasten) oder das
Modul selbst.

WAS NICHT GEZÄHLT WIRD
======================
Methodenaufrufe auf einem Objekt (``self.zeichner.malen()``) — der Name
``malen`` sagt nichts darüber, WELCHE Klasse gemeint ist. Wer das ohne
Typinformation auflöst, rät; und ein geratenes Netz ist schlimmer als
keines. Der Besitz steht dafür im Klassenmodell.
"""
import ast
from collections import defaultdict
from pathlib import Path

#: Verzeichnisse, die nicht zum Netz gehoeren — DIESELBE Liste wie im
#: Klassenmodell. Zwei Kopien liefen beim naechsten Zusatz auseinander:
#: `sicherung` kam dort dazu, hier nicht, und das Netz zaehlte einen
#: Abzug des Projekts mit.
from .klassenmodell import AUS  # noqa: F401

#: Was Python selbst mitbringt. Ohne diese Liste ist `len` der meist-
#: genutzte „Baustein" des Projekts.
EINGEBAUT = {
    'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'print', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted',
    'sum', 'min', 'max', 'abs', 'round', 'any', 'all', 'open', 'type',
    'isinstance', 'issubclass', 'getattr', 'setattr', 'hasattr', 'super',
    'repr', 'format', 'bytes', 'frozenset', 'reversed', 'iter', 'next',
    'property', 'staticmethod', 'classmethod', 'Exception', 'ValueError',
    'TypeError', 'KeyError', 'OSError', 'RuntimeError', 'id', 'hash',
}


class Stelle:
    u"""Eine Definition: Funktion oder Klasse, mit ihrem Ort."""

    __slots__ = ('name', 'art', 'datei', 'zeile')

    #: `art` unterscheidet die Reiter: Funktionen und Klassen stehen
    #: getrennt, obwohl sie im Netz gleich behandelt werden.
    FUNKTION = 'funktion'
    KLASSE = 'klasse'

    def __init__(self, name, art, datei, zeile):
        self.name = name
        self.art = art
        self.datei = datei
        self.zeile = zeile


class Aufrufnetz:
    u"""Liest ein Projekt und weiss danach, wer wen ruft."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        #: ``{name: Stelle}`` — wo etwas definiert ist.
        self.stellen = {}
        #: ``{gerufener: {rufer, …}}``
        self.genutzt_von = defaultdict(set)
        #: ``{rufer: {gerufener, …}}``
        self.nutzt = defaultdict(set)

    def lesen(self):
        baeume = []
        for pfad in sorted(self.wurzel.rglob('*.py')):
            if any(teil in pfad.parts for teil in AUS):
                continue
            try:
                baum = ast.parse(pfad.read_text(encoding='utf-8',
                                                errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            kurz = str(pfad.relative_to(self.wurzel)).replace('\\', '/')
            baeume.append((kurz, baum))
            self._definitionen(baum, kurz)
        # ZWEITER DURCHGANG: Erst wenn alle Definitionen bekannt sind,
        # laesst sich ein Aufruf zuordnen. Beim einen Durchgang zaehlte nur,
        # was VORHER in derselben Datei stand.
        for kurz, baum in baeume:
            self._aufrufe(baum, kurz)
        return self

    # ── Definitionen ────────────────────────────────────────────
    def _definitionen(self, baum, datei):
        for knoten in baum.body:
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.stellen.setdefault(knoten.name, Stelle(
                    knoten.name, Stelle.FUNKTION, datei, knoten.lineno))
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                self.stellen.setdefault(knoten.name, Stelle(
                    knoten.name, Stelle.KLASSE, datei, knoten.lineno))

    # ── Aufrufe ─────────────────────────────────────────────────
    def _aufrufe(self, baum, datei):
        for knoten in baum.body:
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                self._eintragen(knoten.name, knoten)
            else:
                # Modulebene: `URL_PATTERNS = [pfad(...)]` ruft auch.
                self._eintragen('%s (Modulebene)' % datei, knoten)

    def _eintragen(self, rufer, knoten):
        for teil in ast.walk(knoten):
            if not isinstance(teil, ast.Call):
                continue
            name = self._gerufener(teil.func)
            if not name or name == rufer or name in EINGEBAUT:
                continue
            if name not in self.stellen:
                continue            # nichts aus diesem Projekt
            self.nutzt[rufer].add(name)
            self.genutzt_von[name].add(rufer)

    @staticmethod
    def _gerufener(ruf):
        u"""Nur der Aufruf BEIM NAMEN zaehlt.

        ``self.zeichner.malen()`` waere ein Methodenaufruf auf einem Objekt
        — der Name ``malen`` sagt nichts darueber, welche Klasse gemeint
        ist. Wer das ohne Typinformation aufloest, raet.
        """
        if isinstance(ruf, ast.Name):
            return ruf.id
        return ''

    # ── Auskunft ────────────────────────────────────────────────
    def steckbrief(self, name):
        u"""``{name, art, datei, zeile, genutzt_von, nutzt}`` oder ``None``."""
        stelle = self.stellen.get(name)
        if stelle is None:
            return None
        return {
            'name': name,
            'art': stelle.art,
            'datei': stelle.datei,
            'zeile': stelle.zeile,
            'genutzt_von': sorted(self.genutzt_von.get(name, ())),
            'nutzt': sorted(self.nutzt.get(name, ())),
        }

    def steckbriefe(self, namen=None):
        namen = list(namen) if namen is not None else list(self.stellen)
        raus = {}
        for name in namen:
            eintrag = self.steckbrief(name)
            if eintrag:
                raus[name] = eintrag
        return raus

    def kennzahlen(self):
        funktionen = [s for s in self.stellen.values()
                      if s.art == Stelle.FUNKTION]
        ungenutzt = [s.name for s in funktionen
                     if not self.genutzt_von.get(s.name)]
        return {
            'stellen': len(self.stellen),
            'funktionen': len(funktionen),
            'kanten': sum(len(v) for v in self.nutzt.values()),
            'ungenutzte_funktionen': len(ungenutzt),
        }


__all__ = ['Aufrufnetz', 'Stelle']
