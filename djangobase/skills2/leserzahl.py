# -*- coding: utf-8 -*-
u"""Leserzahl - wie viele Funktionen lesen dieses Rueckgabe-Woerterbuch?

WOZU (16.08.2026)
=================
Kriterium 11 verlangt eine Klasse fuer ein Dictionary mit mehr als drei festen
Schluesseln, das DURCH MEHRERE FUNKTIONEN geht. Die erste Haelfte der Bedingung
zaehlt jedes Pruefwerk mit; die zweite fast keines - und ohne sie steht auf der
Liste, was gar keinen Datentyp bildet.

DIE ZAEHLWEISE IST DREIMAL DANEBENGEGANGEN
==========================================
An 68 Befunden gemessen, jedes Mal mit einem anderen Ergebnis:

    nur das eigene Modul        62 von 68 „hoechstens ein Leser"
    reiner Namensabgleich        1 von 68  (272 „Leser" fuer ``kennzahlen``)
    Modul + Importeure          51 von 68 haben zwei oder mehr
    … nach Name geschluesselt   alles falsch: ``kennzahlen`` gibt es fuenfmal,
                                die Aufrufe addierten sich zu einem Zaehler
    … ohne Methoden             eine Methode mit zwei Aufrufern zaehlte null

Was uebrig bleibt und hier steht:

    * Schluessel ist ``(Datei, Funktionsname)`` - nie der Name allein.
    * Ein fremdes Modul zaehlt nur, wenn es den Namen IMPORTIERT.
    * Methoden brauchen keinen Import; bei eindeutigem Namen zaehlen alle
      ``x.name()``-Aufrufe.
    * Die Modulebene ist ein Leser wie jede Funktion.

Das Werkzeug ZEIGT die Zahlen; es aendert nichts. Wer eine Ausnahme darauf
stuetzt, kann sie hier nachrechnen.
"""
import ast
from collections import Counter

from .werkzeug import Ergebnis, Werkzeug2


class Leserzaehlung:
    """Der Index: wer ruft welche Funktion - und darf das ueberhaupt."""

    def __init__(self, baeume):
        #: {relativer Pfad: Syntaxbaum}
        self.baeume = baeume
        self._zahlen = None

    @property
    def zahlen(self):
        if self._zahlen is None:
            self._zahlen = self._sammeln()
        return self._zahlen

    # ---- Aufbau -------------------------------------------------------------
    def _sammeln(self):
        importiert, eigene, methoden = {}, set(), {}
        for name, baum in self.baeume.items():
            for k in ast.walk(baum):
                if isinstance(k, ast.ImportFrom):
                    for a in k.names:
                        importiert.setdefault(a.name, set()).add(name)
                elif isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    eigene.add((name, k.name))
                elif isinstance(k, ast.ClassDef):
                    for m in k.body:
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methoden.setdefault(m.name, set()).add(name)
        eindeutig = {n: next(iter(w)) for n, w in methoden.items() if len(w) == 1}
        aus = {}
        for name, baum in self.baeume.items():
            for traeger in self._traeger(baum):
                wer = "%s:%s" % (name, getattr(traeger, "name", "<modulebene>"))
                for k in ast.walk(traeger):
                    if not isinstance(k, ast.Call):
                        continue
                    gerufen = self._name_von(k.func)
                    if not gerufen or gerufen == getattr(traeger, "name", None):
                        continue
                    if isinstance(k.func, ast.Attribute) and gerufen in eindeutig:
                        aus.setdefault((eindeutig[gerufen], gerufen),
                                       set()).add(wer)
                        continue
                    for (heimat, fname) in eigene:
                        if fname == gerufen and (
                                name == heimat or
                                name in importiert.get(gerufen, set())):
                            aus.setdefault((heimat, gerufen), set()).add(wer)
        return {s: sorted(v) for s, v in aus.items()}

    @staticmethod
    def _traeger(baum):
        """Jede Funktion PLUS die Modulebene - beide koennen Leser sein."""
        aus = [k for k in ast.walk(baum)
               if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))]
        aus.append(ast.Module(
            body=[k for k in baum.body
                  if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef))],
            type_ignores=[]))
        return aus

    @staticmethod
    def _name_von(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return ""


class LeserzahlWerkzeug(Werkzeug2):
    slug = "leserzahl"
    titel = "Rückgabe-Wörterbücher: wie viele Leser?"
    zweck = ("Zählt je Rückgabe-Dictionary, wie viele Funktionen es wirklich "
             "lesen — die zweite Hälfte der Kriterium-11-Bedingung.")
    befund = ("An 68 Befunden gemessen: Die Zählweise ging dreimal daneben, "
              "bevor sie stimmte (nur eigenes Modul: 62 von 68 hätten höchstens "
              "einen Leser; reiner Namensabgleich: 272 „Leser“ für eine "
              "Funktion ``kennzahlen``). Deshalb steht sie hier nachrechenbar.")
    abhilfe = ("Zwei oder mehr Leser: Klasse bauen (Fixer „Rückgabe-Dictionary "
               "in eine Klasse überführen“). Einer oder keiner: liegen lassen — "
               "das ist kein Datentyp, der durch das Programm wandert.")
    kriterium = 11
    dauer = "30–45 s"

    MIN_SCHLUESSEL = 4
    SPALTEN = ("datei", "funktion", "schlüssel", "leser", "wer liest")

    def laufen(self):
        baeume = {}
        for d in self.dateien(".py"):
            if d.baum is not None:
                baeume[d.name] = d.baum
        zaehlung = Leserzaehlung(baeume)
        zeilen, verteilung = [], Counter()
        for name, baum in baeume.items():
            for f in ast.walk(baum):
                if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for k in ast.walk(f):
                    if not isinstance(k, ast.Return) or \
                            not isinstance(k.value, ast.Dict):
                        continue
                    feste = [s.value for s in k.value.keys
                             if isinstance(s, ast.Constant) and
                             isinstance(s.value, str)]
                    if len(feste) < self.MIN_SCHLUESSEL:
                        continue
                    leser = zaehlung.zahlen.get((name, f.name), [])
                    verteilung[min(len(leser), 3)] += 1
                    zeilen.append({
                        "datei": name, "funktion": f.name,
                        "schlüssel": len(feste), "leser": len(leser),
                        "wer liest": ", ".join(leser[:3]) or "—"})
        zeilen.sort(key=lambda z: (-z["leser"], -z["schlüssel"]))
        mehrere = sum(n for k, n in verteilung.items() if k >= 2)
        return Ergebnis(
            list(self.SPALTEN), zeilen,
            "%d Rückgabe-Wörterbücher mit mindestens %d Schlüsseln; %d davon "
            "haben zwei oder mehr Leser und erfüllen Kriterium 11 wirklich."
            % (len(zeilen), self.MIN_SCHLUESSEL, mehrere),
            "Ein einzelner Leser ist kein Datentyp: Dort bleibt das Dictionary "
            "ein lokales Zwischenergebnis.")
