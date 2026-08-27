# -*- coding: utf-8 -*-
u"""Einen Ablauf als SVG zeichnen — von oben nach unten, mit Rauten.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „ich brauche einen klaren Workflow, was in welcher Reihenfolge
     gemacht wird. Kannst du nicht sowas wie ein Ablaufdiagramm machen
     mit Entscheidungsbäumen?"

``workflowbild.py`` ordnet nach ENTFERNUNG vom Einstieg — eine Landkarte.
Hier wird nach REIHENFOLGE gezeichnet: oben faengt es an, unten hoert es
auf, und eine Raute teilt den Weg.

WARUM EINGERUECKT UND NICHT NEBENEINANDER
=========================================
Ein Lehrbuch-Flussdiagramm setzt die beiden Zweige einer Raute
nebeneinander und fuehrt sie darunter wieder zusammen. Das sieht schoen
aus, solange nichts geschachtelt ist.

In echtem Code ist es geschachtelt: eine Frage in einer Schleife in einem
``try``. Nebeneinander waechst die Breite dabei exponentiell — bei vier
Ebenen steht der rechte Zweig 16 Spalten weit weg, und die Linie dorthin
kreuzt alles.

Eingerueckt waechst sie linear. Man liest es wie eine Gliederung: Der
senkrechte Strich links sagt „das gehoert alles zu dieser Frage", und was
danach wieder auf der Hoehe des Elters steht, ist die Zusammenfuehrung.

DIE FORMEN
==========
    Rechteck      ein Schritt: hier wird etwas getan
    Raute         eine Entscheidung
    Rahmen        eine Wiederholung oder eine Absicherung
    abgerundet    ein Ende: zurueck, Fehler, Schleife verlassen
"""
from html import escape

#: Masse.
BREITE = 430
HOEHE = 30
RAUTE = 34
ZEILE = 40
EINZUG = 26
RAHMEN = 22
#: Platz fuer die Beschriftung eines Zweigs („ja" / „nein").
MARKE = 22

FARBEN = {
    'schritt': ('#1a1f26', '#2a3038'),
    'frage': ('#241d33', '#8b7bd8'),
    'ende': ('#2a1d1d', '#d87b7b'),
    'schleife': ('#1a2630', '#38d4d8'),
    'block': ('#1a2630', '#2a3038'),
    'absicherung': ('#2a2519', '#d8b45e'),
}


class Kasten:
    u"""Ein gezeichnetes Teil mit seinem Platz."""

    __slots__ = ('knoten', 'x', 'y', 'breite', 'marke')

    def __init__(self, knoten, x, y, breite, marke=''):
        self.knoten = knoten
        self.x = x
        self.y = y
        self.breite = breite
        #: „ja" / „nein" / „danach immer" — was ueber dem Kasten steht.
        self.marke = marke


class Ablaufbild:
    u"""Ein ``Ablauf`` als SVG.

        >>> Ablaufbild(ablauf).svg()      # doctest: +SKIP
        '<svg ...>'
    """

    def __init__(self, ablauf):
        self.ablauf = ablauf
        self.kaesten = []
        #: (x, y1, y2) — die senkrechten Striche der Gliederung.
        self.striche = []
        self.breite = 0
        self.hoehe = 0

    # ── Anordnen ────────────────────────────────────────────────

    def anordnen(self):
        y = self._folge(self.ablauf.knoten, RAHMEN, RAHMEN)
        self.hoehe = int(y + RAHMEN)
        self.breite = int(max([k.x + k.breite for k in self.kaesten],
                              default=BREITE) + RAHMEN)
        return self

    def _folge(self, knoten, x, y, marke=''):
        u"""Eine Folge untereinander setzen; gibt das neue ``y`` zurueck."""
        for stelle, k in enumerate(knoten):
            y = self._eins(k, x, y, marke if stelle == 0 else '')
        return y

    def _eins(self, k, x, y, marke=''):
        if marke:
            y += MARKE
        breite = max(160, BREITE - (x - RAHMEN))
        hoch = RAUTE if k.art == 'frage' else HOEHE
        self.kaesten.append(Kasten(k, x, y, breite, marke))
        y += hoch + (ZEILE - HOEHE)
        oben = y
        for feld, beschriftung in (('ja', u'ja'), ('nein', u'sonst'),
                                   ('rumpf', ''), ('sonst', u'bei Fehler'),
                                   ('immer', u'danach immer')):
            kinder = getattr(k, feld, None)
            if not kinder:
                continue
            y = self._folge(kinder, x + EINZUG, y, beschriftung)
        if y > oben:
            self.striche.append((x + 9, oben - (ZEILE - HOEHE) + 4, y - 12))
        return y

    # ── Zeichnen ────────────────────────────────────────────────

    def svg(self):
        if not self.kaesten:
            self.anordnen()
        teile = ['<svg xmlns="http://www.w3.org/2000/svg" '
                 'viewBox="0 0 %d %d" width="%d" height="%d" class="ab-bild">'
                 % (self.breite, self.hoehe, self.breite, self.hoehe),
                 self._stil()]
        for x, y1, y2 in self.striche:
            teile.append('<path class="ab-ast" d="M%d %d L%d %d"/>'
                         % (x, y1, x, y2))
        for kasten in self.kaesten:
            teile.extend(self._zeichnen(kasten))
        teile.append('</svg>')
        return '\n'.join(teile)

    @staticmethod
    def _stil():
        return (
            '<style>'
            '.ab-k{stroke-width:1;rx:4}'
            '.ab-t{font:500 12px system-ui,sans-serif;fill:#e6edf3}'
            '.ab-z{font:400 9px system-ui,sans-serif;fill:#8b949e}'
            '.ab-m{font:600 9px system-ui,sans-serif;fill:#8b949e;'
            'text-transform:uppercase;letter-spacing:.06em}'
            '.ab-ast{stroke:#3a4450;stroke-width:1;fill:none}'
            '.ab-pfeil{stroke:#3a4450;stroke-width:1;fill:none}'
            '</style>')

    def _zeichnen(self, kasten):
        k = kasten.knoten
        fuell, rand = FARBEN.get(k.art, FARBEN['schritt'])
        hoch = RAUTE if k.art == 'frage' else HOEHE
        aus = []
        if k.ziel:
            # Eine Gruppe mit `data-ziel`: Die Seite macht daraus einen
            # Klick, der in DESSEN Ablauf fuehrt. Damit muss das Bild
            # nicht alles einsetzen und bleibt lesbar.
            aus.append('<g data-ziel="%s">' % escape(k.ziel))
        if kasten.marke:
            aus.append('<text class="ab-m" x="%d" y="%d">%s</text>'
                       % (kasten.x + 4, kasten.y - 6, escape(kasten.marke)))
        if k.art == 'frage':
            aus.append(self._raute(kasten, fuell, rand, hoch))
        else:
            rund = 13 if k.art == 'ende' else 4
            aus.append('<rect class="ab-k" x="%d" y="%d" width="%d" '
                       'height="%d" rx="%d" fill="%s" stroke="%s"/>'
                       % (kasten.x, kasten.y, kasten.breite, hoch, rund,
                          fuell, rand))
        aus.append('<text class="ab-t" x="%d" y="%d">%s</text>'
                   % (kasten.x + 14, kasten.y + hoch / 2 + 4,
                      escape(self._beschriftung(k))))
        rechts = kasten.x + kasten.breite
        aus.append('<text class="ab-z" x="%d" y="%d" text-anchor="end">%s</text>'
                   % (rechts - 10, kasten.y + hoch / 2 + 4,
                      escape('%s%d' % ('→ ' + k.ziel + '  ' if k.ziel else '',
                                       k.zeile))))
        if k.ziel:
            aus.append('</g>')
        return aus

    @staticmethod
    def _raute(kasten, fuell, rand, hoch):
        u"""Eine Raute in Kastenbreite — sonst passt kein Text hinein.

        Ein gleichseitiges Rhombus waere lehrbuchtreu und unlesbar: Die
        Bedingung ``not cap.isOpened()`` braucht Platz, und ein Diagramm,
        in dem die Bedingung abgeschnitten ist, beantwortet die Frage
        nicht, um die es geht.
        """
        x, y, b = kasten.x, kasten.y, kasten.breite
        ecke = 16
        punkte = '%d,%d %d,%d %d,%d %d,%d %d,%d %d,%d' % (
            x + ecke, y, x + b - ecke, y, x + b, y + hoch / 2,
            x + b - ecke, y + hoch, x + ecke, y + hoch, x, y + hoch / 2)
        return ('<polygon class="ab-k" points="%s" fill="%s" stroke="%s"/>'
                % (punkte, fuell, rand))

    @staticmethod
    def _beschriftung(k):
        if k.art == 'frage':
            return u'wenn %s' % k.text
        return k.text
