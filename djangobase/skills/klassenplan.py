# -*- coding: utf-8 -*-
u"""Klassenplan - was aus freien Modulfunktionen eine Klasse machen wuerde.

DIE LAGE (16.08.2026)
=====================
Kriterium 1 meldet Dateien, deren Funktionen denselben Zustand von Hand
durchreichen:

    def _matrizen_alt(grid, kombis): …
    def _batch_neu(grid, kombis): …
    def _alter_aufruf(grid, kombis, day_group): …

``grid`` und ``kombis`` sind keine Parameter, sondern Felder eines Objekts, das
es nicht gibt. Dieses Werkzeug rechnet die Umbauvorlage aus: welche Argumente
Felder werden, welche Funktionen dadurch Methoden, wie der Konstruktor aussieht.

FELD ODER PIPELINE - DIE PRUEFUNG, DIE DAZUGEHOERT
==================================================
Nicht jedes geteilte Argument ist ein Feld. In einer Kette

    aus = tabelle(aus)
    aus = schalter_pruefen(aus)

ist ``aus`` ein ZWISCHENERGEBNIS; eine Klasse mit ``self.aus`` waere eine
Verkleidung. Unterscheidbar ist es daran, ob die Funktion das Argument auch
ZURUECKGIBT. Die Spalte „art" sagt es je Argument.

Im shortlongx-Review waren alle 40 gemeldeten Faelle echte Felder - die Vermutung
„das sind bloss Pipelines" hielt der Messung nicht stand. Genau deshalb steht sie
hier als Spalte und nicht als stille Ausnahme.

SCHREIBT KEINEN CODE UM
=======================
Der Umbau bleibt Handarbeit: Bei jeder Funktion ist zu entscheiden, ob sie
wirklich zum Objekt gehoert, und ein automatisch eingefuegtes ``self.`` erzeugt
genau die Sorte stiller Fehler, gegen die der ganze Durchgang laeuft.
"""
import ast
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug


class Argument:
    """Ein Argumentname und die Frage: Feld oder Pipeline-Wert?"""

    def __init__(self, name):
        self.name = name
        self.traegt = 0             # wie viele Funktionen nehmen ihn
        self.gibt_zurueck = 0       # wie viele geben ihn auch zurueck

    @property
    def ist_pipeline(self):
        return bool(self.traegt) and self.gibt_zurueck >= self.traegt / 2

    @property
    def art(self):
        return "Pipeline" if self.ist_pipeline else "Feld"


class Klassenplan(Werkzeug):
    slug = "klassenplan"
    titel = "Freie Funktionen → Klasse: der Umbauplan"
    zweck = ("Für jede Datei mit gemeinsam getragenen Argumenten: welche zu "
             "Feldern werden, welche Funktionen zu Methoden — und ob es "
             "wirklich Felder sind oder nur Zwischenergebnisse einer Kette.")
    befund = ("Skripte mit sieben bis vierzehn Funktionen, die dieselben zwei "
              "bis vier Werte durchreichen. Das ist der Zustand eines Objekts, "
              "von Hand herumgetragen.")
    abhilfe = ("Klasse mit den genannten Feldern; die Funktionen werden "
               "Methoden. Wo die Spalte „Pipeline“ steht, NICHT umbauen — dort "
               "wäre die Klasse eine Verkleidung.")
    dauer = "3–8 s"
    kriterium = 1

    #: Ab so vielen tragenden Funktionen gilt ein Argument als Kandidat.
    FELD_AB = 2
    #: Ab so vielen Modulfunktionen lohnt die Frage ueberhaupt.
    AB_FUNKTIONEN = 3
    UNINTERESSANT = {"self", "cls", "request", "args", "kwargs",
                     "x", "y", "n", "i", "k", "v", "s", "t"}

    #: Vier freie Funktionen, die zwei Werte ueberall mitschleppen
    #: (``konto``, ``kurse``) und einen dritten nur an einer Stelle brauchen.
    #: Genau diese Unterscheidung ist der Zweck: Was wird Feld, was bleibt
    #: Parameter.
    anlassfall = Anlassfall(
        {"depot.py": '''def wert(konto, kurse):
    return sum(konto[s] * kurse[s] for s in konto)


def gewichtung(konto, kurse):
    gesamt = wert(konto, kurse)
    return {s: konto[s] * kurse[s] / gesamt for s in konto}


def abweichung(konto, kurse, ziel):
    ist = gewichtung(konto, kurse)
    return {s: ziel.get(s, 0) - ist.get(s, 0) for s in konto}


def bericht(konto, kurse):
    return "%.2f" % wert(konto, kurse)
'''},
        erwartet_in="konto",
        warum="Kriterium 1: was mehrfach durchgereicht wird, ist ein Feld — "
              "was nur einmal vorkommt, bleibt Parameter")

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None:
                continue
            funktionen = [k for k in d.baum.body
                          if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(funktionen) < self.AB_FUNKTIONEN:
                continue
            args = self._argumente(funktionen)
            geteilt = [a for a in args.values() if a.traegt >= self.FELD_AB]
            if not geteilt:
                continue
            geteilt.sort(key=lambda a: -a.traegt)
            felder = [a for a in geteilt if not a.ist_pipeline]
            zeilen.append({
                "datei": d.name, "zeile": funktionen[0].lineno,
                "funktionen": len(funktionen),
                "felder": ", ".join("%s (%d×)" % (a.name, a.traegt)
                                    for a in geteilt[:4]),
                "art": "Felder" if felder and len(felder) == len(geteilt)
                       else ("Pipeline" if not felder else "gemischt"),
                "klasse": self._klassenname(d.name),
            })
        zeilen.sort(key=lambda z: (z["art"] != "Felder", -z["funktionen"]))
        echte = [z for z in zeilen if z["art"] != "Pipeline"]
        return Ergebnis(
            ["datei", "zeile", "funktionen", "felder", "art", "klasse"], zeilen,
            "%d Dateien mit geteiltem Zustand, davon %d mit echten Feldern"
            % (len(zeilen), len(echte)),
            "„Pipeline“ heißt: Der Wert wird durchgereicht UND zurückgegeben — "
            "eine Kette, keine Klasse. Nur „Felder“ lohnt den Umbau.")

    def _argumente(self, funktionen):
        aus = {}
        for f in funktionen:
            zurueck = {k.value.id for k in ast.walk(f)
                       if isinstance(k, ast.Return) and isinstance(k.value, ast.Name)}
            for a in f.args.args:
                if a.arg in self.UNINTERESSANT:
                    continue
                arg = aus.setdefault(a.arg, Argument(a.arg))
                arg.traegt += 1
                if a.arg in zurueck:
                    arg.gibt_zurueck += 1
        return aus

    @staticmethod
    def _klassenname(dateiname):
        stamm = dateiname.replace("\\", "/").split("/")[-1]
        stamm = stamm[:-3] if stamm.endswith(".py") else stamm
        return "".join(t.capitalize() for t in stamm.lstrip("_").split("_"))
