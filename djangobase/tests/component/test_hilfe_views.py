"""Component-Tests: die djangoBase-Hilfe-/Verwaltungsseiten rendern (Staff)."""
from django.test import override_settings
from django.urls import reverse

from ..base import BasisTest


class HilfeViewsTest(BasisTest):
    def setUp(self):
        self.client = self.staff_client()

    def _ok(self, name):
        r = self.client.get(reverse(name))
        self.assertEqual(r.status_code, 200, f"{name} -> {r.status_code}")
        return r

    def test_versionen(self):
        self._ok("djangobase:versionen")

    def test_logs(self):
        self._ok("djangobase:logs")

    def test_tests(self):
        self._ok("djangobase:tests")

    def test_traffic(self):
        self._ok("djangobase:traffic")

    def test_uebersetzung(self):
        self._ok("djangobase:uebersetzung")

    def test_benutzer_liste(self):
        r = self._ok("djangobase:benutzer")
        self.assertContains(r, "Eingeloggt")   # Spaltenkopf (Session-Status)

    @override_settings(DJANGOBASE={"zugriff": "staff"})
    def test_nicht_staff_kein_zugriff(self):
        """Der Override ist noetig, weil der Test sonst vom Gastgeber abhaengt.

        Gemessen am 13.08.2026 in HumanBodyWeb: Dieses Projekt hat keine
        Anmeldung und setzt `zugriff: none` — damit darf jeder auf die
        Hilfe-Seiten, und der Test schlug fehl, ohne dass an djangoBase etwas
        kaputt war. Ein Test, dessen Ergebnis von den Settings des Gastgebers
        abhaengt, prueft nicht djangoBase, sondern den Gastgeber."""
        from django.test import Client
        c = Client()
        c.force_login(self.nutzer(username="kein_staff", is_staff=False))
        r = c.get(reverse("djangobase:benutzer"))
        self.assertIn(r.status_code, (302, 403))   # umgeleitet oder verboten
