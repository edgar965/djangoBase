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
Ein Baum von der Wurzel abwaerts — genau das Bild, das die Frage
beantwortet: „hast du eine Basisklasse, und alles andere geht wie ein Baum
davon ab?" Wer viel haelt, steht oben; was gehalten wird, darunter.

Die Kinder eines Kastens stehen NICHT in einer Zeile, sondern in einem
ungefaehr quadratischen Block (24.08.2026, auf Ansage: „nicht alles in
einer Zeile … höhe und breite gleichermassen genutzt"). Vorher ergab
`PersonDetector` mit vierzehn gehaltenen Klassen ein Bild von 3500 Punkten
Breite bei 500 Hoehe: Man scrollte quer und sah nie mehr als ein Drittel.

Jeder Ast wird von unten nach oben vermessen und der Halter ueber der
Mitte seines Blocks abgesetzt. Kein Kraeftemodell und keine
Kantenglaettung: Beides braucht Iterationen und macht das Ergebnis von
Zufall abhaengig.
"""
from html import escape

#: Masse eines Kastens.
BREITE = 190
KOPF = 26
ZEILE = 16
RAND = 8

#: Abstaende zwischen den Aesten.
ABSTAND_X = 34
ABSTAND_Y = 62
#: Luft am Bildrand.
RAHMEN = 40

#: Die gesuchte Form des Bildes: breiter als hoch, wie ein Bildschirm.
ZIEL_VERHAELTNIS = 1.55

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
    u"""Ordnet Kästen in Ebenen an und schreibt das SVG."""

    def __init__(self, kaesten, linien, wurzel=None, steckbriefe=None):
        self.klassen = {k.name: k for k in kaesten}
        self.linien = linien
        self.wurzel = wurzel or (kaesten[0].name if kaesten else None)
        self.plaetze = {}
        #: ``{name: steckbrief}`` — fuer Hover-Text und Popup. Optional:
        #: Ohne sie zeigt der Hover nur Name und Fundstelle wie bisher.
        self.steckbriefe = steckbriefe or {}

    # ── Anordnung: ein echter Baum ──────────────────────────────
    def _baum(self):
        u"""Wer haengt unter wem — jede Klasse bekommt GENAU einen Platz.

        Eine Klasse kann von mehreren gehalten werden (`Lock` haengt an
        drei Stellen). Im Bild darf sie trotzdem nur einmal stehen, sonst
        gaebe es zwei Kaesten mit demselben Namen. Sie bekommt den Platz
        unter dem ERSTEN Halter, den der Weg von der Wurzel aus erreicht;
        die uebrigen Linien laufen quer dorthin.
        """
        gehalten = {}
        for linie in self.linien:
            gehalten.setdefault(linie.von, []).append(linie.nach)
        kinder = {name: [] for name in self.klassen}
        vergeben = {self.wurzel} if self.wurzel else set()
        rand = [self.wurzel] if self.wurzel else []
        while rand:
            naechste = []
            for name in rand:
                for ziel in sorted(set(gehalten.get(name, []))):
                    if ziel in vergeben or ziel not in self.klassen:
                        continue
                    vergeben.add(ziel)
                    kinder[name].append(ziel)
                    naechste.append(ziel)
            rand = naechste
        # Was von der Wurzel aus nicht erreichbar ist, haengt als eigener
        # Strauss unter ihr — es gehoert zum Ausschnitt, aber nicht zum Baum.
        rest = [n for n in sorted(self.klassen) if n not in vergeben]
        if rest and self.wurzel:
            kinder[self.wurzel].extend(rest)
        return kinder

    @staticmethod
    def _spalten(masse):
        u"""Wie viele Kinder nebeneinander, bevor umgebrochen wird?

        DIE ANSAGE (Edgar, 24.08.2026)
        ==============================
            „mach die Klassenstruktur geordneter, nicht alles in einer
             Zeile, möglichst als Ast und höhe und breite gleichermassen
             genutzt"

        Gerechnet wird mit den GEMESSENEN Massen der Kinder, nicht mit
        einer angenommenen Kastengroesse. Ein Kasten ist je nach Zahl
        seiner Felder 110 bis 190 hoch — wer mit einem festen Wert rechnet,
        liegt um die Haelfte daneben und bekommt wieder ein schlauchfoermiges
        Bild.

        Nachgemessen an `PersonDetector` (14 gehaltene Klassen)::

            eine Zeile                    3500 x  500   quer, unbrauchbar
            Wurzel aus der Anzahl          718 x 1394   hoch, unbrauchbar
            feste Kastenhoehe (110)        942 x 1210   noch zu hoch
            gemessene Masse                             passt

        Durchprobiert werden alle Spaltenzahlen; genommen wird die, deren
        Block dem `ZIEL_VERHAELTNIS` am naechsten kommt. Bei zwanzig
        Kindern sind das zwanzig Rechnungen — nicht der Rede wert.
        """
        anzahl = len(masse)
        if anzahl <= 3:
            return anzahl or 1
        beste, abstand = anzahl, None
        for spalten in range(2, anzahl + 1):
            reihen = [masse[i:i + spalten]
                      for i in range(0, anzahl, spalten)]
            breite = max(sum(b for b, _h in r) + ABSTAND_X * (len(r) - 1)
                         for r in reihen)
            hoehe = (sum(max(h for _b, h in r) for r in reihen)
                     + ABSTAND_Y * (len(reihen) - 1))
            if hoehe <= 0:
                continue
            weit = abs(breite / hoehe - ZIEL_VERHAELTNIS)
            if abstand is None or weit < abstand:
                beste, abstand = spalten, weit
        return beste

    def _masse_ast(self, name, kinder, gesehen=None):
        u"""``(Breite, Hoehe)`` des ganzen Astes unter `name`."""
        gesehen = gesehen if gesehen is not None else set()
        if name in gesehen:
            return (BREITE, 0)
        gesehen.add(name)
        eigen_h = Kasten(self.klassen[name], 0, 0).hoehe
        meine = kinder.get(name) or []
        if not meine:
            return (BREITE, eigen_h)
        reihen = self._reihen(meine, kinder, gesehen)
        block_b = max(sum(b for b, _h in r) + ABSTAND_X * (len(r) - 1)
                      for r in reihen)
        block_h = (sum(max(h for _b, h in r) for r in reihen)
                   + ABSTAND_Y * (len(reihen) - 1))
        return (max(BREITE, block_b), eigen_h + ABSTAND_Y + block_h)

    def _reihen(self, meine, kinder, gesehen):
        u"""Die Kinder in Reihen aufteilen, je mit ihren Astmassen."""
        masse = [self._masse_ast(k, kinder, gesehen) for k in meine]
        spalten = self._spalten(masse)
        return [masse[i:i + spalten] for i in range(0, len(masse), spalten)]

    def _setzen(self, name, x, y, kinder, gesehen):
        u"""Den Ast ab `name` an die Stelle (x, y) legen."""
        if name in gesehen:
            return
        gesehen.add(name)
        breite, _hoehe = self._masse_ast(name, kinder, set())
        kasten = Kasten(self.klassen[name],
                        x=x + (breite - BREITE) / 2, y=y)
        self.plaetze[name] = kasten
        meine = [k for k in (kinder.get(name) or []) if k not in gesehen]
        if not meine:
            return
        alle_masse = [self._masse_ast(k, kinder, set()) for k in meine]
        spalten = self._spalten(alle_masse)
        oben = y + kasten.hoehe + ABSTAND_Y
        for anfang in range(0, len(meine), spalten):
            reihe = meine[anfang:anfang + spalten]
            masse = [self._masse_ast(k, kinder, set()) for k in reihe]
            reihe_b = sum(b for b, _h in masse) + ABSTAND_X * (len(reihe) - 1)
            links = x + (breite - reihe_b) / 2
            for kind, (kb, _kh) in zip(reihe, masse):
                self._setzen(kind, links, oben, kinder, gesehen)
                links += kb + ABSTAND_X
            oben += max(h for _b, h in masse) + ABSTAND_Y

    def anordnen(self):
        if not self.klassen:
            return self
        kinder = self._baum()
        start = (self.wurzel if self.wurzel in self.klassen
                 else sorted(self.klassen)[0])
        self._setzen(start, RAHMEN, RAHMEN, kinder, set())
        # Was der Baum nicht erreicht hat (Ringe): rechts daneben.
        offen = [n for n in sorted(self.klassen) if n not in self.plaetze]
        if offen:
            x = max(k.x + BREITE for k in self.plaetze.values()) + ABSTAND_X
            y = RAHMEN
            for name in offen:
                k = Kasten(self.klassen[name], x, y)
                self.plaetze[name] = k
                y += k.hoehe + ABSTAND_Y
        return self

    def masse(self):
        if not self.plaetze:
            return (400, 200)
        breite = max(k.x + BREITE for k in self.plaetze.values()) + RAHMEN
        hoehe = max(k.y + k.hoehe for k in self.plaetze.values()) + RAHMEN
        return (int(breite), int(hoehe))

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
            '<marker id="km-hält" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" fill="var(--km-strich,#7aa2c8)"/>'
            '</marker></defs>')

    def _hovertext(self, klasse):
        u"""Was beim Zeigen erscheint — beide Richtungen der Beziehung.

        DIE ANSAGE (Edgar, 24.08.2026)
        ==============================
            „kannst du bei den Klassen im Hover und bei Klick darauf (Popup)
             eigenschaften zeigen, wie: Von wem genutzt, und welche
             Unterklassen (als Instanzen) als Member"

        Die Linien im Bild zeigen nur nach unten: was eine Klasse haelt.
        Die Gegenrichtung — WER haelt sie — ist im Bild oft gar nicht zu
        sehen, weil der Halter ausserhalb der gezeigten Nachbarschaft liegt.
        """
        s = self.steckbriefe.get(klasse.name)
        zeilen = ['%s   (%s:%d)' % (klasse.name, klasse.datei, klasse.zeile)]
        if not s:
            return escape(chr(10).join(zeilen))
        if s['genutzt_von']:
            zeilen.append('genutzt von: ' + ', '.join(
                '%s.%s' % (g['von'], g['feld']) for g in s['genutzt_von'][:6]))
        else:
            zeilen.append('genutzt von: niemandem')
        if s['haelt']:
            zeilen.append('hält: ' + ', '.join(
                '%s = %s (%s)' % (h['feld'], h['klasse'], h['viel'])
                for h in s['haelt'][:6]))
        if s['beerbt_von']:
            zeilen.append('beerbt von: ' + ', '.join(s['beerbt_von'][:6]))
        if s['basen']:
            zeilen.append('erbt von: ' + ', '.join(s['basen']))
        zeilen.append('%d Felder, %d Methoden'
                      % (len(s['felder']), s['methodenzahl']))
        return escape(chr(10).join(zeilen))

    def _kasten(self, k):
        h = k.hoehe
        n = escape(k.klasse.name)
        raus = ['<g class="km-kasten" data-km-klasse="%s">' % n,
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
        raus.append('<title>%s</title>' % self._hovertext(k.klasse))
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
