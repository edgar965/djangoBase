"""Integration-Test: Übersetzungs-Status (Registrieren → Übersetzung → Bilanz).
Ohne externe API: eine Übersetzung wird direkt in die DB gelegt und der
Katalog/Status daraus berechnet."""
from djangobase import uebersetzung as ue
from djangobase.models import TextQuelle, Uebersetzung

from ..base import BasisTest, StoreIsolationMixin


class UebersetzungFlowTest(StoreIsolationMixin, BasisTest):
    def setUp(self):
        self.store_isolieren()
        ue.katalog_leeren()
        from djangobase import store
        store.speichern_gruppe("uebersetzung", {"uebersetzung_sprachen": ["en"]})

    def test_status_zaehlt_aktuell_veraltet_fehlt(self):
        # zwei Quelltexte registrieren
        ue.text_holen("Orte", ue.BASIS)
        ue.text_holen("Ausflüge", ue.BASIS)
        q1 = TextQuelle.objects.get(quelle="Orte")
        # genau eine aktuelle Übersetzung anlegen
        Uebersetzung.objects.create(quelle=q1, sprache="en", text="Places",
                                    quelle_hash=ue._hash("Orte"))
        ue.katalog_leeren()
        anzahl, zeilen = ue.sprach_status()
        en = next(z for z in zeilen if z["code"] == "en")
        self.assertEqual(anzahl, 2)
        self.assertEqual(en["aktuell"], 1)
        self.assertEqual(en["fehlt"], 1)

    def test_geaenderter_quelltext_macht_uebersetzung_veraltet(self):
        ue.text_holen("Mehr laden", ue.BASIS)
        q = TextQuelle.objects.get(quelle="Mehr laden")
        Uebersetzung.objects.create(quelle=q, sprache="en", text="Load more",
                                    quelle_hash=ue._hash("alter text"))  # falscher Hash
        ue.katalog_leeren()
        _anzahl, zeilen = ue.sprach_status()
        en = next(z for z in zeilen if z["code"] == "en")
        self.assertEqual(en["veraltet"], 1)

    def test_aktive_sprachen_aus_store(self):
        self.assertIn("en", ue.aktive_sprachen())
