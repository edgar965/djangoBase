"""Component-Tests: Benutzer-Aktionen (Freischalten, E-Mail-Bestätigung)."""
from django.urls import reverse

from djangobase.models import Teilnehmer

from ..base import BasisTest


class BenutzerAktionenTest(BasisTest):
    def setUp(self):
        self.client = self.staff_client()

    def test_freischalten_setzt_freigegeben_am(self):
        u = self.nutzer(username="wartend", is_active=False)
        self.client.post(reverse("djangobase:benutzer_status", args=[u.pk]),
                         {"zurueck": "/benutzer/"})
        u.refresh_from_db()
        self.assertTrue(u.is_active)
        t = Teilnehmer.objects.get(user=u)
        self.assertIsNotNone(t.freigegeben_am)   # Audit-Zeitstempel gesetzt

    def test_inline_sprache_aendern(self):
        u = self.nutzer(username="sprachwechsel")
        self.client.post(reverse("djangobase:benutzer_inline", args=[u.pk]),
                         {"feld": "sprache", "wert": "en", "zurueck": "/benutzer/"})
        self.assertEqual(Teilnehmer.objects.get(user=u).sprache, "en")
