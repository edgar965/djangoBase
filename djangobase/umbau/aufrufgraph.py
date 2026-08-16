# -*- coding: utf-8 -*-
"""Aufrufgraph innerhalb einer Datei — wer ruft wen, und ueber Themen hinweg?

Der Schnitt einer grossen Datei scheitert an den gemeinsamen Helfern: Eine
private Funktion, die von vier Themen benutzt wird, wird beim Verschieben
entweder kopiert (dann laufen die Kopien auseinander) oder vergessen (dann
fehlt sie). Dieses Werkzeug zeigt vor dem ersten Schnitt, welche das sind.

Aufruf:  python -m djangobase.umbau.aufrufgraph <datei> [--gemeinsam]
"""
import ast
import sys
from collections import defaultdict
from pathlib import Path


from .strukturbericht import Strukturbericht


class Aufrufgraph:
    """Wer ruft wen innerhalb EINER Datei."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.quelle = self.pfad.read_text(encoding='utf-8', errors='replace')
        self.baum = ast.parse(self.quelle)
        self.definiert = {}          # name -> (zeile, laenge, thema)
        self.rufe = defaultdict(set)  # rufer -> {gerufene}
        self._sammeln()

    def _sammeln(self):
        for k in self.baum.body:
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.definiert[k.name] = (
                    k.lineno, (k.end_lineno or k.lineno) - k.lineno,
                    Strukturbericht.thema(k.name))
        for k in self.baum.body:
            if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for knoten in ast.walk(k):
                if isinstance(knoten, ast.Call):
                    ziel = self._name(knoten.func)
                    if ziel and ziel in self.definiert and ziel != k.name:
                        self.rufe[k.name].add(ziel)

    @staticmethod
    def _name(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return None

    # ------------------------------------------------------------------ lesen

    def rufer_von(self):
        """{gerufene: {rufer}}"""
        raus = defaultdict(set)
        for rufer, ziele in self.rufe.items():
            for z in ziele:
                raus[z].add(rufer)
        return raus

    def gemeinsame_helfer(self, min_themen=2):
        """[(name, zeilen, [themen], [rufer])] — von mehreren Themen benutzt."""
        raus = []
        for ziel, rufer in self.rufer_von().items():
            themen = {self.definiert[r][2] for r in rufer if r in self.definiert}
            if len(themen) < min_themen:
                continue
            zeile, laenge, _ = self.definiert[ziel]
            raus.append((ziel, laenge, sorted(themen), sorted(rufer)))
        raus.sort(key=lambda e: (-len(e[2]), -e[1]))
        return raus

    def einsame(self):
        """Definitionen, die niemand in dieser Datei ruft (oft Endpunkte)."""
        gerufen = set(self.rufer_von())
        return sorted(n for n in self.definiert if n not in gerufen)

    def bericht(self, nur_gemeinsam=False):
        z = ['%s: %d Definitionen' % (self.pfad.name, len(self.definiert)), '']
        gem = self.gemeinsame_helfer()
        z.append('GEMEINSAME HELFER (von mehreren Themen gerufen): %d' % len(gem))
        for name, laenge, themen, rufer in gem:
            z.append('  %-40s %4d Z.  Themen: %-32s  %d Rufer'
                     % (name[:40], laenge, ','.join(themen), len(rufer)))
        if nur_gemeinsam:
            return '\n'.join(z)
        z.append('')
        z.append('NUR INNERHALB EINES THEMAS: %d'
                 % (len(self.rufer_von()) - len(gem)))
        return '\n'.join(z)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    g = Aufrufgraph(sys.argv[1])
    print(g.bericht('--gemeinsam' in sys.argv))


if __name__ == '__main__':
    main()
