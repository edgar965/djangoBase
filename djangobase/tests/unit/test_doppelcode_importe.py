# -*- coding: utf-8 -*-
u"""`doppelcode` meldet keine reinen Importbloecke mehr.

DER FEHLALARM (27.08.2026, 3DTools)
===================================
Vier Module bekamen eine Warnung fuer diesen Block::

    import json
    import logging
    import os
    import re

    from django.conf import settings

Er IST in allen vier gleich — und muss es sein. Wer `json` braucht, importiert
`json`; zusammenfassen laesst sich daran nichts. Von 187 gemeldeten Stellen
waren 20 von dieser Sorte, und sie standen ganz oben, weil sie in den meisten
Dateien vorkommen.

WAS HIER GEPRUEFT WIRD
======================
Beide Richtungen: Der Fehlalarm muss weg sein UND echter doppelter Code muss
bleiben — auch dann, wenn er mit Importen ANFAENGT.
"""

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.doppelcode import Doppelcode

NUR_IMPORTE = '''import json
import logging
import os
import re

from django.conf import settings
from django.http import JsonResponse
'''

ECHTER_CODE = '''def preis_pruefen(betrag):
    if betrag < 0:
        raise ValueError('negativ')
    if betrag > 1000:
        raise ValueError('zu gross')
    return round(betrag, 2)
'''


class _Werkzeug(Doppelcode):
    u"""Ein `Doppelcode`, der in einem Wegwerf-Verzeichnis sucht."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def projektdateien(self, *_endungen):
        return sorted(self._ordner.rglob('*.py'))

    def kurz(self, datei):
        return Path(datei).name


def _lauf(dateien):
    with tempfile.TemporaryDirectory() as ordner:
        for name, inhalt in dateien.items():
            (Path(ordner) / name).write_text(inhalt, encoding='utf-8')
        return _Werkzeug(ordner).pruefen()


class ImportbloeckeTest(SimpleTestCase):

    def test_gleiche_importbloecke_sind_kein_befund(self):
        ergebnis = _lauf({'eins.py': NUR_IMPORTE, 'zwei.py': NUR_IMPORTE})
        self.assertEqual(ergebnis.befunde, [],
                         'ein Importblock laesst sich nicht zusammenfassen')

    def test_die_zahl_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertuer."""
        ergebnis = _lauf({'eins.py': NUR_IMPORTE, 'zwei.py': NUR_IMPORTE})
        text = ' '.join(' '.join(ergebnis.kopf).split())
        self.assertIn('reine Importbloecke', text)

    def test_echter_doppelter_code_bleibt_ein_befund(self):
        u"""DIE GEGENPROBE: Der Waechter muss weiter anschlagen."""
        ergebnis = _lauf({'eins.py': ECHTER_CODE, 'zwei.py': ECHTER_CODE})
        self.assertEqual(len(ergebnis.befunde), 1, ' | '.join(ergebnis.kopf))

    def test_importe_PLUS_code_bleiben_ein_befund(self):
        u"""Streng gezaehlt: Nur ein Fenster, das NUR Importe enthaelt, faellt raus."""
        gemischt = 'import os\nimport re\n' + ECHTER_CODE
        ergebnis = _lauf({'eins.py': gemischt, 'zwei.py': gemischt})
        self.assertGreaterEqual(len(ergebnis.befunde), 1,
                                ' | '.join(ergebnis.kopf))
