# -*- coding: utf-8 -*-
"""Einen Import in eine JS-Datei einfuegen — an der richtigen Stelle.

WARUM als eigenes Modul (16.08.2026): Beim Umstellen auf `Serverabruf` und
`Protokoll` sind mehr als 40 Dateien betroffen. Der Import muss dabei

  * nach dem LETZTEN vollstaendigen Import stehen (nicht nach der ersten Zeile
    eines mehrzeiligen Imports — sonst landet er MITTEN in einem Import und die
    Datei ist unlesbar; genau das ist am 16.08.2026 drei Dateien passiert),
  * bei einer Datei ohne Importe hinter den Kopfkommentar (nicht davor),
  * mit der richtigen Anzahl `../` je nach Ablageort der Datei.

Aufruf:  python -m djangobase.umbau.jsimporte <klasse> <datei> [<datei> …]
Beispiel: python -m djangobase.umbau.jsimporte Protokoll static/js/a.js

Die Zuordnung Klasse -> Datei steht in GEMEINSAM. Projekte mit anderem
Ablageort setzen `Importblock.ZIELORDNER`.
"""

import os
import sys
from pathlib import Path

from ..skills.jsklammern import Klammerzaehler

#: Klasse -> Dateiname im Ordner `gemeinsam`
GEMEINSAM = {
    'Serverabruf': 'serverabruf.js',
    'Protokoll': 'protokoll.js',
    'Zeiten': 'zeiten.js',
    'Knopfmeldung': 'knopfmeldung.js',
    'Hautfarbe': 'hautfarbe.js',
    'Morphliste': 'morphliste.js',
    'Metaregler': 'metaregler.js',
    'Buehne': 'buehne.js',
    'Skelettanzeige': 'skelettanzeige.js',
}


class Importblock:
    """Der Importbereich am Kopf einer JS-Datei."""

    #: So weit oben wird nach Importen gesucht.
    KOPFZEILEN = 80
    #: Wo die gemeinsamen Klassen liegen, relativ zu `static/`. Projekte mit
    #: anderer Ablage setzen das vor dem Aufruf.
    ZIELORDNER = ('viewer', 'gemeinsam')

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.zeilen = self.pfad.read_text(encoding='utf-8').split('\n')

    def hat(self, datei):
        return any(datei in zeile for zeile in self.zeilen[:Importblock.KOPFZEILEN])

    def sicherstellen(self, klasse):
        """Import ergänzen, wenn er fehlt. Liefert True, wenn geändert."""
        datei = GEMEINSAM[klasse]
        if self.hat(datei):
            return False
        zeile = "import { %s } from '%s/%s';" % (klasse, self._pfad(), datei)
        self.zeilen.insert(self._stelle() + 1, zeile)
        return True

    def _stelle(self):
        """Zeilennummer, hinter der der Import stehen soll.

        FEHLER 16.08.2026: Die Suche nahm jede Zeile, die mit `;` endet und
        ` from ` enthaelt. In `modellgenerator_ui.js` traf das eine MELDUNG —
        `console.log('… config from loaded character:', …);` — und der Import
        landete mitten in einer Methode. Deshalb: nur Zeilen, die selbst mit
        `import` beginnen; das Ende einer mehrzeiligen Import-Anweisung wird
        ueber die Klammertiefe gesucht.
        """
        ende = -1
        i = 0
        grenze = min(len(self.zeilen), Importblock.KOPFZEILEN)
        while i < grenze:
            if not self.zeilen[i].lstrip().startswith('import'):
                i += 1
                continue
            zaehler = Klammerzaehler()
            while i < grenze:
                zaehler.zeile(self.zeilen[i])
                fertig = (zaehler.tiefe <= 0
                          and self.zeilen[i].rstrip().endswith(';'))
                ende = i
                i += 1
                if fertig:
                    break
        return ende if ende >= 0 else self._kopfende()

    def _kopfende(self):
        """Letzte Zeile des Kopfkommentars, sonst -1."""
        if not self.zeilen or not self.zeilen[0].lstrip().startswith('/*'):
            return -1
        for i, zeile in enumerate(self.zeilen[:Importblock.KOPFZEILEN]):
            if '*/' in zeile:
                return i
        return -1

    def _pfad(self):
        """Relativer Pfad zum Ordner `gemeinsam` von dieser Datei aus."""
        teile = self.pfad.parts
        if 'static' not in teile:
            raise ValueError('Datei liegt nicht unter static/: %s' % self.pfad)
        static = Path(*teile[:teile.index('static') + 1])
        ziel = static.joinpath(*Importblock.ZIELORDNER)
        pfad = os.path.relpath(ziel, self.pfad.parent).replace('\\', '/')
        return pfad if pfad.startswith('.') else './' + pfad

    def schreiben(self):
        self.pfad.write_text('\n'.join(self.zeilen), encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 3:
        print(__doc__)
        return
    klasse, *dateien = sys.argv[1:]
    if klasse not in GEMEINSAM:
        print('Unbekannte Klasse: %s (bekannt: %s)'
              % (klasse, ', '.join(sorted(GEMEINSAM))))
        return
    for datei in dateien:
        block = Importblock(datei)
        if block.sicherstellen(klasse):
            block.schreiben()
            print('%s: %s ergänzt' % (datei, klasse))
        else:
            print('%s: schon vorhanden' % datei)


if __name__ == '__main__':
    main()
