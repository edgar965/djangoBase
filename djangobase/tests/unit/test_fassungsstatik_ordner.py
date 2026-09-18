# -*- coding: utf-8 -*-
"""Welche Baeume die Fassung bestimmen — und welche nicht.

ANLASS (06.09.2026, in Roomguest gemessen): Ein Projekt, das seine Statik nach
Django-Art in ``<app>/static/`` legt und kein ``STATICFILES_DIRS`` setzt, hatte
hier NULL Ordner zu durchsuchen. Die Fassung blieb konstant ``0``, jede Adresse
lautete ``/statik/v-0/…`` — und ``ausliefern`` gibt sie mit ``immutable`` fuer
ein Jahr frei. Eine Aenderung waere beim Browser nie angekommen.
"""

import os
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from djangobase.fassungsstatik import Fassungsstatik

#: Das Repo, in dem das Paket ``djangobase`` liegt. Mit ihm als ``BASE_DIR``
#: ist ``djangobase`` eine PROJEKTEIGENE Anwendung mit ``static/`` — der
#: Fall aus Roomguest, nachgestellt am echten Paket statt an einer Attrappe.
REPO = Path(__file__).resolve().parents[3]


@override_settings(BASE_DIR=str(REPO), STATICFILES_DIRS=[], STATIC_ROOT=None)
class DieDurchsuchtenOrdner(SimpleTestCase):
    databases = []

    def setUp(self):
        Fassungsstatik.vergessen()
        self.addCleanup(Fassungsstatik.vergessen)

    def test_app_ordner_zaehlen_mit(self):
        """Ohne sie waere die Fassung in App-Statik-Projekten immer 0."""
        gefunden = [os.path.normcase(o) for o in Fassungsstatik._ordner()]
        self.assertIn(os.path.normcase(str(REPO / "djangobase" / "static")), gefunden)

    @override_settings(BASE_DIR=str(REPO.parent / "gibt-es-nicht"))
    def test_eine_app_ausserhalb_zaehlt_nicht(self):
        """Die Gegenprobe: Ausserhalb von ``BASE_DIR`` ist es Fremdcode."""
        self.assertEqual(Fassungsstatik._app_ordner(), [])

    def test_site_packages_bleibt_aussen_vor(self):
        """Eine virtuelle Umgebung IM Projektordner ist der Normalfall
        (``A:\\Roomguest\\pythonVENV``). Ohne die Pruefung landete Djangos
        eigene Admin-Statik im Durchlauf — teuer und sachlich falsch."""
        for ordner in Fassungsstatik._ordner():
            teile = os.path.abspath(ordner).replace("\\", "/").split("/")
            for fremd in Fassungsstatik.FREMD:
                self.assertNotIn(fremd, teile, "%s liegt in %s" % (ordner, fremd))

    @override_settings(BASE_DIR=None)
    def test_ohne_basisordner_keine_app_ordner(self):
        """Ohne ``BASE_DIR`` fehlt die Grenze — dann lieber gar nichts."""
        self.assertEqual(Fassungsstatik._app_ordner(), [])

    def test_die_fassung_ist_eine_zeit_keine_null(self):
        """Die Gegenprobe zum Anlass: 0 hiesse „aendert sich nie"."""
        self.assertGreater(Fassungsstatik.fassung(), 0)

    def test_der_pfad_traegt_die_fassung(self):
        pfad = Fassungsstatik.pfad("x/y.js")
        self.assertTrue(pfad.startswith("/%s/v-" % Fassungsstatik.PRAEFIX), pfad)
        self.assertTrue(pfad.endswith("/x/y.js"), pfad)
        self.assertNotIn("/v-0/", pfad)
