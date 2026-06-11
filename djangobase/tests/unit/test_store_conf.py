"""Unit-Tests: Einstellungs-Store + conf()-Overrides (isolierte JSON-Datei)."""
from djangobase import store
from djangobase.conf import conf

from ..base import BasisTest, StoreIsolationMixin


class StoreConfTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()   # echte .djangobase.json bleibt unberührt

    def test_gruppe_speichern_wirkt_in_conf(self):
        store.speichern_gruppe("freigabe", {"freigabe_nutzer_noetig": True})
        self.assertTrue(conf().get("freigabe_nutzer_noetig"))

    def test_gruppe_leeren_setzt_default(self):
        store.speichern_gruppe("freigabe", {"freigabe_nutzer_noetig": True})
        store.leeren_gruppe("freigabe")
        self.assertFalse(conf().get("freigabe_nutzer_noetig"))

    def test_nur_whitelist_keys_gespeichert(self):
        store.speichern({"freigabe_nutzer_noetig": True, "boeses_feld": "x"})
        gespeichert = store.laden()
        self.assertIn("freigabe_nutzer_noetig", gespeichert)
        self.assertNotIn("boeses_feld", gespeichert)

    def test_gruppe_merge_behaelt_andere(self):
        store.speichern_gruppe("freigabe", {"freigabe_nutzer_noetig": True})
        store.speichern_gruppe("uebersetzung", {"uebersetzung_sprachen": ["en"]})
        self.assertTrue(conf().get("freigabe_nutzer_noetig"))
        self.assertEqual(conf().get("uebersetzung_sprachen"), ["en"])
