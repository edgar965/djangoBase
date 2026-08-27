# -*- coding: utf-8 -*-
u"""Ein Ablauf als UML-Aktivitaetsdiagramm — Achse, Rauten, Pfeile.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „mach mir die grafische Ausgabe von vorher, kein Quelltext, aber
     sowas in der Richtung des Screenshots"
    „belasse diese Ansicht, die ist auch nicht schlecht. mache eine neue
     Seite /hilfe/ablauf mit der neuen anforderung"

Die Vorlage ist ein klassisches Aktivitaetsdiagramm: ein gefuellter Kreis
oben, eine senkrechte Achse, abgerundete Kaesten mit ProsaTEXT, Rauten
mit Kanten in eckigen Klammern, eine Zusammenfuehrung als Balken und ein
Doppelkreis unten.

WAS DIESES BILD ANDERS MACHT ALS ``ablaufbild.py``
==================================================
``ablaufbild.py`` zeigt den Quelltext, eingerueckt wie eine Gliederung.
Das ist genau, aber es liest sich wie Code — weil es Code IST.

Hier steht Prosa (siehe ``beschriftung.py``) und die Form folgt der
Vorlage: echte Pfeile, beschriftete Zweige, Anfang und Ende als Kreise.
Beide Ansichten bleiben; sie beantworten verschiedene Fragen.

DIE ANORDNUNG
=============
Eine MITTELACHSE traegt den Hauptweg. Eine Raute schickt ihren
``ja``-Zweig nach LINKS in eine Nebenspur und fuehrt ihn darunter wieder
auf die Achse zurueck — genau wie in der Vorlage.

Warum nicht beide Zweige symmetrisch? Weil der Hauptweg dann bei jeder
Frage die Spur wechselt und man ihn verliert. In der Vorlage laeuft er
ebenfalls durch: geradeaus ist „weiter", zur Seite ist „der Sonderfall".
"""
from html import escape

#: Masse.
KASTEN_B = 210
KASTEN_H = 54
RAUTE = 44
LUFT = 46
#: Abstand Nebenspur zur Achse. GROSS GENUG FUER DIE MARKE (27.08.2026):
#: Bei 270 blieben zwischen Kastenrand und Raute noch 43 Punkte, und
#: „[ja]" stand als Buchstabensalat dazwischen. Jetzt sind es 123.
SPUR = 340
RAND = 40
KREIS = 22

FARBEN = {
    'kasten': ('#eef2f6', '#9fb6cc', '#3d4b57'),
    'frage': ('#8fb2ce', '#6f93b0'),
    'balken': '#7d9db8',
    'linie': '#8fb2ce',
    'text': '#4a5a66',
}


class Teil:
    u"""Ein gezeichnetes Element mit Mittelpunkt und Groesse."""

    __slots__ = ('art', 'text', 'x', 'y', 'breite', 'hoehe', 'ziel',
                 'zeile', 'knoten')

    def __init__(self, art, text, x, y, breite, hoehe, ziel='', zeile=0,
                 knoten=None):
        self.art = art
        self.text = text
        self.x = x            # Mitte
        self.y = y            # Oberkante
        self.breite = breite
        self.hoehe = hoehe
        self.ziel = ziel
        self.zeile = zeile
        #: Der Ablauf-Knoten dahinter — Grundlage der Angaben beim
        #: Ueberfahren und beim Anklicken.
        self.knoten = knoten

    @property
    def unten(self):
        return self.y + self.hoehe

    @property
    def links(self):
        return self.x - self.breite / 2.0

    @property
    def rechts(self):
        return self.x + self.breite / 2.0


class Aktivitaetsbild:
    u"""Ein ``Ablauf`` im Stil eines UML-Aktivitaetsdiagramms."""

    def __init__(self, ablauf, beschrifter=None, herkunft=None):
        self.ablauf = ablauf
        #: ``knoten -> Satz`` — wird von aussen gestellt, damit das Bild
        #: nichts ueber Docstrings und Namen wissen muss.
        self.beschrifter = beschrifter or (lambda k: k.text)
        #: ``knoten -> dict`` mit Klasse, Methode, Modul, Zeile.
        #:
        #: WOHER EIN KASTEN KOMMT (27.08.2026, auf Ansage)
        #: ==============================================
        #:     „kannst du hover und popups machen, die bei Klick auf einen
        #:      Bereich die Klasse und die Methode anzeigt?"
        #:
        #: Der Satz im Kasten ist Prosa — gut zum Lesen, aber er sagt
        #: nicht, WO das steht. Diese Angaben haengen als Daten am Kasten;
        #: die Seite macht daraus ein Fenster beim Ueberfahren und beim
        #: Anklicken. Das Bild selbst bleibt ein Bild.
        self.herkunft = herkunft or (lambda k: {})
        self.teile = []
        self.kanten = []      # (x1,y1,x2,y2,marke) — als Polylinie
        self.breite = 0
        self.hoehe = 0

    # ── Anordnen ────────────────────────────────────────────────

    def anordnen(self):
        achse = RAND + SPUR
        y = RAND
        start = Teil('start', '', achse, y, KREIS, KREIS)
        self.teile.append(start)
        y = start.unten + LUFT
        y, letzte = self._folge(self.ablauf.knoten, achse, y, start)
        ende = Teil('ende', '', achse, y, KREIS, KREIS)
        self.teile.append(ende)
        if letzte is not None:
            self._pfeil(letzte, ende)
        self.hoehe = int(ende.unten + RAND)
        self.breite = int(max([t.rechts for t in self.teile] +
                              [x for _a, x, _b, _c in
                               [(0, k[0], 0, 0) for k in self.kanten]] +
                              [achse + SPUR]) + RAND)
        return self

    def _folge(self, knoten, achse, y, voriges):
        for k in knoten:
            y, voriges = self._eins(k, achse, y, voriges)
        return y, voriges

    def _eins(self, k, achse, y, voriges):
        text = self.beschrifter(k)
        if k.art == 'frage':
            return self._frage(k, text, achse, y, voriges)
        if k.art in ('schleife', 'block'):
            return self._schleife(k, text, achse, y, voriges)
        if k.art == 'absicherung':
            return self._folge(list(k.rumpf) + list(k.immer), achse, y,
                               voriges)
        hoehe = KASTEN_H if k.art != 'ende' else KASTEN_H
        art = 'ausgang' if k.art == 'ende' else 'kasten'
        teil = Teil(art, text, achse, y, KASTEN_B, hoehe,
                    getattr(k, 'ziel', ''), k.zeile, k)
        self.teile.append(teil)
        if voriges is not None:
            self._pfeil(voriges, teil)
        return teil.unten + LUFT, (None if art == 'ausgang' else teil)

    def _frage(self, k, text, achse, y, voriges):
        u"""Raute auf der Achse, ``ja`` nach links, danach zurueck."""
        raute = Teil('frage', text, achse, y, RAUTE, RAUTE, '',
                     k.zeile, k)
        self.teile.append(raute)
        if voriges is not None:
            self._pfeil(voriges, raute)
        y = raute.unten + LUFT
        # NICHT WEITER ALS AN DEN RAND (27.08.2026)
        # Verschachtelte Fragen wanderten sonst je Ebene eine Spur nach
        # links; gemessen an `backfill_soft_biometrics` bis x = -1040,
        # also weit ausserhalb des Bildes. Ueberlappen kann dabei nichts:
        # `y` waechst immer, zwei Teile derselben Spur stehen also nie
        # auf derselben Hoehe.
        neben = max(achse - SPUR, RAND + KASTEN_B / 2.0)
        ende_links = None
        if k.ja:
            y_links = raute.y
            voriges_links = None
            for kind in k.ja:
                y_links, voriges_links = self._eins(kind, neben, y_links,
                                                    voriges_links)
            if voriges_links is not None:
                ende_links = voriges_links
            # Waagerechter Pfeil von der Raute in die Nebenspur
            erster = self._erster_ab(raute)
            if erster is not None:
                self._kante(raute.links, raute.y + RAUTE / 2.0,
                            erster.rechts, erster.y + erster.hoehe / 2.0,
                            self._marke(k, True))
            y = max(y, y_links)
        # Der Nein-Weg laeuft auf der Achse weiter.
        nach = raute
        if k.nein:
            y, nach = self._folge(k.nein, achse, y, raute)
        if ende_links is not None:
            # Zusammenfuehrung: der Nebenweg kommt auf die Achse zurueck.
            balken = Teil('balken', '', achse, y, 120, 10)
            self.teile.append(balken)
            self._kante(ende_links.x, ende_links.unten,
                        balken.links, balken.y + 5, '')
            self._pfeil(nach, balken)
            return balken.unten + LUFT, balken
        if not k.nein:
            self._marke_setzen(raute, self._marke(k, False))
        return y, nach

    def _schleife(self, k, text, achse, y, voriges):
        u"""Rumpf auf der Achse, dazu ein Ruecklaufpfeil rechts."""
        balken = Teil('balken', '', achse, y, 120, 10)
        self.teile.append(balken)
        if voriges is not None:
            self._pfeil(voriges, balken)
        y = balken.unten + LUFT
        y, letzte = self._folge(k.rumpf, achse, y, balken)
        raute = Teil('frage', text, achse, y, RAUTE, RAUTE, '',
                     k.zeile, k)
        self.teile.append(raute)
        if letzte is not None:
            self._pfeil(letzte, raute)
        rechts = achse + SPUR
        self._kante(raute.rechts, raute.y + RAUTE / 2.0,
                    rechts, balken.y + 5, u'[weiter]', ecke=True,
                    ziel_x=balken.rechts)
        self._marke_setzen(raute, u'[fertig]')
        return raute.unten + LUFT, raute

    # ── Kanten ──────────────────────────────────────────────────

    def _pfeil(self, von, nach, marke=''):
        self._kante(von.x, von.unten, nach.x, nach.y, marke)

    def _kante(self, x1, y1, x2, y2, marke='', ecke=False, ziel_x=None):
        self.kanten.append((x1, y1, x2, y2, marke, ecke, ziel_x))

    def _marke_setzen(self, raute, marke):
        u"""Beschriftung an den geradeaus weiterlaufenden Ausgang."""
        self.kanten.append((raute.x, raute.unten, raute.x,
                            raute.unten + LUFT * 0.6, marke, False, None))

    def _erster_ab(self, raute):
        u"""Das erste Teil, das nach dieser Raute in die Nebenspur kam."""
        stelle = self.teile.index(raute)
        for t in self.teile[stelle + 1:]:
            if t.x < raute.x:
                return t
        return None

    @staticmethod
    def _marke(k, ja):
        text = getattr(k, 'text', '')
        return u'[%s]' % (text if ja else u'sonst')

    # ── Zeichnen ────────────────────────────────────────────────

    def svg(self):
        if not self.teile:
            self.anordnen()
        aus = ['<svg xmlns="http://www.w3.org/2000/svg" '
               'viewBox="0 0 %d %d" width="%d" height="%d" class="ak-bild">'
               % (self.breite, self.hoehe, self.breite, self.hoehe),
               self._stil(), self._pfeilspitze(),
               # DER GRUND GEHOERT INS BILD, NICHT INS STILBLATT
               # (27.08.2026): `background: #fff` an der Buehne wurde vom
               # dunklen Thema des Wirtsprojekts ueberschrieben — auch mit
               # `!important`. Ein Rechteck im SVG bringt den Grund mit,
               # auch wenn jemand das Bild speichert oder ausdruckt.
               #
               # Als STIL, nicht als Attribut: Ein `fill="…"` ist nur ein
               # Vorschlag und verliert gegen jede CSS-Regel des
               # Wirtsprojekts — beim ersten Versuch blieb die Flaeche
               # dunkel, obwohl das Attribut dastand.
               '<rect x="0" y="0" width="%d" height="%d" '
               'style="fill:#ffffff"/>' % (self.breite, self.hoehe)]
        for kante in self.kanten:
            aus.extend(self._kante_zeichnen(*kante))
        for teil in self.teile:
            aus.extend(self._teil_zeichnen(teil))
        aus.append('</svg>')
        return '\n'.join(aus)

    @staticmethod
    def _pfeilspitze():
        return ('<defs><marker id="ak-spitze" markerWidth="9" '
                'markerHeight="9" refX="8" refY="3" orient="auto">'
                '<path d="M0,0 L8,3 L0,6 z" fill="%s"/></marker></defs>'
                % FARBEN['linie'])

    @staticmethod
    def _stil():
        u"""Ein weisser Hof hinter jeder Beschriftung.

        LESBAR NEBEN DEN BLOECKEN (27.08.2026, auf Ansage)
        ==================================================
        ``paint-order: stroke`` zeichnet erst den Rand, dann die Fuellung.
        Mit weissem Rand liegt damit ein Hof unter der Schrift, und eine
        Linie, die darunter durchlaeuft, schneidet sie nicht mehr.

        Ohne das lag ``[not os.path.isdir(…)]`` mitten auf der Raute und
        war weder als Text noch als Raute zu erkennen.
        """
        return ('<style>'
                '.ak-t{font:400 14px system-ui,sans-serif;fill:%s}'
                '.ak-m{font:400 11px system-ui,sans-serif;fill:#5d6b76;'
                'paint-order:stroke;stroke:#fff;stroke-width:3.5px;'
                'stroke-linejoin:round}'
                '.ak-z{font:400 10px system-ui,sans-serif;fill:#93a3ae;'
                'paint-order:stroke;stroke:#fff;stroke-width:3px;'
                'stroke-linejoin:round}'
                '.ak-l{stroke:%s;stroke-width:1.4;fill:none;'
                'marker-end:url(#ak-spitze)}'
                '</style>' % (FARBEN['text'], FARBEN['linie']))

    def _kante_zeichnen(self, x1, y1, x2, y2, marke, ecke, ziel_x):
        if ecke:
            d = 'M%.0f %.0f H%.0f V%.0f H%.0f' % (x1, y1, x2, y2, ziel_x)
        elif abs(x1 - x2) > 2 and abs(y1 - y2) > 2:
            d = 'M%.0f %.0f V%.0f H%.0f' % (x1, y1, y2, x2)
        else:
            d = 'M%.0f %.0f L%.0f %.0f' % (x1, y1, x2, y2)
        aus = ['<path class="ak-l" d="%s"/>' % d]
        if marke:
            aus.append(self._marke_zeichnen(x1, y1, x2, y2, marke))
        return aus

    @staticmethod
    def _marke_zeichnen(x1, y1, x2, y2, marke):
        u"""Die Beschriftung einer Kante — dorthin, wo Platz ist.

        WAAGERECHT oder SENKRECHT sind zwei verschiedene Faelle:

        * Ein waagerechter Zweig hat die ganze Spur als Platz. Die Marke
          steht mittig darueber und wird auf diese Breite gekuerzt —
          vorher lief sie ueber die Raute hinaus.
        * Ein senkrechter Weg hat gar keine Breite. Die Marke steht
          darum NEBEN der Linie, links buendig, statt auf ihr.
        """
        waagerecht = abs(y1 - y2) < 12
        if waagerecht:
            platz = abs(x2 - x1) - 16
            kurz = Aktivitaetsbild._passend(marke, platz)
            stelle = ('x="%.0f" y="%.0f" text-anchor="middle"'
                      % ((x1 + x2) / 2.0, min(y1, y2) - 9))
        else:
            kurz = Aktivitaetsbild._passend(marke, SPUR - 30)
            stelle = ('x="%.0f" y="%.0f"'
                      % (max(x1, x2) + 10, (y1 + y2) / 2.0 + 4))
        # Der VOLLE Text als Tooltip: Gekuerzt wird, damit das Bild lesbar
        # bleibt — die Bedingung ganz zu verlieren waere zu teuer.
        titel = ('<title>%s</title>' % escape(marke)) if kurz != marke else ''
        return '<text class="ak-m" %s>%s%s</text>' % (stelle, titel,
                                                      escape(kurz))

    @staticmethod
    def _passend(text, platz_px):
        u"""So viele Zeichen, wie in ``platz_px`` passen — rund 6 px je
        Zeichen bei 11 px Schrift."""
        hoechstens = max(8, int(platz_px / 6.0))
        text = ' '.join(str(text).split())
        if len(text) <= hoechstens:
            return text
        schluss = ']' if text.endswith(']') else ''
        return text[:hoechstens - 1 - len(schluss)] + u'…' + schluss

    def _teil_zeichnen(self, t):
        if t.art == 'start':
            return ['<circle cx="%.0f" cy="%.0f" r="%d" fill="%s"/>'
                    % (t.x, t.y + KREIS / 2.0, KREIS // 2, FARBEN['balken'])]
        if t.art == 'ende':
            m = t.y + KREIS / 2.0
            return ['<circle cx="%.0f" cy="%.0f" r="%d" fill="none" '
                    'stroke="%s" stroke-width="1.5"/>'
                    % (t.x, m, KREIS // 2, FARBEN['balken']),
                    '<circle cx="%.0f" cy="%.0f" r="%d" fill="%s"/>'
                    % (t.x, m, KREIS // 2 - 4, FARBEN['balken'])]
        if t.art == 'balken':
            return ['<rect x="%.0f" y="%.0f" width="%d" height="%d" '
                    'fill="%s"/>' % (t.links, t.y, t.breite, t.hoehe,
                                     FARBEN['balken'])]
        if t.art == 'frage':
            fuell, rand = FARBEN['frage']
            h = t.hoehe
            punkte = '%.0f,%.0f %.0f,%.0f %.0f,%.0f %.0f,%.0f' % (
                t.x, t.y, t.x + h / 2.0, t.y + h / 2.0,
                t.x, t.y + h, t.x - h / 2.0, t.y + h / 2.0)
            inhalt = ['<polygon points="%s" fill="%s" stroke="%s"/>'
                      % (punkte, fuell, rand)]
            return self._umhuellen(t, inhalt)
        fuell, rand, _t = FARBEN['kasten']
        rund = 22 if t.art == 'ausgang' else 6
        inhalt = ['<rect x="%.0f" y="%.0f" width="%d" height="%d" rx="%d" '
                  'fill="%s" stroke="%s"/>' % (t.links, t.y, t.breite,
                                               t.hoehe, rund, fuell, rand)]
        inhalt.extend(self._text(t))
        return self._umhuellen(t, inhalt)

    def _umhuellen(self, t, inhalt):
        u"""Die Herkunft als Daten an den Kasten haengen.

        Jeder Kasten und jede Raute — nicht nur die mit einem Ziel: Auch
        wo der Weg nicht weitergeht, will man wissen, WO das steht. Die
        Seite baut daraus das Fenster beim Ueberfahren und beim Anklicken.
        """
        if t.knoten is None:
            return inhalt
        angaben = dict(self.herkunft(t.knoten) or {})
        angaben.setdefault('zeile', t.zeile)
        if t.ziel:
            angaben['ziel'] = t.ziel
        felder = ' '.join('data-%s="%s"' % (name, escape(str(wert)))
                          for name, wert in sorted(angaben.items()) if wert)
        if not felder:
            return inhalt
        return (['<g class="ak-teil" %s>' % felder] + inhalt + ['</g>'])

    def _text(self, t):
        u"""Bis zu zwei Zeilen mittig im Kasten."""
        zeilen = self._umbrechen(t.text)
        hoch = t.y + t.hoehe / 2.0 - (len(zeilen) - 1) * 8 + 5
        aus = ['<text class="ak-t" x="%.0f" y="%.0f" text-anchor="middle">'
               '%s</text>' % (t.x, hoch + i * 17, escape(z))
               for i, z in enumerate(zeilen)]
        if t.zeile:
            aus.append(self._zeilennummer(t))
        return aus

    @staticmethod
    def _zeilennummer(t):
        u"""LINKS oben im Kasten — nie rechts.

        Rechts stand sie genau dort, wo die Achse und die naechste Raute
        liegen: „166" klebte an der Raute und lag zugleich unter der
        Kanten-Beschriftung. Links ist bei jedem Kasten Platz, egal auf
        welcher Spur er steht.
        """
        return ('<text class="ak-z" x="%.0f" y="%.0f">%d</text>'
                % (t.links + 9, t.y + 15, t.zeile))

    @staticmethod
    def _umbrechen(text, breit=26, hoechstens=2):
        woerter = str(text).split()
        zeilen, jetzt = [], ''
        for w in woerter:
            versuch = (jetzt + ' ' + w).strip()
            if len(versuch) <= breit or not jetzt:
                jetzt = versuch
            else:
                zeilen.append(jetzt)
                jetzt = w
            if len(zeilen) == hoechstens:
                break
        if jetzt and len(zeilen) < hoechstens:
            zeilen.append(jetzt)
        if len(zeilen) == hoechstens and len(' '.join(zeilen)) < len(text):
            zeilen[-1] = zeilen[-1][:breit - 1] + u'…'
        return zeilen or ['']
