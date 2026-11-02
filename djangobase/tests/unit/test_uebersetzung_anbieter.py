"""Unit-Tests: Anbieterwahl der Übersetzung (Google Vorgabe, Azure umschaltbar) — ohne Netz, mit Attrappen."""

from unittest import mock

from django.test import override_settings

from djangobase import uebersetzung as ue
from djangobase.uebersetzer_azure import AzureUebersetzer
from djangobase.uebersetzer_google import GoogleUebersetzer

from ..base import BasisTest


class UebersetzungAnbieterTest(BasisTest):
    def _conf(self, **werte):
        return mock.patch.object(ue, "conf", return_value={"uebersetzung_anbieter": "google", **werte})

    def test_vorgabe_ist_google(self):
        with self._conf(), override_settings(AZURE_TRANSLATOR_KEY="x"):
            self.assertEqual(ue.anbieter(), "google")

    def test_azure_ohne_schluessel_bleibt_google(self):
        with self._conf(uebersetzung_anbieter="azure"), override_settings(AZURE_TRANSLATOR_KEY=""):
            self.assertEqual(ue.anbieter(), "google")

    def test_azure_mit_schluessel(self):
        with self._conf(uebersetzung_anbieter="azure"), override_settings(AZURE_TRANSLATOR_KEY="x"):
            self.assertEqual(ue.anbieter(), "azure")

    def test_azure_liefert_ergebnis(self):
        with (
            self._conf(uebersetzung_anbieter="azure"),
            override_settings(AZURE_TRANSLATOR_KEY="x"),
            mock.patch.object(AzureUebersetzer, "uebersetze", return_value="Places") as azure,
            mock.patch.object(GoogleUebersetzer, "uebersetze") as google,
        ):
            self.assertEqual(ue.uebersetze("Orte", "en"), "Places")
        azure.assert_called_once_with("Orte", "de", "en")
        google.assert_not_called()

    def test_azure_liefert_nichts_dann_google(self):
        with (
            self._conf(uebersetzung_anbieter="azure"),
            override_settings(AZURE_TRANSLATOR_KEY="x"),
            mock.patch.object(AzureUebersetzer, "uebersetze", return_value=None),
            mock.patch.object(GoogleUebersetzer, "uebersetze", return_value="Places") as google,
        ):
            self.assertEqual(ue.uebersetze("Orte", "en"), "Places")
        google.assert_called_once()

    def test_azure_ohne_schluessel_ruft_nichts_auf(self):
        with override_settings(AZURE_TRANSLATOR_KEY=""), mock.patch("urllib.request.urlopen") as netz:
            self.assertIsNone(AzureUebersetzer.uebersetze("Orte", "de", "en"))
        netz.assert_not_called()

    def test_azure_schreibt_chinesisch_anders(self):
        with override_settings(AZURE_TRANSLATOR_KEY="x", AZURE_TRANSLATOR_REGION="westeurope"):
            anfrage = AzureUebersetzer._anfrage("<b>Orte</b>", "de", "zh-CN")
        self.assertIn("to=zh-Hans", anfrage.full_url)
        self.assertIn("textType=html", anfrage.full_url)
        self.assertEqual(anfrage.get_header("Ocp-apim-subscription-region"), "westeurope")
