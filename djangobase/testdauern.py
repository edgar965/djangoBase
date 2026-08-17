# -*- coding: utf-8 -*-
u"""Dauern - die Laufzeit je Testcase aus der Ausgabe von ``manage.py test`` lesen.

WOHER DIE ZAHLEN KOMMEN
=======================
``unittest`` kann seit Python 3.12 die Laufzeit jedes Testcases ausgeben:

    manage.py test <label> --durations 0

    Slowest test durations
    ----------------------
    1.234s     test_import (mail.tests.unit.test_x.XTest.test_import)
    0.002s     test_leer (mail.tests.unit.test_x.XTest.test_leer)

``0`` heisst „alle, nicht nur die langsamsten". Aeltere Interpreter kennen die
Option nicht und brechen mit ``unrecognized arguments`` ab - deshalb fragt
:meth:`unterstuetzt` den Interpreter, der die Tests wirklich faehrt, statt den
des Servers anzunehmen. In den Konsumenten-Projekten sind das oft verschiedene
(fester venv-Pfad in ``test_befehle``).

WARUM NICHT DER TESTLAEUFER SELBST MESSEN SOLL
==============================================
Die Tests laufen in einem eigenen Prozess (``subprocess.run``). Ihn zu
instrumentieren hiesse, in jedes Projekt einen eigenen Testlaeufer zu setzen -
sechs Kopien einer Sache, die unittest schon kann.

DER ZEITSTEMPEL-PRAEFIX
=======================
Im Projekt assistant traegt JEDE stdout-Zeile einen Zeitstempel
(``mail.apps.install_stdout_timestamps``). Ein Muster, das den Zeilenanfang
festnagelt, findet dort nichts. Deshalb wird die Zeile ohne Ankerung gelesen
- gesucht wird das Paar „Sekunden + Test-ID in Klammern", egal was davor steht.
"""
import re
import subprocess

__all__ = ["Dauern"]


class Dauern:
    """Laufzeiten je Testcase - Parser plus Fähigkeitsprobe des Interpreters."""

    #: ``1.234s     test_name (paket.modul.Klasse.test_name)``
    #: Ohne ``^``: siehe Modulkopf (Zeitstempel-Praefix im Projekt assistant).
    ZEILE = re.compile(r"(\d+[.,]\d+)\s*s\s+\S+\s+\(([\w.]+)\)")
    #: Damit nicht die ganze Ausgabe durchsucht wird, wenn es keinen Block gibt.
    KOPF = "Slowest test durations"
    #: Ergebnis der Probe je Interpreter - der Aufruf kostet ~50 ms.
    _kann = {}

    @classmethod
    def unterstuetzt(cls, python):
        u"""Kennt dieser Interpreter ``--durations``? (Python 3.12 und neuer)"""
        schluessel = str(python)
        if schluessel not in cls._kann:
            try:
                r = subprocess.run(
                    [schluessel, "-c",
                     "import sys; print(1 if sys.version_info >= (3, 12) else 0)"],
                    capture_output=True, text=True, timeout=20)
                cls._kann[schluessel] = (r.stdout or "").strip() == "1"
            except Exception:
                # Laesst sich der Interpreter nicht befragen, wird die Option
                # NICHT gesetzt: Ein Testlauf, der an einem unbekannten Argument
                # scheitert, waere teurer als fehlende Laufzeiten.
                cls._kann[schluessel] = False
        return cls._kann[schluessel]

    @classmethod
    def option_setzen(cls, cmd):
        u"""``--durations 0`` ergaenzen, wenn es geht - sonst das Kommando lassen.

        Das Kommando kommt aus ``DJANGOBASE["test_befehle"]`` und gehoert dem
        Projekt; angefasst wird nur eine KOPIE, und nur wenn dort noch keine
        ``--durations``-Option steht.
        """
        toks = [str(t) for t in (cmd or [])]
        if not toks or "test" not in toks or any("--durations" in t for t in toks):
            return toks
        if not cls.unterstuetzt(toks[0]):
            return toks
        return toks + ["--durations", "0"]

    @classmethod
    def lesen(cls, text):
        u"""``{test_id: sekunden}`` aus der Ausgabe - leer, wenn es keinen Block gibt.

        Gelesen wird ab dem Kopf „Slowest test durations"; Zeilen davor koennen
        dieselbe Form haben (etwa in einer Fehlermeldung) und wuerden sonst als
        Laufzeit gelten.
        """
        if not text:
            return {}
        start = text.find(cls.KOPF)
        if start < 0:
            return {}
        aus = {}
        for sek, test_id in cls.ZEILE.findall(text[start:]):
            try:
                aus[test_id] = float(sek.replace(",", "."))
            except ValueError:
                continue
        return aus
