"""Unit-Tests: Traffic-Helfer (Gerät, Bot, anonymer Hash, Verbrauch)."""
from django.test import RequestFactory

from djangobase import traffic
from djangobase.models import Verbrauch

from ..base import BasisTest

DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit Chrome/126 Safari"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148 Safari"
IPAD = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) Safari"

# Header, die ein echtes Chromium auf HTTPS mitschickt.
SEC_FETCH = {"HTTP_SEC_FETCH_SITE": "none", "HTTP_SEC_FETCH_MODE": "navigate",
             "HTTP_SEC_FETCH_DEST": "document"}


class TrafficUnitTest(BasisTest):
    def setUp(self):
        self.rf = RequestFactory()

    def test_geraet_erkennung(self):
        self.assertEqual(traffic.geraet_von_ua(IPHONE), "mobile")
        self.assertEqual(traffic.geraet_von_ua(IPAD), "tablet")
        self.assertEqual(traffic.geraet_von_ua(DESKTOP), "desktop")

    def test_bot_erkennung(self):
        self.assertTrue(bool(traffic.BOT_RE.search("Googlebot/2.1")))
        self.assertTrue(bool(traffic.BOT_RE.search("python-requests/2.0")))
        self.assertTrue(bool(traffic.BOT_RE.search("Scrapy/2.11")))
        self.assertTrue(bool(traffic.BOT_RE.search("axios/1.6.0")))
        self.assertFalse(bool(traffic.BOT_RE.search(DESKTOP)))

    # ---- ist_bot: kombinierte Heuristik ---------------------------------
    def test_ist_bot_leerer_ua(self):
        req = self.rf.get("/", secure=True)
        self.assertTrue(traffic.ist_bot(req, "", "/"))

    def test_ist_bot_bot_ua(self):
        req = self.rf.get("/", secure=True, **SEC_FETCH)
        self.assertTrue(traffic.ist_bot(req, "python-requests/2.0", "/"))

    def test_echter_browser_mit_sec_fetch_ist_kein_bot(self):
        req = self.rf.get("/touren/", secure=True, **SEC_FETCH)
        self.assertFalse(traffic.ist_bot(req, DESKTOP, "/touren/"))

    def test_gefaelschtes_chromium_ohne_sec_fetch_ist_bot(self):
        # Chrome-UA über HTTPS, aber keine Fetch-Metadata-Header -> Scraper.
        req = self.rf.get("/touren/", secure=True)
        self.assertTrue(traffic.ist_bot(req, DESKTOP, "/touren/"))

    def test_chromium_ohne_sec_fetch_ueber_http_ist_kein_bot(self):
        # Über reines HTTP senden Browser keine Fetch-Metadata -> Heuristik
        # darf NICHT greifen (sonst False Positives in der lokalen Entwicklung).
        req = self.rf.get("/touren/")   # secure=False
        self.assertFalse(traffic.ist_bot(req, DESKTOP, "/touren/"))

    def test_safari_ohne_sec_fetch_ist_kein_bot(self):
        # iPhone-Safari (kein "Chrome/" im UA) -> Heuristik greift nicht.
        req = self.rf.get("/touren/", secure=True)
        self.assertFalse(traffic.ist_bot(req, IPHONE, "/touren/"))

    def test_scanner_pfad_trotz_browser_ua_ist_bot(self):
        req = self.rf.get("/wp-login.php", secure=True, **SEC_FETCH)
        self.assertTrue(traffic.ist_bot(req, DESKTOP, "/wp-login.php"))

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
