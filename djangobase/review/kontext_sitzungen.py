# -*- coding: utf-8 -*-
u"""Welche Claude-Code-Protokolle es zu diesem Projekt gibt.

Getrennt von ``kontext.py``: Dort wird EIN Protokoll ausgewertet, hier
wird gesucht, welche es ueberhaupt gibt. Zwei Fragen, zwei Klassen.

WIE DER ORDNERNAME ENTSTEHT
===========================
Claude Code legt je Projektpfad einen Ordner unter
``~/.claude/projects/`` an. Der Name ist der Pfad mit ersetzten
Sonderzeichen: ``A:\\assistant`` wird zu ``a--assistant``. Die Regel ist
nicht dokumentiert, deshalb wird sie hier NICHT geraten: Zuerst wird der
abgeleitete Name versucht, und wenn es ihn nicht gibt, wird unter allen
Ordnern der gesucht, dessen Protokolle den Projektpfad nennen.
"""
import re
from datetime import datetime
from pathlib import Path


class Sitzungen:
    u"""Die Protokolldateien zu einem Projektverzeichnis."""

    #: Mehr als das liest niemand durch; die neuesten zuerst.
    HOECHSTENS = 12

    def __init__(self, projektpfad, wurzel=None):
        self.projektpfad = Path(projektpfad)
        self.wurzel = Path(wurzel) if wurzel else (
            Path.home() / '.claude' / 'projects')

    def ordner(self):
        u"""Der Protokollordner dieses Projekts — oder ``None``."""
        if not self.wurzel.is_dir():
            return None
        geraten = self.wurzel / self._abgeleitet()
        if geraten.is_dir():
            return geraten
        return self._suchen()

    def _abgeleitet(self):
        u"""``A:\\assistant`` -> ``a--assistant``."""
        text = str(self.projektpfad).lower()
        return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

    def _suchen(self):
        u"""Der Ordner, dessen Name auf den Projektnamen endet.

        Der Rueckfall, wenn die Ableitung nicht passt (andere Fassung von
        Claude Code, anderer Pfadaufbau). Geraten wird trotzdem nicht: Es
        muss der Projektname sein, nicht irgendein Ordner.
        """
        name = self.projektpfad.name.lower()
        treffer = [p for p in self.wurzel.iterdir()
                   if p.is_dir() and p.name.lower().endswith('-' + name)]
        if not treffer:
            return None
        return max(treffer, key=lambda p: p.stat().st_mtime)

    def liste(self):
        u"""``[{name, pfad, mb, wann}]`` — die neuesten zuerst."""
        ordner = self.ordner()
        if ordner is None:
            return []
        dateien = sorted(ordner.glob('*.jsonl'),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        raus = []
        for pfad in dateien[:self.HOECHSTENS]:
            stand = pfad.stat()
            raus.append({
                'name': pfad.stem,
                'pfad': str(pfad),
                'mb': round(stand.st_size / 1e6, 1),
                'wann': datetime.fromtimestamp(stand.st_mtime).strftime(
                    '%d.%m.%Y %H:%M'),
            })
        return raus

    def neueste(self):
        eintraege = self.liste()
        return eintraege[0]['pfad'] if eintraege else None

    def gueltig(self, pfad):
        u"""Liegt ``pfad`` wirklich im Protokollordner dieses Projekts?

        Der Wert kommt aus einem Formular. Ohne diese Pruefung liesse
        sich jede Datei des Rechners als „Protokoll" einlesen.
        """
        ordner = self.ordner()
        if ordner is None or not pfad:
            return False
        try:
            ziel = Path(pfad).resolve()
        except OSError:
            return False
        return (ziel.parent == ordner.resolve() and ziel.suffix == '.jsonl'
                and ziel.is_file())


__all__ = ['Sitzungen']
