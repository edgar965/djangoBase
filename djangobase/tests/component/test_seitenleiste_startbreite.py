# -*- coding: utf-8 -*-
"""Die Seitenleiste hat schon beim ERSTEN Aufbau ihre richtige Breite.

DER BEFUND (10.09.2026, im Wirt CamTrack gemessen)
==================================================
Die Ruhemessung des Wirts (``longrunner/test_gitter_ruhemessung.py``)
meldete bei jedem Seitenaufbau ``Kachel aendert 2x ihre Groesse
(erlaubt: 0)`` — und zwar fuer ALLE elf Kacheln. Nachgemessen mit einem
Beobachter, der vor dem ersten Bildaufbau steht, frisches Browserprofil
(also ohne ``localStorage``)::

    285 ms  --sidebar-width nicht gesetzt   Inhalt 1350 px breit
    310 ms  --sidebar-width: 200px          Inhalt waechst ...
    449 ms  ...                             Inhalt 1398 px breit

Der Ablauf war: Das Stilblatt ``sidebar.css`` setzt ``--sidebar-width:
250px``, der fruehe Setzer in ``_shell.html`` liess die Variable ohne
gespeicherten Wert in Ruhe — und ``sidebar_resizer.js`` schob sie danach
auf seinen ``data-default``. Der Wirt hatte den auf 200 gestellt. Also
50 Punkte Sprung bei jedem Aufbau, vorgefuehrt von ``.main-wrapper``
mit ``transition: margin-left 0.2s``, und jede Kachel wanderte mit.

Nach der Behebung: EINE Groesse ueber den ganzen Aufbau, die Ruhemessung
des Wirts meldet ``Groesse 0x`` fuer alle elf Kacheln.

WARUM DAS IN DJANGOBASE NIE AUFFIEL
===================================
djangoBases eigener ``sidebar_default`` ist 250 — derselbe Wert wie im
Stilblatt. Die beiden Vorgaben widersprachen sich also nur bei einem Wirt,
der ``sidebar_default`` verstellt. Ein Standard, den zwei Stellen
unabhaengig voneinander festlegen, ist einer zu viel.

WARUM DER LAUFZEIT-SPEICHER HIER STILLGELEGT WIRD
=================================================
``conf()`` legt am Ende ``_overrides_anwenden()`` darueber — die auf der
Einstellungen-Seite gespeicherten Werte des WIRTS. Die erste Fassung
dieser Pruefung lief ohne das und war damit gruen, weil CamTrack
zufaellig 200 gespeichert hatte; ``override_settings`` kam gar nicht zum
Zug. Das ist genau der Fall, vor dem ``test_hilfe_views`` warnt: Ein
Test, dessen Ergebnis von den Einstellungen des Wirts abhaengt, prueft
nicht djangoBase.
"""

import re
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from ..base import BasisTest

#: Der Setzer steht im Kopf und ist an dieser Eigenschaft zu erkennen.
SETZER = re.compile(r"setProperty\('--sidebar-width'")

#: Was der Wirt gespeichert hat, geht diese Pruefung nichts an.
OHNE_SPEICHER = "djangobase.store.laden"


class _Startbreite(BasisTest):
    def setUp(self):
        self.client = self.staff_client()

    def _kopf(self):
        with mock.patch(OHNE_SPEICHER, return_value={}):
            antwort = self.client.get(reverse("djangobase:versionen"))
        self.assertEqual(antwort.status_code, 200)
        return antwort.content.decode("utf-8").split("</head>", 1)[0]


@override_settings(
    DJANGOBASE={"resizable_sidebar": True, "sidebar_default": 200, "sidebar_min": 140, "sidebar_max": 480}
)
class DieStartbreiteStehtImHtml(_Startbreite):
    def test_der_setzer_steht_im_kopf(self):
        self.assertRegex(
            self._kopf(),
            SETZER,
            "Ohne diesen Setzer malt der Browser erst die Breite aus dem "
            "Stilblatt und rueckt danach auf die eingestellte — sichtbar "
            "als Sprung des ganzen Inhalts.",
        )

    def test_die_eingestellte_vorgabe_steht_darin(self):
        """Nicht irgendein Wert, sondern der aus den Einstellungen.

        Das war die Luecke: Den Setzer gab es, aber er sprang nur an, wenn
        ein gespeicherter Wert da war. Ohne den galt das Stilblatt — und
        das kennt ``sidebar_default`` nicht.
        """
        hinter_dem_setzer = self._kopf().split("setProperty('--sidebar-width'")[-1][:400]
        self.assertIn(
            "200",
            hinter_dem_setzer,
            'Die Vorgabe aus DJANGOBASE["sidebar_default"] muss im Kopf '
            "landen, sonst wirkt sie erst nach dem ersten Bildaufbau.",
        )

    def test_die_grenzen_stehen_ebenfalls_darin(self):
        """Sonst kann der Setzer einen gespeicherten Ausreisser nicht kappen."""
        kopf = self._kopf()
        self.assertIn("var min=140, max=480;", kopf)


@override_settings(DJANGOBASE={"resizable_sidebar": False})
class OhneVerstellbareLeisteGibtEsIhnNicht(_Startbreite):
    """Wer die Leiste nicht verstellen laesst, braucht auch den Setzer
    nicht — dann gilt schlicht das Stilblatt, und es gibt nichts, was
    davon abweichen koennte."""

    def test_kein_setzer_im_kopf(self):
        self.assertNotRegex(self._kopf(), SETZER)
