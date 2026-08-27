# -*- coding: utf-8 -*-
u"""Einen Weg als SVG zeichnen — Kaesten, Bogen, Spalten nach Tiefe.

WARUM SELBST GEZEICHNET
=======================
Dieselbe Begruendung wie in ``klassenbild.py``: Im Projekt liegt keine
Zeichen-Bibliothek. Eine nachzuladen hiesse, fuer ein Bild eine
Abhaengigkeit ins Haus zu holen, die offline nicht laedt.

DIE ANORDNUNG: SPALTEN NACH ENTFERNUNG
======================================
Das Klassenbild ordnet nach Besitz und wird darum ein Baum von oben nach
unten. Ein Weg hat eine andere Form: Er laeuft. Links steht, womit es
anfaengt; jede Spalte weiter rechts ist ein Schritt weiter weg vom
Einstieg.

Das ist die Anordnung aus der Vorlage, die Edgar gezeigt hat (27.08.2026):
Karten in Spalten, dazwischen Bogen, und man liest von links nach rechts
wie einen Satz.

WARUM BOGEN UND KEINE GERADEN
=============================
Bei fuenfzig Kanten laufen Geraden durcheinander und man verliert die
Spur. Ein Bogen, der waagerecht aus dem Kasten austritt und waagerecht in
den naechsten eintritt, bleibt auch im Gedraenge verfolgbar — und
ueberdeckt keinen Kastentext, weil er ausserhalb der Spalten verlaeuft.

DIE FARBE SAGT, WIE SICHER DIE KANTE IST
========================================
    durchgezogen   ``name()``            — steht so im Code
    durchgezogen   ``self.feld.name()``  — Feldtyp im Code nachgelesen
    gestrichelt    ueber einen eindeutigen Methodennamen erschlossen

Wer dem Bild eine Kante nicht glaubt, sieht an der Linie, wie sie
zustande kam.
"""
from html import escape

#: Masse eines Kastens.
BREITE = 178
HOEHE = 40
#: Abstand zwischen zwei Spalten (Mitte zu Mitte).
SPALTE = 244
#: Abstand zwischen zwei Kaesten derselben Spalte.
ZEILE = 54
#: Luft am Bildrand.
RAHMEN = 28

#: Hoehe des Fussvermerks unter einem Bild, das nicht den ganzen Weg
#: zeigt. Siehe ``Workflowbild._abschluss``.
VERMERK = 26

#: Rueckfall fuer die Zeilenzahl, falls sich keine bessere findet.
MAX_JE_SPALTE = 14

#: Die gesuchte Form des Bildes: breiter als hoch, wie ein Bildschirm.
#: Dieselbe Zahl wie in ``klassenbild.py`` — aus demselben Grund.
ZIEL_VERHAELTNIS = 1.55

FARBEN = {
    'aufruf': '#38d4d8',
    'besitz': '#8b7bd8',
    'methode': '#7a8a99',
}


class Karte:
    u"""Ein Kasten mit seinem Platz im Bild."""

    __slots__ = ('schritt', 'x', 'y')

    def __init__(self, schritt, x, y):
        self.schritt = schritt
        self.x = x
        self.y = y

    @property
    def mitte_y(self):
        return self.y + HOEHE / 2.0

    @property
    def rechts(self):
        return self.x + BREITE


class Workflowbild:
    u"""Ein ``Weg`` als SVG.

        >>> Workflowbild(weg).svg()      # doctest: +SKIP
        '<svg ...>'
    """

    def __init__(self, weg):
        self.weg = weg
        self.karten = {}
        self.breite = 0
        self.hoehe = 0

    # ── Anordnen ────────────────────────────────────────────────

    def anordnen(self):
        u"""Je Tiefe ein Block, der umbricht statt in die Laenge zu gehen.

        EINE SPALTE JE TIEFE REICHT NICHT (27.08.2026)
        ==============================================
        Erster Versuch: eine Spalte je Tiefe, Kaesten untereinander.
        Gemessen an ``manage.py live_detect`` ergab das **966 mal 4214**
        Punkte — ein Streifen, bei dem man senkrecht scrollt und nie zwei
        Spalten zugleich sieht. Grund: In der Tiefe 2 stehen 45 Kaesten.

        Darum bricht ein Block jetzt in Unterspalten um, und die Zeilenzahl
        wird so gewaehlt, dass das Bild ungefaehr Bildschirmform bekommt —
        dieselbe Ueberlegung wie in ``klassenbild.py``, nur waagerecht.
        """
        spalten = {}
        for schritt in self.weg.schritte:
            spalten.setdefault(schritt.tiefe, []).append(schritt)
        if not spalten:
            self.breite = self.hoehe = RAHMEN * 2
            return self
        zeilen = self._zeilen_waehlen(spalten)
        x = RAHMEN
        hoechste = 0
        for tiefe in sorted(spalten):
            eintraege = sorted(spalten[tiefe],
                               key=lambda s: s.bezug.anzeige.lower())
            for stelle, schritt in enumerate(eintraege):
                unter, reihe = divmod(stelle, zeilen)
                self.karten[schritt.bezug.anzeige] = Karte(
                    schritt, x + unter * SPALTE, RAHMEN + reihe * ZEILE)
            unterspalten = max(1, -(-len(eintraege) // zeilen))
            x += unterspalten * SPALTE
            hoechste = max(hoechste, min(len(eintraege), zeilen))
        self.breite = int(x - SPALTE + BREITE + RAHMEN)
        self.hoehe = RAHMEN * 2 + max(hoechste, 1) * ZEILE
        # Platz fuer den Fussvermerk, wenn der Weg weitergeht als das Bild
        # (siehe _abschluss weiter unten).
        if getattr(self.weg, 'abgeschnitten', False):
            self.hoehe += VERMERK
        return self

    @staticmethod
    def _zeilen_waehlen(spalten):
        u"""Die Zeilenzahl, bei der das Bild am ehesten Bildschirmform hat.

        Durchprobiert statt gerechnet: Die Breite haengt an der Zahl der
        Unterspalten, und die springt (ein Kasten mehr kann eine ganze
        Spalte kosten). Eine geschlossene Formel traefe daneben; sechs bis
        dreissig Kandidaten durchzurechnen kostet nichts.
        """
        beste, bester_abstand = MAX_JE_SPALTE, None
        for zeilen in range(6, 31):
            breite = sum(max(1, -(-len(e) // zeilen)) for e in
                         spalten.values()) * SPALTE
            hoehe = min(max(len(e) for e in spalten.values()),
                        zeilen) * ZEILE
            if not hoehe:
                continue
            abstand = abs(breite / float(hoehe) - ZIEL_VERHAELTNIS)
            if bester_abstand is None or abstand < bester_abstand:
                beste, bester_abstand = zeilen, abstand
        return beste

    # ── Zeichnen ────────────────────────────────────────────────

    def svg(self):
        if not self.karten:
            self.anordnen()
        teile = ['<svg xmlns="http://www.w3.org/2000/svg" '
                 'viewBox="0 0 %d %d" width="%d" height="%d" '
                 'class="wf-bild">' % (self.breite, self.hoehe,
                                       self.breite, self.hoehe)]
        teile.append(self._stil())
        teile.extend(self._kanten())
        teile.extend(self._kaesten())
        teile.extend(self._abschluss())
        teile.append('</svg>')
        return '\n'.join(teile)

    def _abschluss(self):
        u"""Der Vermerk, wenn das Bild weniger zeigt als den ganzen Weg.

        WARUM DAS INS BILD GEHOERT (27.08.2026)
        =======================================
        Die Tiefengrenze ist Absicht: Ohne sie laufen alle Wege bei den
        Hilfsfunktionen zusammen und jedes Bild sieht aus wie jedes
        andere. Das Werkzeug ``dokumentation`` meldete das Abschneiden
        trotzdem als Hinweis, und die Begruendung dort war praezise:

            „ein Bild, das seine eigene Grenze verschweigt, wird fuer das
             Ganze gehalten."

        Genau das - und nur das - behebt diese Zeile. Wer das Bild
        ansieht, liest jetzt selbst, dass es weitergeht. An assistant
        betraf das 33 von 34 Bildern.
        """
        if not getattr(self.weg, 'abgeschnitten', False):
            return []
        return ['<text class="wf-mehr" x="%d" y="%d">%s</text>'
                % (RAHMEN, self.hoehe - RAHMEN // 2,
                   u'… hier geht der Weg weiter, als das Bild zeigt '
                   u'(%d Klassen in %d Schritten gezeichnet)'
                   % (len(self.weg.klassen), len(self.weg.schritte)))]

    @staticmethod
    def _stil():
        return (
            '<style>'
            '.wf-k{fill:var(--ct-bg-card,#1a1f26);'
            'stroke:var(--ct-border,#2a3038);stroke-width:1;rx:5}'
            '.wf-k-start{stroke:#38d4d8;stroke-width:2}'
            '.wf-n{font:600 11px system-ui,sans-serif;'
            'fill:var(--ct-text,#e6edf3)}'
            '.wf-m{font:400 9px system-ui,sans-serif;'
            'fill:var(--ct-text-muted,#8b949e)}'
            '.wf-mehr{font:italic 400 11px system-ui,sans-serif;'
            'fill:var(--ct-text-muted,#8b949e)}'
            '.wf-l{fill:none;stroke-width:1.2;opacity:.55}'
            '</style>')

    def _kanten(self):
        aus = []
        for kante in self.weg.kanten:
            a = self.karten.get(kante.von)
            b = self.karten.get(kante.nach)
            if a is None or b is None or a is b:
                continue
            aus.append(self._bogen(a, b, kante.grund))
        return aus

    @staticmethod
    def _bogen(a, b, grund):
        u"""Waagerecht austreten, waagerecht eintreten.

        Der Griff (``kraft``) waechst mit dem Abstand: Bei einem Sprung
        ueber mehrere Spalten wird der Bogen flacher statt eckiger.
        """
        x1, y1 = a.rechts, a.mitte_y
        x2, y2 = b.x, b.mitte_y
        kraft = max(30.0, abs(x2 - x1) * 0.45)
        strich = ' stroke-dasharray="4 3"' if grund == 'methode' else ''
        return ('<path class="wf-l" d="M%.1f %.1f C%.1f %.1f %.1f %.1f '
                '%.1f %.1f" stroke="%s"%s/>' % (
                    x1, y1, x1 + kraft, y1, x2 - kraft, y2, x2, y2,
                    FARBEN.get(grund, '#7a8a99'), strich))

    def _kaesten(self):
        aus = []
        for karte in sorted(self.karten.values(),
                            key=lambda k: (k.x, k.y)):
            bezug = karte.schritt.bezug
            klasse = 'wf-k wf-k-start' if karte.schritt.tiefe == 0 \
                else 'wf-k'
            aus.append('<rect class="%s" x="%d" y="%d" width="%d" '
                       'height="%d"/>' % (klasse, karte.x, karte.y,
                                          BREITE, HOEHE))
            aus.append('<text class="wf-n" x="%d" y="%d">%s</text>' % (
                karte.x + 9, karte.y + 17, escape(
                    self._kuerzen(bezug.anzeige, 26))))
            aus.append('<text class="wf-m" x="%d" y="%d">%s:%d</text>' % (
                karte.x + 9, karte.y + 31, escape(
                    self._kuerzen(bezug.modul, 28)), bezug.zeile))
        return aus

    @staticmethod
    def _kuerzen(text, wie_viel):
        u"""Von LINKS kuerzen bei Modulpfaden — hinten steht das Wesentliche.

        ``live.orchestrator.producer_pool`` sagt als ``…orchestrator.
        producer_pool`` mehr als als ``live.orchestrator.pro…``.
        """
        if len(text) <= wie_viel:
            return text
        if '.' in text:
            return u'…' + text[-(wie_viel - 1):]
        return text[:wie_viel - 1] + u'…'
