# -*- coding: utf-8 -*-
u"""Wann gilt eine Tabellenzelle als ZAHL — und wann als Text?

DER BEFUND (28.08.2026, 3DTools, Spalte „Name" der Auftragstabelle)
===================================================================
`TabellenSortierung._zahl` warf alles außer Ziffern und Trennern weg und las
den Rest als Zahl. Aus Dateinamen wurden damit unsichtbare Zahlen::

    "Speed.mp4"           ->  ".4"    ->    4
    "005 DanceLang.mp4"   -> "005.4"  ->   54
    "Nussknacker.webm"    -> ""       -> null (ans Ende sortiert)

Die Spalte sortierte danach — sichtbar falsch, aber nicht als Fehler erkennbar:
Die Reihenfolge sieht nur „irgendwie durcheinander" aus. Auch das eigene
Beispiel im Kopf von `tabellen_sortierung.js` war betroffen: „Kapitel 9" wurde
zu 9 und kam nie bei `localeCompare` an, obwohl die Datei genau das verspricht.

WARUM ES HIER GEPRÜFT WIRD UND NICHT IM BROWSER
===============================================
Das Muster ist eine reguläre Ausdrucksform in einer JS-Datei. Node ist nicht in
jeder Umgebung da; Pythons `re` kann dieselbe Form lesen, wenn man die
JS-Schreibweise abschneidet. Geprüft wird damit GENAU das Muster aus der
ausgelieferten Datei — keine Kopie, die auseinanderlaufen kann.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

JS = (Path(__file__).resolve().parents[2] / 'static' / 'djangobase' / 'js'
      / 'tabellen_sortierung.js')

#: Die Zeile, die das Muster hält.
MUSTER = re.compile(r'const ZAHL_MIT_EINHEIT\s*=\s*(/.*?/);', re.S)


def _als_python(js_muster):
    u"""`/…/` in ein Python-Muster übersetzen (ohne Flags — es hat keine)."""
    inhalt = js_muster.strip()[1:-1]
    # JS erlaubt `\$` und `\/`; Python kennt beides als schlichtes Zeichen.
    return re.compile(inhalt.replace(r'\/', '/').replace(r'\$', r'\$'))


class ZahlErkennungTest(SimpleTestCase):
    u"""Das Muster aus der ausgelieferten Datei, an echten Zellinhalten."""

    #: (Zellinhalt, gilt als Zahl)
    FAELLE = (
        # Zahlen — die müssen numerisch sortieren
        ('1.234,5', True),
        ('-0,18', True),
        ('0', True),
        ('1234', True),
        ('32,7 MB', True),
        ('15 %', True),
        ('12 €', True),
        ('€ 12', True),
        ('120 km/h', True),
        # Text — der muss über localeCompare gehen
        ('Speed.mp4', False),
        ('005 DanceLang.mp4', False),
        ('001_ShyrinKurz.mp4', False),
        ('Nussknacker.webm', False),
        ('Kapitel 9', False),
        ('28.08.2026 14:05', False),
        ('GVHMR', False),
        ('', False),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        text = JS.read_text(encoding='utf-8')
        treffer = MUSTER.search(text)
        assert treffer, 'ZAHL_MIT_EINHEIT steht nicht mehr in %s' % JS.name
        cls.muster = _als_python(treffer.group(1))

    def test_jeder_fall(self):
        for inhalt, erwartet in self.FAELLE:
            with self.subTest(zelle=inhalt):
                ist = bool(self.muster.match(inhalt.strip()))
                self.assertIs(ist, erwartet,
                              u'%r gilt als %s, erwartet %s'
                              % (inhalt, 'Zahl' if ist else 'Text',
                                 'Zahl' if erwartet else 'Text'))

    def test_die_gegenprobe_wuerde_anschlagen(self):
        u"""Das ALTE Verhalten muss durchfallen — sonst prüft der Test nichts.

        So sah `_zahl` bis zum 28.08.2026 aus: alles außer Ziffern und
        Trennern wegwerfen.
        """
        def alt(text):
            roh = re.sub(r'[^\d,.\-]', '', text)
            return bool(re.search(r'\d', roh))

        self.assertTrue(alt('Speed.mp4'),
                        'die alte Fassung hielt Dateinamen fuer Zahlen')
        self.assertFalse(self.muster.match('Speed.mp4'),
                         'die neue darf das nicht mehr')

    def test_das_muster_steht_nur_einmal_in_der_datei(self):
        u"""Zwei Fassungen desselben Musters laufen auseinander."""
        text = JS.read_text(encoding='utf-8')
        self.assertEqual(text.count('ZAHL_MIT_EINHEIT ='), 1)
