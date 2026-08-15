# -*- coding: utf-8 -*-
"""Wächter für das Rücklesen der Logdateien.

WARUM (Review 13.08.2026, gemessen)
-----------------------------------
`_tail_lines` liest von hinten in 64-KB-Blöcken und hört auf, sobald es genug
Zeilenumbrüche gesehen hat — an einer echten 3,4-MB-Datei gemessen: 200 Zeilen
in 1 ms, 20.000 Zeilen in 53 ms. Der Vorwurf „liest die ganze Datei in den
Speicher" war damit für normale Logs widerlegt.

Nur greift die Abbruchbedingung nach ZEILEN nicht, wenn es kaum Zeilen gibt:
Bei 30 Zeilen à 2 MB (ein Traceback mit eingebettetem base64-Bild, eine
JSON-Zeile über Megabyte) las die Schleife alle 60 MB. Mit der Byte-Grenze sind
es 8 MB in 572 ms.
"""
import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.views.logs import MAX_TAIL_BYTES, _tail_lines


class TailLinesTest(SimpleTestCase):

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='logtest-'))
        self.addCleanup(lambda: shutil.rmtree(self.d, ignore_errors=True))

    def test_letzte_zeilen_in_der_richtigen_reihenfolge(self):
        f = self.d / 'a.log'
        f.write_text("\n".join('Zeile %d' % i for i in range(1000)), encoding='utf-8')
        z = _tail_lines(f, 5)
        self.assertEqual(z, ['Zeile %d' % i for i in range(995, 1000)])

    def test_kleine_datei_ganz(self):
        f = self.d / 'b.log'
        f.write_text('eins\nzwei\n', encoding='utf-8')
        self.assertEqual(_tail_lines(f, 100), ['eins', 'zwei'])

    def test_fehlende_datei_ist_leer(self):
        self.assertEqual(_tail_lines(self.d / 'gibtesnicht.log', 10), [])
        self.assertEqual(_tail_lines(None, 10), [])

    def test_wenige_sehr_lange_zeilen_sprengen_den_speicher_nicht(self):
        """DER FALL, DEN DIE ZEILENZÄHLUNG NICHT ABDECKT (13.08.2026).

        Ohne Byte-Grenze las die Schleife hier die ganze Datei, weil die
        gesuchten Zeilenumbrüche fehlen."""
        f = self.d / 'lang.log'
        with open(f, 'wb') as fh:
            for _ in range(6):                       # 6 x 2 MB = 12 MB
                fh.write(b'x' * (2 * 1024 * 1024) + b'\n')
        z = _tail_lines(f, 200)
        gelesen = sum(len(x) for x in z)
        self.assertLessEqual(gelesen, MAX_TAIL_BYTES + 65536,
                             'es wurden %.1f MB gelesen, Grenze ist %.1f MB'
                             % (gelesen / 1048576, MAX_TAIL_BYTES / 1048576))
        self.assertGreater(gelesen, 0, 'gar nichts gelesen')

    def test_rotierte_dateien_werden_mitgelesen(self):
        f = self.d / 'c.log'
        f.write_text('neu1\nneu2\n', encoding='utf-8')
        (self.d / 'c.log.1').write_text('alt1\nalt2\n', encoding='utf-8')
        z = _tail_lines(f, 10)
        self.assertEqual(z, ['alt1', 'alt2', 'neu1', 'neu2'],
                         'Reihenfolge alt->neu stimmt nicht: %r' % z)
