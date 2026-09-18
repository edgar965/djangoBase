# -*- coding: utf-8 -*-
"""`testlaeufer.Testlaeufer` — der Läufer richtet die Sperren ein, nicht die Basisklasse.

Geprüft wird nur die Verdrahtung: Nach ``setup_test_environment`` steht die
Netzsperre, nach ``teardown_test_environment`` ist sie weg, und der Schalter
``DJANGOBASE_NETZSPERRE = False`` lässt sie aus. Was die Sperre tut, steht in
`test_netzsperre.py`.
"""

import socket
from unittest import mock

from django.test import SimpleTestCase, override_settings
from django.test.runner import DiscoverRunner

from djangobase.netzsperre import Netzsperre
from djangobase.testlaeufer import Testlaeufer


class DerLaeufer(SimpleTestCase):
    def setUp(self):
        Netzsperre.aufheben()
        self.connect_vorher = socket.socket.connect

    def tearDown(self):
        Netzsperre.aufheben()

    def _fahren(self):
        """Djangos eigenes ``setup_test_environment`` läuft hier schon — es darf
        nicht ein zweites Mal aufgerufen werden, deshalb wird der Elternteil
        stillgelegt. Geprüft wird, was DIESER Läufer hinzufügt."""
        laeufer = Testlaeufer(verbosity=0)
        with (
            mock.patch.object(DiscoverRunner, "setup_test_environment"),
            mock.patch.object(DiscoverRunner, "teardown_test_environment"),
        ):
            laeufer.setup_test_environment()
            aktiv = Netzsperre.aktiv()
            laeufer.teardown_test_environment()
        return aktiv

    def test_richtet_die_netzsperre_ein_und_nimmt_sie_zurueck(self):
        self.assertTrue(self._fahren())
        self.assertFalse(Netzsperre.aktiv())
        self.assertIs(socket.socket.connect, self.connect_vorher)

    @override_settings(DJANGOBASE_NETZSPERRE=False)
    def test_laesst_sich_je_lauf_abschalten(self):
        self.assertFalse(self._fahren())
