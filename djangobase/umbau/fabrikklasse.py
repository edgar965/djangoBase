# -*- coding: utf-8 -*-
"""Wandelt eine Fabrikfunktion mit Closure in eine echte Klasse.

Gedacht fuer das Muster, das in diesem Projekt mehrfach vorkommt:

    export function createViewer(config) {
        let scene, camera, renderer;          // Zustand in der Closure
        function loadMesh() { … scene … }     // Funktionen greifen darauf zu
        return { loadMesh, … };
    }

Die Datei laesst sich so nicht aufteilen: Jede Funktion haengt an Variablen, die
nur innerhalb der Fabrik sichtbar sind. Als Klasse werden aus den Variablen
Felder (`this.scene`) und aus den Funktionen Methoden — und danach kann man
Methodengruppen in eigene Module ziehen.

Das Werkzeug arbeitet auf der Codesicht, ersetzt also nichts in Zeichenketten
(der Fehler, der `'label-renderer'` zu `'label-Testzustand.renderer'` gemacht
hat). Was es NICHT kann: entscheiden, was fachlich zusammengehoert. Die
Aufteilung in Module bleibt Handarbeit.

Aufruf:  python -m djangobase.umbau.fabrikklasse <datei> <fabrikname> <klasse>
"""
import re
import sys
from pathlib import Path


from .codesicht import Codesicht


class Fabrikumbau:
    """Findet Closure-Variablen und innere Funktionen einer Fabrikfunktion."""

    def __init__(self, pfad, fabrik):
        self.pfad = Path(pfad)
        self.quelle = self.pfad.read_text(encoding='utf-8')
        self.maske = Codesicht.maske(self.quelle)
        self.fabrik = fabrik
        self.anfang, self.ende = self._grenzen()

    def _grenzen(self):
        m = re.search(r'(?m)^(?:export\s+)?function\s+%s\s*\('
                      % re.escape(self.fabrik), self.maske)
        if not m:
            raise SystemExit('Fabrik %s nicht gefunden' % self.fabrik)
        tiefe, i, offen = 0, m.start(), False
        while i < len(self.maske):
            if self.maske[i] == '{':
                tiefe += 1
                offen = True
            elif self.maske[i] == '}':
                tiefe -= 1
                if offen and tiefe == 0:
                    return m.start(), i + 1
            i += 1
        raise SystemExit('Ende der Fabrik nicht gefunden')

    def _rumpfmaske(self):
        return self.maske[self.anfang:self.ende]

    def felder(self):
        """Namen der Variablen, die direkt in der Fabrik deklariert sind."""
        namen = []
        for m in re.finditer(r'(?m)^    (?:let|const|var)\s+([^;=\n]+?)(?:\s*=|;)',
                             self._rumpfmaske()):
            for stueck in m.group(1).split(','):
                treffer = re.match(r'\s*([A-Za-z_$][\w$]*)', stueck)
                if treffer:
                    namen.append(treffer.group(1))
        return namen

    def methoden(self):
        """Namen der Funktionen, die direkt in der Fabrik stehen."""
        return re.findall(r'(?m)^    (?:async\s+)?function\s+([A-Za-z_$][\w$]*)',
                          self._rumpfmaske())

    def bericht(self):
        f, me = self.felder(), self.methoden()
        print('Fabrik %s: Zeilen %d-%d'
              % (self.fabrik,
                 self.quelle[:self.anfang].count('\n') + 1,
                 self.quelle[:self.ende].count('\n') + 1))
        print('  %2d Felder:   %s' % (len(f), ', '.join(f)))
        print('  %2d Methoden: %s' % (len(me), ', '.join(me)))
        return f, me


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    Fabrikumbau(sys.argv[1], sys.argv[2]).bericht()


if __name__ == '__main__':
    main()
