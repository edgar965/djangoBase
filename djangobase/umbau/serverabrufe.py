# -*- coding: utf-8 -*-
"""Stellt `fetch` + `json()` auf `Serverabruf.json()` um — nur eindeutige Faelle.

WARUM (16.08.2026): An 125 Stellen wurde die Antwort ohne `.ok`-Pruefung
weiterverarbeitet. Bei einem Serverfehler kommt eine HTML-Fehlerseite, `json()`
scheitert daran, und in der Konsole steht "Unexpected token '<'" — eine Meldung,
die nichts ueber die Ursache sagt.

VORSICHT: Dieses Skript aendert Code. Deshalb fasst es nur an, was es sicher
erkennt:

  * Die beiden Anweisungen muessen unmittelbar aufeinander folgen:
        const X = await fetch(ADRESSE[, WAHL]);      (auch mehrzeilig)
        const Y = await X.json();
  * `X` darf danach im restlichen Text NICHT mehr vorkommen — sonst wird die
    Antwort noch fuer `status`, `headers` oder `text()` gebraucht.
  * Zeilen in Kommentaren bleiben unberuehrt.

Zweiter Fall, seit 16.08.2026 ebenfalls mechanisch:
        const Y = await (await fetch(ADRESSE)).json();
Ein Einzeiler, der die Antwort gar nicht erst benennt — hier ist die Umstellung
eindeutig, weil niemand sie danach noch anfassen kann.

Alles andere bleibt liegen und wird als "manuell" gemeldet. Ein Werkzeug, das im
Zweifel zugreift, macht mehr kaputt als es aufraeumt.

Aufruf:  python -m djangobase.umbau.serverabrufe <wurzel> [--schreiben]
"""

import re
import sys
from pathlib import Path

from ..skills2.jsklammern import Klammerzaehler
from .jsimporte import Importblock

AUSSER = {'node_modules', 'vendor', 'theatre', 'theatre-studio', '__pycache__',
          'TestCharakter', 'alt', 'Backup', 'ProjektTemp'}

#: `const resp = await fetch(...)` — auch mehrzeilig, dann steht der Rest
#: (Optionsobjekt) in den Folgezeilen bis zur ausgleichenden Klammer.
FETCH = re.compile(r'^(\s*)const\s+(\w+)\s*=\s*await\s+fetch\(')
#: `const data = await resp.json();`
JSON = re.compile(r'^(\s*)const\s+(\w+)\s*=\s*await\s+(\w+)\.json\(\);?\s*$')
#: `const daten = await (await fetch(ADRESSE)).json();` — einzeilig, verschachtelt
VERSCHACHTELT = re.compile(
    r'await\s*\(\s*await\s+fetch\((.+?)\)\s*\)\s*\.json\(\)')


class ServerabrufUmstellung:
    """Eine Datei umstellen und Bericht erstatten."""

    def __init__(self, pfad):
        self.pfad = pfad
        self.zeilen = pfad.read_text(encoding='utf-8').split('\n')
        self.geaendert = []
        self.manuell = []

    def durchgehen(self):
        neu = []
        i = 0
        while i < len(self.zeilen):
            paar = self._paar(i)
            if paar:
                ersatz, verbraucht = paar
                neu.extend(ersatz)
                self.geaendert.append(i + 1)
                i += verbraucht
                continue
            einzeiler = self._verschachtelt(i)
            if einzeiler:
                neu.append(einzeiler)
                self.geaendert.append(i + 1)
                i += 1
                continue
            if 'await fetch(' in self.zeilen[i] and not self._kommentar(i):
                self.manuell.append((i + 1, self.zeilen[i].strip()[:90]))
            neu.append(self.zeilen[i])
            i += 1
        self.zeilen = neu
        return self

    def _kommentar(self, i):
        blank = self.zeilen[i].lstrip()
        return blank.startswith(('//', '*', '/*'))

    def _verschachtelt(self, i):
        """Ersatzzeile fuer `await (await fetch(A)).json()`, sonst None."""
        if self._kommentar(i):
            return None
        treffer = VERSCHACHTELT.search(self.zeilen[i])
        if not treffer:
            return None
        return (self.zeilen[i][:treffer.start()]
                + 'await Serverabruf.json(%s)' % treffer.group(1)
                + self.zeilen[i][treffer.end():])

    def _blockende(self, i):
        """Letzte Zeile der `fetch(...)`-Anweisung, die in Zeile i beginnt."""
        zaehler = Klammerzaehler(1)
        tiefe = zaehler.zeile(self.zeilen[i].split('await fetch(', 1)[1])
        ende = i
        while tiefe > 0:
            ende += 1
            if ende >= len(self.zeilen) or ende - i > 20:
                return None      # unabgeschlossen: Finger weg
            tiefe = zaehler.zeile(self.zeilen[ende])
        return ende

    def _paar(self, i):
        """Ersatzzeilen und Zeilenzahl, wenn hier ein fetch/json-Paar steht."""
        if not FETCH.match(self.zeilen[i]) or self._kommentar(i):
            return None
        ende = self._blockende(i)
        if ende is None or ende + 1 >= len(self.zeilen):
            return None
        zweite = JSON.match(self.zeilen[ende + 1])
        if not zweite:
            return None
        antwortname = FETCH.match(self.zeilen[i]).group(2)
        _, zielname, benutzt = zweite.groups()
        if benutzt != antwortname:
            return None
        # Wird die Antwort spaeter noch gebraucht? Dann nicht anfassen.
        rest = '\n'.join(self.zeilen[ende + 2:])
        if re.search(r'\b%s\b' % re.escape(antwortname), rest):
            return None
        # Nur der Kopf wird ersetzt; ein mehrzeiliges Optionsobjekt und die
        # schliessende Klammer bleiben unveraendert stehen.
        kopf = re.sub(r'const\s+\w+\s*=\s*await\s+fetch\(',
                      'const %s = await Serverabruf.json(' % zielname,
                      self.zeilen[i], count=1)
        ersatz = [kopf] + self.zeilen[i + 1:ende + 1]
        if i == ende and not ersatz[0].rstrip().endswith(';'):
            ersatz[0] = ersatz[0].rstrip() + ';'
        return ersatz, ende + 2 - i

    def import_ergaenzen(self):
        """Import auf `Serverabruf` ergaenzen (siehe js_importe.Importblock)."""
        block = Importblock(self.pfad)
        block.zeilen = self.zeilen          # Stand dieser Umstellung, nicht Platte
        if block.sicherstellen('Serverabruf'):
            self.zeilen = block.zeilen

    def schreiben(self):
        self.pfad.write_text('\n'.join(self.zeilen), encoding='utf-8')


def dateien(wurzel):
    for pfad in sorted(Path(wurzel).rglob('*.js')):
        if any(teil in AUSSER for teil in pfad.parts) or '.min.' in pfad.name:
            continue
        yield pfad


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    wurzel = argumente[0] if argumente else 'static/viewer'
    schreiben = '--schreiben' in sys.argv

    umgestellt = 0
    offen = []
    for pfad in dateien(wurzel):
        arbeit = ServerabrufUmstellung(pfad).durchgehen()
        if arbeit.geaendert:
            arbeit.import_ergaenzen()
            if schreiben:
                arbeit.schreiben()
            umgestellt += len(arbeit.geaendert)
            print('%s: %d Stellen' % (pfad, len(arbeit.geaendert)))
        offen.extend((pfad, nummer, text) for nummer, text in arbeit.manuell)

    print('\n%d Stellen umgestellt%s' % (umgestellt,
                                        '' if schreiben else ' (Probelauf)'))
    print('%d Stellen brauchen Handarbeit:' % len(offen))
    for pfad, nummer, text in offen:
        print('  %s:%d  %s' % (pfad, nummer, text))


if __name__ == '__main__':
    main()
