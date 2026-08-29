# -*- coding: utf-8 -*-
u"""Zirkelkarte — für JEDE Trennlinie einer Datei auf einmal: Zirkel oder nicht.

WARUM (29.08.2026, gemessen)
============================
``JsSchnitt._beste`` probierte jede Funktionsgrenze einzeln durch und liess für
jede den Zirkeltest neu rechnen. Der besteht aus zwei regulären Ausdrücken je
NAME über den jeweils anderen Dateiteil — also Kandidaten × Namen Suchläufe
über je halbe Dateigrösse.

Am eigenen Anlassfall des Werkzeugs (602 Zeilen, 602 Namen, 520 Kandidaten)
waren das rund 300.000 Suchläufe: **186,9 Sekunden für eine Datei.** Der
Anlassfall-Check fährt jedes Werkzeug einmal an seinem Fall, und der Testfall
darüber ruft ihn viermal — der Lauf kam nach 550 s nicht durch, obwohl im Kopf
der Testdatei „~30 Sekunden" steht. Aufgefallen ist es erst, als
``manage.py test djangobase`` in den Zeitablauf lief.

Ausgelöst hat es eine Zahl, nicht ein Umbau: Am 28.08.2026 wurde ``GRENZE`` von
200 auf 300 gezogen, und die Vorlage rechnet mit (``HAELFTE = GRENZE``). Aus
402 Zeilen wurden 602 — bei kubischem Aufwand das 3,4-fache.

WIE ES JETZT GEHT
=================
Die Frage „braucht unten etwas von oben?" hängt nur an zwei Zahlen je Name:
wo er DEFINIERT wird und wo er zuletzt VORKOMMT. Ein Schnitt bei ``b`` trennt
genau dann, wenn kein Name über ``b`` hinausreicht:

    unten braucht oben  ⟺  ∃ Name mit  def < b ≤ letztes Vorkommen
    oben braucht unten  ⟺  ∃ Name mit  erstes Vorkommen < b ≤ def

Beide Bedingungen sind Intervalle in ``b``. Ein Durchgang über die Datei sammelt
alle Vorkommen, ein Differenzfeld deckt die Intervalle ab — danach kostet jede
Trennlinie eine Feldabfrage. Aus 186,9 s werden 0,05 s.

Die Antwort ist dieselbe: ``tests/unit/test_jszirkel.py`` rechnet beide
Fassungen auf echten Dateien gegeneinander.
"""
import re

#: Definitionen auf Modulebene — dieselbe Schreibweise wie in `Schnittstelle`.
DEFINITION = re.compile(
    r"^(?:export )?(?:async )?(?:function|class|const) (\w+)", re.M)

#: Ein Bezeichner, der NICHT hinter einem Punkt steht (also kein Feldzugriff).
#: Entspricht dem `(?<![.\w])name\b` der Einzelabfrage.
VORKOMMEN = re.compile(r"(?<![.\w])(\w+)\b")


class Zirkelkarte:
    """Sagt für jede Trennlinie einer Datei, ob sie einen Zirkel schneidet."""

    def __init__(self, quellzeilen):
        self.zeilen = quellzeilen
        anzahl = len(quellzeilen)
        #: Name -> (erste, letzte) Definitionszeile, 0-basiert.
        #:
        #: ZWEI ZAHLEN, NICHT EINE: `function x(){}` darf in JS zweimal auf
        #: Modulebene stehen. Die alte Fassung fragte je Trennlinie „steht
        #: eine Definition ueber mir?" (also die ERSTE) und „steht eine
        #: unter mir?" (also die LETZTE). Mit nur einer Zahl waere die
        #: Antwort bei einer Doppeldefinition eine andere gewesen.
        self.definiert = {}
        for nr, zeile in enumerate(quellzeilen):
            treffer = DEFINITION.match(zeile)
            if not treffer:
                continue
            name = treffer.group(1)
            erste, _letzte = self.definiert.get(name, (nr, nr))
            self.definiert[name] = (erste, nr)

        erstes = {}
        letztes = {}
        for nr, zeile in enumerate(quellzeilen):
            for name in VORKOMMEN.findall(zeile):
                if name not in self.definiert:
                    continue
                erstes.setdefault(name, nr)
                letztes[name] = nr

        # Zwei Differenzfelder ueber die moeglichen Trennlinien 0..anzahl.
        hoch = [0] * (anzahl + 2)
        runter = [0] * (anzahl + 2)
        for name, (erste_def, letzte_def) in self.definiert.items():
            bis = letztes.get(name, letzte_def)
            if bis > erste_def:               # unten braucht oben: (def, bis]
                hoch[erste_def + 1] += 1
                hoch[bis + 1] -= 1
            ab = erstes.get(name, erste_def)
            if ab < letzte_def:               # oben braucht unten: (ab, def]
                runter[ab + 1] += 1
                runter[letzte_def + 1] -= 1

        self._unten_braucht_oben = self._decke(hoch, anzahl)
        self._oben_braucht_unten = self._decke(runter, anzahl)

    @staticmethod
    def _decke(differenz, anzahl):
        """Aus dem Differenzfeld die Wahrheitswerte je Trennlinie."""
        decke = [False] * (anzahl + 2)
        stand = 0
        for i in range(anzahl + 2):
            stand += differenz[i]
            decke[i] = stand > 0
        return decke

    def zirkel(self, bei):
        """Braucht bei dieser Trennlinie JEDE Seite etwas von der anderen?"""
        return self._unten_braucht_oben[bei] and self._oben_braucht_unten[bei]

    def richtung(self, bei):
        """Welche Seite hängt an welcher — in den Worten des Berichts."""
        unten = self._unten_braucht_oben[bei]
        oben = self._oben_braucht_unten[bei]
        if not (unten or oben):
            return "keine"
        return "unten←oben" if not oben else "oben←unten"
