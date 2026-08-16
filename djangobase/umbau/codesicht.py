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
        js_schneider.py, die sich an einer Klammer in einem regulaeren Ausdruck
        verzaehlt hat.
        """
        aus = list(s)
        for anfang, ende in cls._nichtcode(s):
            for i in range(anfang, ende):
                if aus[i] != '\n':
                    aus[i] = ' '
        return ''.join(aus)

    @classmethod
    def _nichtcode(cls, s):
        """Bereiche [anfang, ende) von Kommentaren, Texten und Ausdruecken.

        Bei Vorlagen bleiben die `${…}`-Abschnitte ausgespart: dort steht Code.
        """
        bereiche = []
        i, n = 0, len(s)
        letztes = '\n'
        while i < n:
            c = s[i]
            if c == '/' and i + 1 < n and s[i + 1] == '/':
                j = s.find('\n', i)
                j = n if j < 0 else j
                bereiche.append((i, j))
                i = j
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '*':
                j = s.find('*/', i + 2)
                j = n if j < 0 else j + 2
                bereiche.append((i, j))
                i = j
                continue
            if c == '/' and letztes in cls.VOR_REGEX:
                j = cls._regexende(s, i)
                if j > 0:
                    bereiche.append((i, j))
                    i = j
                    letztes = ')'
                    continue
            if c in '"\'':
                j = i + 1
                while j < n and s[j] != c:
                    j += 2 if s[j] == '\\' else 1
                bereiche.append((i, min(j + 1, n)))
                i = j + 1
                letztes = ')'
                continue
            if c == '`':
                i = cls._vorlagenbereiche(s, i, bereiche)
                letztes = ')'
                continue
            if not c.isspace():
                letztes = c
            elif c == '\n':
                letztes = '\n'
            i += 1
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

    @classmethod
    def _vorlagenbereiche(cls, s, i, bereiche):
        """Vorlage ab dem Gegenzeichen; Textteile eintragen, Code auslassen."""
        n = len(s)
        stueck = i               # Beginn des laufenden Textteils
        i += 1
        while i < n:
            c = s[i]
            if c == '\\':
                i += 2
                continue
            if c == '`':
                bereiche.append((stueck, i + 1))
                return i + 1
            if c == '$' and i + 1 < n and s[i + 1] == '{':
                bereiche.append((stueck, i + 2))
                tiefe, j = 1, i + 2
                while j < n and tiefe:
                    if s[j] == '{':
                        tiefe += 1
                    elif s[j] == '}':
                        tiefe -= 1
                    elif s[j] == '`':
                        j = cls._vorlagenbereiche(s, j, bereiche)
                        continue
                    j += 1
                stueck = j - 1       # die schliessende Klammer zaehlt zum Text
                i = j
                continue
            i += 1
        bereiche.append((stueck, n))
        return n

    @classmethod
    def _durchlauf(cls, s):
        aus = []
        i, n = 0, len(s)
        letztes = '\n'          # letztes bedeutungstragendes Zeichen
        while i < n:
            c = s[i]
            # ---- Kommentare
            if c == '/' and i + 1 < n and s[i + 1] == '/':
                while i < n and s[i] != '\n':
                    i += 1
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '*':
                ende = s.find('*/', i + 2)
                i = n if ende < 0 else ende + 2
                aus.append(' ')
                continue
            # ---- regulaerer Ausdruck
            if c == '/' and letztes in cls.VOR_REGEX:
                j, in_klasse = i + 1, False
                while j < n:
                    if s[j] == '\\':
                        j += 2
                        continue
                    if s[j] == '[':
                        in_klasse = True
                    elif s[j] == ']':
                        in_klasse = False
                    elif s[j] == '/' and not in_klasse:
                        break
                    elif s[j] == '\n':
                        j = -1
                        break
                    j += 1
                if j > 0 and j < n:
                    i = j + 1
                    while i < n and s[i].isalpha():   # Kennzeichen g, i, m, …
                        i += 1
                    aus.append(' ')
                    letztes = ')'                      # verhaelt sich wie ein Wert
                    continue
            # ---- einfache und doppelte Anfuehrungszeichen
            if c in '"\'':
                j = i + 1
                while j < n and s[j] != c:
                    j += 2 if s[j] == '\\' else 1
                aus.append(c + c)
                i = j + 1
                letztes = ')'
                continue
            # ---- Vorlage: nur die Einsetzungen behalten
            if c == '`':
                i, teile = cls._vorlage(s, i)
                aus.extend(teile)
                letztes = ')'
                continue
            aus.append(c)
            if not c.isspace():
                letztes = c
            elif c == '\n':
                letztes = '\n'
            i += 1
        return ''.join(aus)

    @classmethod
    def _vorlage(cls, s, i):
        """Ab dem oeffnenden Gegenzeichen bis zum schliessenden.

        Verschachtelte Vorlagen in `${…}` werden mitgenommen — genau daran ist
        die Regex-Fassung gescheitert.
        """
        teile = []
        i += 1
        n = len(s)
        while i < n:
            c = s[i]
            if c == '\\':
                i += 2
                continue
            if c == '`':
                return i + 1, teile
            if c == '$' and i + 1 < n and s[i + 1] == '{':
                tiefe, j = 1, i + 2
                while j < n and tiefe:
                    if s[j] == '{':
                        tiefe += 1
                    elif s[j] == '}':
                        tiefe -= 1
                    elif s[j] == '`':
                        j, unter = cls._vorlage(s, j)
                        teile.extend(unter)
                        continue
                    j += 1
                # Der Inhalt einer Einsetzung ist selbst wieder Code: er kann
                # Texte enthalten (`${an ? 'An' : 'Aus'}`). Ohne diesen zweiten
                # Durchlauf zaehlte der Scanner `An` und `Aus` als Bezeichner.
                teile.append(' ' + cls._durchlauf(s[i + 2:j - 1]) + ' ')
                i = j
                continue
            i += 1
        return i, teile
