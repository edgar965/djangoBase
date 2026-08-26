# -*- coding: utf-8 -*-
u"""Die Baumsicht — misst, ob das Objektmodell wirklich ein Baum ist.

DER ZWEIFEL, DER RECHT HATTE (Edgar, 23.08.2026)
================================================
Auf die Meldung „29 eigene Klassen entstehen auf Modulebene, Idealwert 1":

    „Ist denn alles so implementiert? Kann ich nicht glauben, hast du eine
     Basisklasse, und alle andere geht wie ein Baum davon ab??"

Er hatte recht. Die erste Fassung zaehlte nur die WURZELN und schloss
daraus, alles andere haenge an einem Baum. Das war eine Annahme, keine
Messung. Nachgemessen an CamTrack::

    Klassen im Projekt                 548   100 %
      haengen als self.x an einer       74    14 %   <- der Baum
      entstehen auf Modulebene          29     5 %   <- Wurzeln
      nur oertlich in Funktionen       319    58 %
      nirgends erzeugt                 127    23 %

Vierzehn Prozent. Und es gibt nicht EINEN Baum, sondern fuenf mittelgrosse
(PersonDetector 14 Klassen, StrictPersonDetector 10, LiveOrchestrator 9) —
daneben 474 Klassen, die an keinem haengen.

WAS HIER GEPRUEFT WIRD
======================
1. Die vier Toepfe sind erschoepfend und ueberschneidungsfrei.
2. Was das Rahmenwerk erzeugt, gilt nicht als tot. Ohne diese Ausnahme
   meldet das Werkzeug halb Django als toten Bestand.
3. Eine Fabrik-Methode (``cls()``) zaehlt als Erzeugung. Beim ersten Lauf
   stand ``AusschnittNachzieher`` unter den Toten — er laeuft im Dienst.
4. Die dicken Aeste werden benannt: Wer haelt wie viele?
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.objektwurzeln import Baumsicht

from ..base import BasisTest


class BaumsichtTest(BasisTest):

    def _lauf(self, dateien, **argumente):
        ordner = Path(tempfile.mkdtemp(prefix='baum_'))
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden('objektwurzeln')
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    @staticmethod
    def _zahl(satz, stichwort):
        for zeile in satz.kopf:
            if zeile.startswith(stichwort):
                return int(zeile.split(':')[1].strip().split()[0])
        raise AssertionError('%r steht nicht im Kopf: %s' % (stichwort,
                                                             satz.kopf))

    # ---------------------------------------------------- die vier Toepfe
    def test_die_vier_toepfe_stehen_im_kopf(self):
        satz = self._lauf({'a.py': 'class A:\n    pass\n'}, ab='0')
        for stichwort in ('im Baum', 'Wurzeln', 'nur oertlich',
                          'nirgends erzeugt'):
            self.assertTrue(any(z.startswith(stichwort) for z in satz.kopf),
                            '%r fehlt: %s' % (stichwort, satz.kopf))

    def test_jede_klasse_liegt_in_genau_einem_topf(self):
        satz = self._lauf({'a.py': (
            'class Zaehler:\n    pass\n\n\n'          # im Baum
            'class Wurzel:\n    pass\n\n\n'           # Modulebene
            'class Fluechtig:\n    pass\n\n\n'        # nur oertlich
            'class Tot:\n    pass\n\n\n'              # nirgends
            'class Halter:\n'
            '    def __init__(self):\n'
            '        self.z = Zaehler()\n\n\n'
            'def mach():\n'
            '    return Fluechtig()\n\n\n'
            'W = Wurzel()\n')}, ab='0')
        gesamt = self._zahl(satz, 'im Baum')
        gesamt += self._zahl(satz, 'Wurzeln')
        gesamt += self._zahl(satz, 'nur oertlich')
        gesamt += self._zahl(satz, 'nirgends erzeugt')
        alle = int(satz.kopf[1].split()[0])
        self.assertEqual(gesamt, alle,
                         'die Toepfe ueberschneiden sich oder es fehlt einer')

    def test_ein_gehaltenes_liegt_im_baum(self):
        satz = self._lauf({'a.py': (
            'class Zaehler:\n    pass\n\n\n'
            'class Halter:\n'
            '    def __init__(self):\n'
            '        self.z = Zaehler()\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'im Baum'), 1)

    def test_die_dicken_aeste_werden_benannt(self):
        satz = self._lauf({'a.py': (
            'class A:\n    pass\n\n\nclass B:\n    pass\n\n\n'
            'class Dienst:\n'
            '    def __init__(self):\n'
            '        self.a = A()\n'
            '        self.b = B()\n')}, ab='0')
        self.assertTrue(any('Dienst (2)' in z for z in satz.kopf), satz.kopf)

    # ------------------------------------------- was NICHT tot ist
    def test_eine_basisklasse_ist_nicht_tot(self):
        """Erzeugt wird die Unterklasse."""
        satz = self._lauf({'a.py': (
            'class Basis:\n    pass\n\n\n'
            'class Kind(Basis):\n    pass\n\n\n'
            'def mach():\n    return Kind()\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'nirgends erzeugt'), 0)

    def test_ein_model_ist_nicht_tot(self):
        """Der ORM erzeugt es, nicht der Quelltext. Ohne diese Ausnahme
        meldet das Werkzeug halb Django als toten Bestand."""
        satz = self._lauf({'a.py': (
            'from django.db import models\n\n\n'
            'class Kamera(models.Model):\n'
            '    pass\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'nirgends erzeugt'), 0)

    def test_eine_fabrik_methode_zaehlt_als_erzeugung(self):
        """DER FEHLER AUS DEM ERSTEN LAUF.

        ``AusschnittNachzieher`` stand unter den ersten zehn Toten — er wird
        ueber ``get_instance()`` -> ``cls()`` erzeugt und laeuft im Dienst.
        """
        satz = self._lauf({'a.py': (
            'class Wache:\n'
            '    _instanz = None\n\n'
            '    @classmethod\n'
            '    def get_instance(cls):\n'
            '        if cls._instanz is None:\n'
            '            cls._instanz = cls()\n'
            '        return cls._instanz\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'nirgends erzeugt'), 0,
                         'eine Klasse mit Fabrik-Methode gilt als tot')

    def test_meta_ist_kein_objekt(self):
        satz = self._lauf({'a.py': (
            'from django.db import models\n\n\n'
            'class Kamera(models.Model):\n'
            '    class Meta:\n'
            '        ordering = []\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'nirgends erzeugt'), 0)

    # --------------------------------------------------- was tot IST
    def test_eine_klasse_die_niemand_ruft_wird_gemeldet(self):
        satz = self._lauf({'a.py': (
            'class Vergessen:\n'
            '    def tu_was(self):\n'
            '        return 1\n')}, ab='0')
        self.assertEqual(self._zahl(satz, 'nirgends erzeugt'), 1)
        self.assertTrue(any('Vergessen' in b.was for b in satz.befunde))

    def test_der_befund_sagt_was_zu_tun_ist(self):
        satz = self._lauf({'a.py': 'class Vergessen:\n    pass\n'}, ab='0')
        tot = [b for b in satz.befunde if 'Vergessen' in b.was]
        self.assertTrue(tot)
        # Seit der Korrektur vom 23.08.2026 (Utility-Klassen galten als tot)
        # nennt der Befund beide Formen, in denen der Name vorkommen koennte.
        self.assertIn('Vor dem Löschen', tot[0].warum)
        self.assertIn('Vergessen.etwas', tot[0].warum)


class DieAnteileStimmen(BasisTest):

    def test_anteil_rechnet_prozent(self):
        sicht = Baumsicht({'A', 'B', 'C', 'D'}, {'A'}, {'B'}, {'C'}, {})
        self.assertAlmostEqual(sicht.anteil(sicht.im_baum), 25.0)
        self.assertEqual(sicht.nur_lokal, {'D'})

    def test_ohne_klassen_kein_teilen_durch_null(self):
        sicht = Baumsicht(set(), set(), set(), set(), {})
        self.assertEqual(sicht.anteil(set()), 0.0)
        self.assertTrue(sicht.zeilen())
