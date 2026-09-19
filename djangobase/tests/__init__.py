# -*- coding: utf-8 -*-
"""Prüfungen von djangoBase.

Diese Datei wird beim Import JEDES Prüfmoduls ausgeführt — deshalb steht
hier die Ablageumleitung: Ab jetzt schreibt `tempfile` ins Projekt, nicht
in den System-Zwischenspeicher. Begründung und Zahlen in
`ablageumleitung.py`.

NUR IM PRÜFLAUF (19.09.2026)
============================
Importiert wird dieses Paket nicht nur vom Testläufer. Hilfe → Tests zählt die
Prüffälle mit ``DiscoverRunner.build_suite`` — IM LAUFENDEN SERVER. Wer dort
``djangobase.tests.konform`` in den Testbefehlen führt (jeder Konsument), holte
sich damit die Netzsperre in den Web-Dienst: In SchweizerMakler schlug danach
jede Immobiliensuche fehl mit „Netzwerkzugriff im Test verboten: 13.225.245.23:443",
nachdem Edgar die Tests-Seite geöffnet hatte (error.log 14:56). Ein Import darf
keinen Prozess umbauen, in dem gar nicht geprüft wird.

Woran ein Prüflauf zu erkennen ist: Djangos ``setup_test_environment`` legt
``_TestState.saved_data`` an — und der Läufer ruft es VOR ``build_suite``, also
vor diesem Import. Im Server gibt es das Attribut nicht.
"""

from .ablageumleitung import Ablageumleitung


def im_prueflauf():
    """Läuft gerade ein Django-Prüflauf in diesem Prozess?"""
    from django.test.utils import _TestState

    return hasattr(_TestState, "saved_data")


if im_prueflauf():
    Ablageumleitung.einrichten()

    # Dasselbe für das Netz (18.09.2026): Kein Prüffall von djangoBase telefoniert
    # nach draußen. Loopback bleibt offen; wer Netz braucht, stellt den einen Fall
    # in `with Netzsperre.erlaubt():`. Begründung in `netzsperre.py`.
    from ..netzsperre import Netzsperre

    Netzsperre.einrichten()
