# -*- coding: utf-8 -*-
"""Stellt `console.log` auf `Protokoll.debug`/`Protokoll.info` um.

WARUM (16.08.2026): Im Frontend standen 144 `console.log`-Aufrufe. Sie fuellen
die Konsole bei jeder Aktion und verdecken damit echte Fehler — an genau diesem
Tag steckten dort drei stille Ausfaelle, die niemandem aufgefallen sind
(`fn.applyFacialExpression`, `fn.startWizard`, `fn.renderAlignmentPreview`).

Die Einordnung folgt EINER Regel, damit sie nachpruefbar ist:

  * `Protokoll.info`  — abgeschlossene Vorgaenge, die jemand angestossen hat:
    gespeichert, exportiert, fertig. Die will man ohne Debug-Schalter sehen.
  * `Protokoll.debug` — alles andere. Erscheint nur mit `?debug=1` oder
    `localStorage.humanbody.debug = '1'`.

Der Bereich (erstes Argument) kommt aus dem `[…]`-Praefix der Meldung, wenn es
eines gibt — sonst aus dem Ordner der Datei (BEREICHE unten). Damit steht in der
Konsole weiter vorne, woher die Zeile kommt, ohne dass es jede Meldung selbst
schreiben muss.

`console.warn` und `console.error` bleiben unberuehrt: Sie sind nie das Problem.

Aufruf:  python -m djangobase.umbau.protokoll <wurzel> [--schreiben]
"""

import re
import sys
from pathlib import Path

from .jsimporte import Importblock

AUSSER = {'node_modules', 'vendor', 'theatre', 'theatre-studio', '__pycache__',
          'TestCharakter', 'alt', 'Backup', 'ProjektTemp'}

#: Ordner -> Bereichsname in der Konsole
BEREICHE = {
    'bvh_studio': 'BVH Studio',
    'scene': 'Szene',
    'modellgenerator': 'Modellbau',
    'viewer': 'Viewer',
    'cloth': 'Kleidung',
    'photo_to_3d': 'Photo->3D',
    'animation': 'Animation',
    'result_character': 'Ergebnis',
    'vergleich': 'Vergleich',
    'modellbau': 'Modellbau',
    'eigenschaften': 'BVH Studio',
    'einstellungen': 'Einstellungen',
    'bvh_player': 'BVH Player',
    'js': 'BVH Player',
    'gemeinsam': 'Gemeinsam',
}

#: Meldungen mit diesen Woertern sind abgeschlossene Vorgaenge -> info.
#:
#: FEHLER 16.08.2026: Hier stand auch das nackte `Export`. Damit wurde
#: "[Cloth Export] bound 4 buttons" zur Vorgangsmeldung — das Wort stand im
#: BEREICHSNAMEN, nicht in der Meldung. Geprueft wird deshalb nur die Meldung
#: ohne Praefix, und `Export` nur als Verb.
LAUT = re.compile(r'gespeichert|saved|exportiert|exported|fertig'
                  r'|abgeschlossen|Export (?:fertig|done)', re.I)

#: `console.log(` — der Rest kann ueber mehrere Zeilen gehen
AUFRUF = re.compile(r'^(\s*)console\.log\(')
#: Praefix in der Meldung: '[BVH Studio] text' oder `[Preview] ${x}`
PRAEFIX = re.compile(r'^([\'"`])\[([^\]]+)\]\s?')


class ProtokollUmstellung:
    """Eine Datei umstellen und Bericht erstatten."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.zeilen = self.pfad.read_text(encoding='utf-8').split('\n')
        self.geaendert = []

    def bereich(self):
        for teil in reversed(self.pfad.parts[:-1]):
            if teil in BEREICHE:
                return BEREICHE[teil]
        return 'HumanBody'

    def durchgehen(self):
        for i, zeile in enumerate(self.zeilen):
            treffer = AUFRUF.match(zeile)
            if not treffer:
                continue
            neu = self._ersatz(i, treffer)
            if neu is None:
                continue
            self.zeilen[i] = neu
            self.geaendert.append(i + 1)
        return self

    def _ersatz(self, i, treffer):
        """Ersatz fuer die Zeile i, oder None wenn nicht sicher machbar."""
        einzug = treffer.group(1)
        rest = self.zeilen[i][treffer.end():]
        # Mehrzeilige Aufrufe: nur der Kopf wird ersetzt, der Rest bleibt.
        argumente = rest
        praefix = PRAEFIX.match(argumente.lstrip())
        bereich = self.bereich()
        if praefix:
            bereich = praefix.group(2)
            anfuehrung = praefix.group(1)
            # Praefix aus der Meldung nehmen; bleibt ein leerer String uebrig,
            # faellt das Argument ganz weg.
            gekuerzt = argumente.lstrip()[praefix.end():]
            if gekuerzt.startswith(anfuehrung):          # Meldung war nur '[X] '
                gekuerzt = gekuerzt[1:].lstrip(', ')
                argumente = gekuerzt
            else:
                argumente = anfuehrung + gekuerzt
        # Nur die Meldung selbst zaehlt, nicht der Bereichsname davor.
        stufe = 'info' if LAUT.search(argumente) else 'debug'
        return '%sProtokoll.%s(%s, %s' % (einzug, stufe,
                                          self._text(bereich), argumente)

    @staticmethod
    def _text(bereich):
        return "'%s'" % bereich.replace("'", "\\'")

    def import_ergaenzen(self):
        block = Importblock(self.pfad)
        block.zeilen = self.zeilen
        if block.sicherstellen('Protokoll'):
            self.zeilen = block.zeilen

    def schreiben(self):
        self.pfad.write_text('\n'.join(self.zeilen), encoding='utf-8')


def dateien(wurzel):
    for pfad in sorted(Path(wurzel).rglob('*.js')):
        if any(teil in AUSSER for teil in pfad.parts) or '.min.' in pfad.name:
            continue
        if pfad.name in ('protokoll.js',):      # die Klasse selbst
            continue
        yield pfad


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    wurzel = argumente[0] if argumente else 'HumanBodyWeb/static'
    schreiben = '--schreiben' in sys.argv

    gesamt = 0
    for pfad in dateien(wurzel):
        arbeit = ProtokollUmstellung(pfad).durchgehen()
        if not arbeit.geaendert:
            continue
        arbeit.import_ergaenzen()
        if schreiben:
            arbeit.schreiben()
        gesamt += len(arbeit.geaendert)
        print('%s: %d Stellen' % (pfad, len(arbeit.geaendert)))
    print('\n%d Stellen umgestellt%s' % (gesamt,
                                        '' if schreiben else ' (Probelauf)'))


if __name__ == '__main__':
    main()
