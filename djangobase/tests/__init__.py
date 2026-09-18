# -*- coding: utf-8 -*-
"""Prüfungen von djangoBase.

Diese Datei wird beim Import JEDES Prüfmoduls ausgeführt — deshalb steht
hier die Ablageumleitung: Ab jetzt schreibt `tempfile` ins Projekt, nicht
in den System-Zwischenspeicher. Begründung und Zahlen in
`ablageumleitung.py`.
"""

from .ablageumleitung import Ablageumleitung

Ablageumleitung.einrichten()

# Dasselbe für das Netz (18.09.2026): Kein Prüffall von djangoBase telefoniert
# nach draußen. Loopback bleibt offen; wer Netz braucht, stellt den einen Fall
# in `with Netzsperre.erlaubt():`. Begründung in `netzsperre.py`.
from ..netzsperre import Netzsperre  # noqa: E402

Netzsperre.einrichten()
