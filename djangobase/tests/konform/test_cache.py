# -*- coding: utf-8 -*-
u"""Sieht der Nutzer je eine gecachte Seite?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „lege einen testcase an um das caching zu überprüfen - damit ich nicht
     gecachte versionen von seiten sehe!"

DIE ZWEI HÄLFTEN, DIE MAN LEICHT VERWECHSELT
============================================
    HTML-Seiten     dürfen NIE aus dem Cache kommen. Wer nach einem Deploy die
                    Seite von gestern sieht, sucht den Fehler im Code — und
                    findet ihn nicht, weil der Code richtig ist.
    Statik (JS/CSS) SOLL aus dem Cache kommen. Sonst lädt jede Seite alles neu.
                    Dass eine geänderte Datei trotzdem ankommt, besorgt die
                    ``?v=``-Kennung: neue Fassung, neue URL, neuer Eintrag.

Eine Middleware, die pauschal ``no-store`` auf ALLES setzt, macht die zweite
Hälfte kaputt. Genau das tut ``NoCacheMiddleware`` in ShortLongX (ihr Kommentar
sagt „during development"): Jeder Seitenaufruf lädt sämtliche Module neu, und
das ``?v=``-Busting daneben ist wirkungslos, weil ohnehin nie gecacht wird.

OHNE DATENBANK
==============
Geprüft wird die Middleware direkt — mit einer erfundenen Anfrage und einer
erfundenen Antwort, wie beim Aufzeichnungs-Test. Kein Client, kein Login, keine
Test-DB.
"""
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from djangobase.apps import CACHE_MIDDLEWARE
from djangobase.cache_middleware import CacheHeaderMiddleware

HTML = b"<html><body><h1>Seite</h1></body></html>"


def _durch(antwort, pfad="/dax-handel/", **get):
    u"""Eine Antwort durch die Middleware schicken."""
    anfrage = RequestFactory().get(pfad, data=get)
    return CacheHeaderMiddleware(lambda r: antwort)(anfrage)


class SeitenNichtCachenTest(SimpleTestCase):
    u"""Der eigentliche Auftrag: keine gecachten Seiten."""

    databases = []

    def test_html_traegt_no_store(self):
        antwort = _durch(HttpResponse(HTML))
        steuerung = (antwort.get("Cache-Control") or "").lower()
        self.assertIn("no-store", steuerung,
                      u"HTML-Antworten müssen no-store tragen, sonst zeigt der "
                      u"Browser nach einem Deploy die alte Seite. Gefunden: %r"
                      % antwort.get("Cache-Control"))
        self.assertIn("no-cache", steuerung)
        self.assertIn("must-revalidate", steuerung)

    def test_alte_zwischenspeicher_werden_mitgenommen(self):
        u"""``Pragma`` und ``Expires`` sind für HTTP/1.0-Proxys — sie kosten
        nichts und schließen die letzte Lücke."""
        antwort = _durch(HttpResponse(HTML))
        self.assertEqual((antwort.get("Pragma") or "").lower(), "no-cache")
        self.assertEqual(antwort.get("Expires"), "0")

    def test_json_bleibt_unberuehrt(self):
        u"""Eine API-Antwort ist keine Seite; wer sie cachen will, soll das
        selbst entscheiden."""
        antwort = _durch(JsonResponse({"ok": True}), pfad="/api/status/")
        self.assertIsNone(antwort.get("Pragma"))

    @override_settings(DJANGOBASE_CACHE_ERLAUBT=["/oeffentlich/"])
    def test_ausnahmen_werden_geachtet(self):
        u"""Wer eine Seite bewusst cachen lässt, trägt ihren Pfad ein."""
        antwort = _durch(HttpResponse(HTML), pfad="/oeffentlich/start/")
        self.assertIsNone(antwort.get("Cache-Control"))

    @override_settings(DJANGOBASE_CACHE_HEADER=False)
    def test_abschaltbar(self):
        antwort = _durch(HttpResponse(HTML))
        self.assertIsNone(antwort.get("Cache-Control"))


class StatikCachenTest(SimpleTestCase):
    u"""Die andere Hälfte: versionierte Statik DARF lange liegen bleiben."""

    databases = []

    def test_statik_mit_kennung_wird_lange_gecacht(self):
        antwort = _durch(HttpResponse(b"/* css */", content_type="text/css"),
                         pfad="/static/app/x.css", v="123")
        steuerung = (antwort.get("Cache-Control") or "").lower()
        self.assertIn("max-age=", steuerung,
                      u"Versionierte Statik soll gecacht werden — sonst lädt "
                      u"jeder Seitenaufruf alles neu, und das ?v=-Busting "
                      u"daneben ist wirkungslos.")
        self.assertIn("immutable", steuerung)
        self.assertNotIn("no-store", steuerung)

    def test_statik_ohne_kennung_wird_nachgefragt(self):
        u"""Ohne Kennung: liegen bleiben ja, ungefragt ausliefern nein.

        BIS ZUM 05.09.2026 STAND HIER `assertIsNone` — die Antwort trug gar
        keinen `Cache-Control`-Header, in der Annahme, dann entscheide
        `Last-Modified`. Das tut es nicht: Ohne Angabe zur Frische schätzt
        der Browser selbst, nämlich 10 % des Dateialters. Eine drei Wochen
        alte Datei gilt damit zwei Tage als frisch und wird ausgeliefert,
        OHNE zu fragen.

        In 3DTools kostete das die halbe Seite: Ein ES-Modul kam frisch, sein
        Geschwistermodul aus dem Zwischenspeicher, und der fehlende Export
        riss den ganzen Modulbaum ab (`SyntaxError: … does not provide an
        export named …`) — HTTP 200, leere Szene, ein einziger Konsoleneintrag.
        """
        antwort = _durch(HttpResponse(b"/* css */", content_type="text/css"),
                         pfad="/static/app/x.css")
        steuerung = (antwort.get("Cache-Control") or "").lower()
        self.assertIn("no-cache", steuerung)

    def test_und_dabei_nicht_verboten(self):
        u"""`no-cache` heißt „vor der Benutzung fragen", nicht „nicht
        speichern". Stünde hier `no-store`, lüde jede Seite alles neu — genau
        der Fehler, gegen den diese Middleware geschrieben ist."""
        antwort = _durch(HttpResponse(b"/* css */", content_type="text/css"),
                         pfad="/static/app/x.css")
        self.assertNotIn("no-store", (antwort.get("Cache-Control") or "").lower())


class EingehaengtTest(SimpleTestCase):
    u"""Die Middleware muss auch laufen."""

    databases = []

    def test_middleware_steht_in_der_kette(self):
        self.assertIn(CACHE_MIDDLEWARE, list(settings.MIDDLEWARE),
                      u"djangobase.apps.ready() trägt sie normalerweise selbst "
                      u"nach — steht sie nicht drin, setzt niemand die Header.")

    def test_keine_pauschale_nocache_middleware(self):
        u"""Eine projekteigene Middleware, die ALLES auf no-store setzt, hebt
        die Statik-Hälfte wieder auf.

        Gemeldet statt stillschweigend überschrieben: Welche von beiden gewinnt,
        hängt an der Reihenfolge in MIDDLEWARE — das ist keine Eigenschaft, auf
        die man sich verlassen sollte."""
        verdaechtig = [m for m in settings.MIDDLEWARE
                       if "nocache" in m.lower().replace("_", "")
                       and not m.startswith("djangobase.")]
        self.assertFalse(verdaechtig,
                         u"Diese Middleware setzt vermutlich pauschal "
                         u"no-store: %s\n\nDamit lädt der Browser bei JEDEM "
                         u"Seitenaufruf sämtliche JS/CSS neu, und das "
                         u"?v=-Cache-Busting ist wirkungslos. djangoBase "
                         u"unterscheidet HTML und versionierte Statik — die "
                         u"eigene kann raus." % ", ".join(verdaechtig))


class GegenprobeTest(SimpleTestCase):
    u"""Greifen die Prüfungen?"""

    databases = []

    def test_ohne_middleware_fehlen_die_header(self):
        u"""Sonst wäre „no-store gefunden" auch ohne die Middleware wahr."""
        antwort = HttpResponse(HTML)
        self.assertIsNone(antwort.get("Cache-Control"))

    def test_html_wird_an_content_type_erkannt(self):
        u"""Nicht am Pfad: Eine Seite unter /api/ ist genauso eine Seite."""
        antwort = _durch(HttpResponse(HTML), pfad="/api/irgendwas/")
        self.assertIn("no-store", (antwort.get("Cache-Control") or "").lower())

    def test_fehler_in_der_middleware_kostet_keine_seite(self):
        u"""Header sind Beiwerk — eine Ausnahme darf die Antwort nicht killen."""
        mw = CacheHeaderMiddleware(lambda r: HttpResponse(HTML))
        mw._setzen = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaputt"))
        antwort = mw(RequestFactory().get("/"))
        self.assertEqual(antwort.status_code, 200)
        self.assertIn(b"<h1>Seite</h1>", antwort.content)
