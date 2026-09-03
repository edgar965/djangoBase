# -*- coding: utf-8 -*-
u"""`modulzustand` meldet keine Skripte und keine Namensgleichheit mehr.

DER FEHLALARM (03.09.2026, shortlongx)
======================================
23 offene Zeilen, davon **20 keine**:

* **12 in Skripten.** Ein Skript läuft EINMAL in EINEM Prozess. Der Schaden,
  den dieses Werkzeug sucht — zwei gleichzeitige Läufe ziehen sich den Zustand
  weg — kann dort nicht entstehen. Neun davon waren dasselbe ``FEHLER = []``
  in Vergleichs-Werkzeugen.
* **10 nur namensgleich.** ``SYSTEM = {...}`` in drei Tests, das nur an
  Funktionen weitergereicht wird. Verändert wurde ein gleichnamiger Name
  woanders — in einer Datei, die ihn selbst bindet.

WARUM AM CODE UND NICHT AM ORDNER
=================================
Die ältere Fassung in shortlongx schloss pauschal ``werkzeug/`` aus. Eine
Ordnerliste rät: Sie übersieht das Skript, das woanders liegt, und sie nimmt
Dienstcode mit, der zufällig dort steht. Genau das ist passiert —
``werkzeug/raster_pool.py`` hält einen echten veränderlichen Modulzustand und
fiel durch die Ordner-Ausnahme heraus. ``if __name__ == "__main__"`` steht
dagegen im Code und meint genau das.

WAS HIER GEPRÜFT WIRD
=====================
Beide Richtungen: Die Ausnahmen müssen greifen UND ein echter geteilter
Zustand in Dienstcode muss weiter gemeldet werden.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.modulzustand import ModulZustand
from djangobase.skills.werkzeug import Quelldatei

#: Dienstcode: ein Zwischenspeicher, den zwei Anfragen gleichzeitig anfassen.
DIENST = '''_CACHE = {}


def merken(name, wert):
    _CACHE[name] = wert


def lesen(name):
    return _CACHE.get(name)
'''

#: Dasselbe, aber als Skript - ein Lauf, ein Prozess.
SKRIPT = DIENST + '''

if __name__ == "__main__":
    merken("a", 1)
    print(lesen("a"))
'''

#: Eine Konstante, die niemand verändert - anderswo gibt es den Namen als
#: lokal gebundene Variable.
KONSTANTE = '''SYSTEM = {"name": "Deckung", "stop": 20.0}


def fahren():
    return berechne(SYSTEM)
'''

FREMD_MIT_EIGENEM_NAMEN = '''def sammeln():
    SYSTEM = {}
    SYSTEM.update({"x": 1})
    return SYSTEM
'''


class _Zustand(ModulZustand):
    u"""Sucht in einem Wegwerf-Verzeichnis statt im Projekt."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(self._ordner.rglob(muster))

    def dateien(self, endung=".py"):
        return [Quelldatei(p, self._ordner)
                for p in sorted(self._ordner.rglob("*" + endung))]


def _lauf(dateien):
    u"""Das Ergebnis wird NOCH IM Kontext geholt - ``Quelldatei`` liest träge."""
    with tempfile.TemporaryDirectory() as ordner:
        for name, inhalt in dateien.items():
            (Path(ordner) / name).write_text(inhalt, encoding="utf-8")
        erg = _Zustand(ordner).laufen()
        return [dict(z) for z in erg.zeilen], erg.zusammenfassung


class SkriptTest(SimpleTestCase):

    def test_skript_ist_kein_offener_befund(self):
        zeilen, _kopf = _lauf({"werkzeug.py": SKRIPT})
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        self.assertEqual(offen, [], "ein Lauf, ein Prozess")

    def test_die_zahl_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertür."""
        _zeilen, kopf = _lauf({"werkzeug.py": SKRIPT})
        self.assertIn("in Skripten", kopf)

    def test_dienstcode_bleibt_ein_befund(self):
        u"""DIE GEGENPROBE: Der Wächter muss weiter anschlagen."""
        zeilen, kopf = _lauf({"dienst.py": DIENST})
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        self.assertEqual(len(offen), 1, kopf)
        self.assertEqual(offen[0]["name"], "_CACHE")

    def test_der_ordnername_entscheidet_nicht(self):
        u"""Dieselbe Datei unter zwei Namen — beide Male Dienstcode."""
        zeilen, _kopf = _lauf({"werkzeug_dienst.py": DIENST})
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        self.assertEqual(
            len(offen), 1,
            "der Name „werkzeug“ macht aus Dienstcode kein Skript")


class NamensgleichheitTest(SimpleTestCase):

    def test_konstante_ist_kein_zustand(self):
        zeilen, _kopf = _lauf({"eins.py": KONSTANTE,
                               "zwei.py": FREMD_MIT_EIGENEM_NAMEN})
        namen = [z["name"] for z in zeilen]
        self.assertNotIn("SYSTEM", namen, "niemand verändert sie")

    def test_die_zahl_steht_in_der_kopfzeile(self):
        _zeilen, kopf = _lauf({"eins.py": KONSTANTE,
                               "zwei.py": FREMD_MIT_EIGENEM_NAMEN})
        self.assertIn("namensgleich", kopf)

    def test_echte_fremde_aenderung_bleibt_ein_befund(self):
        u"""DIE GEGENPROBE: Über Dateigrenzen hinweg ist der Fall SCHLIMMER."""
        fremd = 'from eins import SYSTEM\n\n\ndef setzen():\n    SYSTEM.update({"x": 1})\n'
        zeilen, kopf = _lauf({"eins.py": KONSTANTE, "zwei.py": fremd})
        self.assertTrue(any(z["name"] == "SYSTEM" for z in zeilen), kopf)
