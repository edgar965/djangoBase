# -*- coding: utf-8 -*-
u"""Szenarien — BDD ohne Gherkin: sagt jede Prüfung, was sie erwartet?

DIE FRAGE (Edgar, 26.08.2026)
=============================
    „github copilot / cursor IDE hat tools zur BDD Muster Programmierung.
     Macht es sinn, dass ich die anwende?"

Gemessen statt geraten. Am Ursprungsprojekt:

    1538 Prüfmethoden, 368 Prüfklassen
    88 % tragen bereits einen SATZ als Namen
       (`test_ausgeblendete_person_bleibt_ausgeblendet`)
    50 von 60 Werkzeugen haben einen `Anlassfall` — wörtlich Given/When/Then

Die Substanz von BDD war also da, die Schreibweise auch. Was fehlte, waren
die LÜCKEN: 179 Seiten und Endpunkte ohne jede Abnahme, ein Werkzeug ohne
Beispiel, und 12 % Prüfungen, deren Name nichts erwartet (`test_basic`,
`test_it_works`).

Ein Rahmenwerk hätte daran nichts geändert — Gherkin schreibt keine
fehlenden Prüfungen. Deshalb dieses Werkzeug statt `pytest-bdd`: Es prüft
die drei Zusicherungen, die BDD wirklich gibt.

DIE DREI
========
1. **Jede Regel hat ein Beispiel.** Ein Werkzeug ohne `Anlassfall` und
   ohne Begründung ist eine Behauptung.
2. **Jeder Prüfungsname nennt das erwartete Verhalten.** `test_grid` sagt
   nichts; wer ihn rot sieht, muss den Rumpf lesen.
3. **Keine Prüfung ohne Zusicherung.** Ein Testkörper, der nichts
   behauptet, meldet grün, egal was passiert — die teuerste Sorte.

WAS ES NICHT PRÜFT
==================
Ob die Zusicherung die RICHTIGE ist. Das kann kein Werkzeug; dafür gibt
es den Anlassfall, der den Fall vorführt.
"""
from __future__ import annotations

import ast

from ..testsatz import Testsatz
from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug
from .pruefcode import Pruefcode

#: KEINE DATEINAMEN-LISTE MEHR (27.08.2026)
#: =======================================
#: Hier standen ``PRUEFORTE`` und ``PRUEFDATEI``: Ein Prüf-Modul war, was
#: ``test_`` heißt oder unter ``tests/`` liegt.
#:
#: Das war ein Behelf gegen einen Fehlalarm vom 26.08.2026 — der erste
#: Wurf nahm auch ``*_test.py`` und meldete zwei Verstösse in
#: ``app/views/cameras/connection_test.py``, einer ANSICHT.
#:
#: Der Behelf kostete mehr, als er einbrachte: Gemessen übersah er **73
#: Prüfmethoden** in djangoBase, darunter ALLE Grundtests
#: (``grundtests.py``, ``befundgrenzen.py``, ``endpunkttests.py``,
#: ``leistungstests.py``). Wer die Regeln des Hauses prüft, entging der
#: Prüfung, weil seine Datei nicht so heißt wie die anderen.
#:
#: Jetzt entscheidet ``Pruefcode`` über die VERERBUNG. Das findet mehr und
#: ist zugleich genauer: ``class ConnectionTester:`` hat gar keine Basis
#: und fällt von selbst heraus.

#: So viele Wörter braucht der ERGEBNISTEIL mindestens — also der Teil aus
#: dem Methodennamen, ohne die Klasse.
#:
#: ZWEI, NICHT DREI — EINE TEUER BEZAHLTE UNTERSCHEIDUNG (27.08.2026)
#: =================================================================
#: Hier standen zwei Zahlen für zwei verschiedene Dinge nebeneinander:
#: `szenarien` verlangte DREI Wörter in der ganzen Kennung (Klasse plus
#: Methode), `bdd-saetze` ZWEI im Ergebnisteil allein. Beim Zusammenlegen
#: habe ich die Drei auf den Ergebnisteil angewandt.
#:
#: Gemessen an CamTrack: **0 Befunde wurden zu 41**, und die 41 waren
#: falsch. „Reihenfolge stimmt" ist eine vollständige Aussage; sie hat nur
#: zwei Wörter. Ebenso „Setzt Verweis" und „Meldet Abbruchgrund".
#:
#: Eins ist ein Gegenstand („Versionen"), zwei tragen eine Aussage
#: („Versionen laden"). Mehr zu verlangen bestraft knappe, richtige Namen.
WOERTER_IM_ERGEBNIS = 2

#: Namen, die nichts erwarten — auch wenn sie lang genug sind.
NICHTSSAGEND = ('test_basic', 'test_it_works', 'test_works', 'test_ok',
                'test_simple', 'test_main', 'test_all', 'test_stuff',
                'test_smoke', 'test_case', 'test_1', 'test_2', 'test_x')

#: Aufrufe, die eine Zusicherung sind.
ZUSICHERND = ('assert', 'fail', 'skipTest', 'raises', 'assertRaises')


class Szenarienpruefer:
    u"""Beurteilt die Prüfmethoden EINER Klasse.

    KEIN NodeVisitor MEHR (27.08.2026)
    ==================================
    Vorher lief er selbst über den Baum und nahm jede Funktion, deren Name
    mit ``test`` anfängt — egal, wo sie stand. Das erzwang den
    Dateinamen-Filter davor, und der übersah 73 Prüfmethoden in
    djangoBase, weil `grundtests.py` nicht `test_` heißt.

    Jetzt sagt `Pruefcode` über die VERERBUNG, welche Klassen Prüfungen
    sind, und übergibt sie hier. Damit fällt beides weg: der Filter und
    die eigene Suche.
    """

    def __init__(self, datei):
        self.datei = datei
        self.befunde = []
        self._klasse = []

    def beurteilen_klasse(self, klasse, methoden):
        self._klasse = [klasse.name]
        for m in methoden:
            self._beurteilen(m)
        return self.befunde

    # ── Die beiden Fragen an eine Prüfmethode ───────────────────

    def _beurteilen(self, knoten):
        wo = '.'.join(self._klasse + [knoten.name])
        if not self._sagt_etwas(wo):
            self.befunde.append(Befund(
                '%s:%d' % (self.datei, knoten.lineno),
                u'Name nennt kein Verhalten: %s' % wo,
                u'Gelesen als „%s" — %s. Wer diesen Namen rot sieht, weiß '
                u'nicht, was kaputt ist; er muss den Rumpf lesen. Ein Name '
                u'wie `test_person_bleibt_nach_dem_merge_erhalten` sagt es '
                u'selbst.'
                % (Testsatz(wo).satz(),
                   ', '.join(self.maengel(wo)) or u'zu wenig Wörter'),
                Befund.HINWEIS))
        if not self._sichert_zu(knoten):
            self.befunde.append(Befund(
                '%s:%d' % (self.datei, knoten.lineno),
                u'Prüfung ohne Zusicherung: %s' % wo,
                u'Der Rumpf behauptet nichts — die Prüfung meldet grün, '
                u'egal was der Code tut. Das ist teurer als keine Prüfung, '
                u'weil sie Sicherheit vortäuscht.', Befund.FEHLER))

    @staticmethod
    def _sagt_etwas(voll):
        u"""Wird aus der Kennung ein Satz? Gelesen mit ``Testsatz``.

        EINE LESART, NICHT ZWEI (27.08.2026)
        ====================================
            „merge das mit dem was es schon gibt, keine Duplikate"

        Hier stand eine eigene Heuristik: Unterstriche zählen, gegen eine
        Liste nichtssagender Namen halten. Daneben entstand `bdd-saetze`
        mit derselben Frage, aber über ``Testsatz`` gelesen.

        Gemessen an djangoBase fanden beide **dieselben 16** Namen —
        `szenarien` zusätzlich 2 stumme Prüfungen, die `bdd-saetze` gar
        nicht sucht. Also: eine echte Teilmenge, und zwei Fassungen
        derselben Frage, die beim nächsten Anfassen auseinanderlaufen.

        Jetzt entscheidet ``Testsatz`` — dieselbe Lesart, die auch die
        Tests-Seite anzeigt. Was dort als Satz erscheint, gilt hier als
        Satz.
        """
        methode = voll.rsplit('.', 1)[-1]
        if methode in NICHTSSAGEND:
            return False
        return not Szenarienpruefer.maengel(voll)

    @staticmethod
    def maengel(voll):
        u"""Was dieser Kennung zum Satz fehlt — leere Liste, wenn nichts.

        Gemeldet wird nur, was OHNE Sprachwissen entscheidbar ist: ein
        Ergebnisteil aus zu wenigen Wörtern und ein fehlender Gegenstand.
        Auf ein Verb zu prüfen bräuchte ein Wörterbuch, und Fehlalarme
        sind hier teurer als fehlende Befunde.
        """
        satz = Testsatz(voll)
        aus = []
        if not satz.gegenstand():
            aus.append(u'ohne Gegenstand')
        if len(satz.ergebnis().split()) < WOERTER_IM_ERGEBNIS:
            aus.append(u'ohne Aussage')
        return aus

    @staticmethod
    def _sichert_zu(knoten):
        u"""Steht im Rumpf irgendwo eine Zusicherung?

        Auch ein ``with self.assertRaises(...)`` und ein ``assert`` zaehlen
        — und ein Aufruf einer eigenen Hilfsmethode, die ihrerseits
        zusichert, ist nicht erkennbar. Deshalb wird auch jeder Aufruf auf
        ``self`` als moegliche Zusicherung gewertet: Lieber einen Befund
        weniger als einen falschen.
        """
        for teil in ast.walk(knoten):
            if isinstance(teil, ast.Assert):
                return True
            if isinstance(teil, ast.Call):
                name = getattr(teil.func, 'attr', '') or \
                    getattr(teil.func, 'id', '')
                if any(name.startswith(z) for z in ZUSICHERND):
                    return True
                # Eigene Hilfsmethode: `self._pruefe_dass(...)`.
                eigner = getattr(teil.func, 'value', None)
                if (isinstance(eigner, ast.Name) and eigner.id == 'self'
                        and name.startswith('_')):
                    return True
            if isinstance(teil, ast.Raise):
                return True
        return False


class Szenarien(BefundWerkzeug):

    kriterium = 19
    slug = 'szenarien'
    titel = u'Szenarien: sagt jede Prüfung, was sie erwartet?'
    zweck = (u'BDD ohne Gherkin. Findet Prüfungen, deren Name kein Verhalten '
             u'nennt, und — schwerer — Prüfungen, die gar nichts zusichern '
             u'und deshalb immer grün melden.')
    abhilfe = (u'Vor einem Review und nach jedem Zuwachs an Prüfungen. Ein '
               u'Name, den man erst durch Lesen des Rumpfes versteht, kostet '
               u'genau dann Zeit, wenn man sie nicht hat: wenn er rot ist.')
    befund = (u'Im Ursprungsprojekt trugen 88 % der 1538 Prüfungen schon '
              u'einen Satz als Namen — das Muster war da, die Ausreisser '
              u'fielen nur nicht auf.')
    dauer = u'wenige Sekunden'

    anlassfall = Anlassfall(
        {'tests/test_a.py':
            'import unittest\n'
            '\n\n'
            'class A(unittest.TestCase):\n'
            '    def test_basic(self):\n'
            '        self.assertTrue(True)\n'
            '\n'
            '    def test_person_bleibt_nach_dem_merge_erhalten(self):\n'
            '        x = 1\n'
            '        print(x)\n'
            '\n'
            '    def test_person_wird_richtig_geloescht(self):\n'
            '        self.assertEqual(1, 1)\n'},
        mindestens=2, erwartet_in='test_basic',
        warum=u'Ein nichtssagender Name und eine Prüfung ohne Zusicherung — '
              u'die dritte macht beides richtig und darf nicht mitgemeldet '
              u'werden')

    # ------------------------------------------------------------------
    def pruefen(self, **_argumente):
        u"""Erst das ganze Projekt einlesen, dann urteilen.

        Zwei Durchgaenge, weil Vererbung sich nicht in einer Datei
        entscheidet: `Pruefcode` muss ALLE Klassen kennen, bevor es sagen
        kann, ob `JobsSeiteBasis` eine Pruefbasis ist.
        """
        eingelesen = list(self._einlesen())
        pruefcode = Pruefcode().lesen(eingelesen)
        befunde, dateien, methoden = [], 0, 0
        for kurz, baum in eingelesen:
            klassen = pruefcode.pruefklassen(baum)
            if not klassen:
                continue
            dateien += 1
            for klasse, eigene in klassen:
                methoden += len(eigene)
                pruefer = Szenarienpruefer(kurz)
                pruefer.beurteilen_klasse(klasse, eigene)
                befunde.extend(pruefer.befunde)

        ohne_zusicherung = sum(1 for b in befunde if b.gewicht == Befund.FEHLER)
        stumm = len(befunde) - ohne_zusicherung
        anteil = (100.0 * (methoden - stumm) / methoden) if methoden else 100.0
        kopf = ['%d Prüfdateien, %d Prüfmethoden' % (dateien, methoden),
                '%d ohne jede Zusicherung — die melden grün, egal was '
                'passiert' % ohne_zusicherung,
                '%d mit einem Namen, der kein Verhalten nennt (%.0f %% tun es)'
                % (stumm, anteil)]
        if not befunde:
            kopf.append('Keine — jede Prüfung nennt ihr Verhalten und '
                        'sichert es zu.')
        return Befundsatz(self.titel, kopf, befunde)

    def _einlesen(self):
        u"""``(kurzer Pfad, Syntaxbaum)`` fuer jede lesbare Datei."""
        for datei in self.projektdateien('.py'):
            try:
                yield (self.kurz(datei),
                       ast.parse(datei.read_text(encoding='utf-8',
                                                 errors='replace')))
            except (SyntaxError, OSError, ValueError):
                continue

