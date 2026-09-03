# -*- coding: utf-8 -*-
u"""ScheinDocstring - Text, der wie Doku aussieht und keine ist.

DER ANLASS (03.09.2026, shortlongx)
===================================
In ``werkzeug/pruefwerk/groesse.py`` stand::

    def _klassen_gehoeren_zusammen(self, d, klassen):
        \"\"\"… Unter %d Zeilen ist die Uebersicht ohnehin da. …\"\"\" % self.ZUSAMMEN_BIS

Ein String-Literal MIT Formatierung ist kein Docstring, sondern ein Ausdruck.
``__doc__`` bleibt ``None`` - ``help()`` zeigt nichts, kein Werkzeug findet den
Text, und die Zeichenkette wird bei jedem Aufruf gebaut und weggeworfen. In
jedem Editor sieht die Stelle aus wie jede andere Dokumentation.

DIE SCHARFE REGEL
=================
Gemeldet wird NUR, wo der erste Ausdruck an der **Wurzel** aus einem
String-Literal gebaut ist: ``"…" % x``, ein f-String, ``"…".format(…)``.

Die erste, grobe Fassung („der erste Ausdruck enthaelt irgendwo einen langen
String") meldete **71** Stellen statt einer - jedes
``parser.add_argument("--x", help="…")`` und jedes ``print("…")`` am
Funktionsanfang. Fehlalarme sind teurer als fehlende Befunde: Sie verdecken die
echten.

Reine stdlib.
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class ScheinDocstring(BefundWerkzeug):

    slug = 'schein-docstring'
    kriterium = 5
    titel = 'Docstrings, die keine sind'
    zweck = ('Findet Text am Anfang von Modul, Klasse oder Funktion, der '
             'formatiert wird und deshalb kein Docstring ist: ``__doc__`` bleibt '
             '``None``, und der Text wird bei jedem Aufruf gebaut und '
             'weggeworfen.')
    abhilfe = ('Immer, wenn eine Zahl aus dem Code in die Doku soll. Die '
               'Formatierung entfernen und den Wert bei seinem NAMEN nennen - '
               'dann steht die Zahl weiter an genau einer Stelle.')
    befund = ('In shortlongx eine Methode, deren 1.000 Zeichen Herleitung seit '
              'Monaten unsichtbar waren: ``\"\"\"… %d …\"\"\" % self.ZUSAMMEN_BIS``. '
              'Gefunden hatte es basedpyright als ``reportUnusedExpression`` - '
              'und der Autor hielt es zuerst fuer einen Fehlalarm.')
    dauer = 'Sekunden'

    anlassfall = Anlassfall(
        {"groesse.py": 'class Groesse:\n'
                       '    GRENZE = 300\n\n'
                       '    def passt(self, n):\n'
                       '        """Unter %d Zeilen ist es in Ordnung."""'
                       ' % self.GRENZE\n'
                       '        return n <= self.GRENZE\n',
         # Der AUSGENOMMENE Fall daneben: ein normaler Aufruf am
         # Funktionsanfang. Die grobe Fassung meldete davon 71 statt 1.
         "befehl.py": 'def argumente(p):\n'
                      '    p.add_argument("--datei", help="Welche Datei?")\n'},
        mindestens=1, hoechstens=1, erwartet_in="passt",
        warum="Tausend Zeichen Herleitung, die in keiner Hilfe erscheinen und "
              "bei jedem Aufruf neu gebaut und weggeworfen werden")

    def pruefen(self, **_argumente):
        dateien = self.dateien(".py")
        befunde = []
        for d in dateien:
            if d.baum is None:
                continue
            for traeger in self._traeger(d.baum):
                erster = traeger.body[0]
                if self._aus_literal(erster.value):
                    befunde.append(self._befund(d, traeger, erster))
        return Befundsatz(self.titel, ["%d Dateien" % len(dateien)], befunde)

    @staticmethod
    def _traeger(baum):
        u"""Alles, was einen Docstring haben KANN und mit einem Ausdruck beginnt."""
        arten = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        return [k for k in ast.walk(baum)
                if isinstance(k, arten) and k.body
                and isinstance(k.body[0], ast.Expr)
                and not (isinstance(k.body[0].value, ast.Constant)
                         and isinstance(k.body[0].value.value, str))]

    @staticmethod
    def _aus_literal(wert):
        u"""Ist dieser Ausdruck an der WURZEL aus einem String-Literal gebaut?"""
        if isinstance(wert, ast.JoinedStr):                       # f"…"
            return True
        if isinstance(wert, ast.BinOp) and isinstance(wert.op, ast.Mod):
            return (isinstance(wert.left, ast.Constant)
                    and isinstance(wert.left.value, str))
        if isinstance(wert, ast.Call) and isinstance(wert.func, ast.Attribute):
            ziel = wert.func.value                                # "…".format(…)
            return (wert.func.attr == 'format' and isinstance(ziel, ast.Constant)
                    and isinstance(ziel.value, str))
        return False

    def _befund(self, datei, traeger, erster):
        name = getattr(traeger, "name", "<Modul>")
        return Befund(
            "%s:%d" % (datei.name, erster.lineno),
            "%s hat keinen Docstring, nur einen Ausdruck" % name,
            self._hinweis(erster.value),
            Befund.WARNUNG)

    @staticmethod
    def _hinweis(wert):
        if isinstance(wert, ast.JoinedStr):
            return ("f vor den Anfuehrungszeichen entfernen und die Werte im "
                    "Text benennen statt einsetzen")
        return ("Formatierung entfernen und den Wert bei seinem Namen nennen - "
                "dann steht die Zahl weiter an genau einer Stelle")
