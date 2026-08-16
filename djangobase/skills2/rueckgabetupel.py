# -*- coding: utf-8 -*-
u"""RueckgabeTupel - Datensaetze, die als Tupel aus einer Funktion kommen.

    Kriterium 10 des Auftrags: „Datensatz mit mehr als drei Feldern, der seine
    Funktion verlaesst -> eigene Klasse"

WARUM MEHR ALS DREI
===================
Bis drei Werte haelt man die Reihenfolge im Kopf: ``(ok, wert, fehler)``. Ab
vier nicht mehr - und der Aufrufer schreibt:

    a, b, c, d, e = rechnen(...)

Vertauscht jemand beim Umbau zwei Rueckgabewerte, faellt das nicht auf: Es gibt
keinen Namen, an dem es sich reiben koennte. Eine Klasse (oder wenigstens ein
NamedTuple) macht daraus einen Fehler, den man sieht.

WAS NICHT GEMELDET WIRD
=======================
Tupel mit bis zu drei Feldern und Generatoren (``yield a, b, c, d``) - die
laufen meist direkt in eine Schleife, die sie sofort auspackt.
"""
import ast

from .werkzeug import Ergebnis, Werkzeug2


class RueckgabeTupel(Werkzeug2):
    slug = "rueckgabetupel"
    titel = "Rückgabe-Tupel mit vielen Feldern"
    zweck = ("Funktionen, die mehr als drei Werte als Tupel zurückgeben — der "
             "Aufrufer muss ihre Reihenfolge kennen.")
    befund = ("Ein vertauschtes Paar in einer fünfstelligen Rückgabe fällt "
              "nirgends auf: Es gibt keinen Namen, an dem es sich reiben könnte.")
    abhilfe = ("Klasse mit benannten Feldern; wenn es wirklich nur ein Datensatz "
               "ist, ein NamedTuple oder ein dataclass.")
    dauer = "3–8 s"
    kriterium = 10

    MIN_FELDER = 4

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None:
                continue
            for f in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                for r in [k for k in ast.walk(f) if isinstance(k, ast.Return)]:
                    wert = r.value
                    if not isinstance(wert, ast.Tuple):
                        continue
                    if len(wert.elts) < self.MIN_FELDER:
                        continue
                    zeilen.append({
                        "datei": d.name, "zeile": r.lineno, "funktion": f.name,
                        "felder": len(wert.elts),
                        "inhalt": self._beschreiben(wert)})
        zeilen.sort(key=lambda z: -z["felder"])
        return Ergebnis(
            ["datei", "zeile", "funktion", "felder", "inhalt"], zeilen,
            "%d Rückgabe-Tupel mit mehr als drei Feldern" % len(zeilen),
            "Faustregel: Was man beim Auspacken benennen muss, sollte schon "
            "beim Zurückgeben einen Namen haben.")

    @staticmethod
    def _beschreiben(tupel):
        """Die Elemente grob benennen, soweit sie einen Namen haben."""
        namen = []
        for e in tupel.elts:
            if isinstance(e, ast.Name):
                namen.append(e.id)
            elif isinstance(e, ast.Attribute):
                namen.append(e.attr)
            elif isinstance(e, ast.Constant):
                namen.append(repr(e.value)[:12])
            else:
                namen.append("…")
        return ", ".join(namen[:6])
