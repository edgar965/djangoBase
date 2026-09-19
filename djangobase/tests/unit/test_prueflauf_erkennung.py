# -*- coding: utf-8 -*-
"""``djangobase.tests`` baut nur im Prüflauf den Prozess um — nie beim bloßen Import.

DER VORFALL (SchweizerMakler, 19.09.2026)
========================================
Hilfe → Tests zählt die Prüffälle mit ``DiscoverRunner.build_suite`` im laufenden
Server. Das importiert ``djangobase.tests`` — und dessen ``__init__`` richtete seit
dem 18.09.2026 bedingungslos die Netzsperre ein. Der Web-Dienst konnte danach kein
Portal mehr erreichen: „Netzwerkzugriff im Test verboten: 13.225.245.23:443", bei
einer Immobiliensuche, nicht in einem Test. Betroffen war jeder Konsument mit
``djangobase.tests.konform`` in den Testbefehlen.
"""

from django.test import SimpleTestCase
from django.test.utils import _TestState

from djangobase import tests as pruefpaket


class DieErkennung(SimpleTestCase):
    def test_im_prueflauf_ist_wahr(self):
        """Hier läuft ein Prüflauf — also muss die Erkennung anschlagen."""
        self.assertTrue(pruefpaket.im_prueflauf())

    def test_ohne_testumgebung_ist_falsch(self):
        """Der Zustand des Servers: ``setup_test_environment`` ist nie gelaufen."""
        gesichert = _TestState.saved_data
        del _TestState.saved_data
        try:
            self.assertFalse(pruefpaket.im_prueflauf())
        finally:
            _TestState.saved_data = gesichert

    def test_die_quelle_haengt_beides_an_die_erkennung(self):
        """Ablageumleitung UND Netzsperre stehen hinter dem ``if`` — nicht nur eine."""
        from pathlib import Path

        quelle = Path(pruefpaket.__file__).read_text(encoding="utf-8")
        kopf, rumpf = quelle.split("if im_prueflauf():", 1)
        self.assertNotIn("Ablageumleitung.einrichten()", kopf)
        self.assertNotIn("Netzsperre.einrichten()", kopf)
        self.assertIn("Ablageumleitung.einrichten()", rumpf)
        self.assertIn("Netzsperre.einrichten()", rumpf)
