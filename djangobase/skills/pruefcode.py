# -*- coding: utf-8 -*-
u"""Was ist Pruefcode? EINE Antwort, fuer alle Werkzeuge.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „die andere Session sagte mir, BDD würde nur nach einem festen Muster
     suchen, nicht allgemein, im ganzen Code"
    „merge das mit dem was es schon gibt, keine Duplikate"

Sie hat recht, und es ist nachgemessen. ``szenarien`` und ``bdd-saetze``
entschieden beide ueber den DATEINAMEN::

    if not pfad.name.startswith('test_'):
        continue

Gemessen am 27.08.2026:

    CamTrack     1.437 Pruefmethoden gesehen,   0 uebersehen
    djangoBase   1.024 gesehen,                31 UEBERSEHEN

Und die 31 sind ausgerechnet die Waechter des Projekts —
``grundtests.py``, ``befundgrenzen.py``, ``endpunkttests.py``,
``leistungstests.py``. Wer die Regeln des Hauses prueft, entging der
Pruefung, weil seine Datei nicht so heisst wie die anderen.

DIE ALLGEMEINE REGEL: VERERBUNG STATT DATEINAME
===============================================
Ein Test ist ein Test, weil er von einer Test-Basis erbt — nicht weil die
Datei ``test_`` heisst. Und zwar TRANSITIV: In diesen Projekten erbt kaum
etwas direkt von ``TestCase``, sondern ueber eigene Basen::

    TestCase  <-  BasisTest  <-  JobsSeiteBasis  <-  die eigentliche Pruefung

Gezaehlt am 27.08.2026 stehen 284 Klassen auf ``TestCase``, 191 auf
``SimpleTestCase``, 162 auf ``BasisTest`` und ein Dutzend weitere auf
projekteigenen Basen wie ``MitTempordner`` oder ``ZeitleisteBasis``. Eine
feste Namensliste haette die letzte Gruppe wieder verfehlt; darum wird bis
zum Fixpunkt aufgeloest.

WARUM DAS NICHT NUR MEHR, SONDERN AUCH GENAUER FINDET
=====================================================
Der Dateiname-Filter war ein Behelf gegen einen frueheren Fehlalarm: Am
26.08.2026 meldete ``szenarien`` zwei Verstoesse in
``app/views/cameras/connection_test.py`` — einer ANSICHT.
``ConnectionTester.test_http_snapshot(ip, port, …)`` probiert
Schnappschuss-Pfade an einer Kamera durch; sie heisst nur so.

Nachgesehen: ``class ConnectionTester:`` hat GAR KEINE Basis. Die
Vererbungsregel schliesst sie also von selbst aus — sie braucht den
Dateinamen-Behelf nicht und ist zugleich breiter. Ein Filter, der beides
besser macht, ist selten; hier ist es einer.
"""
from __future__ import annotations

import ast

#: Die Basen, bei denen die Aufloesung anfaengt. Alles Weitere findet sich
#: von selbst, indem einer Klasse gefolgt wird, die von hier erbt.
WURZELBASEN = {
    'TestCase', 'SimpleTestCase', 'TransactionTestCase',
    'LiveServerTestCase', 'StaticLiveServerTestCase',
    'IsolatedAsyncioTestCase',
}

#: Womit eine Pruefmethode anfaengt. Das IST ein festes Muster — aber
#: eines, das der Testlaeufer selbst vorgibt: Was nicht so heisst, fuehrt
#: `unittest` gar nicht aus.
METHODENVORSATZ = 'test'


class Pruefcode:
    u"""Entscheidet fuer EIN Projekt, welche Klassen Pruefungen sind.

    Zweistufig, weil Vererbung sich nicht in einer Datei entscheidet:
    erst das ganze Projekt einlesen (``lesen``), dann fragen
    (``ist_pruefklasse``).

        >>> p = Pruefcode().lesen(dateien)     # doctest: +SKIP
        >>> p.ist_pruefklasse(knoten)          # doctest: +SKIP
        True
    """

    def __init__(self):
        #: Klassenname -> Menge der Basisnamen
        self._basen = {}
        #: Klassennamen, die (transitiv) Pruefbasen sind
        self.pruefbasen = set(WURZELBASEN)

    # ── Einlesen ────────────────────────────────────────────────

    def lesen(self, dateien):
        u"""``dateien``: (pfad, baum)-Paare des ganzen Projekts."""
        for _pfad, baum in dateien:
            if baum is None:
                continue
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.ClassDef):
                    self._basen.setdefault(knoten.name, set()).update(
                        self.basisnamen(knoten))
        self._aufloesen()
        return self

    def _aufloesen(self):
        u"""Bis zum Fixpunkt: Wer von einer Pruefbasis erbt, ist eine.

        Eine einzelne Runde reichte nicht — ``JobsSeiteBasis`` erbt von
        ``BasisTest``, das von ``TestCase``. Wie viele Stufen es sind,
        weiss man vorher nicht, also wird gedreht, bis nichts mehr
        dazukommt. Das sind in der Praxis drei bis vier Durchgaenge.
        """
        gewachsen = True
        while gewachsen:
            gewachsen = False
            for name, basen in self._basen.items():
                if name in self.pruefbasen:
                    continue
                if basen & self.pruefbasen:
                    self.pruefbasen.add(name)
                    gewachsen = True

    # ── Fragen ──────────────────────────────────────────────────

    def ist_pruefklasse(self, knoten):
        u"""Erbt diese Klasse (transitiv) von einer Test-Basis?"""
        return bool(self.basisnamen(knoten) & self.pruefbasen)

    def pruefmethoden(self, knoten):
        u"""Die Methoden dieser Klasse, die der Testlaeufer ausfuehrt."""
        return [k for k in knoten.body
                if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))
                and k.name.startswith(METHODENVORSATZ)]

    def pruefklassen(self, baum):
        u"""Alle Pruefklassen EINER Datei, mit ihren Methoden."""
        aus = []
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef) and self.ist_pruefklasse(knoten):
                methoden = self.pruefmethoden(knoten)
                if methoden:
                    aus.append((knoten, methoden))
        return aus

    # ── Kleinteil ───────────────────────────────────────────────

    @staticmethod
    def basisnamen(knoten):
        u"""``class A(x.TestCase, Mixin)`` -> ``{'TestCase', 'Mixin'}``.

        Der Punkt wird abgeschnitten: Ob jemand ``TestCase`` oder
        ``unittest.TestCase`` schreibt, ist Geschmack und darf nicht
        darueber entscheiden, ob die Pruefung geprueft wird.
        """
        aus = set()
        for basis in getattr(knoten, 'bases', ()):
            if isinstance(basis, ast.Attribute):
                aus.add(basis.attr)
            elif isinstance(basis, ast.Name):
                aus.add(basis.id)
        return aus
