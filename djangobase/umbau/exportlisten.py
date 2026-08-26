# -*- coding: utf-8 -*-
"""Bringt `export { … };`-Listen mit dem Dateiinhalt in Einklang.

WARUM (16.08.2026): Mehrere Module dieses Projekts sammeln ihre Exporte am
Dateiende in einer Liste statt `export` vor jede Definition zu schreiben. Wandert
eine Definition beim Aufteilen in ein anderes Modul, bleibt ihr Name in der Liste
stehen — und node meldet beim Laden:

    SyntaxError: Export '_renderMHList' is not defined in module

Das Werkzeug streicht Namen, die es in der Datei nicht (mehr) gibt, und nimmt
Namen auf, die dort jetzt liegen und vorher exportiert waren.

Aufruf:  python -m djangobase.umbau.exportlisten <datei> [<datei> ...] [--namen a,b]
"""
import re
import sys
from pathlib import Path


from .codesicht import Codesicht


class Exportlisten:
    """Eine Datei und ihre abschliessende Exportliste."""

    LISTE = re.compile(r'(?m)^export\s*\{([^}]*)\}\s*;')

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.quelle = self.pfad.read_text(encoding='utf-8')
        self.code = Codesicht(self.quelle).code

    def definiert(self):
        """Namen, die in dieser Datei auf oberster Ebene stehen."""
        namen = set()
        for muster in (r'(?m)^(?:export\s+)?(?:async\s+)?function\*?\s+([A-Za-z_$][\w$]*)',
                       r'(?m)^(?:export\s+)?class\s+([A-Za-z_$][\w$]*)',
                       r'(?m)^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)'):
            namen |= set(re.findall(muster, self.code))
        return namen

    def bereinigen(self, ergaenzen=()):
        """Liste an den Inhalt anpassen. Gibt (gestrichen, ergänzt) zurück."""
        da = self.definiert()
        treffer = self.LISTE.search(self.quelle)
        vorhanden = []
        if treffer:
            vorhanden = [s.strip() for s in treffer.group(1).split(',') if s.strip()]
        bleibt = [n for n in vorhanden if n.split(' as ')[0].strip() in da]
        neu = [n for n in ergaenzen if n in da and n not in bleibt]
        gestrichen = [n for n in vorhanden if n not in bleibt]
        endliste = bleibt + neu
        if not treffer:
            if not neu:
                return gestrichen, []
            self.pfad.write_text(
                self.quelle.rstrip() + '\n\nexport { %s };\n' % ', '.join(endliste),
                encoding='utf-8')
            return gestrichen, neu
        ersatz = ('export { %s };' % ', '.join(endliste)) if endliste else ''
        text = self.quelle.replace(treffer.group(0), ersatz)
        self.pfad.write_text(text, encoding='utf-8')
        return gestrichen, neu


def main():
    dateien = [a for a in sys.argv[1:] if not a.startswith('--')]
    ergaenzen = []
    for a in sys.argv[1:]:
        if a.startswith('--namen'):
            ergaenzen = a.split('=', 1)[1].split(',')
    if not dateien:
        raise SystemExit(__doc__)
    for d in dateien:
        weg, dazu = Exportlisten(d).bereinigen(ergaenzen)
        print('%-46s gestrichen: %-28s ergänzt: %s'
              % (Path(d).name, ', '.join(weg) or '—', ', '.join(dazu) or '—'))


if __name__ == '__main__':
    main()
