# -*- coding: utf-8 -*-
u"""`szenarien` erkennt Pruefungen, die ihr Urteil ZURUECKGEBEN.

DER FEHLALARM (27.08.2026, 3DTools)
===================================
Neben `unittest` gibt es Testbasen, deren Vertrag lautet: Eine Pruefmethode
liefert ``(bestanden, text)``, und der Rahmen macht daraus die Zusicherung.
3DTools hat 127 solcher Faelle (`tests/base.TestCategory`, umgesetzt in
`core/tests/ui/test_oberflaeche.py`). Alle 127 galten als „ohne jede
Zusicherung — die melden gruen, egal was passiert" — und wurden als **Fehler**
gefuehrt, dem schwersten Gewicht des Werkzeugs.

Das Gegenteil war wahr: Der Vergleich stand im `return`.

WAS HIER GEPRUEFT WIRD
======================
Die vier Formen, die vorkommen, UND die Gegenprobe: Ein Rumpf, der wirklich
nichts behauptet, muss weiter durchfallen.
"""

import ast

from django.test import SimpleTestCase

from djangobase.skills.szenarien import Szenarienpruefer


def _sichert_zu(quelle):
    baum = ast.parse(quelle)
    return Szenarienpruefer._sichert_zu(baum.body[0])


class UrteilAlsRueckgabeTest(SimpleTestCase):

    def test_vergleich_im_return(self):
        self.assertTrue(_sichert_zu(
            'def test_x():\n'
            '    r = holen()\n'
            "    return r.zahl == 3, 'zahl=%d' % r.zahl\n"))

    def test_urteil_ueber_eine_variable(self):
        u"""Die uebliche zweizeilige Form."""
        self.assertTrue(_sichert_zu(
            'def test_x():\n'
            '    ok = bool(abs(a) < 1e-5 and abs(b) < 1e-5)\n'
            "    return ok, 'a=%s' % a\n"))

    def test_ausdruecklicher_fehlschlagzweig(self):
        u"""Wer irgendwo `False` zurueckgeben KANN, meldet nicht immer gruen."""
        self.assertTrue(_sichert_zu(
            'def test_x():\n'
            '    if status != 200:\n'
            "        return False, 'HTTP %d' % status\n"
            "    return True, 'ok'\n"))

    def test_bool_aufruf(self):
        self.assertTrue(_sichert_zu(
            'def test_x():\n'
            "    return bool(r.gespeichert), 'code=%d' % r.code\n"))

    # -------------------------------------------------------- Gegenproben

    def test_nur_return_true_ist_KEINE_zusicherung(self):
        u"""DIE GEGENPROBE: Genau das meldet gruen, egal was passiert."""
        self.assertFalse(_sichert_zu(
            'def test_x():\n'
            '    fahren()\n'
            "    return True, 'lief durch'\n"))

    def test_ohne_return_bleibt_es_ein_befund(self):
        self.assertFalse(_sichert_zu(
            'def test_x():\n'
            '    fahren()\n'))

    def test_rueckgabe_von_daten_ist_keine_zusicherung(self):
        self.assertFalse(_sichert_zu(
            'def test_x():\n'
            '    daten = holen()\n'
            '    return daten\n'))
