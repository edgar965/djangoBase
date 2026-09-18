# -*- coding: utf-8 -*-
"""`netzsperre.Netzsperre` — im Prüflauf geht kein Socket nach draußen.

DER ANLASS (gunSlinger, 18.09.2026)
===================================
Dort sichert eine autouse-Fixture jeden Test gegen echte HTTP-Aufrufe. Hier
sitzt die Sperre eine Schicht tiefer, am Socket, damit sie ``requests``,
``smtplib`` und ``imaplib`` genauso trifft wie ``httpx`` — und zusätzlich in
``sock_connect`` der asyncio-Loops, weil der Proactor-Loop auf Windows am
``socket.connect`` vorbeigeht.

WAS HIER GEPRÜFT WIRD
=====================
Beide Richtungen: Ein Zugriff nach draußen wird gesperrt UND die Fälle, die
weiter gehen müssen (Loopback, Freigabe-Block, Freigabe-Liste), gehen weiter.
Kein Test hier braucht wirklich Netz — die „Verbindung" nach draußen wird
schon VOR dem Senden abgefangen, und die lokale läuft auf einen Port, an dem
niemand lauscht.

Die Sperre ist ein Prozess-Schalter; jeder Fall räumt sie in ``tearDown`` weg.
"""

import asyncio
import socket

from django.test import SimpleTestCase, override_settings

from djangobase.netzsperre import NetzImTestVerboten, Netzsperre

DRAUSSEN = ("203.0.113.7", 80)  # TEST-NET-3, nie geroutet
LOKAL = ("127.0.0.1", 9)


class _MitSperre(SimpleTestCase):
    def setUp(self):
        Netzsperre.aufheben()
        Netzsperre.zuruecksetzen()
        self.vorher = socket.socket.connect

    def tearDown(self):
        Netzsperre.aufheben()
        Netzsperre.zuruecksetzen()
        self.assertIs(socket.socket.connect, self.vorher, "Die Sperre muss sich spurlos zurücknehmen")

    @staticmethod
    def _verbinden(adresse):
        sock = socket.socket()
        sock.settimeout(0.3)
        try:
            sock.connect(adresse)
        finally:
            sock.close()


class EinZugriffNachDraussen(_MitSperre):
    def test_wird_mit_ziel_und_ausweg_gesperrt(self):
        Netzsperre.einrichten()
        with self.assertRaises(NetzImTestVerboten) as fang:
            self._verbinden(DRAUSSEN)
        self.assertEqual(fang.exception.ziel, "203.0.113.7:80")
        self.assertIn("Netzsperre.erlaubt()", str(fang.exception))
        self.assertEqual(Netzsperre.gesperrt, [("203.0.113.7", 80)])

    def test_ist_kein_oserror_damit_httpx_ihn_nicht_wiederholt(self):
        self.assertFalse(issubclass(NetzImTestVerboten, OSError))
        self.assertTrue(issubclass(NetzImTestVerboten, RuntimeError))

    def test_wird_auch_ueber_asyncio_gesperrt(self):
        Netzsperre.einrichten()

        async def raus():
            await asyncio.open_connection(*DRAUSSEN)

        with self.assertRaises(NetzImTestVerboten):
            asyncio.run(raus())

    def test_geht_ohne_sperre_normal_weiter(self):
        """Die Gegenprobe: ohne `einrichten()` greift nichts ein (Timeout, kein Verbot)."""
        with self.assertRaises(OSError):
            self._verbinden(DRAUSSEN)


class WasWeiterGehenMuss(_MitSperre):
    def test_loopback_bleibt_erlaubt(self):
        """Dahinter liegt die Datenbank — ein Verbot hier hieße: kein Test läuft mehr."""
        Netzsperre.einrichten()
        for adresse in (LOKAL, ("localhost", 9)):
            with self.assertRaises(OSError, msg=str(adresse)):
                self._verbinden(adresse)  # abgelehnt vom OS, nicht von der Sperre
        self.assertTrue(Netzsperre.zulaessig(("::1", 9, 0, 0)))
        self.assertEqual(Netzsperre.gesperrt, [])

    def test_im_erlaubt_block_darf_dieser_thread_hinaus(self):
        Netzsperre.einrichten()
        self.assertFalse(Netzsperre.zulaessig(DRAUSSEN))
        with Netzsperre.erlaubt():
            self.assertTrue(Netzsperre.zulaessig(DRAUSSEN))
            with Netzsperre.erlaubt():  # verschachtelt bleibt offen …
                self.assertTrue(Netzsperre.zulaessig(DRAUSSEN))
            self.assertTrue(Netzsperre.zulaessig(DRAUSSEN))
        self.assertFalse(Netzsperre.zulaessig(DRAUSSEN))  # … und danach wieder zu

    def test_freigabe_liste_und_einstellung(self):
        Netzsperre.einrichten(erlaubt=["203.0.113.7"])
        self.assertTrue(Netzsperre.zulaessig(DRAUSSEN))
        self.assertFalse(Netzsperre.zulaessig(("203.0.113.8", 80)))

    @override_settings(DJANGOBASE_NETZ_ERLAUBT=["203.0.113.9"])
    def test_freigabe_aus_den_settings(self):
        Netzsperre.einrichten()
        self.assertTrue(Netzsperre.zulaessig(("203.0.113.9", 443)))

    def test_unix_und_sonderadressen_bleiben_unberuehrt(self):
        Netzsperre.einrichten()
        self.assertTrue(Netzsperre.zulaessig("/tmp/socket"))
        self.assertTrue(Netzsperre.zulaessig(("", 80)))

    def test_mehrfach_einrichten_ist_harmlos(self):
        Netzsperre.einrichten()
        erste = socket.socket.connect
        Netzsperre.einrichten()
        self.assertIs(socket.socket.connect, erste)
        self.assertTrue(Netzsperre.aktiv())
