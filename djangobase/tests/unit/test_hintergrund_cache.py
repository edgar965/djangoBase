# -*- coding: utf-8 -*-
"""Wächter für HintergrundCache — wer rechnet, wenn der Wert zu alt ist.

WARUM (Review 15.08.2026)
-------------------------
`holen()` liefert normalerweise den letzten bekannten Wert sofort und erneuert im
Hintergrund. Ab `STALE_FAKTOR x Haltbarkeit` gilt der Wert aber als zu alt und
wurde SYNCHRON neu berechnet — und zwar ausserhalb jeder Sperre. Nach einer
langen Ruhephase (Server stand über Nacht) kommen mehrere Anfragen gleichzeitig,
und jede rechnete für sich. Bei der Versionen-Seite sind das mehrere
`gh`-Aufrufe zu je rund fünf Sekunden nebeneinander.

Jetzt rechnet genau einer; die anderen bekommen den alten Wert.
"""
import threading
import time

from django.test import SimpleTestCase

from djangobase.hintergrund_cache import HintergrundCache


class ZuAlterWertTest(SimpleTestCase):

    def test_nur_einer_rechnet_wenn_der_wert_zu_alt_ist(self):
        zaehler = {'n': 0}
        sperre = threading.Lock()

        def bauen():
            with sperre:
                zaehler['n'] += 1
            time.sleep(0.4)
            return 'neu-%d' % zaehler['n']

        c = HintergrundCache('probe', bauen, ttl_s=0.01)
        self.assertEqual(c.holen(), 'neu-1')          # erster Abruf rechnet
        time.sleep(0.05 + 0.01 * c.STALE_FAKTOR)      # sicher „zu alt"

        ergebnisse = []
        faeden = [threading.Thread(target=lambda: ergebnisse.append(c.holen()))
                  for _ in range(6)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join(5)

        self.assertEqual(zaehler['n'], 2,
                         'es liefen %d Berechnungen statt einer' % (zaehler['n'] - 1))
        self.assertEqual(len(ergebnisse), 6)
        self.assertTrue(all(e is not None for e in ergebnisse),
                        'ein Abruf kam ohne Wert zurück')

    def test_alter_wert_kommt_sofort(self):
        def langsam():
            time.sleep(0.6)
            return 'spaet'

        c = HintergrundCache('probe2', langsam, ttl_s=0.01)
        c._wert, c._ts = 'alt', time.time()           # so tun, als gäbe es einen
        time.sleep(0.02)
        t0 = time.perf_counter()
        wert = c.holen()
        dauer = time.perf_counter() - t0
        self.assertEqual(wert, 'alt')
        self.assertLess(dauer, 0.3, 'der Abruf hat auf die Erneuerung gewartet')

    def test_fehler_gibt_die_sperre_wieder_frei(self):
        """Sonst steht der Cache für immer auf „baut gerade"."""
        zustand = {'kaputt': True}

        def bauen():
            if zustand['kaputt']:
                raise RuntimeError('kein Netz')
            return 'geht'

        c = HintergrundCache('probe3', bauen, ttl_s=0.01)
        with self.assertRaises(RuntimeError):
            c.holen()
        self.assertFalse(c.zustand()['laeuft'],
                         'nach einem Fehler steht der Cache auf „baut gerade"')
        zustand['kaputt'] = False
        self.assertEqual(c.holen(), 'geht')
