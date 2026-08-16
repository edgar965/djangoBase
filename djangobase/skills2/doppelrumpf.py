# -*- coding: utf-8 -*-
u"""Doppelrumpf - zeichengleiche Funktions- und Klassenrumpfe finden.

WAS ES GEFUNDEN HAT (shortlongx, 16.08.2026)
============================================
Vier Werkzeuge, die je einen Import-Befehl gegen absichtlich beschaedigten Code
fahren, trugen denselben Ablauf Zeile fuer Zeile viermal. Dabei faellt auf, was
Duplikate wirklich kosten: Als der Befehl umgebaut wurde, zeigte die
Schadensliste EINES der vier ins Leere - drei Tage lang war das eine Sicherung,
die keine mehr war, und niemandem fiel es auf.

Weitere Funde derselben Art: dieselbe „wo endet der Import-Kopf?"-Funktion in
fuenf Werkzeugen (in drei davon OHNE die Begruendung, warum sie ueber den
Syntaxbaum gehen muss), derselbe Zugriff auf den System-Speicher in drei.

WORAUF ZU ACHTEN IST
====================
Zeichengleich heisst nicht austauschbar. Zwei der gefundenen Paare hatten
dieselbe Rechnung, aber verschiedene Signaturen; beim Zusammenlegen muss man die
Aufrufer mitnehmen, sonst wandert der Fehler nur.

Der Vergleich laeuft ueber den Syntaxbaum OHNE Docstrings - sonst gelten zwei
identische Funktionen als verschieden, nur weil eine besser erklaert ist.
"""
import ast
from collections import defaultdict

from .werkzeug import Ergebnis, Werkzeug2


class Doppelrumpf(Werkzeug2):
    slug = "doppelrumpf"
    titel = "Gleiche Rümpfe (Duplikate)"
    zweck = ("Funktionen und Klassen mit zeichengleichem Rumpf — über alle "
             "Dateien hinweg, Docstrings ausgenommen.")
    befund = ("Vier Gegenproben-Werkzeuge trugen denselben Ablauf viermal. Als "
              "der geprüfte Befehl umgebaut wurde, lief eine davon ins Leere — "
              "unbemerkt, weil sie niemand von selbst startet.")
    abhilfe = ("Zusammenlegen — aber die Signaturen vergleichen: Zeichengleich "
               "heißt nicht austauschbar. Danach jeden Aufrufer einmal fahren.")
    dauer = "5–12 s"
    kriterium = 6

    #: Rumpfe unter dieser Zeilenzahl sind zu klein, um etwas auszusagen
    #: (``return self.x`` steht zu Recht ueberall).
    MINDEST_ZEILEN = 4

    def laufen(self):
        gruppen = defaultdict(list)
        for d in self.dateien():
            if d.baum is None:
                continue
            for k in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef):
                if self._laenge(k) < self.MINDEST_ZEILEN:
                    continue
                schluessel = self._fingerabdruck(k)
                if schluessel:
                    gruppen[schluessel].append((d.name, k.lineno, k.name,
                                                self._laenge(k)))
        zeilen = []
        for eintraege in gruppen.values():
            if len(eintraege) < 2:
                continue
            datei, zeile, name, laenge = eintraege[0]
            weitere = "; ".join("%s:%d %s" % (f, z, n) for f, z, n, _ in eintraege[1:4])
            zeilen.append({"datei": datei, "zeile": zeile, "name": name,
                           "kopien": len(eintraege), "zeilen": laenge,
                           "weitere": weitere})
        zeilen.sort(key=lambda z: (-z["kopien"], -z["zeilen"]))
        gesamt = sum(z["kopien"] - 1 for z in zeilen)
        return Ergebnis(
            ["datei", "zeile", "name", "kopien", "zeilen", "weitere"], zeilen,
            "%d Gruppen, %d überzählige Kopien" % (len(zeilen), gesamt),
            "Erfahrungsgemäß wird bei einem Fehler nur EINE Kopie repariert. "
            "Je größer der Rumpf, desto teurer die Doppelung.")

    @staticmethod
    def _laenge(knoten):
        ende = getattr(knoten, "end_lineno", None) or knoten.lineno
        return ende - knoten.lineno + 1

    @staticmethod
    def _fingerabdruck(knoten):
        """Der Rumpf ohne Docstring als Zeichenkette - oder None."""
        koerper = [x for x in knoten.body
                   if not (isinstance(x, ast.Expr)
                           and isinstance(getattr(x, "value", None), ast.Constant)
                           and isinstance(x.value.value, str))]
        if not koerper:
            return None
        try:
            return ast.dump(ast.Module(body=koerper, type_ignores=[]))
        except (TypeError, ValueError):
            return None
