# -*- coding: utf-8 -*-
u"""Wer ruft wen — für Funktionen dasselbe, was das Klassenmodell für
Klassen leistet.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „mache alle Klassen in allen Tabs und alle Funktionen aus allen Tabs
     auch als Gliederung mit Knöpfen, so dass man sieht, wer sie nutzt, und
     welche andere Unterklassen / funktionen sie nutzen"

Das Klassenmodell beantwortet das über den BESITZ (``self.x = Klasse()``).
Für eine freie Funktion gibt es keinen Besitz — sie wird gerufen. Und davon
gibt es in CamTrack 820 auf Modulebene, mehr als es Klassen gibt.

WAS DER ERSTE LAUF ZEIGTE
=========================
    1737 Definitionen, 1691 Aufrufe, **359 Funktionen ruft niemand**
    `person_rename`              genutzt von: niemandem   (Django-Ansicht)
    `compute_accept_threshold`   genutzt von: NUR einer Testklasse

Die letzte Zeile ist der interessante Fall: Produktionscode, den
ausschliesslich ein Test anfasst.
"""
import tempfile
from pathlib import Path

from djangobase.umbau.aufrufnetz import Aufrufnetz, Stelle

from ..base import BasisTest


def _netz(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='an_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return Aufrufnetz(ordner).lesen()


class WerRuftWen(BasisTest):

    def _kette(self):
        return _netz({'a.py': (
            'def lade():\n    return 1\n\n\n'
            'def zeichne():\n'
            '    return lade()\n\n\n'
            'class Seite:\n'
            '    def bauen(self):\n'
            '        return zeichne()\n')})

    def test_ein_aufruf_wird_beiden_seiten_zugeschrieben(self):
        n = self._kette()
        self.assertEqual(n.steckbrief('lade')['genutzt_von'], ['zeichne'])
        self.assertEqual(n.steckbrief('zeichne')['nutzt'], ['lade'])

    def test_eine_klasse_gilt_als_rufer(self):
        u"""Nicht die einzelne Methode — im Bild ist die Klasse der Kasten."""
        self.assertEqual(self._kette().steckbrief('zeichne')['genutzt_von'],
                         ['Seite'])

    def test_ueber_dateigrenzen_hinweg(self):
        u"""DER FEHLER AUS DEM ERSTEN WURF: Bei EINEM Durchgang zaehlte nur,
        was vorher in derselben Datei stand."""
        n = _netz({'spaet.py': 'def zieht():\n    return frueh()\n',
                   'frueh.py': 'def frueh():\n    return 1\n'})
        self.assertEqual(n.steckbrief('frueh')['genutzt_von'], ['zieht'])

    def test_was_niemand_ruft_hat_eine_leere_liste(self):
        n = _netz({'a.py': 'def einsam():\n    pass\n'})
        self.assertEqual(n.steckbrief('einsam')['genutzt_von'], [])
        self.assertEqual(n.kennzahlen()['ungenutzte_funktionen'], 1)

    # ── was NICHT gezaehlt wird ──────────────────────────────────
    def test_eingebaute_zaehlen_nicht(self):
        u"""Ohne diese Liste ist `len` der meistgenutzte Baustein."""
        n = _netz({'a.py': 'def zaehle(x):\n    return len(x)\n'})
        self.assertEqual(n.steckbrief('zaehle')['nutzt'], [])

    def test_fremde_namen_zaehlen_nicht(self):
        n = _netz({'a.py': 'import json\n\n\n'
                           'def lies(t):\n    return json.loads(t)\n'})
        self.assertEqual(n.steckbrief('lies')['nutzt'], [])

    def test_ein_methodenaufruf_wird_nicht_geraten(self):
        u"""`self.zeichner.malen()` — der Name `malen` sagt nichts darueber,
        WELCHE Klasse gemeint ist. Wer das ohne Typinformation aufloest,
        raet; ein geratenes Netz ist schlimmer als keines."""
        n = _netz({'a.py': (
            'def malen():\n    pass\n\n\n'
            'class Seite:\n'
            '    def bauen(self):\n'
            '        self.zeichner.malen()\n')})
        self.assertEqual(n.steckbrief('malen')['genutzt_von'], [])

    def test_der_selbstaufruf_zaehlt_nicht(self):
        n = _netz({'a.py': 'def rekursiv(n):\n'
                           '    return rekursiv(n - 1) if n else 0\n'})
        self.assertEqual(n.steckbrief('rekursiv')['genutzt_von'], [])

    # ── Auskunft ─────────────────────────────────────────────────
    def test_die_art_steht_dabei(self):
        n = self._kette()
        self.assertEqual(n.steckbrief('lade')['art'], Stelle.FUNKTION)
        self.assertEqual(n.steckbrief('Seite')['art'], Stelle.KLASSE)

    def test_die_fundstelle_steht_dabei(self):
        s = _netz({'wo/a.py': 'def hier():\n    pass\n'}).steckbrief('hier')
        self.assertEqual((s['datei'], s['zeile']), ('wo/a.py', 1))

    def test_eine_unbekannte_liefert_nichts(self):
        self.assertIsNone(self._kette().steckbrief('GibtsNicht'))
