# -*- coding: utf-8 -*-
u"""Ein Routenziel, das eine Klassenmethode ist, muss seine Klasse behalten.

DER ANLASS (02.09.2026, Projekt 3DTools)
========================================
Nach dem Umbau „Funktionen in Klassen" zeigen dort alle Routen auf
Klassenmethoden::

    path('', Webseiten.start, name='dashboard')

`Einstiegssucher.routen()` schnitt mit ``rsplit('.', 1)[-1]`` alles bis
auf ``start`` weg, und `Workflowliste._start` suchte danach eine FREIE
Funktion oder Klasse dieses Namens. Die gibt es nicht — **88 von 89
Routen fielen aus**, die Workflow-Landkarte blieb leer, und das Werkzeug
`dokumentation` meldete „0 Wege gezeichnet".

Das ist die gefaehrliche Sorte Null: Sie liest sich wie „nichts zu
beanstanden" und heisst „nichts gesehen". Nach der Reparatur sind es
8 Wege und 172 gegen den Quelltext gehaltene Kaesten.

WAS NICHT KAPUTTGEHEN DARF
==========================
Projekte mit Modulfunktionen als View (``views.dashboard``) und solche
mit klassenbasierten Views (``X.as_view()``) muessen unveraendert
bleiben. Unterschieden wird an der Grossschreibung — derselben Regel,
nach der der ``as_view``-Zweig schon vorher gearbeitet hat.
"""
from django.test import SimpleTestCase

from ...umbau.einstiege import Einstiegssucher


class EineKlassenmethodeBehaeltIhreKlasse(SimpleTestCase):
    u"""Der Fall, an dem 88 Routen hingen."""

    def test_die_klasse_bleibt_vor_dem_methodennamen(self):
        self.assertEqual(Einstiegssucher._kurzziel('views.Webseiten.start'),
                         'Webseiten.start')

    def test_auch_bei_langem_modulpfad(self):
        self.assertEqual(
            Einstiegssucher._kurzziel(
                'core.views.api.Auftragsendpunkte.starten_formular'),
            'Auftragsendpunkte.starten_formular')

    def test_ohne_modul_bleibt_es_wie_es_ist(self):
        self.assertEqual(Einstiegssucher._kurzziel('Webseiten.start'),
                         'Webseiten.start')


class EineModulfunktionBleibtEinNackterName(SimpleTestCase):
    u"""Die Gegenprobe: Was vorher richtig war, bleibt richtig.

    Ohne sie koennte die Regel auch jedes Modul mitschleppen — dann
    faende `_start` in den anderen Projekten nichts mehr.
    """

    def test_ein_kleingeschriebenes_modul_faellt_weg(self):
        self.assertEqual(Einstiegssucher._kurzziel('views.dashboard'),
                         'dashboard')

    def test_auch_ein_zwischenmodul_faellt_weg(self):
        self.assertEqual(
            Einstiegssucher._kurzziel('views.admin_views.export_csv'),
            'export_csv')

    def test_ein_nackter_name_bleibt_nackt(self):
        self.assertEqual(Einstiegssucher._kurzziel('dashboard'), 'dashboard')
