# -*- coding: utf-8 -*-
u"""Wachstum - welche Bauform in einer Schleife WIRKLICH quadratisch waechst.

DIE MESSUNG STATT DER BEHAUPTUNG (16.08.2026)
=============================================
Ein Pruefwerk meldete 44 Stellen mit der Begruendung:

    „Jeder Durchlauf legt eine neue Liste an und kopiert die alte - der Aufwand
     waechst quadratisch mit der Zahl der Durchlaeufe."

Das ist eine Zahlenaussage ohne Messung, und sie ist falsch. Gemessen bei
vervierfachter Durchlaufzahl - linear waere Faktor 4, quadratisch 16:

    liste += [x]                 Faktor  3,0   linear
    liste.append(x)              Faktor  3,6   linear
    liste = liste + [x]          Faktor 15,0   QUADRATISCH
    s += "…"                     Faktor  4,4   linear
    s += "…" (zweite Referenz)   Faktor  5,9   linear
    "".join(teile)               Faktor  5,3   linear

``list.__iadd__`` mutiert IN PLACE - es ist ``extend``, kein Kopieren. Und
CPython optimiert ``s += x``, solange der String nur eine Referenz hat.
Quadratisch ist allein die NEUZUWEISUNG, die eine neue Liste erzeugt.

Dieses Werkzeug misst es NACH - auf der Maschine, auf der es laeuft. Wer die
Regel uebernimmt, soll die Zahl dazu haben und sie nicht glauben muessen.
"""
import timeit

from .werkzeug import Ergebnis, Werkzeug2


class Bauform:
    """Eine Schreibweise und wie sie sich bei vervierfachter Groesse verhaelt."""

    #: Linear waere dieser Faktor, quadratisch sein Quadrat.
    FAKTOR = 4

    def __init__(self, name, funktion, klein, urteil_erwartet):
        self.name = name
        self.funktion = funktion
        self.klein = klein
        self.urteil_erwartet = urteil_erwartet

    def messen(self, laeufe=20):
        gross = self.klein * self.FAKTOR
        a = timeit.timeit(lambda: self.funktion(self.klein), number=laeufe)
        b = timeit.timeit(lambda: self.funktion(gross), number=laeufe)
        return a, b, (b / a if a else 0.0)

    @staticmethod
    def urteil(faktor):
        """Linear waere 4, quadratisch 16 - die Schwellen liegen dazwischen.

        SIE MUESSEN WEIT GENUG AUSEINANDER: Mit einer Grenze bei 6 fiel die
        Textform mit zweiter Referenz (gemessen 5,9 bis 6,8 je nach Lauf) mal
        auf „linear", mal auf „dazwischen" - dasselbe Verhalten, zwei Urteile.
        Eine Messgroesse mit Rauschen braucht Abstand zur Grenze, sonst misst
        man die Tagesform der Maschine (16.08.2026)."""
        if faktor < 8:
            return "linear"
        if faktor > 12:
            return "QUADRATISCH"
        return "dazwischen"


def _liste_plusgleich(n):
    aus = []
    for i in range(n):
        aus += [i]
    return aus


def _liste_append(n):
    aus = []
    for i in range(n):
        aus.append(i)
    return aus


def _liste_neuzuweisung(n):
    aus = []
    for i in range(n):
        aus = aus + [i]           # DIESE Form kopiert wirklich
    return aus


def _text_plusgleich(n):
    s = ""
    for _i in range(n):
        s += "x" * 20
    return s


def _text_join(n):
    teile = []
    for _i in range(n):
        teile.append("x" * 20)
    return "".join(teile)


def _text_gehalten(n):
    """Eine zweite Referenz verhindert die CPython-Optimierung."""
    s, halten = "", []
    for i in range(n):
        s += "x" * 20
        if i % 500 == 0:
            halten.append(s)
    return s


class Wachstum(Werkzeug2):
    slug = "wachstum"
    titel = "Wächst das wirklich quadratisch?"
    zweck = ("Misst die üblichen Schleifen-Bauformen bei vervierfachter Größe. "
             "Linear wäre Faktor 4, quadratisch 16.")
    befund = ("44 Befunde behaupteten „wächst quadratisch“ für ``x += [...]`` — "
              "gemessen Faktor 3,0. Quadratisch ist allein ``x = x + [...]``.")
    abhilfe = ("Nur die Neuzuweisung ersetzen. ``+=`` mutiert in place; die "
               "Textform optimiert CPython. Wer ``join`` will, misst vorher.")
    dauer = "3–10 s"
    kriterium = 12

    FORMEN = (
        ("liste += [x]", _liste_plusgleich, 2000, "linear"),
        ("liste.append(x)", _liste_append, 2000, "linear"),
        ("liste = liste + [x]", _liste_neuzuweisung, 2000, "QUADRATISCH"),
        ("s += '…'", _text_plusgleich, 4000, "linear"),
        ("''.join(teile)", _text_join, 4000, "linear"),
        ("s += '…' (2. Referenz)", _text_gehalten, 4000, "linear"),
    )

    def laufen(self):
        zeilen, abweichungen = [], 0
        for name, fn, klein, erwartet in self.FORMEN:
            form = Bauform(name, fn, klein, erwartet)
            a, b, faktor = form.messen()
            urteil = form.urteil(faktor)
            if urteil != erwartet:
                abweichungen += 1
            zeilen.append({
                "bauform": name,
                "klein": "%d× %.4f s" % (klein, a),
                "groß": "%d× %.4f s" % (klein * 4, b),
                "faktor": round(faktor, 1),
                "urteil": urteil,
                "erwartet": erwartet,
            })
        return Ergebnis(
            ["bauform", "klein", "groß", "faktor", "urteil", "erwartet"], zeilen,
            "6 Bauformen gemessen, %d weichen von der Erwartung ab" % abweichungen,
            "Linear = Faktor 4, quadratisch = 16. Weicht etwas ab, ist es die "
            "Maschine oder eine neue Python-Fassung — dann gilt die Messung "
            "hier, nicht die Tabelle im Kopf.")
