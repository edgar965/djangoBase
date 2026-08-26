"""Component-Tests: Einstellungen-Tab-Seite (Profil-Combobox + Tabs + Speichern)."""
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from djangobase import store
from djangobase.conf import conf

from ..base import BasisTest, StoreIsolationMixin


def _mit_schalter(wert):
    u"""``DJANGOBASE`` des Wirt-Projekts mit gesetztem ``profile_switcher``.

    WARUM DER TEST DEN SCHALTER SELBST SETZT (17.08.2026)
    Er forderte die Profil-Combobox unbedingt — und war damit im Wirt
    ``assistant`` dauerhaft rot: Der setzt ``profile_switcher: False``, weil es
    dort nur EIN Profil gibt, und die Combobox steht in der Vorlage hinter genau
    diesem Schalter. Ein Test, der die Konfiguration des Wirts nicht beachtet,
    prueft nicht djangoBase, sondern das Projekt, in dem er zufaellig laeuft.
    """
    return dict(getattr(settings, "DJANGOBASE", {}) or {},
                profile_switcher=wert)


class EinstellungenTabsTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()
        self.c = self.staff_client()
        self.url = reverse("djangobase:einstellungen")

    def test_get_zeigt_combobox_und_tabs(self):
        with override_settings(DJANGOBASE=_mit_schalter(True)):
            r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="profil"')          # Profil-Combobox
        self.assertContains(r, 'data-bs-toggle="tab"')   # Tab-Navigation

    def test_ohne_schalter_keine_combobox(self):
        u"""Die Gegenprobe: ``profile_switcher=False`` blendet sie wirklich aus.

        Ohne diesen Fall koennte der Schalter unwirksam werden, ohne dass es
        auffällt — und der Test oben wuerde weiter grün sein."""
        with override_settings(DJANGOBASE=_mit_schalter(False)):
            r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'id="profil-select"')
        self.assertContains(r, 'data-bs-toggle="tab"')   # Tabs bleiben

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

    def test_layout_dropdown_zeigt_beide_optionen(self):
        r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="base_template"')
        self.assertContains(r, "djangoBase Standard")                 # Option 1
        self.assertContains(r, "djangobase/base_cleanorga.html")      # Option 2 (CleanOrga)

    def test_mitgeliefertes_cleanorga_layout_rendert(self):
        # Zweites, helles Layout per base_template aktivieren -> Seite rendert
        # in djangobase/base_cleanorga.html und lädt cleanorga.css.
        store.speichern_gruppe("djangobase",
                               {"base_template": "djangobase/base_cleanorga.html"})
        r = self.c.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "djangobase/base_cleanorga.html")
        self.assertContains(r, "cleanorga.css")
