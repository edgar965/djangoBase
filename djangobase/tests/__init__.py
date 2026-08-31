# -*- coding: utf-8 -*-
u"""Prüfungen von djangoBase.

Diese Datei wird beim Import JEDES Prüfmoduls ausgeführt — deshalb steht
hier die Ablageumleitung: Ab jetzt schreibt `tempfile` ins Projekt, nicht
in den System-Zwischenspeicher. Begründung und Zahlen in
`ablageumleitung.py`.
"""
from .ablageumleitung import Ablageumleitung

Ablageumleitung.einrichten()
