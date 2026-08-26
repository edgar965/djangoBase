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

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

#: Ordner-Teile, in denen Prüf-Code steht.
PRUEFORTE = ('tests', 'test', 'pruefungen')

#: NUR das Präfix, NICHT die Endung (berichtigt 26.08.2026)
#: ========================================================
#: Der erste Wurf nahm auch ``*_test.py`` — und meldete prompt zwei
#: Verstösse in ``app/views/cameras/connection_test.py``. Das ist eine
#: ANSICHT: `ConnectionTester.test_http_snapshot(ip, port, …)` probiert
#: Schnappschuss-Pfade an einer Kamera durch. Sie heisst nur so.
#:
#: Ein Werkzeug, das Produktivcode als Prüfung anmahnt, wird ignoriert —
#: und nimmt die echten vier daneben mit.
PRUEFDATEI = ('test_',)

#: So viele Wörter muss ein Prüfungsname mindestens haben, um ein Satz zu
#: sein. Drei, nicht fünf: `test_person_wird_geloescht` ist ein Satz.
WOERTER_MINDESTENS = 3

#: Namen, die nichts erwarten — auch wenn sie lang genug sind.
NICHTSSAGEND = ('test_basic', 'test_it_works', 'test_works', 'test_ok',
                'test_simple', 'test_main', 'test_all', 'test_stuff',
                'test_smoke', 'test_case', 'test_1', 'test_2', 'test_x')

#: Aufrufe, die eine Zusicherung sind.
ZUSICHERND = ('assert', 'fail', 'skipTest', 'raises', 'assertRaises')


class Szenarienpruefer(ast.NodeVisitor):
    u"""Liest EIN Prüf-Modul und beurteilt jede Prüfmethode darin."""

    def __init__(self, datei):
        self.datei = datei
        self.befunde = []
        self._klasse = []

    def visit_ClassDef(self, knoten):
        self._klasse.append(knoten.name)
        self.generic_visit(knoten)
        self._klasse.pop()

    def visit_FunctionDef(self, knoten):
        if knoten.name.startswith('test'):
            self._beurteilen(knoten)
        self.generic_visit(knoten)

    # ── Die beiden Fragen an eine Prüfmethode ───────────────────

    def _beurteilen(self, knoten):
        wo = '.'.join(self._klasse + [knoten.name])
        if not self._sagt_etwas(wo):
            self.befunde.append(Befund(
                '%s:%d' % (self.datei, knoten.lineno),
                u'Name nennt kein Verhalten: %s' % wo,
                u'Wer diesen Namen rot sieht, weiß nicht, was kaputt ist — '
                u'er muss den Rumpf lesen. Ein Name wie '
                u'`test_person_bleibt_nach_dem_merge_erhalten` sagt es '
                u'selbst.', Befund.HINWEIS))
        if not self._sichert_zu(knoten):
            self.befunde.append(Befund(
                '%s:%d' % (self.datei, knoten.lineno),
                u'Prüfung ohne Zusicherung: %s' % wo,
                u'Der Rumpf behauptet nichts — die Prüfung meldet grün, '
                u'egal was der Code tut. Das ist teurer als keine Prüfung, '
                u'weil sie Sicherheit vortäuscht.', Befund.FEHLER))

    @staticmethod
    def _sagt_etwas(voll):
        u"""Der GANZE Name — Klasse UND Methode (berichtigt 26.08.2026).

        Der erste Wurf sah nur die Methode und meldete 52 Prüfungen an.
        Nachgesehen sind die meisten davon im Zusammenhang tadellos::

            KameraUndPerson.test_nur_bekannte
            CosineSimilarityTests.test_identical_vectors
            PointInPolygonTests.test_inside_square

        Der Satz steht dort verteilt: Die Klasse nennt den Gegenstand, die
        Methode den Fall. Genau so meldet unittest sie auch, wenn eine rot
        wird — als ``Klasse.methode``. Wer nur die Methode beurteilt,
        verlangt, dass der Gegenstand zweimal dasteht.

        Was damit trotzdem auffällt, ist der echte Fall: ``A.test_basic``
        sagt auch mit Klasse nichts, und ``test_yolo`` ohne Klasse erst
        recht.
        """
        methode = voll.rsplit('.', 1)[-1]
        if methode in NICHTSSAGEND:
            return False
        return voll.replace('.', '_').count('_') >= WOERTER_MINDESTENS

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
        befunde, dateien, methoden = [], 0, 0
        for datei in self.projektdateien('.py'):
            kurz = self.kurz(datei)
            if not self._ist_pruefcode(kurz):
                continue
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8',
                                                 errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            dateien += 1
            methoden += sum(1 for k in ast.walk(baum)
                            if isinstance(k, ast.FunctionDef)
                            and k.name.startswith('test'))
            pruefer = Szenarienpruefer(kurz)
            pruefer.visit(baum)
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

    @staticmethod
    def _ist_pruefcode(kurz):
        teile = [t.lower() for t in kurz.replace('\\', '/').split('/')]
        name = teile[-1]
        return (any(t in PRUEFORTE for t in teile[:-1])
                or any(m in name for m in PRUEFDATEI))
