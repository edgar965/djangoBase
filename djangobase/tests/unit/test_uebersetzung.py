"""Unit-Tests: Übersetzungs-Katalog (ohne externe Übersetzungs-API)."""
from djangobase import uebersetzung as ue
from djangobase.models import TextQuelle

from ..base import BasisTest


class UebersetzungUnitTest(BasisTest):
    def setUp(self):
        ue.katalog_leeren()

    def test_hash_ist_stabil_und_unterscheidet(self):
        self.assertEqual(ue._hash("Hallo"), ue._hash("Hallo"))
        self.assertNotEqual(ue._hash("Hallo"), ue._hash("Welt"))

    def test_basis_sprache_bleibt_unveraendert(self):
        self.assertEqual(ue.text_holen("Orte", ue.BASIS), "Orte")

    def test_unbekannter_text_wird_als_quelle_registriert(self):
        ue.text_holen("Ausflüge", ue.BASIS)
        self.assertTrue(TextQuelle.objects.filter(quelle="Ausflüge").exists())

    def test_fehlende_uebersetzung_faellt_auf_deutsch_zurueck(self):
        self.assertEqual(ue.text_holen("Mehr laden", "en"), "Mehr laden")

    def test_leerer_text(self):
        self.assertEqual(ue.text_holen("   ", "en"), "")

    def test_sprachcodes_sind_eindeutig(self):
        codes = [c for c, _n, _f in ue.SPRACHEN]
        self.assertEqual(len(codes), len(set(codes)))

    def test_html_zerlegung_erhaelt_tags(self):
        # uebersetze() darf ohne Netz keine echte Übersetzung machen, aber die
        # Tag-Zerlegung ist reine Logik: der Regex trennt Tags von Text.
        teile = ue._TAG_RE.split('<a href="x">Hallo</a>')
        self.assertIn("Hallo", teile)
        self.assertTrue(any(t.startswith("<a") for t in teile))
