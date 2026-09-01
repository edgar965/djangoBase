# -*- coding: utf-8 -*-
u"""Eine Beschriftung in einer Annotation ist kein fehlender Name.

DER ANLASS (HumanBodyBlender, 01.09.2026)
=========================================
`code-qualitaet` meldete dort 226 „Echte Fehler" — 110 davon Woerter
wie ``Region``, ``Farbe``, ``Name``. Blender-Addons deklarieren ihre
Eigenschaften seit 2.80 als Annotation::

    region: EnumProperty(name="Region", default="TORSO")

In Python ist eine Annotation, die eine Zeichenkette IST, eine
Vorwaertsreferenz (``x: "MeineKlasse"``). pyflakes parst deshalb jede
Zeichenkette im Annotationsteilbaum als Code — auch die Argumente
eines Aufrufs. Derselbe Quelltext als Zuweisung erzeugt keine einzige
dieser Meldungen.

Zwei Meldungsarten, ein Grund: Ein Einzelwort parst und wird zu
``UndefinedName``; ``"Alpha Channel"`` parst nicht und wird zu
``ForwardAnnotationSyntaxError``. Nach dem Fix nur der ersten blieben
in einer einzigen Datei 40 der zweiten stehen.

DIE TRENNLINIE IST DER AUFRUF. Was in einem Aufruf steht, ist ein
Argument; die Annotation selbst und ein Index (``Optional["X"]``)
bleiben echte Vorwaertsreferenzen — dort ist ein fehlender Name ein
Befund und muss es bleiben.

BDD - GEGEBEN / DANN
====================
    EineBlenderEigenschaft      ... ihre Beschriftungen sind keine Namen
    EineEchteVorwaertsreferenz  ... bleibt gemeldet
    EinEchterFehlerDaneben      ... bleibt gemeldet
"""
import ast
import unittest

from djangobase.umbau.codequalitaet import _annotationsketten


class AnnotationsBasis(unittest.TestCase):
    u"""Faehrt pyflakes und trennt nach dem Filter."""

    databases = []
    QUELLE = ""

    def urteile(self):
        u"""(gemeldet, verworfen) — die Namen aus den pyflakes-Meldungen."""
        from pyflakes.checker import Checker
        baum = ast.parse(self.QUELLE)
        ketten = _annotationsketten(baum)
        gemeldet, verworfen = [], []
        for m in Checker(baum, filename="probe.py").messages:
            art = type(m).__name__
            if art not in ("UndefinedName", "ForwardAnnotationSyntaxError"):
                continue
            wert = m.message_args[0] if m.message_args else ""
            if (m.lineno, wert) in ketten:
                verworfen.append(wert)
            else:
                gemeldet.append(wert)
        return gemeldet, verworfen


class EineBlenderEigenschaft(AnnotationsBasis):
    u"""Eigenschaften mit Beschriftung, ein- und mehrwortig."""

    QUELLE = (
        "class Props:" + chr(10) +
        '    region: EnumProperty(name="Region", default="TORSO")' + chr(10) +
        '    alpha: BoolProperty(name="Alpha Channel")' + chr(10) +
        '    art: EnumProperty(items=[("A", "Ah", "das erste")])' + chr(10))

    def test_beschriftungen_gelten_nicht_als_namen(self):
        _gemeldet, verworfen = self.urteile()
        for wort in ("Region", "TORSO", "Alpha Channel", "Ah", "das erste"):
            self.assertIn(wort, verworfen)

    def test_der_aufruf_selbst_bleibt_ein_befund(self):
        u"""EnumProperty ist wirklich nicht eingefuehrt — das ist echt."""
        gemeldet, _verworfen = self.urteile()
        self.assertIn("EnumProperty", gemeldet)


class EineEchteVorwaertsreferenz(AnnotationsBasis):
    u"""Die Annotation IST eine Zeichenkette — hier zaehlt der Name."""

    QUELLE = (
        "from typing import Optional" + chr(10) +
        "class Props:" + chr(10) +
        '    a: "GibtEsNicht"' + chr(10) +
        '    b: Optional["AuchNicht"]' + chr(10))

    def test_bleibt_gemeldet(self):
        gemeldet, verworfen = self.urteile()
        self.assertIn("GibtEsNicht", gemeldet)
        self.assertIn("AuchNicht", gemeldet)
        self.assertEqual(verworfen, [])


class EinEchterFehlerDaneben(AnnotationsBasis):
    u"""Der Filter darf nur die Beschriftung nehmen, nichts sonst."""

    QUELLE = (
        "class Props:" + chr(10) +
        '    region: EnumProperty(name="Region")' + chr(10) +
        "" + chr(10) +
        "    def f(self):" + chr(10) +
        "        return fehlt_wirklich" + chr(10))

    def test_der_echte_fehler_ueberlebt(self):
        gemeldet, verworfen = self.urteile()
        self.assertIn("fehlt_wirklich", gemeldet)
        self.assertEqual(verworfen, ["Region"])


class EineSabotage(AnnotationsBasis):
    u"""Sabotage: Steht die Beschriftung in einer ANDEREN Zeile,

    darf der Filter sie nicht greifen. So faellt auf, wenn jemand die
    Zeilenpruefung herausnimmt und der Filter zu grob wird.
    """

    QUELLE = (
        "class Props:" + chr(10) +
        '    region: EnumProperty(name="Region")' + chr(10) +
        "" + chr(10) +
        "    def f(self):" + chr(10) +
        "        return Region" + chr(10))

    def test_dieselbe_zeichenkette_in_anderer_zeile_bleibt(self):
        gemeldet, _verworfen = self.urteile()
        self.assertIn("Region", gemeldet)
