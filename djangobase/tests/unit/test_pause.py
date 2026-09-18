# -*- coding: utf-8 -*-
u"""`pause.Pause` — Warten, das man hineinreicht, abbricht und nachzählt.

DER ANLASS (gunSlinger, 18.09.2026)
===================================
Eine Lesepause von 58 s ließ den Knopf „Abbrechen" 58 s lang wirkungslos
erscheinen, und kein Test konnte die Pausenlogik fahren, ohne wirklich zu
warten. Die Bauform steht im Kopf von `pause.py`.

WAS HIER GEPRÜFT WIRD
=====================
Drei Eigenschaften, jede mit ihrer Gegenrichtung:
1. `sofort()` wartet nicht, zählt aber mit — und eine echte `Pause()` wartet
   wirklich (sonst wäre der Ersatz keiner).
2. `abbrechen()` beendet ein laufendes Warten von 30 s in Millisekunden — und
   ohne Abbruch läuft die Zeit durch.
3. Nach `zuruecksetzen()` wartet dieselbe Pause wieder.
"""
import threading

from django.test import SimpleTestCase

from djangobase.pause import Pause


class EineSofortPause(SimpleTestCase):

    def test_wartet_nicht_zaehlt_aber_jede_anforderung(self):
        pause = Pause.sofort()
        start = Pause.jetzt()
        ergebnisse = [pause.warten(30), pause.warten(0.5), pause.warten(0)]
        self.assertLess(Pause.jetzt() - start, 0.5)
        self.assertEqual(ergebnisse, [True, True, True])
        self.assertEqual(pause.gewartet, [30.0, 0.5, 0.0])
        self.assertEqual(pause.gesamt, 30.5)

    def test_meldet_einen_abbruch_trotzdem(self):
        pause = Pause.sofort()
        pause.abbrechen()
        self.assertFalse(pause.warten(1))


class EineEchtePause(SimpleTestCase):

    def test_wartet_wirklich(self):
        u"""Die Gegenrichtung zu `sofort()`: ohne Ersatz vergeht Zeit."""
        pause = Pause()
        start = Pause.jetzt()
        self.assertTrue(pause.warten(0.05))
        self.assertGreaterEqual(Pause.jetzt() - start, 0.04)

    def test_endet_sofort_beim_abbruch_aus_einem_anderen_thread(self):
        pause = Pause()
        threading.Timer(0.05, pause.abbrechen).start()
        start = Pause.jetzt()
        self.assertFalse(pause.warten(30), 'False = abgebrochen')
        self.assertLess(Pause.jetzt() - start, 2.0, 'Ein Abbruch darf nicht die 30 s abwarten')
        self.assertTrue(pause.abgebrochen)
        self.assertFalse(pause.warten(5), 'Nach dem Abbruch kehrt jedes Warten sofort zurück')

    def test_wartet_nach_dem_zuruecksetzen_wieder(self):
        pause = Pause()
        pause.abbrechen()
        pause.warten(1)
        pause.zuruecksetzen()
        self.assertFalse(pause.abgebrochen)
        self.assertEqual(pause.gewartet, [])
        self.assertTrue(pause.warten(0.01))

    def test_null_und_negativ_warten_nicht(self):
        pause = Pause()
        start = Pause.jetzt()
        self.assertTrue(pause.warten(0) and pause.warten(-3))
        self.assertLess(Pause.jetzt() - start, 0.1)
