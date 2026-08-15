# -*- coding: utf-8 -*-
"""Wächter für den Commit-Cache der Versionen-Seite.

WARUM (Review 13.08.2026, gemessen)
-----------------------------------
Die Seite holt Commit-Listen über die GitHub-CLI — vier Repos mal zwei Aufrufe,
jeder mit bis zu 10 s Zeitgrenze, alle IN der Anfrage. Gemessen an HumanBodyWeb:

    erster Aufruf (kalt)   4,9 s
    zweiter Aufruf (warm)  0,7 s

Bei einem TTL von 300 s zahlte diese 4,9 s jedes Mal derjenige, der nach Ablauf
der Haltbarkeit zuerst kommt. Jetzt wird der alte Wert ausgeliefert und im
Hintergrund erneuert — nur der allererste Abruf rechnet noch in der Anfrage,
denn vorher gibt es nichts zu zeigen.
"""
import threading
import time

from django.test import SimpleTestCase

from djangobase.views.versions import _Einmalig, _TTLCache


class TTLCacheTest(SimpleTestCase):

    def test_erster_abruf_rechnet(self):
        """Vorher gibt es nichts anzuzeigen — hier ist Warten richtig."""
        c = _TTLCache(300.0)
        self.assertEqual(c.get_or_compute('k', lambda: 'wert'), 'wert')

    def test_abgelaufener_abruf_liefert_sofort_den_alten_wert(self):
        c = _TTLCache(300.0)
        c.get_or_compute('k', lambda: 'alt')
        c._ttl = 0.0                                  # Haltbarkeit vorspulen

        gerufen = threading.Event()

        def langsam():
            gerufen.set()
            time.sleep(1.0)
            return 'neu'

        t0 = time.perf_counter()
        wert = c.get_or_compute('k', langsam)
        dauer = time.perf_counter() - t0

        self.assertEqual(wert, 'alt', 'der alte Wert muss sofort kommen')
        self.assertLess(dauer, 0.3, 'die Anfrage hat auf die Erneuerung gewartet (%.2f s)' % dauer)
        self.assertTrue(gerufen.wait(2), 'die Erneuerung wurde nicht angestossen')
        for _ in range(40):                           # auf den Faden warten
            if c.get_or_compute('k', langsam) == 'neu':
                break
            time.sleep(0.1)
        self.assertEqual(c.get_or_compute('k', langsam), 'neu',
                         'der erneuerte Wert kam nicht an')

    def test_nur_ein_erneuerungsfaden_je_schluessel(self):
        """Sonst startet jede Anfrage nach Ablauf ihren eigenen `gh`-Aufruf."""
        c = _TTLCache(300.0)
        c.get_or_compute('k', lambda: 'alt')
        c._ttl = 0.0
        zaehler = {'n': 0}
        sperre = threading.Lock()

        def langsam():
            with sperre:
                zaehler['n'] += 1
            time.sleep(0.5)
            return 'neu'

        for _ in range(10):
            c.get_or_compute('k', langsam)
        time.sleep(1.2)
        self.assertEqual(zaehler['n'], 1,
                         'es liefen %d Erneuerungen statt einer' % zaehler['n'])

    def test_fehler_im_hintergrund_laesst_den_alten_wert_stehen(self):
        c = _TTLCache(300.0)
        c.get_or_compute('k', lambda: 'alt')
        c._ttl = 0.0

        def kaputt():
            raise RuntimeError('gh antwortet nicht')

        self.assertEqual(c.get_or_compute('k', kaputt), 'alt')
        time.sleep(0.3)
        self.assertEqual(c.get_or_compute('k', kaputt), 'alt',
                         'nach einem Fehler in der Erneuerung ist der Wert weg')


class EinmaligTest(SimpleTestCase):
    def test_nur_der_erste_gewinnt(self):
        e = _Einmalig()
        self.assertTrue(e.add_if_absent('a'))
        self.assertFalse(e.add_if_absent('a'))
        e.discard('a')
        self.assertTrue(e.add_if_absent('a'))
