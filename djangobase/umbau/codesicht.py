# -*- coding: utf-8 -*-
"""Codesicht — JavaScript-Quelltext ohne Kommentare und Zeichenkettenrumpf.

WARUM kein regulaerer Ausdruck (16.08.2026): Die erste Fassung von
js_unbekannte_namen.py hat Kommentare, Texte und Vorlagen mit einer Kette von
`re.sub` entfernt. Das geht schief, sobald ein Apostroph in einer Vorlage steht
(`Es geht's`): Das Muster fuer einfache Anfuehrungszeichen greift ueber die
Vorlage hinweg, frisst dabei ein Gegenzeichen — und ab da ist die ganze Datei
verschoben. In viewer/websocket.js verschwand so `export function wsSend`, und
der Scanner meldete den selbst definierten Namen als unbekannt.

Ein Durchlauf Zeichen fuer Zeichen kennt dagegen immer seinen Zustand. Der
Aufwand ist ein einmaliger; die Alternative sind Fehlalarme in jedem Lauf.

`${…}` in Vorlagen bleibt erhalten: dort steht Code.
"""


class Codesicht:
    """Der Codeanteil einer Quelldatei — Texte sind geleert, Kommentare weg."""

    #: Nach diesen Zeichen beginnt ein `/` einen regulaeren Ausdruck, keine Division.
    VOR_REGEX = set('(,=:[!&|?{};+-*%~^<>') | {'\n', 'return', 'typeof'}

    def __init__(self, quelle):
        self.quelle = quelle
        self.code = self._durchlauf(quelle)

    @classmethod
    def maske(cls, s):
        """Gleich langer Text, in dem alles ausser Code durch Leerzeichen ersetzt ist.

        Zeilenumbrueche bleiben stehen, Zeichenpositionen stimmen also weiter.
        Fuer alle Werkzeuge, die zeilenweise arbeiten und trotzdem wissen
        muessen, welche Klammer echter Code ist — etwa die Blocksuche in
        js_schneider.py, die sich an einer Klammer in einem regulaeren
        Ausdruck verzaehlt hat.
        """
        aus = list(s)
        for anfang, ende, _art in cls._teile(s):
            for i in range(anfang, ende):
                if aus[i] != '\n':
                    aus[i] = ' '
        return ''.join(aus)

    @classmethod
    def _durchlauf(cls, s):
        """Derselbe Text, aber VERDICHTET: Nichtcode faellt weg oder schrumpft.

        Der Unterschied zu `maske` ist nur der Platzhalter je Art — die
        Regeln, was Nichtcode IST, stehen einmal in `_teile`.
        """
        aus, zuletzt = [], 0
        for anfang, ende, art in cls._teile(s):
            aus.append(s[zuletzt:anfang])
            aus.append(cls.PLATZHALTER.get(art, ' ')
                       if art != 'text' else s[anfang] * 2)
            zuletzt = ende
        aus.append(s[zuletzt:])
        return ''.join(aus)

    #: Was im verdichteten Text an die Stelle eines Nichtcode-Bereichs tritt.
    #:
    #: Ein Zeilenkommentar faellt ganz weg — sein Zeilenumbruch gehoert nicht
    #: zum Bereich und bleibt dadurch erhalten. Ein Blockkommentar kann Zeilen
    #: verschlucken; er wird zu EINEM Leerzeichen, damit die Zeichen davor und
    #: danach nicht zusammenkleben. Bei `text` steht das Anfuehrungszeichen
    #: doppelt (siehe `_durchlauf`) — die Werkzeuge sollen sehen, DASS dort
    #: eine Zeichenkette war.
    PLATZHALTER = {'zeilenkommentar': '', 'blockkommentar': ' ',
                   'regex': ' ', 'vorlagentext': ' '}

    # ------------------------------------------------------------- Scanner

    @classmethod
    def _teile(cls, s):
        """Die Nichtcode-Bereiche als ``(anfang, ende, art)``, der Reihe nach.

        EIN SCANNER FUER BEIDE SICHTEN (29.08.2026): Bis dahin gab es zwei —
        `_nichtcode` fuer `maske` und `_durchlauf` fuer `.code`. Sie kannten
        dieselben Regeln, hatten sie getrennt ausgeschrieben und
        widersprachen sich bereits: `maske` liess Zeichenketten INNERHALB
        einer Vorlagen-Einsetzung stehen.

        DER ZUSTAND, der das noetig macht: Innerhalb von ``${…}`` ist wieder
        Code — mit Zeichenketten, Kommentaren und Vorlagen. Der Scanner
        merkt sich deshalb einen Stapel offener Vorlagen und je Vorlage, ob
        er gerade im Text oder in einer Einsetzung steht.
        """
        bereiche = []
        i, n = 0, len(s)
        letztes = '\n'
        #: Je offene Vorlage: [Beginn des laufenden Textstuecks, Klammertiefe].
        #: Tiefe 0 heisst „im Text", groesser 0 „in einer Einsetzung".
        vorlagen = []

        while i < n:
            c = s[i]

            # ---- im TEXTTEIL einer Vorlage
            if vorlagen and vorlagen[-1][1] == 0:
                if c == '\\':
                    i += 2
                    continue
                if c == '`':
                    bereiche.append((vorlagen.pop()[0], i + 1, 'vorlagentext'))
                    letztes = ')'
                    i += 1
                    continue
                if c == '$' and i + 1 < n and s[i + 1] == '{':
                    bereiche.append((vorlagen[-1][0], i + 2, 'vorlagentext'))
                    vorlagen[-1][1] = 1
                    i += 2
                    continue
                i += 1
                continue

            # ---- Kommentare
            if c == '/' and i + 1 < n and s[i + 1] == '/':
                j = s.find('\n', i)
                j = n if j < 0 else j
                bereiche.append((i, j, 'zeilenkommentar'))
                i = j
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '*':
                j = s.find('*/', i + 2)
                j = n if j < 0 else j + 2
                bereiche.append((i, j, 'blockkommentar'))
                i = j
                continue

            # ---- regulaerer Ausdruck (nur, wenn davor kein Wert steht)
            if c == '/' and letztes in cls.VOR_REGEX:
                j = cls._regexende(s, i)
                if j > 0:
                    bereiche.append((i, j, 'regex'))
                    i = j
                    letztes = ')'
                    continue

            # ---- Zeichenketten
            if c in '"\'':
                j = i + 1
                while j < n and s[j] != c:
                    j += 2 if s[j] == '\\' else 1
                bereiche.append((i, min(j + 1, n), 'text'))
                i = j + 1
                letztes = ')'
                continue

            # ---- Vorlage beginnt
            if c == '`':
                vorlagen.append([i, 0])
                i += 1
                continue

            # ---- Klammern innerhalb einer Einsetzung mitzaehlen
            if vorlagen:
                if c == '{':
                    vorlagen[-1][1] += 1
                elif c == '}':
                    vorlagen[-1][1] -= 1
                    if vorlagen[-1][1] == 0:
                        # Die schliessende Klammer zaehlt zum naechsten
                        # Textstueck — so stand es schon in der alten Fassung.
                        vorlagen[-1][0] = i
                        letztes = ')'
                        i += 1
                        continue

            if not c.isspace():
                letztes = c
            elif c == '\n':
                letztes = '\n'
            i += 1

        # Eine nicht geschlossene Vorlage: der Rest ist Text.
        while vorlagen:
            bereiche.append((vorlagen.pop()[0], n, 'vorlagentext'))
        return bereiche

    @classmethod
    def _regexende(cls, s, i):
        """Position hinter dem regulaeren Ausdruck, oder -1."""
        j, in_klasse, n = i + 1, False, len(s)
        while j < n:
            if s[j] == '\\':
                j += 2
                continue
            if s[j] == '[':
                in_klasse = True
            elif s[j] == ']':
                in_klasse = False
            elif s[j] == '/' and not in_klasse:
                j += 1
                while j < n and s[j].isalpha():
                    j += 1
                return j
            elif s[j] == '\n':
                return -1
            j += 1
        return -1

