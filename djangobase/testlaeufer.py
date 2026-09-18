# -*- coding: utf-8 -*-
u"""Testläufer — was in JEDEM Prüflauf gelten soll, steht hier, nicht in jeder Basisklasse.

WARUM EIN LÄUFER UND KEINE BASISKLASSE
======================================
Eine Basisklasse erreicht nur, wer von ihr erbt. Ein Prüffall, den jemand mit
``unittest.TestCase`` oder ``SimpleTestCase`` schreibt, erbt nichts — und
genau der ist es, der dann nach draußen telefoniert oder auf C: schreibt.
pytest löst das mit einer autouse-Fixture (gunSlinger, 18.09.2026); bei
Django ist der Ort dafür ``setup_test_environment`` des Läufers: einmal je
Prozess, vor dem ersten Fall, für alle Fälle.

WAS ER EINRICHTET
=================
- `netzsperre.Netzsperre` — kein Socket nach draußen (Loopback bleibt).
- `tests.ablageumleitung.Ablageumleitung` — ``tempfile`` schreibt ins Projekt.

Beides wird beim Abbau zurückgenommen.

BENUTZUNG
=========
In ``settings.py``::

    TEST_RUNNER = "djangobase.testlaeufer.Testlaeufer"

Wer schon einen eigenen Läufer hat (assistant: ``TaggedDiscoverRunner``), erbt
von diesem statt von ``DiscoverRunner`` — oder ruft in seinem
``setup_test_environment`` ``Netzsperre.einrichten()`` selbst.
"""
from django.test.runner import DiscoverRunner


class Testlaeufer(DiscoverRunner):
    u"""DiscoverRunner plus die Sicherungen, die jeder Lauf haben soll."""

    #: Abschaltbar für einen einzelnen Lauf, etwa einen Longrunner gegen
    #: ein LAN-Gerät: ``DJANGOBASE_NETZSPERRE = False`` in den Settings.
    NETZSPERRE_SCHALTER = "DJANGOBASE_NETZSPERRE"

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        from .tests.ablageumleitung import Ablageumleitung
        Ablageumleitung.einrichten()
        if self.netzsperre_gewollt():
            from .netzsperre import Netzsperre
            Netzsperre.einrichten()

    def teardown_test_environment(self, **kwargs):
        from .netzsperre import Netzsperre
        Netzsperre.aufheben()
        super().teardown_test_environment(**kwargs)

    @classmethod
    def netzsperre_gewollt(cls):
        from django.conf import settings
        return bool(getattr(settings, cls.NETZSPERRE_SCHALTER, True))
