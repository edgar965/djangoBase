# -*- coding: utf-8 -*-
"""KonformTest — die Basis der Prüfungen, die den KONSUMENTEN ansehen.

WARUM EINE EIGENE BASIS (18.09.2026)
====================================
Die Konformitätsprüfungen fragen: erbt DIESES Projekt djangoBase wirklich —
LOGGING über ``dblog.config``, Menü und Version im ``DJANGOBASE``-Dict,
Vorlagen mit Fassungspfad, Tabellen mit Sortierung? Das sind Fragen an ein
Projekt mit Inhalt. Der Prüf-Wirt von djangoBase (``A:\\tmp_dbhost``) hat
keinen: keine Vorlage, kein Skript, kein Menü. Dort meldeten 19 dieser
Prüfungen rot — nicht, weil etwas kaputt war, sondern weil sie ein Projekt
maßen, das keines ist. Rot ohne Befund ist die Sorte Meldung, die man
irgendwann überliest.

Ein Wirt, der kein Konsument ist, sagt das in seinen Einstellungen::

    DJANGOBASE_KONFORM = False

Dann werden diese Prüfungen ÜBERSPRUNGEN, mit Grund — der dritte Zustand
neben grün und rot (dieselbe Regel wie bei ``test_skills_codequalitaet``).
Konsumenten setzen nichts; für sie gilt weiter ``True``.

Was NICHT über diese Basis läuft: die ``GegenprobeTest``-Klassen und die
Werkzeugprüfungen daneben. Sie prüfen die Erkennung selbst (trifft das Muster
das Gemeinte?) und brauchen keinen Konsumenten — sie laufen überall.
"""

import unittest

from django.conf import settings
from django.test import SimpleTestCase

__all__ = ["KonformTest"]


class KonformTest(SimpleTestCase):
    """Eine Prüfung, die Einstellungen oder Dateien des Konsumenten liest."""

    databases = []

    GRUND = (
        "Konformitätsprüfung gilt dem Konsumenten — dieser Wirt sagt mit "
        "DJANGOBASE_KONFORM = False, dass er keiner ist"
    )

    @classmethod
    def setUpClass(cls):
        if not getattr(settings, "DJANGOBASE_KONFORM", True):
            raise unittest.SkipTest(cls.GRUND)
        super().setUpClass()
