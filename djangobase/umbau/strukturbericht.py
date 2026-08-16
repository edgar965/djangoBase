# -*- coding: utf-8 -*-
"""Strukturbericht einer grossen Datei — Grundlage fuer den Schnitt.

Zeigt je Top-Level-Definition: Name, Zeilen, Groesse, benutzte Module und die
Frage, ob es ein Django-Endpunkt ist. Daraus laesst sich ablesen, welche
Funktionen zusammengehoeren — und das ist die Vorarbeit fuer die Aufteilung in
Klassen und Module.

Aufruf:  python -m djangobase.umbau.strukturbericht <datei> [--gruppen]
"""
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path


class Strukturbericht:
    """Liest eine Python-Datei und ordnet ihre Definitionen."""

    #: Wortstaemme, nach denen gruppiert wird (Reihenfolge = Vorrang).
    THEMEN = [
        ('mesh', ('mesh', 'vertices', 'geometry', 'subdiv')),
        ('morph', ('morph', 'slider', 'shape', 'body_type')),
        ('skelett', ('skeleton', 'bone', 'rig', 'joint', 'pose')),
        ('retarget', ('retarget', 'bvh', 'anim')),
        ('kleidung', ('garment', 'cloth', 'wardrobe', 'mh_proxy', 'pattern',
                      'preset')),
        ('foto', ('photo', 'smplx', 'smpl', 'silhouette', 'texture', 'align')),
        ('studio', ('studio', 'theatre', 'scene', 'project', 'audio')),
        ('haare', ('hair', 'beard')),
        ('system', ('log', 'pref', 'config', 'settings', 'status', 'health')),
    ]

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.quelle = self.pfad.read_text(encoding='utf-8', errors='replace')
        self.baum = ast.parse(self.quelle)

    def eintraege(self):
        """[(name, art, zeile, laenge, thema, ist_endpunkt)]"""
        raus = []
        for k in self.baum.body:
            if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                continue
            art = 'klasse' if isinstance(k, ast.ClassDef) else 'funktion'
            laenge = (k.end_lineno or k.lineno) - k.lineno
            raus.append((k.name, art, k.lineno, laenge, self.thema(k.name),
                         self._ist_endpunkt(k)))
        return raus

    @classmethod
    def thema(cls, name):
        klein = name.lower()
        for thema, worte in cls.THEMEN:
            if any(w in klein for w in worte):
                return thema
        return 'rest'

    @staticmethod
    def _ist_endpunkt(knoten):
        """Django-View? Erkennbar an `request` als erstem Parameter."""
        if isinstance(knoten, ast.ClassDef):
            return False
        args = [a.arg for a in knoten.args.args]
        return bool(args) and args[0] == 'request'

    def gruppen(self):
        g = defaultdict(list)
        for name, art, zeile, laenge, thema, endpunkt in self.eintraege():
            g[thema].append((name, zeile, laenge, endpunkt))
        return g

    def bericht(self, mit_gruppen=False):
        zeilen = ['%s — %d Zeilen' % (self.pfad.name,
                                      self.quelle.count('\n') + 1)]
        eintraege = self.eintraege()
        endpunkte = sum(1 for e in eintraege if e[5])
        zeilen.append('%d Definitionen, davon %d Endpunkte'
                      % (len(eintraege), endpunkte))
        zeilen.append('')
        if mit_gruppen:
            for thema, posten in sorted(self.gruppen().items(),
                                        key=lambda kv: -sum(p[2] for p in kv[1])):
                summe = sum(p[2] for p in posten)
                zeilen.append('=== %-10s %3d Definitionen, %5d Zeilen'
                              % (thema, len(posten), summe))
                for name, zeile, laenge, endpunkt in sorted(posten,
                                                            key=lambda p: -p[2]):
                    zeilen.append('    %-46s %5d Z. ab %5d %s'
                                  % (name[:46], laenge, zeile,
                                     'API' if endpunkt else ''))
        else:
            for name, art, zeile, laenge, thema, endpunkt in sorted(
                    eintraege, key=lambda e: -e[3]):
                zeilen.append('  %-46s %5d Z. ab %5d  %-9s %s'
                              % (name[:46], laenge, zeile, thema,
                                 'API' if endpunkt else art))
        return '\n'.join(zeilen)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    b = Strukturbericht(sys.argv[1])
    print(b.bericht('--gruppen' in sys.argv))


if __name__ == '__main__':
    main()
