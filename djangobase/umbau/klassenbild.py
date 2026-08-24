# -*- coding: utf-8 -*-
u"""Das Klassenmodell als SVG — Kaesten, Linien, Vielfachheiten.

WARUM SELBST GEZEICHNET (24.08.2026)
====================================
Im Projekt liegt keine Zeichen-Bibliothek: kein Mermaid, kein d3, kein
Graphviz. Eine nachzuladen hiesse, fuer ein Bild eine Abhaengigkeit ins
Haus zu holen, die offline nicht laedt und beim naechsten Umbau gepflegt
werden will.

SVG von Hand ist hier billiger, als es klingt: Kaesten sind Rechtecke,
Beziehungen sind Linien, und die Anordnung ist ein Baum. Das Ergebnis
laeuft ohne Netz, laesst sich vergroessern ohne zu verpixeln und mit
Rechtsklick speichern.

DIE ANORDNUNG
=============
Nach EBENEN, von der Wurzel abwaerts — genau das Bild, das die Frage
beantwortet: „hast du eine Basisklasse, und alles andere geht wie ein Baum
davon ab?" Wer viel haelt, steht oben; was gehalten wird, darunter.

Kein Kraeftemodell und keine Kantenglaettung: Beides braucht Iterationen
und macht das Ergebnis von Zufall abhaengig. Bei einer Nachbarschaft von
zwanzig Kaesten reicht die Ebene.
"""
from html import escape

#: Masse eines Kastens.
BREITE = 190
KOPF = 26
ZEILE = 16
RAND = 8

#: Abstaende im Raster.
SPALTE = 250
EBENE = 190

#: Hoechstens so viele Eintraege je Abteil — darunter wird gekuerzt.
MAX_FELDER = 5
MAX_METHODEN = 4


class Kasten:
    u"""Eine Klasse mit ihrem Platz im Bild."""

    __slots__ = ('klasse', 'x', 'y', 'felder', 'methoden')

    def __init__(self, klasse, x, y):
        self.klasse = klasse
        self.x = x
        self.y = y
        self.felder = klasse.felder[:MAX_FELDER]
        self.methoden = klasse.methoden[:MAX_METHODEN]

    @property
    def hoehe(self):
        zeilen = max(1, len(self.felder)) + max(1, len(self.methoden))
        return KOPF + zeilen * ZEILE + 2 * RAND

    @property
    def mitte_x(self):
        return self.x + BREITE / 2


class Klassenbild:
    u"""Ordnet Kaesten in Ebenen an und schreibt das SVG."""

    def __init__(self, kaesten, linien, wurzel=None):
        self.klassen = {k.name: k for k in kaesten}
        self.linien = linien
        self.wurzel = wurzel or (kaesten[0].name if kaesten else None)
        self.plaetze = {}

    # ── Anordnung ───────────────────────────────────────────────
    def _ebenen(self):
        u"""Wer haelt wen — daraus die Ebene. Die Wurzel steht oben."""
        tiefe = {self.wurzel: 0} if self.wurzel else {}
        rand = [self.wurzel] if self.wurzel else []
        gehalten = {}
        for linie in self.linien:
            gehalten.setdefault(linie.von, []).append(linie.nach)
        while rand:
            naechste = []
            for name in rand:
                for ziel in gehalten.get(name, []):
                    if ziel not in tiefe:
                        tiefe[ziel] = tiefe[name] + 1
                        naechste.append(ziel)
            rand = naechste
        # Was von der Wurzel aus nicht erreichbar ist, kommt in die letzte
        # Ebene — es gehoert zum Ausschnitt, haengt aber nicht am Baum.
        tiefste = max(tiefe.values()) if tiefe else 0
        for name in self.klassen:
            tiefe.setdefault(name, tiefste + 1)
        return tiefe

    def anordnen(self):
        tiefe = self._ebenen()
        je_ebene = {}
        for name in sorted(self.klassen, key=lambda n: (tiefe[n], n)):
            je_ebene.setdefault(tiefe[name], []).append(name)
        for ebene, namen in je_ebene.items():
            for i, name in enumerate(namen):
                self.plaetze[name] = Kasten(self.klassen[name],
                                            x=40 + i * SPALTE,
                                            y=40 + ebene * EBENE)
        return self

    def masse(self):
        if not self.plaetze:
            return (400, 200)
        breite = max(k.x + BREITE for k in self.plaetze.values()) + 60
        hoehe = max(k.y + k.hoehe for k in self.plaetze.values()) + 60
        return (breite, hoehe)

    # ── Zeichnen ────────────────────────────────────────────────
    def svg(self):
        self.anordnen()
        breite, hoehe = self.masse()
        teile = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" class="km-bild">' % (breite, hoehe, breite, hoehe),
            self._muster(),
            '<rect width="100%" height="100%" fill="var(--km-grund,#12161c)"/>',
        ]
        # Linien zuerst: Sie liegen hinter den Kaesten.
        for linie in self.linien:
            teile.append(self._linie(linie))
        for kasten in self.plaetze.values():
            teile.append(self._kasten(kasten))
        teile.append('</svg>')
        return '\n'.join(t for t in teile if t)

    @staticmethod
    def _muster():
        u"""Der Vererbungspfeil: ein hohles Dreieck, wie in UML ueblich."""
        return (
            '<defs><marker id="km-erbt" viewBox="0 0 12 12" refX="11" '
            'refY="6" markerWidth="11" markerHeight="11" orient="auto">'
            '<path d="M0,0 L12,6 L0,12 z" fill="var(--km-grund,#12161c)" '
            'stroke="var(--km-strich,#7aa2c8)" stroke-width="1.2"/>'
            '</marker>'
            '<marker id="km-haelt" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" fill="var(--km-strich,#7aa2c8)"/>'
            '</marker></defs>')

    def _kasten(self, k):
        h = k.hoehe
        n = escape(k.klasse.name)
        raus = ['<g class="km-kasten">',
                '<rect x="%d" y="%d" width="%d" height="%d" rx="3" '
                'fill="var(--km-fuell,#1b2129)" '
                'stroke="var(--km-strich,#7aa2c8)" stroke-width="1.2"/>'
                % (k.x, k.y, BREITE, h),
                '<text x="%d" y="%d" text-anchor="middle" class="km-name" '
                'fill="var(--km-text,#e6edf3)" font-size="13" '
                'font-weight="600">%s</text>'
                % (k.mitte_x, k.y + 18, n)]
        y = k.y + KOPF
        raus.append(self._trenner(k, y))
        for feld in k.felder:
            y += ZEILE
            raus.append(self._zeile(k, y, feld.zeile))
        if not k.felder:
            y += ZEILE
        rest = len(k.klasse.felder) - len(k.felder)
        if rest > 0:
            raus.append(self._zeile(k, y, '… %d weitere' % rest, matt=True))
        y += RAND
        raus.append(self._trenner(k, y))
        for name in k.methoden:
            y += ZEILE
            raus.append(self._zeile(k, y, '+ %s()' % escape(name)))
        raus.append('<title>%s — %s:%d</title>'
                    % (n, escape(k.klasse.datei), k.klasse.zeile))
        raus.append('</g>')
        return '\n'.join(raus)

    @staticmethod
    def _trenner(k, y):
        return ('<line x1="%d" y1="%d" x2="%d" y2="%d" '
                'stroke="var(--km-strich,#7aa2c8)" stroke-width="0.8"/>'
                % (k.x, y, k.x + BREITE, y))

    @staticmethod
    def _zeile(k, y, text, matt=False):
        farbe = 'var(--km-matt,#8b98a5)' if matt else 'var(--km-text,#e6edf3)'
        return ('<text x="%d" y="%d" font-size="11" fill="%s">%s</text>'
                % (k.x + RAND, y, farbe, escape(text)[:30]))

    def _linie(self, linie):
        a = self.plaetze.get(linie.von)
        b = self.plaetze.get(linie.nach)
        if not a or not b:
            return ''
        x1, y1 = a.mitte_x, a.y + a.hoehe
        x2, y2 = b.mitte_x, b.y
        if b.y < a.y:                     # Ziel liegt hoeher: oben heraus
            y1, y2 = a.y, b.y + b.hoehe
        erbt = linie.art == 'erbt'
        raus = ['<path d="M%.0f,%.0f L%.0f,%.0f" fill="none" '
                'stroke="var(--km-strich,#7aa2c8)" stroke-width="1.1" %s '
                'marker-end="url(#%s)"/>'
                % (x1, y1, x2, y2,
                   'stroke-dasharray="4 3"' if erbt else '',
                   'km-erbt' if erbt else 'km-haelt')]
        if not erbt:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if linie.name:
                raus.append('<text x="%.0f" y="%.0f" font-size="10" '
                            'fill="var(--km-matt,#8b98a5)" '
                            'text-anchor="middle">%s</text>'
                            % (mx, my - 4, escape(linie.name)[:18]))
            raus.append('<text x="%.0f" y="%.0f" font-size="10" '
                        'fill="var(--km-matt,#8b98a5)">%s</text>'
                        % (x2 + 6, y2 - 5, escape(linie.vielfachheit)))
        return '\n'.join(raus)


__all__ = ['Klassenbild', 'Kasten']
