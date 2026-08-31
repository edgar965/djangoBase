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
    s += "…"                     Faktor  4,0   linear
    s += "…" (zweite Referenz)   Faktor 14,3   QUADRATISCH
    "".join(teile)               Faktor  5,3   linear

``list.__iadd__`` mutiert IN PLACE - es ist ``extend``, kein Kopieren. Und
CPython optimiert ``s += x``, solange der String nur EINE Referenz hat.
Quadratisch ist die NEUZUWEISUNG, die eine neue Liste erzeugt - und die
Textform, sobald jemand den String nebenher festhaelt.

DIE ZEILE MIT DER ZWEITEN REFERENZ WAR SELBST FALSCH GEMESSEN (30.08.2026):
Sie stand hier als „Faktor 5,9 linear“ - und die Messfunktion hielt den String
nur bei jedem 500. Durchlauf fest. Damit mass sie weder den einen noch den
anderen Fall, landete bei 7,9 direkt auf der Urteilsschwelle (8) und wechselte
je nach Lauf zwischen zwei Urteilen. Ein Werkzeug, das gegen unbelegte Zahlen
antritt, hatte selbst eine.

Dieses Werkzeug misst es NACH - auf der Maschine, auf der es laeuft. Wer die
Regel uebernimmt, soll die Zahl dazu haben und sie nicht glauben muessen.
"""
import timeit

from .werkzeug import Ergebnis, Werkzeug


class Bauform:
    """Eine Schreibweise und wie sie sich bei vervierfachter Größe verhält."""

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
        """Linear wäre 4, quadratisch 16 - die Schwellen liegen dazwischen.

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
    """Eine zweite Referenz verhindert die CPython-Optimierung.

    BEI JEDEM DURCHLAUF, nicht bei jedem 500. (Befund 30.08.2026). Vorher
    stand hier ``if i % 500 == 0: halten.append(s)`` - damit fiel die
    Referenzzahl zwischen den Haltepunkten sofort wieder auf 1, und CPython
    optimierte 499 von 500 Durchlaeufen weiter weg. Gemessen, je fuenf Runden
    abwechselnd, Faktor bei vervierfachter Groesse:

        ohne zweite Referenz            4,0    linear
        jede 500. gehalten              7,9    weder noch
        bei jedem Durchlauf gehalten   14,3    QUADRATISCH

    Die mittlere Zeile lag genau auf der Urteilsschwelle (8) - deshalb hiess
    dieselbe Bauform mal „linear“, mal „dazwischen“. Das sah nach Rauschen aus
    und war es nicht: Die Messung zeigte einen Zwischenzustand, den die
    Beschriftung nicht kannte.
    """
    s, halten = "", None
    for _i in range(n):
        halten = s                # <- die zweite Referenz, JETZT
        s += "x" * 20
    return s if halten is None else s


class Wachstum(Werkzeug):
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
        # QUADRATISCH und nicht „linear“ (30.08.2026): Genau das ist die
        # Aussage der Bauform — wer den String festhaelt, nimmt CPython die
        # Optimierung weg. Die alte Erwartung widersprach der Lehre, die das
        # Werkzeug selbst erteilt.
        ("s += '…' (2. Referenz)", _text_gehalten, 4000, "QUADRATISCH"),
    )

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = ("misst nur (wie viel Code dazugekommen ist) - "
                            "dafür gibt es keinen Beispielcode")

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
