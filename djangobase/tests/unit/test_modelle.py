"""Unit-Tests: Benutzer-Modelle (Rollen, Helfer, Audit-Modelle)."""
from django.utils import timezone

from djangobase.models import (LoginSitzung, Provider, Teilnehmer,
                               als_provider, als_teilnehmer)

from ..base import BasisTest


class ModelleUnitTest(BasisTest):
    def test_signal_legt_teilnehmerprofil_an(self):
        u = self.nutzer()
        self.assertTrue(Teilnehmer.objects.filter(user=u).exists())

    def test_als_provider_und_zurueck(self):
        u = self.nutzer()
        prov = als_provider(u, anbietername="Test-Anbieter")
        self.assertIsInstance(prov, Provider)
        self.assertTrue(Provider.objects.filter(pk=prov.pk).exists())
        # Degradieren: Provider-Zeile weg, Teilnehmer bleibt
        als_teilnehmer(u)
        self.assertFalse(Provider.objects.filter(user=u).exists())
        self.assertTrue(Teilnehmer.objects.filter(user=u).exists())

    def test_initialen(self):
        u = self.nutzer(first_name="Edgar", last_name="Mustermann")
        self.assertEqual(u.profil.initialen, "EM")

    def test_loginsitzung_snapshot_ueberlebt_loeschung(self):
        u = self.nutzer(username="weg")
        s = LoginSitzung.objects.create(user=u, benutzer=u.username,
                                        beginn=timezone.now())
        u.delete()
        s.refresh_from_db()
        self.assertIsNone(s.user_id)        # FK auf NULL
        self.assertEqual(s.benutzer, "weg")  # Name bleibt erhalten
