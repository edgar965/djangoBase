"""Unit-Tests: Traffic-Helfer (Gerät, Bot, anonymer Hash, Verbrauch)."""
from djangobase import traffic
from djangobase.models import Verbrauch

from ..base import BasisTest

DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit Chrome/126 Safari"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148 Safari"
IPAD = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) Safari"


class TrafficUnitTest(BasisTest):
    def test_geraet_erkennung(self):
        self.assertEqual(traffic.geraet_von_ua(IPHONE), "mobile")
        self.assertEqual(traffic.geraet_von_ua(IPAD), "tablet")
        self.assertEqual(traffic.geraet_von_ua(DESKTOP), "desktop")

    def test_bot_erkennung(self):
        self.assertTrue(bool(traffic.BOT_RE.search("Googlebot/2.1")))
        self.assertTrue(bool(traffic.BOT_RE.search("python-requests/2.0")))
        self.assertFalse(bool(traffic.BOT_RE.search(DESKTOP)))

    def test_besucher_hash_anonym_und_stabil(self):
        h1 = traffic.besucher_hash("1.2.3.4", "UA")
        h2 = traffic.besucher_hash("1.2.3.4", "UA")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)
        self.assertNotIn("1.2.3.4", h1)   # IP darf nicht im Hash auftauchen

    def test_besucher_hash_unterscheidet_nutzer(self):
        self.assertNotEqual(traffic.besucher_hash("1.2.3.4", "UA"),
                            traffic.besucher_hash("9.9.9.9", "UA"))

    def test_verbrauch_buchen_nur_gueltige_typen(self):
        traffic.verbrauch_buchen("tile", anzahl=5, bytes=1000)
        traffic.verbrauch_buchen("route", anzahl=1, bytes=500, detail="auto")
        traffic.verbrauch_buchen("quatsch", anzahl=99)   # wird ignoriert
        self.assertEqual(Verbrauch.objects.filter(typ="tile").count(), 1)
        self.assertEqual(Verbrauch.objects.filter(typ="route").count(), 1)
        self.assertFalse(Verbrauch.objects.filter(typ="quatsch").exists())

    def test_verbrauch_werte_geklemmt(self):
        traffic.verbrauch_buchen("tile", anzahl=-5, bytes=-9)
        v = Verbrauch.objects.get(typ="tile")
        self.assertGreaterEqual(v.anzahl, 0)
        self.assertGreaterEqual(v.bytes, 0)
