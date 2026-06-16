"""Unit-Tests: Multi-Profil-Store + base_template-Override (isolierte JSON)."""
import json

from djangobase import store
from djangobase.conf import conf

from ..base import BasisTest, StoreIsolationMixin


class ProfileStoreTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()

    def test_default_ein_aktives_profil(self):
        liste = store.profile_liste()
        self.assertEqual(len(liste), 1)
        slug, _label, aktiv = liste[0]
        self.assertTrue(aktiv)
        self.assertEqual(slug, store.STANDARD_SLUG)

    def test_profil_anlegen_und_aktivieren(self):
        slug = store.profil_anlegen("CleanOrga")
        self.assertIn(slug, [s for s, _l, _a in store.profile_liste()])
        self.assertTrue(store.aktiv_setzen(slug))
        self.assertEqual(store.aktiv_slug(), slug)

    def test_werte_pro_profil_getrennt(self):
        store.speichern_gruppe("website", {"titel": "A"})
        self.assertEqual(conf()["titel"], "A")
        slug = store.profil_anlegen("Zweit", kopie_von=store.aktiv_slug())
        store.aktiv_setzen(slug)
        self.assertEqual(conf()["titel"], "A")          # Kopie uebernimmt Werte
        store.speichern_gruppe("website", {"titel": "B"})
        self.assertEqual(conf()["titel"], "B")
        store.aktiv_setzen(store.STANDARD_SLUG)
        self.assertEqual(conf()["titel"], "A")          # Standard unveraendert

    def test_letztes_profil_nicht_loeschbar(self):
        self.assertFalse(store.profil_loeschen(store.STANDARD_SLUG))

    def test_aktives_loeschen_wechselt_aktiv(self):
        slug = store.profil_anlegen("Weg")
        store.aktiv_setzen(slug)
        self.assertTrue(store.profil_loeschen(slug))
        self.assertEqual(store.aktiv_slug(), store.STANDARD_SLUG)

    def test_altes_flaches_format_wird_migriert(self):
        # alte flache JSON-Datei (Format v1) simulieren
        store._pfad().write_text(json.dumps({"titel": "Alt"}), encoding="utf-8")
        self.assertEqual(conf()["titel"], "Alt")
        self.assertEqual(len(store.profile_liste()), 1)
        # erstes Speichern schreibt das neue v2-Format
        store.speichern_gruppe("website", {"titel": "Neu"})
        roh = json.loads(store._pfad().read_text(encoding="utf-8"))
        self.assertEqual(roh.get("format"), 2)
        self.assertIn("profile", roh)
        self.assertEqual(conf()["titel"], "Neu")


class BaseTemplateConfTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()

    def test_default(self):
        self.assertEqual(conf()["base_template"], "djangobase/base.html")

    def test_override_wirkt(self):
        store.speichern_gruppe("djangobase", {"base_template": "cleanorga/base.html"})
        self.assertEqual(conf()["base_template"], "cleanorga/base.html")

    def test_leerer_wert_faellt_auf_default(self):
        store.speichern_gruppe("djangobase", {"base_template": ""})
        self.assertEqual(conf()["base_template"], "djangobase/base.html")
