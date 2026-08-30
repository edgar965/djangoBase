# -*- coding: utf-8 -*-
u"""Übersprungen — jede Prüfung, die grün meldet, ohne geprüft zu haben.

DIE ANSAGE (Edgar, mehrfach)
============================
    „kein Skip test"
    „ein übersprungener Test soll nie grün melden"
    „der test soll sie alle melden"

WAS AM 26.08.2026 DAHINTER STECKTE
==================================
An CamTrack gemessen, nachdem der Schalter einmal gesetzt wurde:

    sechs Prüfungen hinter ``SMART_SEARCH_INTEGRATION``
      fünf davon liefen in 21 s durch und BESTANDEN — der Schalter hielt
      sie ohne Grund zurück
      eine konnte NIE laufen: ein ``django.test.TestCase``, das die leere
      Testdatenbank nach Aufnahmen fragte und sich mit „Keine Recordings
      in DB" selbst übersprang — mit Schalter genau wie ohne

Das ist der eigentliche Schaden: Der Schalter versprach einen Lauf, den es
nicht gab. Ohne Schalter sah die Meldung genauso aus wie mit, also hat es
niemand gemerkt. Dazu kamen drei Skips in djangoBase selbst, von denen
zwei sich in eine gewöhnliche Zusicherung umschreiben liessen und einer
eine echte Abweichung verdeckte (CamTracks ``base.html`` erbte nicht).

WAS DIESES WERKZEUG MELDET
==========================
Jede Stelle im Prüf-Code, an der ein Lauf abgekürzt wird:

    @unittest.skip / @skipIf / @skipUnless   Klassen- und Methoden-Dekorator
    self.skipTest(...)                       im Rumpf
    pytest.skip(...)                         falls pytest im Spiel ist

MIT UNTERSCHIEDLICHEM GEWICHT, denn nicht jeder Fall wiegt gleich:

    FEHLER    ``skipUnless``/``skipIf`` auf einer Umgebungsvariable —
              das ist ein Schalter, den im Alltag niemand setzt. Genau
              die Bauart, die sechs Prüfungen ein Jahr lang stillgelegt
              hat.
    WARNUNG   ``skipTest`` im Rumpf — „nichts zu prüfen gefunden". Oft
              gutgemeint, aber es verdeckt, ob die Bedingung noch stimmt
              oder der Sucher kaputt ist.
    HINWEIS   ``@skip`` ohne Bedingung — dauerhaft stillgelegt, immerhin
              sichtbar.

DIE ALTERNATIVE STEHT IM BEFUND
===============================
Ein Zustand, in dem es nichts zu prüfen gibt, ist ein ERGEBNIS und lässt
sich zusichern::

    # statt:
    if not gefunden:
        self.skipTest('keine fa-*-Icons im Projekt')
    self.assertTrue(eingebunden)

    # so:
    self.assertTrue(nicht_gefunden or eingebunden)

Läuft immer, prüft immer, und wenn der Sucher kaputtgeht, fällt es auf.
"""
from __future__ import annotations

import ast

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall

#: Ordner-Teile, in denen Prüf-Code steht.
PRUEFORTE = ('tests', 'test', 'pruefungen')

#: Datei-Namensmuster für Prüf-Code.
PRUEFDATEI = ('test_', '_test')

#: Die Dekoratoren, die einen ganzen Fall stilllegen.
DEKORATOREN = ('skip', 'skipIf', 'skipUnless')

#: Aufrufe im Rumpf, die mitten im Lauf abbrechen.
RUMPFAUFRUFE = ('skipTest', 'skip')


class Sprungstelle:
    u"""Eine Stelle, an der ein Lauf abgekürzt wird."""

    __slots__ = ('datei', 'zeile', 'art', 'wobei', 'grund')

    def __init__(self, datei, zeile, art, wobei, grund=''):
        self.datei = datei
        self.zeile = zeile
        self.art = art
        self.wobei = wobei
        self.grund = grund

    @property
    def ort(self):
        return '%s:%d' % (self.datei, self.zeile)

    def gewicht(self):
        u"""Wie schwer wiegt diese Stelle?

        Der Schalter auf einer Umgebungsvariablen ist der schwerste Fall:
        Er sieht nach „bei Bedarf einschaltbar" aus, ist im Alltag aber
        eine Abschaltung — und verdeckt, dass der Test womöglich gar nicht
        laufen KANN.
        """
        if self.art == 'umgebung':
            return Befund.FEHLER
        if self.art in ('rumpf', 'versteckt'):
            return Befund.WARNUNG
        return Befund.HINWEIS


class Sprungsucher(ast.NodeVisitor):
    u"""Findet alle Sprungstellen in EINEM Prüf-Modul."""

    def __init__(self, datei):
        self.datei = datei
        self.stellen = []
        self._wobei = []
        #: (Zeile, Spalte) der Aufrufe, die schon als Dekorator gemeldet
        #: wurden. `generic_visit` laeuft danach noch einmal durch die
        #: Dekoratorliste — ohne diese Menge staende jeder zweimal da.
        self._gemeldet = set()

    # ── Dekoratoren ─────────────────────────────────────────────

    @staticmethod
    def _name(knoten):
        u"""``unittest.skipUnless`` -> ``'skipUnless'``."""
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Call):
            return Sprungsucher._name(knoten.func)
        return ''

    @staticmethod
    def _liest_umgebung(knoten):
        u"""Hängt die Bedingung an einer Umgebungsvariablen OHNE Vorgabe?

        EINSCHALTER ODER AUSSCHALTER (26.08.2026)
        =========================================
        Das ist der Unterschied zwischen einem Befund und einem Fehlalarm,
        und mein erster Wurf hat ihn nicht gemacht. Beide Formen sahen
        gleich aus::

            os.environ.get('SMART_SEARCH_INTEGRATION')          opt-in
            os.environ.get('CAMTRACK_RUN_GPU_TESTS', '1') == '1'  opt-out

        Die erste liefert ohne Zutun ``None`` — die Prüfung läuft NIE, bis
        jemand den Schalter kennt und setzt. Genau die Bauart, die sechs
        Prüfungen stillgelegt hat.

        Die zweite hat eine Vorgabe, die sie einschaltet: Sie läuft immer,
        bis jemand sie ausdrücklich abschaltet. Nachgemessen — die drei
        Fälle dahinter laufen und bestehen in 33 s.

        Der zweite Wert im ``get``-Aufruf ist also der ganze Unterschied.
        Ein Werkzeug, das beide gleich meldet, wird ignoriert — und mit ihm
        der echte Fall daneben.
        """
        for teil in ast.walk(knoten):
            if not isinstance(teil, ast.Call):
                continue
            if Sprungsucher._name(teil.func) not in ('get', 'getenv'):
                continue
            if 'environ' not in ast.dump(teil) and 'getenv' not in ast.dump(teil):
                continue
            # Zwei Argumente = mit Vorgabe = Ausschalter, laeuft von selbst.
            if len(teil.args) >= 2 or teil.keywords:
                return False
            return True
        return False

    @staticmethod
    def _text(knoten):
        u"""Der erste Zeichenketten-Wert im Aufruf — meist der Grund."""
        for teil in ast.walk(knoten):
            if isinstance(teil, ast.Constant) and isinstance(teil.value, str):
                if len(teil.value) > 3:
                    return teil.value[:90]
        return ''

    def _dekoratoren(self, knoten):
        for deko in knoten.decorator_list:
            name = self._name(deko)
            if name not in DEKORATOREN:
                continue
            art = 'dauerhaft'
            if name in ('skipIf', 'skipUnless'):
                art = 'umgebung' if self._liest_umgebung(deko) else 'bedingt'
            self._gemeldet.add((deko.lineno, deko.col_offset))
            self.stellen.append(Sprungstelle(
                self.datei, deko.lineno, art,
                '.'.join(self._wobei + [knoten.name]), self._text(deko)))

    def visit_ClassDef(self, knoten):
        self._dekoratoren(knoten)
        self._wobei.append(knoten.name)
        self.generic_visit(knoten)
        self._wobei.pop()

    def visit_FunctionDef(self, knoten):
        self._dekoratoren(knoten)
        self._wobei.append(knoten.name)
        self.generic_visit(knoten)
        self._wobei.pop()

    def visit_Call(self, knoten):
        self._versteckter_waechter(knoten)
        if self._name(knoten.func) in RUMPFAUFRUFE:
            # `x.skip(...)` nur, wenn es nach unittest/pytest aussieht —
            # sonst faengt man jedes `warteschlange.skip()` mit.
            eigner = getattr(knoten.func, 'value', None)
            passt = (self._name(knoten.func) == 'skipTest'
                     or (isinstance(eigner, ast.Name)
                         and eigner.id in ('pytest', 'unittest')))
            if passt:
                self.stellen.append(Sprungstelle(
                    self.datei, knoten.lineno, 'rumpf',
                    '.'.join(self._wobei) or '?', self._text(knoten)))
        self.generic_visit(knoten)

    def _versteckter_waechter(self, knoten):
        u"""``unittest.skipUnless(...)`` als RUECKGABEWERT einer Hilfsfunktion.

        DER BLINDE FLECK (30.08.2026, 3DTools)
        ======================================
        Das Projekt hatte neun JS-Tests hinter einem Node-Waechter. Gemeldet
        wurden ZWEI — die beiden, die den Dekorator ausgeschrieben trugen. Die
        anderen sieben standen als::

            class Jsmodul:
                @staticmethod
                def ohne_node():
                    return unittest.skipUnless(shutil.which('node'), 'node fehlt')

            @Jsmodul.ohne_node()
            class KoerpernetzTest(unittest.TestCase):

        Fuer den Dekorator-Zweig heisst der Dekorator ``ohne_node`` und steht
        nicht in der Liste; der Rumpf-Zweig kannte nur ``skipTest``/``skip``.
        Ein Werkzeug, das sieben von neun Stillegungen uebersieht, meldet eine
        Zahl, die niemand nachrechnet — und die verbliebenen zwei sehen aus wie
        Einzelfaelle.

        Gemeldet wird als ``versteckt`` (WARNUNG): Der Waechter ist da, aber an
        der Klasse, die ihn traegt, ist er nicht zu sehen.
        """
        # NUR die BEDINGTEN Formen: `pytest.skip(...)` im Rumpf faengt der
        # Zweig darunter schon (RUMPFAUFRUFE), und beide zusammen meldeten
        # dieselbe Stelle zweimal — der eigene Test hat es gefangen.
        name = self._name(knoten.func)
        if name not in ('skipIf', 'skipUnless'):
            return
        if (knoten.lineno, knoten.col_offset) in self._gemeldet:
            return
        eigner = getattr(knoten.func, 'value', None)
        if not (isinstance(eigner, ast.Name)
                and eigner.id in ('unittest', 'pytest')):
            return
        self.stellen.append(Sprungstelle(
            self.datei, knoten.lineno, 'versteckt',
            '.'.join(self._wobei) or '?', self._text(knoten)))


class Uebersprungen(BefundWerkzeug):

    #: Kriterium 17 — „Testcases sauber erzeugen für alle wichtigen
    #: Funktionen". Eine Prüfung, die sich selbst überspringt, ist keine
    #: sauber erzeugte Prüfung. Ohne diese Zeile stünde das Werkzeug nur in
    #: der großen Tabelle und liefe beim Sammellauf „Logging & Tests" nicht
    #: mit — genau der Fehler, den dieser Block gerade hatte.
    kriterium = 17
    slug = 'uebersprungen'
    titel = u'Übersprungene Prüfungen'
    zweck = (u'Findet jede Stelle, an der eine Prüfung abgekürzt wird — '
             u'Dekorator, Umgebungsschalter oder skipTest im Rumpf. Ein '
             u'übersprungener Test meldet grün, ohne geprüft zu haben.')
    abhilfe = (u'Vor jedem Release und nach jedem Umbau an den Prüfungen. '
               u'Ein Schalter, den niemand setzt, ist eine Abschaltung.')
    befund = (u'Im Ursprungsprojekt sechs Prüfungen hinter EINER '
              u'Umgebungsvariablen: fünf liefen mit Schalter in 21 s durch '
              u'und bestanden, die sechste konnte gar nicht laufen — sie '
              u'fragte die leere Testdatenbank nach Aufnahmen.')
    dauer = u'wenige Sekunden'

    anlassfall = Anlassfall(
        {'tests/test_a.py':
            'import os\n'
            'import unittest\n'
            '\n\n'
            "@unittest.skipUnless(os.environ.get('ECHT'), 'nur mit ECHT=1')\n"
            'class MitSchalter(unittest.TestCase):\n'
            '    def test_eins(self):\n'
            '        self.assertTrue(True)\n'
            '\n\n'
            'class MitRumpf(unittest.TestCase):\n'
            '    def test_zwei(self):\n'
            "        self.skipTest('nichts gefunden')\n",
         'tests/test_b.py':
            'import unittest\n'
            '\n\n'
            'class OhneAlles(unittest.TestCase):\n'
            '    def test_drei(self):\n'
            '        self.assertTrue(True)\n'},
        mindestens=2, erwartet_in='ECHT',
        warum=u'Zwei Stellen in einer Datei — ein Umgebungsschalter auf der '
              u'Klasse und ein skipTest im Rumpf; die zweite Datei ist '
              u'sauber und darf nicht mitgemeldet werden')

    # ------------------------------------------------------------------
    def pruefen(self, **_argumente):
        befunde, dateien = [], 0
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
            sucher = Sprungsucher(kurz)
            sucher.visit(baum)
            for stelle in sucher.stellen:
                befunde.append(self._befund(stelle))

        schwer = sum(1 for b in befunde if b.gewicht == Befund.FEHLER)
        kopf = ['%d Prüfdateien gelesen' % dateien,
                '%d Stelle(n), an denen ein Lauf abgekuerzt wird' % len(befunde),
                '%d davon hängen an einer Umgebungsvariablen — ein Schalter, '
                'den im Alltag niemand setzt, ist eine Abschaltung' % schwer]
        if not befunde:
            kopf.append('Keine — jede Prüfung läuft wirklich.')
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _ist_pruefcode(kurz):
        teile = [t.lower() for t in kurz.replace('\\', '/').split('/')]
        name = teile[-1]
        return (any(t in PRUEFORTE for t in teile[:-1])
                or any(m in name for m in PRUEFDATEI))

    ART_TEXT = {
        'umgebung': u'Umgebungsschalter',
        'bedingt': u'Bedingung',
        'dauerhaft': u'dauerhaft stillgelegt',
        'rumpf': u'skipTest im Rumpf',
    }

    def _befund(self, stelle):
        was = u'%s: %s' % (self.ART_TEXT.get(stelle.art, stelle.art),
                           stelle.wobei)
        warum = stelle.grund or u'(kein Grund angegeben)'
        if stelle.art == 'umgebung':
            warum += (u' — läuft im Alltag NIE. Vor dem Entfernen einmal '
                      u'mit gesetztem Schalter fahren: Besteht die Prüfung, '
                      u'gehört der Schalter weg; überspringt sie sich '
                      u'weiterhin, kann sie gar nicht laufen.')
        elif stelle.art == 'rumpf':
            warum += (u' — „nichts zu prüfen" ist ein ERGEBNIS und lässt '
                      u'sich zusichern: `assertTrue(nichts_da or bedingung)` '
                      u'läuft immer und fällt auf, wenn der Sucher bricht.')
        return Befund(stelle.ort, was, warum, stelle.gewicht())
