"""Component-Tests: Einstellungen-Tab-Seite (Profil-Combobox + Tabs + Speichern)."""
from django.urls import reverse

from djangobase import store
from djangobase.conf import conf

from ..base import BasisTest, StoreIsolationMixin


class EinstellungenTabsTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()
        self.c = self.staff_client()
        self.url = reverse("djangobase:einstellungen")

    def test_get_zeigt_combobox_und_tabs(self):
        r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="profil"')          # Profil-Combobox
        self.assertContains(r, 'data-bs-toggle="tab"')   # Tab-Navigation

    def test_profil_neu_legt_an_und_aktiviert(self):
        r = self.c.post(self.url, {"aktion": "profil_neu", "profil_label": "CleanOrga"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(store.profile_liste()), 2)
        self.assertNotEqual(store.aktiv_slug(), store.STANDARD_SLUG)

    def test_profil_wechseln(self):
        slug = store.profil_anlegen("Zweit")
        r = self.c.post(self.url, {"aktion": "profil_aktiv", "profil": slug})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(store.aktiv_slug(), slug)

    def test_gruppe_speichern_wirkt(self):
        r = self.c.post(self.url, {"gruppe": "website", "titel": "Meine App",
                                   "logo_icon": "", "untertitel": ""})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(conf()["titel"], "Meine App")

    def test_ungueltiges_base_template_wird_abgelehnt(self):
        r = self.c.post(self.url, {"gruppe": "djangobase",
                                   "base_template": "gibt/es/nicht.html"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(conf()["base_template"], "djangobase/base.html")

    def test_gueltiges_base_template_wird_gespeichert(self):
        r = self.c.post(self.url, {"gruppe": "djangobase",
                                   "base_template": "djangobase/base.html"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(conf()["base_template"], "djangobase/base.html")

    def test_mitgeliefertes_cleanorga_layout_rendert(self):
        # Zweites, helles Layout per base_template aktivieren -> Seite rendert
        # in djangobase/base_cleanorga.html und lädt cleanorga.css.
        store.speichern_gruppe("djangobase",
                               {"base_template": "djangobase/base_cleanorga.html"})
        r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "djangobase/base_cleanorga.html")
        self.assertContains(r, "cleanorga.css")
