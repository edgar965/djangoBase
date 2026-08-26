# -*- coding: utf-8 -*-
u"""Gegenprobe zum Zyklus-Melder: findet er noch, und findet er zu viel?

WARUM ES DIESE PROBE GIBT (25.08.2026)
======================================
``abhaengigkeiten`` meldete im Projekt assistant 13 Zyklen mit der
Schwere ``fehler`` - die einzigen Fehler-Befunde des ganzen Durchgangs
ueber 46 Werkzeuge. Nach Einzelpruefung war KEIN EINZIGER echt.

Alle dreizehn waren bereits aufgeloest, auf genau die zwei Arten, die
Python dafuer kennt::

    def _stand(self):
        from .views_chat_api import ChatApi     # laeuft erst beim Aufruf

    if TYPE_CHECKING:
        from .kern import IndexerJob            # laeuft NIE

Ein Zyklus ueber solche Importe entsteht zur Ladezeit gar nicht. Ihn
als Fehler zu melden dreht die REPARATUR zum BEFUND um: Wer die Liste
nach Schwere sortiert, landet zuerst bei dreizehn Umbauten, von denen
keiner noetig ist - und reisst dabei funktionierende Aufloesungen
wieder auf.

Ein Zyklus ueber Modulebene bleibt ein Fehler. Diese Probe haelt beide
Richtungen fest: Die zweite Haelfte ist die wichtigere, denn die
einfachste Art, die erste gruen zu bekommen, waere den Melder ganz
abzuschalten.
"""
import ast
import textwrap

from django.test import SimpleTestCase

__all__ = ["AbhaengigkeitenProbe"]

ECHTER_ZYKLUS = '''
    from paket.b import Bee

    class Aaa:
        pass
'''

IN_FUNKTION = '''
    class Aaa:
        def hol(self):
            from paket.b import Bee
            return Bee
'''

NUR_TYPPRUEFUNG = '''
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from paket.b import Bee


    class Aaa:
        pass
'''

IM_TRY_OBEN = '''
    try:
        from paket.b import Bee
    except ImportError:
        Bee = None
'''


class AbhaengigkeitenProbe(SimpleTestCase):
    u"""Nur Importe, die beim LADEN laufen, bilden einen Zyklus."""

    def _ziele(self, quelle):
        u"""Welche Module sieht der Melder in diesem Quelltext?"""
        from .abhaengigkeiten import Abhaengigkeiten

        baum = ast.parse(textwrap.dedent(quelle).strip() + '\n')
        return Abhaengigkeiten._importe(baum, 'paket.a', {'paket.b'})

    def test_modulebene_zaehlt(self):
        u"""Der echte Fall - muss weiter gefunden werden."""
        self.assertIn(
            'paket.b', self._ziele(ECHTER_ZYKLUS),
            "Ein Import auf Modulebene läuft beim Laden und bildet einen "
            "echten Zyklus. Wird er nicht mehr gesehen, meldet das Werkzeug "
            "gar keine Zyklen mehr - dann ist es abgeschaltet, nicht "
            "geschaerft.")

    def test_im_try_auf_oberster_ebene_zaehlt_auch(self):
        u"""``try: import`` im Modulrumpf läuft ebenfalls beim Laden."""
        self.assertIn(
            'paket.b', self._ziele(IM_TRY_OBEN),
            "Ein Import in try/except auf oberster Ebene wird beim Laden "
            "ausgefuehrt - er zählt wie jeder andere Modulebene-Import.")

    def test_import_in_funktion_zaehlt_nicht(self):
        u"""Die uebliche Auflösung eines Zirkels - kein Befund."""
        self.assertNotIn(
            'paket.b', self._ziele(IN_FUNKTION),
            "Ein Import im Funktionsrumpf läuft erst beim Aufruf, wenn "
            "beide Module fertig geladen sind. Genau so löst man einen "
            "Zirkel auf; als Zyklus gemeldet wird die Reparatur zum Befund.")

    def test_type_checking_zaehlt_nicht(self):
        u"""``if TYPE_CHECKING:`` wird zur Laufzeit nie ausgefuehrt."""
        self.assertNotIn(
            'paket.b', self._ziele(NUR_TYPPRUEFUNG),
            "Der Block unter `if TYPE_CHECKING:` läuft nie - er steht nur "
            "für die Typpruefung da und ist die sauberste Art, einen "
            "Zirkel zu vermeiden.")
