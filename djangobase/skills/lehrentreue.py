# -*- coding: utf-8 -*-
u"""Lehrentreue — hält der Code die Lehren, die sich prüfen lassen?

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „die lehren sollen die testcases beinhalten. du machst doch immer
     gleiche fixes, kannst du die werkzeuge dazu nicht speichern??"

Von 22 Lehren hatten zehn kein Werkzeug — sie hingen allein an der
Sorgfalt dessen, der gerade schreibt. Nachgesehen, welche davon sich
überhaupt mechanisch prüfen lassen:

    prüfbar                             nicht prüfbar
    ---------------------------------   ------------------------------
    keine-temp-dateien-im-system        values-list-statt-objekte
    unique-axis-vermeiden               fertige-antwort-zwischenspeichern
    bincount-statt-add-at               feld-oder-skalar
    kdtree-workers                      aequivalenz-beweisen
    meta-ordering-distinct              regressionsnetz-vorher

Die rechte Spalte sind Abwägungen und Vorgehensregeln („erst messen",
„vorher ein Netz aufnehmen") — die kann kein Werkzeug beantworten, und
so eines zu bauen hiesse, Fehlalarme zu erzeugen. Die linke Spalte ist
ein Muster im Quelltext, und das findet man.

EIN WERKZEUG, FÜNF REGELN
=========================
Nicht fünf Werkzeuge: Sie greifen alle auf denselben Syntaxbaum
derselben Dateien zu. Fünf Läufe über dasselbe wären fünfmal die Arbeit
für dieselbe Antwort — dieselbe Bauart wie `jsbefunde`, das zehn
Auffälligkeiten in EINEM Durchgang zählt.

Jeder Befund nennt die Lehre, gegen die er verstösst. Damit steht auf
beiden Seiten dasselbe: Die Lehre nennt ihr Werkzeug, das Werkzeug nennt
seine Lehre.
"""
from __future__ import annotations

import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

#: Wie ein Wegwerf-Verzeichnis angelegt wird, ohne ``dir=`` zu setzen.
TEMP_RUFE = ('mkdtemp', 'mkstemp', 'gettempdir', 'NamedTemporaryFile',
             'TemporaryDirectory', 'TemporaryFile')


class Verstoss:
    u"""Eine Stelle, die gegen eine Lehre verstösst."""

    __slots__ = ('datei', 'zeile', 'lehre', 'was', 'warum', 'gewicht')

    def __init__(self, datei, zeile, lehre, was, warum, gewicht):
        self.datei = datei
        self.zeile = zeile
        self.lehre = lehre
        self.was = was
        self.warum = warum
        self.gewicht = gewicht

    def als_befund(self):
        return Befund('%s:%d' % (self.datei, self.zeile),
                      u'%s (Lehre „%s")' % (self.was, self.lehre),
                      self.warum, self.gewicht)


class Regelsucher(ast.NodeVisitor):
    u"""Findet alle fünf Muster in EINEM Durchgang durch den Syntaxbaum."""

    def __init__(self, datei, quelle):
        self.datei = datei
        self.quelle = quelle
        self.verstoesse = []
        #: Nur wo cKDTree vorkommt, ist ein ``.query()`` eine Nachbarsuche.
        self.hat_kdtree = 'KDTree' in quelle

    # ── Hilfen ──────────────────────────────────────────────────

    @staticmethod
    def _name(knoten):
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        if isinstance(knoten, ast.Name):
            return knoten.id
        return ''

    @staticmethod
    def _kette(knoten):
        u"""``np.add.at`` -> ``'np.add.at'`` — so weit es Namen sind."""
        teile = []
        while isinstance(knoten, ast.Attribute):
            teile.append(knoten.attr)
            knoten = knoten.value
        if isinstance(knoten, ast.Name):
            teile.append(knoten.id)
        return '.'.join(reversed(teile))

    def _dazu(self, knoten, lehre, was, warum, gewicht=Befund.WARNUNG):
        self.verstoesse.append(Verstoss(self.datei, knoten.lineno, lehre,
                                        was, warum, gewicht))

    # ── Der eine Durchgang ──────────────────────────────────────

    def visit_Call(self, knoten):
        kette = self._kette(knoten.func)
        name = self._name(knoten.func)
        schluessel = {k.arg for k in knoten.keywords if k.arg}

        # 1. Wegwerf-Dateien im System-Temp statt im Projekt.
        if name in TEMP_RUFE and 'dir' not in schluessel:
            self._dazu(knoten, 'keine-temp-dateien-im-system',
                       u'%s() ohne dir=' % name,
                       u'Schreibt in den System-Temp. Ein abgebrochener Lauf '
                       u'lässt die Dateien dort liegen, und niemand findet '
                       u'sie wieder — `dir=` auf ein Projektverzeichnis '
                       u'setzen.')

        # 2. np.unique(..., axis=...) — teuer bei Paaren.
        if name == 'unique' and 'axis' in schluessel and 'np' in kette:
            self._dazu(knoten, 'unique-axis-vermeiden',
                       u'np.unique(..., axis=...)',
                       u'Sortiert zeilenweise und ist um ein Vielfaches '
                       u'langsamer. Paare als `a * n + b` zu int64 falten '
                       u'und darauf np.unique anwenden.')

        # 3. np.add.at — streuende Summen.
        if kette.endswith('add.at'):
            self._dazu(knoten, 'bincount-statt-add-at', u'np.add.at(...)',
                       u'Arbeitet elementweise. `np.bincount` rechnet '
                       u'dieselbe streuende Summe in einem Zug.')

        # 4. Nachbarsuche ohne workers=-1.
        if (self.hat_kdtree and name == 'query'
                and 'workers' not in schluessel):
            self._dazu(knoten, 'kdtree-workers', u'.query(...) ohne workers=',
                       u'Läuft auf EINEM Kern. `workers=-1` nutzt alle, '
                       u'ohne dass sich am Ergebnis etwas ändert.')

        # 5. values_list(...).distinct() ohne argumentloses order_by().
        if name == 'distinct' and self._ohne_ordnung(knoten.func):
            self._dazu(knoten, 'meta-ordering-distinct',
                       u'values_list(...).distinct() ohne order_by()',
                       u'`Meta.ordering` hängt die Sortierspalten an die '
                       u'Auswahl an — distinct sieht dann Zeilen, die sich '
                       u'nur dort unterscheiden, und liefert Duplikate. Ein '
                       u'argumentloses `.order_by()` davor hebt das auf.',
                       Befund.FEHLER)
        self.generic_visit(knoten)

    def _ohne_ordnung(self, knoten):
        u"""Steht in derselben Kette ein values_list, aber kein order_by?"""
        gesehen_values, gesehen_order = False, False
        while isinstance(knoten, ast.Attribute):
            knoten = knoten.value
            if isinstance(knoten, ast.Call):
                name = self._name(knoten.func)
                if name in ('values_list', 'values'):
                    gesehen_values = True
                elif name == 'order_by':
                    gesehen_order = True
                knoten = knoten.func
        return gesehen_values and not gesehen_order


class Lehrentreue(BefundWerkzeug):

    kriterium = 15
    slug = 'lehren-treue'
    titel = u'Lehrentreue: die prüfbaren Regeln'
    zweck = (u'Prüft die fünf Lehren, die sich am Quelltext ablesen lassen: '
             u'Wegwerf-Dateien im System-Temp, np.unique mit axis, np.add.at, '
             u'Nachbarsuche ohne workers, values_list().distinct() ohne '
             u'order_by().')
    abhilfe = (u'Nach jedem Umbau. Es sind die Fehler, die man beim zweiten '
               u'Mal genauso macht wie beim ersten — deshalb ein Werkzeug '
               u'und keine Erinnerung.')
    befund = (u'Im Ursprungsprojekt hingen zehn der 22 Lehren an gar keiner '
              u'Prüfung. Fünf davon sind Muster im Quelltext und damit '
              u'auffindbar; die anderen fünf sind Abwägungen, für die ein '
              u'Werkzeug nur Fehlalarme erzeugen würde.')
    dauer = u'wenige Sekunden'

    anlassfall = Anlassfall(
        {'rechnen.py':
            'import numpy as np\n'
            'import tempfile\n'
            'from scipy.spatial import cKDTree\n'
            '\n\n'
            'def machen(punkte, werte, index):\n'
            '    ordner = tempfile.mkdtemp()\n'
            '    baum = cKDTree(punkte)\n'
            '    abstand, nachbar = baum.query(punkte, k=2)\n'
            '    paare = np.unique(punkte, axis=0)\n'
            '    summe = np.zeros(10)\n'
            '    np.add.at(summe, index, werte)\n'
            '    return ordner, abstand, nachbar, paare, summe\n',
         'sauber.py':
            'import numpy as np\n'
            'import tempfile\n'
            '\n\n'
            'def machen(werte, index):\n'
            "    ordner = tempfile.mkdtemp(dir='projekt/tmp')\n"
            '    summe = np.bincount(index, weights=werte, minlength=10)\n'
            '    return ordner, summe\n'},
        mindestens=4, erwartet_in='add.at',
        warum=u'Vier verschiedene Muster in einer Datei — und die zweite '
              u'Datei macht dasselbe richtig und darf nicht mitgemeldet '
              u'werden')

    # ------------------------------------------------------------------
    def pruefen(self, **_argumente):
        befunde, gelesen = [], 0
        for datei in self.projektdateien('.py'):
            try:
                quelle = datei.read_text(encoding='utf-8', errors='replace')
                baum = ast.parse(quelle)
            except (SyntaxError, OSError, ValueError):
                continue
            gelesen += 1
            sucher = Regelsucher(self.kurz(datei), quelle)
            sucher.visit(baum)
            befunde.extend(v.als_befund() for v in sucher.verstoesse)

        je_lehre = {}
        for v in befunde:
            lehre = v.was.rsplit(u'„', 1)[-1].rstrip(u'")')
            je_lehre[lehre] = je_lehre.get(lehre, 0) + 1
        kopf = ['%d Dateien gelesen' % gelesen,
                '%d Verstoß/Verstöße gegen die fünf prüfbaren Lehren'
                % len(befunde)]
        for lehre, zahl in sorted(je_lehre.items(), key=lambda p: -p[1]):
            kopf.append('  %-32s %d' % (lehre, zahl))
        if not befunde:
            kopf.append('Keiner — die prüfbaren Lehren werden gehalten.')
        return Befundsatz(self.titel, kopf, befunde)
