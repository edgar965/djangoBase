# -*- coding: utf-8 -*-
u"""`protokoll`: im Ergebnis gemeldet ist gemeldet.

DER FALL (31.08.2026, 3DTools)
==============================
Die Kollisions-Pipelines in `HumanBody/collision/` haben keine
HTTP-Schicht. Sie antworten mit einem Woerterbuch::

    except FileNotFoundError:
        return {'ok': False, 'output': '',
                'log': f'Blender not found at {BLENDER_EXE}'}

Das Werkzeug meldete jede dieser Stellen als „Ausnahme ohne Log" — 13 von
58 Befunden in diesem Baum. Die Ausnahme verschwindet dabei aber nicht:
Sie reist im Rueckgabewert.

BELEGT BIS ZUR OBERFLAECHE, nicht behauptet:

    core/dienste/stoffexportlauf.py:120   'log': ergebnis.get('log', '')
    static/viewer/bvh_studio/export1.js   `(log: ${(data.log || '')…})`
    static/viewer/scene/cloth_export.js   throw new Error(data.error || data.log)

Es ist dieselbe Ueberlegung wie bei „4xx ist gemeldet" und „Django-Messages
sind gemeldet" (beide 17.08.2026) — nur fuer eine Bibliothek ohne HTTP.

DIE GRENZE
==========
Verlangt wird BEIDES: ein Schalter auf `False` UND ein nicht leeres
Textfeld. `return {'ok': False}` allein sagt nicht, WAS schiefging — das
bleibt ein Befund. Sonst waere die Ausnahme ein Schalter, mit dem sich
jeder Befund abstellen laesst.

BDD - GEGEBEN / DANN
====================
    EinErgebnisMitFehlertext   ... wird nicht gemeldet
    EinErgebnisOhneText        ... wird gemeldet
    EinLeeresTextfeld          ... wird gemeldet
    EinStummerBlock            ... wird gemeldet
"""
from djangobase.skills.protokoll import Protokoll

from .test_neue_werkzeuge import WerkzeugBasis


class ProtokollBasis(WerkzeugBasis):
    u"""Faehrt `protokoll` auf eine einzelne Datei."""

    def befunde(self, quelle):
        return self.projekt({'dienst.py': quelle}).fahren(Protokoll)


class EinErgebnisMitFehlertext(ProtokollBasis):
    u"""Gegeben: Der Block gibt Schalter UND Text zurueck."""

    ECHT = """def lauf(pfad):
    try:
        return {'ok': True, 'output': pfad, 'log': ''}
    except FileNotFoundError as e:
        return {'ok': False, 'output': '', 'log': f'nicht gefunden: {e}'}
"""

    def test_er_wird_nicht_gemeldet(self):
        self.assertEqual(self.befunde(self.ECHT), [])

    def test_auch_mit_einem_festen_text(self):
        u"""Der Text muss nicht die Ausnahme nennen — `Blender not found
        at …` sagt genug."""
        quelle = self.ECHT.replace("f'nicht gefunden: {e}'",
                                   "'Blender nicht am erwarteten Ort'")
        self.assertEqual(self.befunde(quelle), [])

    def test_auch_mit_success_und_error(self):
        u"""Andere Projekte schreiben `success`/`error`."""
        quelle = (self.ECHT.replace("'ok'", "'success'")
                           .replace("'log'", "'error'"))
        self.assertEqual(self.befunde(quelle), [])


class EinErgebnisOhneText(ProtokollBasis):
    u"""Gegeben: Nur der Schalter, kein Grund."""

    def test_es_bleibt_ein_befund(self):
        u"""Die Gegenprobe: Sonst waere die Ausnahme ein Schalter, mit dem
        sich jeder Befund abstellen laesst."""
        quelle = """def lauf(pfad):
    try:
        return {'ok': True, 'output': pfad}
    except FileNotFoundError:
        return {'ok': False, 'output': ''}
"""
        self.assertEqual(len(self.befunde(quelle)), 1)

    def test_und_ohne_schalter_auch(self):
        quelle = """def lauf(pfad):
    try:
        return {'log': 'gut'}
    except FileNotFoundError:
        return {'log': 'nicht gefunden'}
"""
        self.assertEqual(len(self.befunde(quelle)), 1)


class EinLeeresTextfeld(ProtokollBasis):
    u"""Gegeben: Das Textfeld ist da, aber leer."""

    def test_es_bleibt_ein_befund(self):
        u"""`'log': ''` sagt genauso wenig wie gar kein Feld."""
        quelle = """def lauf(pfad):
    try:
        return {'ok': True, 'log': 'fertig'}
    except FileNotFoundError:
        return {'ok': False, 'log': ''}
"""
        self.assertEqual(len(self.befunde(quelle)), 1)


class EinStummerBlock(ProtokollBasis):
    u"""Gegeben: Der Block schluckt wirklich."""

    def test_pass_bleibt_ein_befund(self):
        quelle = """def lauf(pfad):
    try:
        return {'ok': True}
    except Exception:
        pass
"""
        zeilen = self.befunde(quelle)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('verschluckt', zeilen[0]['art'])
