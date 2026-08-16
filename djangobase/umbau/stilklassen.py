# -*- coding: utf-8 -*-
u"""Statische `style="…"` durch CSS-Klassen ersetzen.

WARUM (Auftrag Punkt 15, 16.08.2026): 1.266 Inline-Stile in den Vorlagen. Sie
sind weder über ein Theme änderbar noch im Browser auffindbar, und dieselbe
Fassung steht bis zu 78-mal da.

WIE: Gleiche Fassungen werden EINE Klasse. Der Name kommt aus der Tabelle
`NAMEN` — sprechend, nicht generiert: `.hb-zelle` sagt etwas, `.u-17` nicht.
Alles, was dort nicht steht und seltener als `GRENZE` vorkommt, bleibt liegen;
ein Einzelfall in einer Vorlage ist kein Gewinn, wenn der Klassenname dann
`.hb-margin-top-3px-color-888` heißt.

WAS NICHT ANGEFASST WIRD:
* Werte mit `{{ }}`, `{% %}`, `${ }` — sie stehen erst zur Laufzeit fest.
* `style` in JavaScript-Zeichenketten (dort baut der Code HTML zusammen);
  diese Datei fasst nur Markup an, also `.html` ausserhalb von `<script>`.

PRUEFUNG: Eine CSS-Klasse hat eine niedrigere Spezifitaet als ein Inline-Stil.
Deshalb NACH dem Lauf im Browser die berechneten Stile vergleichen
(`djangobase/static/djangobase/js/stilmessung.js`) — nicht nur hinsehen.

Aufruf:  python -m djangobase.umbau.stilklassen <vorlage.html> [--schreiben]
"""
import re
import sys
from collections import Counter
from pathlib import Path

STIL = re.compile(r'\sstyle\s*=\s*"([^"]*)"')
DYNAMISCH = ('{{', '{%', '${')
#: Ab so vielen Vorkommen in EINER Datei lohnt eine eigene Klasse.
#:
#: Erst 3, dann 2 (16.08.2026): Nach dem ersten Durchgang blieben 689 Stellen,
#: die meisten davon Paare. Ein Paar lohnt die Klasse auch — es ist genau der
#: Fall „zweimal dasselbe von Hand gepflegt", den der Auftrag meint.
GRENZE = 2

#: Fassung (normalisiert) -> Klassenname. Sprechende Namen, kein Generat.
NAMEN = {
    'padding: 8px; border-bottom: 1px solid #333;': 'hb-zelle',
    'padding: 10px; text-align: left; border-bottom: 2px solid #444;':
        'hb-kopfzelle',
    'width:16px;': 'hb-symbolspalte',
    'flex:1;': 'hb-dehnt',
    'display:none;': 'hb-versteckt',
    'display:flex;': 'hb-reihe',
    'margin-top:1.5rem;': 'hb-abstand-oben',
    'margin-bottom:0;flex:1;': 'hb-dehnt-ohne-abstand',
    'height:1px;background:var(--border);margin:4px 0;': 'hb-trennlinie',
    'width:40px;height:24px;border:none;cursor:pointer;': 'hb-farbfeld',
    'flex:0 0 auto;padding:6px 10px;': 'hb-fest',
    'color:#888;': 'hb-gedaempft',
    'border-bottom:1px solid var(--border);': 'hb-untere-linie',
    'padding:12px;color:var(--text-muted);font-size:0.8rem;': 'hb-hinweis',
    'font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;'
    'color:var(--text-muted);': 'hb-ueberschrift-klein',
    'cursor:pointer;': 'hb-klickbar',
    'text-align:center;': 'hb-mittig',
    'margin:0;': 'hb-ohne-abstand',
    'width:100%;': 'hb-volle-breite',
    'font-size:0.8rem;': 'hb-klein',
    'font-size:0.75rem;': 'hb-kleiner',
    'color:var(--text-muted);': 'hb-gedaempft-theme',
    # --- aus bvh_studio.html (16.08.2026) ---
    'width:16px;color:#ffc107;': 'hb-symbolspalte-warn',
    'padding:7px 14px;font-size:0.82rem;color:#ccc;cursor:pointer;'
    'display:flex;align-items:center;gap:8px;': 'hb-menueeintrag',
    'margin-left:auto;font-size:0.7rem;color:var(--text-muted);':
        'hb-kuerzel',
    'font-size:0.65rem;': 'hb-winzig',
    'padding:3px 6px;background:var(--bg-card);border:1px solid var(--border);'
    'border-radius:3px;color:var(--text);font-size:0.75rem;': 'hb-eingabe-klein',
    'display:none;position:fixed;z-index:9999;background:var(--bg-secondary);'
    'border:1px solid var(--border);border-radius:6px;padding:4px 0;'
    'min-width:180px;box-shadow:0 8px 24px rgba(0,0,0,0.4);': 'hb-kontextmenue',
    'display:none;margin-top:6px;': 'hb-klappteil',
    'height:4px;background:var(--bg-card);border-radius:2px;overflow:hidden;':
        'hb-balken',
    'font-size:0.7rem;color:var(--text-muted);margin-top:3px;':
        'hb-untertitel',
    'font-size:0.85rem;color:var(--accent);margin-bottom:10px;':
        'hb-abschnittstitel',
    'font-size:0.7rem;color:var(--text-muted);margin-bottom:6px;'
    'line-height:1.4;': 'hb-erklaerung',
    'margin-bottom:6px;': 'hb-abstand-unten',
    'font-size:0.72rem;': 'hb-fein',
    'flex:1;font-size:0.72rem;': 'hb-dehnt-fein',
    'padding:3px 6px;background:var(--bg-card);border:1px solid var(--border);'
    'border-radius:3px;color:var(--text-muted);cursor:pointer;'
    'font-size:0.7rem;': 'hb-knopf-klein',
}


class Stilklassen:
    """Eine HTML-Datei und ihre Inline-Stile."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.text = self.pfad.read_text(encoding='utf-8')
        self.ersetzt = 0
        self.klassen = {}          # Fassung -> Name
        #: Vor dem Umbau erhoben — danach steht im Text kein `style` mehr.
        self.zaehler = self.fassungen()

    def fassungen(self):
        """Statische Fassungen dieser Datei, nach Haeufigkeit."""
        zaehler = Counter()
        for wert in STIL.findall(self.text):
            gestrafft = ' '.join(wert.split()).strip()
            # Leeres `style=""` ist nichts, was eine Klasse braucht.
            if not gestrafft.strip(';'):
                continue
            if any(marke in gestrafft for marke in DYNAMISCH):
                continue
            zaehler[gestrafft] += 1
        return zaehler

    def planen(self):
        """Welche Fassung bekommt welchen Klassennamen?

        Namen muessen EINDEUTIG sein: Zwei verschiedene Fassungen, die beide
        mit `display:none` beginnen, bekamen im ersten Wurf denselben Notnamen
        — die zweite Regel haette die erste ueberschrieben und Elemente still
        falsch dargestellt. Deshalb wird bei einer Kollision durchgezaehlt.
        """
        vergeben = set()
        for fassung, anzahl in self.zaehler.most_common():
            name = NAMEN.get(fassung)
            if not name:
                if anzahl < GRENZE:
                    continue
                name = self._name(fassung)
            if name in vergeben:
                grund = name
                nummer = 2
                while name in vergeben:
                    name = '%s-%d' % (grund, nummer)
                    nummer += 1
            vergeben.add(name)
            self.klassen[fassung] = name
        return self.klassen

    @staticmethod
    def _name(fassung):
        u"""Notname aus der ersten Eigenschaft — nur fuer haeufige Fassungen
        ohne Eintrag in NAMEN. Er ist lesbar genug, um ihn spaeter von Hand zu
        ersetzen, und eindeutig durch die Kurzfassung des Werts."""
        erste = fassung.split(';')[0]
        teil, _, wert = erste.partition(':')
        sauber = re.sub(r'[^a-z0-9]+', '-', (teil + '-' + wert).lower()).strip('-')
        return 'hb-' + sauber[:34]

    def umbauen(self):
        """style="…" durch class="…" ersetzen (bzw. an vorhandene anhaengen)."""
        def ersetzen(treffer):
            fassung = ' '.join(treffer.group(1).split())
            name = self.klassen.get(fassung)
            if not name:
                return treffer.group(0)
            self.ersetzt += 1
            return ' data-neueklasse="%s"' % name

        self.text = STIL.sub(ersetzen, self.text)
        self._klassen_einsetzen()
        return self

    def _klassen_einsetzen(self):
        u"""`data-neueklasse` in ein echtes `class`-Attribut ueberfuehren.

        Zwei Schritte, weil ein Element schon ein `class` haben kann: Erst
        markieren, dann zusammenfuehren. So bleibt die Reihenfolge der
        Attribute erhalten und nichts wird doppelt ersetzt.
        """
        # Fall A: class steht VOR der Markierung
        self.text = re.sub(
            r'class\s*=\s*"([^"]*)"([^<>]*?)\sdata-neueklasse="([^"]+)"',
            lambda t: 'class="%s %s"%s' % (t.group(1), t.group(3), t.group(2)),
            self.text)
        # Fall B: class steht DAHINTER
        self.text = re.sub(
            r'\sdata-neueklasse="([^"]+)"([^<>]*?)class\s*=\s*"([^"]*)"',
            lambda t: '%sclass="%s %s"' % (t.group(2), t.group(3), t.group(1)),
            self.text)
        # Fall C: kein class-Attribut
        self.text = re.sub(r'\sdata-neueklasse="([^"]+)"',
                           lambda t: ' class="%s"' % t.group(1), self.text)

    def css(self):
        """Die neuen Regeln — nach Klassenname sortiert, mit Fundzahl."""
        zaehler = self.zaehler
        zeilen = ['/* Umbau 16.08.2026: aus Inline-Stilen dieser Vorlage.',
                  '   Erzeugt von djangobase.umbau.stilklassen — gleiche',
                  '   Fassungen wurden zu einer Klasse zusammengefasst. */']
        for fassung, name in sorted(self.klassen.items(), key=lambda p: p[1]):
            regeln = '; '.join(t.strip() for t in fassung.split(';') if t.strip())
            # Der Klassenname steht ZWEIMAL im Selektor. Das ist kein
            # Tippfehler: Ein Inline-Stil schlaegt jede Regel; eine einfache
            # Klasse (0,0,1,0) schlaegt `.studio-properties h3` (0,0,1,1)
            # NICHT. Im Browser gemessen (16.08.2026): Die Abschnittstitel
            # verloren dabei ihre Akzentfarbe (rot -> grau) und 2px Abstand.
            # Und (0,0,2,0) reichte immer noch nicht: `.slider-row
            # input[type="color"]` ist (0,0,2,1) und gewann gegen die
            # Farbfelder der Szene. Also DREIMAL — (0,0,3,0). Kein
            # `!important`: das wuerde jede spaetere Anpassung blockieren.
            zeilen.append('.%s.%s.%s { %s; }   /* %dx */'
                          % (name, name, name, regeln, zaehler[fassung]))
        return '\n'.join(zeilen)

    def css_einsetzen(self):
        u"""Die neuen Regeln ans Ende des ersten <style>-Blocks setzen.

        Nicht in eine eigene Datei: Die Vorlagen dieses Projekts bringen ihr
        CSS selbst mit, und eine zusaetzliche Datei muesste eingebunden,
        versioniert und cache-gebustet werden — drei Gelegenheiten, es falsch
        zu machen, fuer nichts.
        """
        if '</style>' not in self.text:
            # Keine Vorlage ohne Stilblock stehen lassen: Einen anlegen. Sonst
            # muesste das CSS in eine eigene Datei, die eingebunden und
            # cache-gebustet werden will.
            treffer = re.search(r'\{%\s*block\s+content\s*%\}', self.text)
            if not treffer:
                raise ValueError('%s: weder <style> noch content-Block'
                                 % self.pfad)
            # ANS ENDE des Blocks, nicht an den Anfang: Ein zusaetzliches
            # Element am Anfang verschiebt die Position aller Geschwister im
            # DOM. Die Nachher-Messung (stil_messung.js) findet ihre Elemente
            # ueber den Positionspfad und meldete dadurch sechs
            # "Abweichungen", die keine waren.
            ende = self.text.rfind('{% endblock %}')
            stelle = ende if ende > treffer.end() else treffer.end()
            self.text = (self.text[:stelle] + '<style>\n</style>\n'
                         + self.text[stelle:])
        stelle = self.text.index('</style>')
        self.text = (self.text[:stelle] + '\n' + self.css() + '\n'
                     + self.text[stelle:])

    def schreiben(self):
        self.pfad.write_text(self.text, encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not argumente:
        print(__doc__)
        return
    schreiben = '--schreiben' in sys.argv
    for datei in argumente:
        vorlage = Stilklassen(datei)
        vorlage.planen()
        vorlage.umbauen()
        print('%s: %d Stellen -> %d Klassen%s'
              % (datei, vorlage.ersetzt, len(vorlage.klassen),
                 '' if schreiben else '  (Probelauf)'))
        if schreiben:
            vorlage.css_einsetzen()
            vorlage.schreiben()
        else:
            print(vorlage.css()[:600])


if __name__ == '__main__':
    main()
