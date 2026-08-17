# -*- coding: utf-8 -*-
u"""Tests der Routen-Auswertung in `testdeckung`.

ANLASS (17.08.2026, 3DTools): Das Werkzeug las den Zielnamen aus
``callback.__name__``. Bei einer klassenbasierten Ansicht heisst der IMMER
``view`` — ``View.as_view()`` gibt eine so benannte Funktion zurueck. Zwei
Folgen, beide still:

1. **Dreizehn Seiten verschwanden hinter einer.** Der Merkposten ``gesehen``
   hielt nur den Zielnamen; ab der zweiten klassenbasierten Seite galt alles
   als „schon gesehen". Ein Projekt, das seine Seiten als Klassen baut, sah
   damit fast keine Luecken mehr — es sah AUFGERAEUMT aus.
2. **Djangos eigene Ansicht galt als Projektseite.** Der Admin legt fuer die
   alte Objekt-Adresse eine ``RedirectView`` an; die wohnt in
   ``django.views.generic.base`` und passte auf keinen Eintrag der
   ``FREMD``-Liste (die kannte nur ``django.contrib``).

Beides sind Fehlalarm bzw. Blindstelle in EINEM Werkzeug — die teuerste Sorte,
weil das Ergebnis danach besser aussieht, als das Projekt ist.
"""
from django.test import override_settings
from django.urls import path
from django.views.generic import RedirectView, TemplateView

from djangobase.skills.testdeckung import Testdeckung

from ..base import BasisTest


#: Das Werkzeug laesst alles liegen, dessen Modulname „djangobase" enthaelt —
#: es soll das HOST-Projekt pruefen, nicht sich selbst. Diese Testdatei liegt
#: aber IN djangobase. Die beiden Attrappen bekommen deshalb ausdruecklich den
#: Modulnamen eines gedachten Projekts; ohne das prueft der Test nichts (die
#: Liste kam leer zurueck, und „leer" haette wie „nichts offen" ausgesehen).
PROJEKTMODUL = "meinprojekt.seiten"


class EigeneSeite(TemplateView):
    u"""Eine Projektseite als Klasse - wie 3DTools sie baut."""
    template_name = "djangobase/base.html"


def freie_ansicht(request):        # pragma: no cover - nur als Route gebraucht
    u"""Eine Ansicht als Funktion - der klassische Fall."""
    return None


EigeneSeite.__module__ = PROJEKTMODUL
freie_ansicht.__module__ = PROJEKTMODUL


#: Vier Routen: zwei Projektklassen, eine Projektfunktion, eine Django-eigene.
#: Der Modulname dieser Datei enthaelt „tests" — deshalb tragen die Zielnamen
#: hier absichtlich KEIN „test", sonst faende sich jede Marke in den Testtexten
#: selbst wieder.
MUSTER = [
    path("erste/", EigeneSeite.as_view(), name="erste_seite"),
    path("zweite/", EigeneSeite.as_view(), name="zweite_seite"),
    path("dritte/", freie_ansicht, name="dritte_seite"),
    path("weiter/", RedirectView.as_view(url="/erste/"), name="weiterleitung"),
]

urlpatterns = MUSTER


class RoutenTest(BasisTest):

    def _routen(self):
        u"""``_routen`` mit leeren Testtexten - alles gilt als ungeprueft."""
        return Testdeckung()._routen("")

    @override_settings(ROOT_URLCONF="djangobase.tests.unit.test_testdeckung")
    def test_zwei_klassenseiten_sind_zwei_zeilen(self):
        u"""Der Kern des Fehlers: Beide heissen ``view``."""
        stellen = [z["stelle"] for z in self._routen()]
        self.assertIn("/erste/", stellen)
        self.assertIn("/zweite/", stellen, "die zweite Klassenseite fehlt — "
                                           "der Merkposten haengt am Zielnamen")

    @override_settings(ROOT_URLCONF="djangobase.tests.unit.test_testdeckung")
    def test_funktionsansicht_kommt_weiter_vor(self):
        u"""Gegenprobe: Der klassische Fall darf nicht verloren gehen."""
        self.assertIn("/dritte/", [z["stelle"] for z in self._routen()])

    @override_settings(ROOT_URLCONF="djangobase.tests.unit.test_testdeckung")
    def test_django_eigene_ansicht_zaehlt_nicht(self):
        u"""``RedirectView`` ist Rahmencode, keine Projektseite."""
        self.assertNotIn("/weiter/", [z["stelle"] for z in self._routen()])

    @override_settings(ROOT_URLCONF="djangobase.tests.unit.test_testdeckung")
    def test_erwaehnter_pfad_gilt_als_geprueft(self):
        u"""Steht der Pfad in einem Test, ist die Seite nicht mehr offen."""
        offen = Testdeckung()._routen('self.client.get("/erste/")')
        self.assertNotIn("/erste/", [z["stelle"] for z in offen])
        self.assertIn("/zweite/", [z["stelle"] for z in offen])

    def test_modul_kommt_von_der_klasse(self):
        u"""``_modul`` fragt ``view_class`` - sonst waere jede klassenbasierte
        Ansicht Rahmencode, weil die Funktion aus ``django.views.generic``
        stammt."""
        self.assertEqual(Testdeckung._modul(EigeneSeite.as_view()), PROJEKTMODUL)
        self.assertTrue(
            Testdeckung._modul(RedirectView.as_view(url="/")).startswith("django."))
        self.assertEqual(Testdeckung._modul(freie_ansicht), PROJEKTMODUL)
