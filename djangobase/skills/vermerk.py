# -*- coding: utf-8 -*-
u"""Der Vermerk, der eine Stelle von einer Lehre ausnimmt.

WAS ER LEISTET
==============
Manche Stelle verstoesst mit Absicht und mit Grund gegen eine Lehre.
Dafuer gibt es eine Schreibweise::

    # Lehre gilt hier nicht ("keine-temp-dateien-im-system"): Der
    # fremde Dienst nimmt nur Pfade aus dem System-Zwischenspeicher an.

Der Vermerk gilt in der Funktion, in der er steht — oder, wenn er im
Dateikopf steht, fuer die ganze Datei. Und er gilt NUR fuer die Lehre,
die er beim Namen nennt.

WARUM EIGENES MODUL (31.08.2026)
================================
Die Logik lag in ``lehrentreue.py``, verwoben mit dessen Besucher.
``systemablage`` kannte deshalb GAR KEINE Einzelfall-Ausnahme, nur eine
Liste von Dateinamen — und meldete eine Stelle, die den Vermerk
ordnungsgemaess trug und deren Grund nachlesbar stimmt (ACE-Step
verlangt ausdruecklich einen Pfad im System-Zwischenspeicher und weist
jeden anderen mit einem Fehler ab).

Zwei Werkzeuge, die dieselbe Lehre durchsetzen, muessen dieselbe
Ausnahme anerkennen — sonst ist die Schreibweise nichts wert.
"""
import ast


class Vermerk:
    u"""Liest die Vermerke einer Quelldatei und beantwortet Fragen dazu."""

    #: Die Einleitung, an der ein Vermerk erkannt wird.
    TEXT = 'Lehre gilt hier nicht'

    #: So viele Zeichen hinter der Einleitung darf der Name der Lehre
    #: stehen. Eine belegte Ausnahme braucht Platz fuer ihre Begruendung.
    REICHWEITE = 400

    def __init__(self, quelle):
        self.zeilen = quelle.splitlines()
        self.funktionen = self._funktionen(quelle)
        self.kopfzeilen = self._kopfende()

    def gilt_nicht(self, zeile, lehre):
        u"""Nimmt ein Vermerk diese Zeile von DIESER Lehre aus?

        DOCSTRINGS ZAEHLEN MIT — UND DAS BLEIBT SO (geprueft 31.08.2026):
        CodeRabbit hat vorgeschlagen, nur noch Python-Kommentar-Tokens zu
        lesen, damit ein Beispiel in einer Zeichenkette keine Warnung
        unterdrueckt. Das waere hier falsch: Der belegte Anlassfall
        (``_vorlage_kopieren`` in ``assistant``) traegt seinen Vermerk IM
        DOCSTRING, und ``test_systemablage.MIT_VERMERK`` sichert genau das ab.
        Ein Umbau auf Kommentare haette die Ausnahme aufgehoben und den Test
        rot gemacht.

        Die Enge kommt anderswoher: Der Vermerk gilt nur fuer die Lehre, die
        er beim NAMEN nennt, und nur im umgebenden Bereich (Funktion oder
        Dateikopf). Beides ist durch Prueffaelle abgedeckt.
        """
        for von, bis in self._bereiche(zeile):
            block = '\n'.join(self.zeilen[von:bis])
            for absatz in block.split(self.TEXT)[1:]:
                # Der Name der Lehre steht im selben oder im naechsten Satz.
                if lehre in absatz[:self.REICHWEITE]:
                    return True
            if lehre in block and self.TEXT in block:
                # Auch die Schreibweise „Lehre gilt hier nicht" VOR dem
                # Namen zaehlt — beides steht in derselben Erklaerung.
                return True
        return False

    # ── intern ──────────────────────────────────────────────────

    def _bereiche(self, zeile):
        u"""Erst die umgebende Funktion, dann der Dateikopf."""
        for von, bis in self.funktionen:
            if von <= zeile <= bis:
                yield von - 1, bis
        yield 0, self.kopfzeilen

    @staticmethod
    def _funktionen(quelle):
        u"""(erste, letzte) Zeile jeder Funktion — auch der verschachtelten."""
        try:
            baum = ast.parse(quelle)
        except (SyntaxError, ValueError):
            return []
        raus = []
        for knoten in ast.walk(baum):
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ende = getattr(knoten, 'end_lineno', None) or knoten.lineno
                raus.append((knoten.lineno, ende))
        return raus

    def _kopfende(self):
        u"""Die letzte Zeile vor der ersten ``def``/``class``."""
        for nr, zeile in enumerate(self.zeilen):
            if zeile.startswith(('def ', 'class ', 'async def ')):
                return nr
        return len(self.zeilen)
