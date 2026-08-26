# -*- coding: utf-8 -*-
"""Findet in ES-Modulen Bezeichner, die nirgends deklariert und nicht importiert sind.

WARUM (16.08.2026): Beim Aufteilen von tracks.js blieb `const ss = sharedState;`
in der Quelldatei zurueck, waehrend zwei herausgeloeste Module `ss.` weiter
benutzten. `node --input-type=module --check` prueft nur die Grammatik und meldet
das NICHT — der Fehler kam erst im Browser als `ReferenceError: ss is not
defined`, und zwar nur, wenn man ein Projekt mit Clips laedt. Ein Ladetest haette
ihn uebersehen.

Das Werkzeug ist bewusst grob: es zerlegt kein vollstaendiges JavaScript, sondern
sammelt alle Deklarationsformen per Muster und meldet den Rest. Fehlalarme sind
eingeplant und werden von Hand geprueft — ein uebersehener echter Fehler ist
teurer als ein Blick auf eine Handvoll harmloser Namen.

GRENZE — hier hilft nur der Browser: Das Werkzeug kennt keine
Sichtbarkeitsbereiche. Ein Name gilt als bekannt, sobald er IRGENDWO in der
Datei deklariert wird. Beim Zerlegen von `renderTimeline` in Methoden wurde
`w` (die Leinwandbreite) nur an eine davon als Parameter uebergeben; die beiden
anderen benutzten es weiter und bekamen zur Laufzeit `w is not defined`. Der
Scanner sah `w` in der Parameterliste der ersten Methode und schwieg.
Fuer eine Sichtbarkeitsanalyse braucht es einen echten Parser — bis dahin
bleibt der Funktionstest im Browser das letzte Netz.

ZWEITE GRENZE — KLASSISCHE SKRIPTE (17.08.2026): Eine Datei ohne `import` und
ohne `export` ist kein ES-Modul. Wird sie als `<script src=…>` geladen, teilt sie
ihren Namensraum mit den Geschwisterdateien: `bvh_ersatzskelett.js` definiert
`class Ersatzskelett`, `bvh_viewer.js` ruft `Ersatzskelett.zeichnen(…)` — beide
stehen in `job_status.html` in dieser Reihenfolge, und es funktioniert. Der
Scanner meldete das als Fehler. Solche Dateien werden deshalb uebersprungen und
in der Zusammenfassung gezaehlt; wer sie wirklich pruefen will, nennt sie
einzeln als Argument.

DRITTE GRENZE — die Muster kennen drei Formen nicht (an echten Dateien gesehen):
verschachtelte Zerlegung (`for (const [a, [b, c]] of …)`), Klassenmethoden, die
per `this.name()` gerufen werden, und Parameter mit Vorgabewert
(`async laufen(frage = {}, faelle = …)`). Alle drei sahen wie unbekannte Namen
aus. Wer die Ausgabe liest, prueft jeden Treffer an der Zeile — die Liste ist ein
Hinweis, kein Urteil.

Aufruf:  python -m djangobase.umbau.unbekanntenamen <ordner> [<ordner> ...]
"""
import re
import sys
from pathlib import Path


from .codesicht import Codesicht
from .kommateilung import Kommateilung

#: Bezeichner, die es in jeder Browser-Umgebung gibt.
GLOBAL = set("""
window document console navigator location history localStorage sessionStorage
fetch FormData Headers Request Response URL URLSearchParams Blob File FileReader
setTimeout clearTimeout setInterval clearInterval requestAnimationFrame
cancelAnimationFrame queueMicrotask structuredClone alert confirm prompt
Math JSON Object Array String Number Boolean Symbol BigInt Date RegExp Error
TypeError RangeError SyntaxError ReferenceError Promise Map Set WeakMap WeakSet
Proxy Reflect Intl parseInt parseFloat isNaN isFinite encodeURIComponent
decodeURIComponent encodeURI decodeURI globalThis undefined NaN Infinity
Float32Array Float64Array Uint8Array Uint16Array Uint32Array Int8Array Int16Array
Int32Array Uint8ClampedArray ArrayBuffer DataView TextEncoder TextDecoder
Image Audio AudioContext webkitAudioContext ResizeObserver MutationObserver
MediaRecorder OffscreenCanvas ImageData Path2D CanvasRenderingContext2D
IntersectionObserver Event CustomEvent MouseEvent KeyboardEvent DragEvent
WebSocket Worker AbortController Element HTMLElement HTMLCanvasElement Node
NodeList performance crypto atob btoa this arguments super import
getComputedStyle PerformanceObserver Option DOMParser XMLHttpRequest
matchMedia scrollTo scrollBy open close print focus blur getSelection
HTMLImageElement HTMLInputElement HTMLSelectElement HTMLTextAreaElement
HTMLFormElement HTMLVideoElement HTMLAudioElement DocumentFragment
CSS WeakRef FinalizationRegistry Notification Range Text Comment
""".split())
#: NACHTRAG (17.08.2026): Die ersten drei Zeilen kamen aus echten Fehlalarmen —
#: `getComputedStyle` (2x), `PerformanceObserver` und `Option` wurden als
#: „nirgends deklariert" gemeldet. Ein Pruefer, der Standard-Globale des Browsers
#: nicht kennt, macht aus jedem sauberen Modul einen Befund; wer die Liste
#: erweitert, prueft danach an einer Datei, dass der Treffer verschwindet UND
#: dass ein echter Fall (Tippfehler im Namen) weiter rot wird.

#: Schluesselwoerter, die wie Bezeichner aussehen.
SCHLUESSEL = set("""
if else for while do switch case default break continue return function class
const let var new delete typeof instanceof in of void yield await async try
catch finally throw extends static get set null true false this super import
export from as with debugger
""".split())

#: Woerter, hinter denen eine Klammer KEINE Parameterliste ist.
STEUERWORTE = {'if', 'while', 'for', 'switch', 'catch', 'return', 'typeof', 'with'}

BEZEICHNER = re.compile(r'[A-Za-z_$][\w$]*')


class Modulnamen:
    """Deklarierte und benutzte Namen einer Moduldatei."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.quelle = self.pfad.read_text(encoding='utf-8')
        self.code = self._ohne_kommentare_und_texte(self.quelle)

    @staticmethod
    def _ohne_kommentare_und_texte(text):
        """Kommentare und Zeichenkettenrumpf entfernen (siehe Codesicht).

        Danach noch die Zahlen: sonst liest der Scanner `0x1a1a2e` als Namen
        `x1a1a2e`. Fehlalarm aus dem ersten Lauf.
        """
        text = Codesicht(text).code
        text = re.sub(r'\b0[xXbBoO][0-9a-fA-F_]+n?', ' ', text)
        return re.sub(r'\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?n?', ' ', text)

    def importiert(self):
        namen = set()
        for m in re.finditer(r'import\s+([\s\S]*?)\s+from\s', self.code):
            teil = m.group(1)
            for inner in re.findall(r'\{([^}]*)\}', teil):
                for stueck in inner.split(','):
                    stueck = stueck.strip()
                    if not stueck:
                        continue
                    namen.add(stueck.split(' as ')[-1].strip())
            teil = re.sub(r'\{[^}]*\}', '', teil)
            for stueck in teil.split(','):
                stueck = stueck.strip()
                if stueck.startswith('*'):
                    namen.add(stueck.split(' as ')[-1].strip())
                elif stueck and BEZEICHNER.fullmatch(stueck):
                    namen.add(stueck)
        return namen

    def deklariert(self):
        namen = set()
        c = self.code
        for muster in (r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)',
                       r'\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)',
                       r'\bclass\s+([A-Za-z_$][\w$]*)',
                       # Statisches Klassenfeld: `static camera = null;`
                       r'(?m)^\s*static\s+([A-Za-z_$][\w$]*)\s*=',
                       r'\bcatch\s*\(\s*([A-Za-z_$][\w$]*)'):
            namen.update(re.findall(muster, c))
        # Mehrfachdeklaration mit und ohne Startwert: `let a, b;` / `let cy = 0, cz = 0;`
        # Je Komma-Abschnitt zaehlt nur der fuehrende Bezeichner.
        # Bis zum Semikolon, nicht bis zum Zeilenende: `const R = …,\n  B = …;`
        # stand in licht.js ueber zwei Zeilen, `B` galt darum als unbekannt.
        for m in re.finditer(r'\b(?:const|let|var)\s+([^;{}]{0,400})', c):
            for abschnitt in Kommateilung.teile(m.group(1)):
                kopf = BEZEICHNER.match(abschnitt.strip())
                if kopf:
                    namen.add(kopf.group(0))
        # Zerlegung: const { a, b: c } = …   /   const [a, b] = …
        for m in re.finditer(r'\b(?:const|let|var)\s*[\{\[]([^\}\]]*)[\}\]]'
                             r'\s*(?:=|\bof\b|\bin\b)', c):
            teil = m.group(1)
            for stueck in teil.split(','):
                stueck = stueck.strip()
                if ':' in stueck:
                    stueck = stueck.split(':')[-1]
                stueck = stueck.split('=')[0].strip().lstrip('.')
                if BEZEICHNER.fullmatch(stueck or ''):
                    namen.add(stueck)
        # Parameterlisten (Pfeil, Funktion, Methode) — grob, dafuer vollstaendig
        for muster in (r'\(([^()]*)\)\s*=>', r'([A-Za-z_$][\w$]*)\s*=>',
                       r'\bfunction\s*\*?\s*[A-Za-z_$\w$]*\s*\(([^()]*)\)'):
            for m in re.finditer(muster, c):
                namen.update(BEZEICHNER.findall(m.group(1)))
        # Methodendefinition: `name(a, b) {` — Name UND Parameter zaehlen.
        # Steuerwoerter ausnehmen: Sonst gilt in `if (state._x) {` der Name
        # `state` als Parameter und damit als deklariert. Genau so blieb ein
        # fehlender `state`-Import in teilnetz_auswahl.js unbemerkt (16.08.2026).
        for m in re.finditer(r'(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(([^()]*)\)\s*\{', c):
            if m.group(1) in STEUERWORTE:
                continue
            namen.add(m.group(1))
            namen.update(BEZEICHNER.findall(m.group(2)))
        return namen

    def benutzt(self):
        """Bezeichner, die als Wert gelesen werden (nicht als Eigenschaft).

        Import- und Export-Zeilen bleiben aussen vor: `import { X as M }` nennt
        `X`, benutzt es aber nicht — sonst meldet der Scanner jeden umbenannten
        Import als unbekannt.
        """
        namen = set()
        rumpf = re.sub(r'(?ms)^\s*import\b.*?(?:;|$)', ' ', self.code)
        # Nur das Weiterreichen entfernen; `export { X };` benutzt die oertliche
        # Bindung und darf mitgeprueft werden.
        rumpf = re.sub(r'(?m)^\s*export\s*\{[^}]*\}\s*from[^;\n]*;?', ' ', rumpf)
        for m in BEZEICHNER.finditer(rumpf):
            name = m.group(0)
            vorher = rumpf[max(0, m.start() - 2):m.start()]
            if vorher.rstrip().endswith('.') or vorher.rstrip().endswith('?.'):
                continue                      # Eigenschaftszugriff
            nachher = rumpf[m.end():m.end() + 2].lstrip()
            if nachher.startswith(':') and Modulnamen._objektschluessel(rumpf, m.start()):
                continue                      # Objektschluessel
            namen.add(name)
        return namen

    @staticmethod
    def _objektschluessel(text, pos):
        """Steht hier wirklich ein Objektschluessel — oder ein Fragezeichenausdruck?

        `{ farbe: rot }` ist ein Schluessel, `a ? ROT : BLAU` nicht. Beide haben
        einen Doppelpunkt hinter dem Namen. Entscheidend ist, was DAVOR steht:
        Ein Schluessel folgt auf `{`, ein Komma oder einen Zeilenanfang.

        BEFUND 16.08.2026: Ohne diese Unterscheidung galt `VE_COLOR_SELECTED` in
        `const c = auswahl.has(i) ? VE_COLOR_SELECTED : VE_COLOR_DEFAULT;` als
        Objektschluessel — also als gar nicht benutzt. Der fehlende Import fiel
        deshalb erst im Browser auf.
        """
        davor = text[:pos].rstrip()
        return not davor or davor[-1] in '{,;'

    def unbekannt(self):
        bekannt = self.importiert() | self.deklariert() | GLOBAL | SCHLUESSEL
        return sorted(n for n in self.benutzt() if n not in bekannt)


#: Diese Dateien werden beim Ordnerlauf uebersprungen.
#:
#: WARUM (17.08.2026): Der erste Lauf ohne Argumente meldete
#: `chart.umd.min.js  $animations, Ct, Dt, Nt, On` — in einer minifizierten
#: Fremdbibliothek sind einbuchstabige Namen der Normalfall und kein Befund. Wer
#: fremden, gebauten Code prueft, erzeugt nur Rauschen; die eigenen Module gehen
#: darin unter.
FREMD = ('vendor', 'node_modules', 'dist', 'bundle', 'staticfiles',
         'theatre', 'theatre-studio')


def eigene_dateien(ordner):
    u"""Alle eigenen .js-Dateien unter den Ordnern — ohne Fremd- und Baucode."""
    for o in ordner:
        for pfad in sorted(o.rglob('*.js')):
            if any(teil in FREMD for teil in pfad.parts):
                continue
            if '.min.' in pfad.name:
                continue
            yield pfad


MODULMERKMAL = re.compile(r'(?m)^\s*(?:import|export)\b')


def ist_esmodul(text):
    u"""Hat die Datei `import` oder `export` auf oberster Ebene?

    Wenn nicht, ist sie ein klassisches Skript und teilt ihren Namensraum mit den
    anderen `<script src=…>` derselben Seite — dann sagt „Name nicht deklariert"
    nichts (siehe ZWEITE GRENZE im Modulkopf).
    """
    return bool(MODULMERKMAL.search(text))


def main():
    ordner = [Path(a) for a in sys.argv[1:]] or [Path('.')]
    einzeln = [p for p in ordner if p.is_file()]
    dateien = einzeln or list(eigene_dateien(ordner))
    treffer, klassisch = 0, 0
    for p in dateien:
        if not einzeln and not ist_esmodul(p.read_text(encoding='utf-8',
                                                       errors='replace')):
            klassisch += 1
            continue
        offen = Modulnamen(p).unbekannt()
        if offen:
            treffer += 1
            print('%-52s %s' % (p.as_posix(), ', '.join(offen[:12])))
    print('\n%d Dateien geprüft, %d mit unbekannten Namen'
          % (len(dateien) - klassisch, treffer))
    if klassisch:
        print('%d klassische Skripte übersprungen (kein import/export — ihre '
              'Namen kommen aus Geschwisterdateien). Einzeln als Argument '
              'nennen, um sie doch zu prüfen.' % klassisch)


if __name__ == '__main__':
    main()
