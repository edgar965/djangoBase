"""Integration-Tests: Login-Audit (Sitzungen) + Signup-Freigabe-Gating."""
from django.test import Client

from djangobase.models import LoginSitzung, Teilnehmer

from ..base import BasisTest, StoreIsolationMixin


class LoginAuditTest(BasisTest):
    def test_login_legt_sitzung_an_logout_schliesst_sie(self):
        self.nutzer(username="audit", passwort="pw-test-12345")
        c = Client()
        self.assertTrue(c.login(username="audit", password="pw-test-12345"))
        s = LoginSitzung.objects.filter(benutzer="audit").order_by("-beginn").first()
        self.assertIsNotNone(s)
        self.assertIsNone(s.ende)
        # eingeloggt-Flag gesetzt
        self.assertTrue(Teilnehmer.objects.get(user__username="audit").eingeloggt)
        c.logout()
        s.refresh_from_db()
        self.assertIsNotNone(s.ende)   # Logout schließt die Sitzung

    def test_zweiter_login_schliesst_offene_sitzung(self):
        self.nutzer(username="doppel", passwort="pw-test-12345")
        Client().login(username="doppel", password="pw-test-12345")
        Client().login(username="doppel", password="pw-test-12345")
        offen = LoginSitzung.objects.filter(benutzer="doppel", ende__isnull=True).count()
        self.assertEqual(offen, 1)   # nur die jeweils neueste bleibt offen


class SignupGatingTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()

    def _signup(self, rolle):
        from djangobase.forms import RollenSignupForm
        from django.contrib.auth import get_user_model
        f = RollenSignupForm()
        f.cleaned_data = {"vorname": "T", "name": "X", "rolle": rolle, "anbietername": ""}
        u = get_user_model()(username=f"signup_{rolle}", email=f"{rolle}@example.com")
        u.set_password("pw-test-12345")
        f.signup(None, u)
        u.refresh_from_db()
        return u

    def test_ohne_gating_sofort_aktiv(self):
        from djangobase import store
        store.leeren_gruppe("freigabe")
        self.assertTrue(self._signup("nutzer").is_active)

    def test_nutzer_gating_sperrt_login(self):
        from djangobase import store
        store.speichern_gruppe("freigabe", {"freigabe_nutzer_noetig": True})
        self.assertFalse(self._signup("nutzer").is_active)

    def test_provider_gating_trifft_nur_provider(self):
        from djangobase import store
        store.speichern_gruppe("freigabe", {"freigabe_provider_noetig": True})
        self.assertFalse(self._signup("anbieter").is_active)
        self.assertTrue(self._signup("nutzer").is_active)   # Nutzer ungated
