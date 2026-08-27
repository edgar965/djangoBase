# -*- coding: utf-8 -*-
u"""Kommt die Aufzeichnung auch in Projekten an, die djangoBases Vorlagen NICHT nutzen?

DER BEFUND (21.08.2026, gemeldet aus CamTrack)
=============================================
    „Die Übernahme kam nicht an. djangoBase legt die Bedienung in seine eigene
     Seitenleiste und lädt die Module in seiner eigenen Hülle — beides benutzt
     CamTrack nicht. Ergebnis: Auf /kameras/, /live/kalender/ und jeder anderen
     Seite gab es weder den Bereich noch die Module. Der Aufzeichner lief
     ausschließlich unter /hilfe/ — also genau dort, wo niemand etwas
     aufzeichnen will."

Das Markup lag in ``_sidebar.html``, die Skripte in ``_shell.html``. Beide
Vorlagen gehören djangoBase; wer eine eigene Basis-Vorlage hat, erbt sie nicht.

WAS HIER GEPRÜFT WIRD
=====================
Nicht, dass die Dateien existieren — das taten sie vorher auch. Geprüft wird das
Verhalten an einer HTML-Antwort, die von djangoBase NICHTS weiß: ein nacktes
``<html><body>…</body></html>``. Genau das ist der Fall, der gemeldet wurde.

Dazu die Grenzen, an denen eine solche Middleware sonst Schaden anrichtet: JSON,
Weiterleitungen, Fehlerseiten, Fragmente ohne ``</body>`` — und die doppelte
Einbindung, wenn eine Vorlage die Module schon selbst lädt.
"""
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from djangobase.aufzeichnung_middleware import AufzeichnungMiddleware

FREMDE_SEITE = (b"<!doctype html><html><head><title>Kameras</title></head>"
                b"<body><h1>Kameras</h1></body></html>")


def _mw(antwort):
    u"""Middleware mit fester Antwort - ohne echte Request-Kette."""
    return AufzeichnungMiddleware(lambda request: antwort)


class MiddlewareTest(SimpleTestCase):

    def setUp(self):
        self.rf = RequestFactory()

    def _durch(self, antwort, pfad="/kameras/"):
        return _mw(antwort)(self.rf.get(pfad))

    def test_fremde_seite_bekommt_die_module(self):
        u"""DER gemeldete Fall: eine Seite ganz ohne djangoBase-Vorlagen."""
        antwort = self._durch(HttpResponse(FREMDE_SEITE))
        text = antwort.content.decode()
        for modul in ("aufzeichner.js", "aufzeichner_leiste.js",
                      "aufzeichner_abspieler.js", "css/aufzeichner.css"):
            self.assertIn(modul, text,
                          u"Auf /kameras/ fehlt %r — genau der gemeldete "
                          u"Befund" % modul)

    def test_wird_vor_body_ende_eingehaengt(self):
        u"""Sonst stünde es hinter dem schließenden Tag - Browser verzeihen das,
        aber ein Modul-Script gehört in den Body."""
        antwort = self._durch(HttpResponse(FREMDE_SEITE))
        text = antwort.content.decode()
        self.assertLess(text.index("aufzeichner_leiste.js"), text.index("</body>"))

    def test_content_length_wird_nachgezogen(self):
        u"""Ein zu kurzes Content-Length schneidet die Seite im Browser ab."""
        roh = HttpResponse(FREMDE_SEITE)
        roh["Content-Length"] = str(len(FREMDE_SEITE))
        antwort = self._durch(roh)
        self.assertEqual(int(antwort["Content-Length"]), len(antwort.content))

    def test_json_bleibt_unberuehrt(self):
        antwort = self._durch(JsonResponse({"ok": True}))
        self.assertEqual(antwort.content, b'{"ok": true}')

    def test_fragment_ohne_body_bleibt_unberuehrt(self):
        u"""Ein nachgeladenes Schnipsel hat kein </body> - dort würde die
        Einbettung mitten im Inhalt landen."""
        roh = HttpResponse(b"<tr><td>Zeile</td></tr>")
        self.assertEqual(self._durch(roh).content, b"<tr><td>Zeile</td></tr>")

    def test_weiterleitung_und_fehler_bleiben_unberuehrt(self):
        for code in (302, 404, 500):
            antwort = self._durch(HttpResponse(FREMDE_SEITE, status=code))
            self.assertNotIn(b"aufzeichner_leiste.js", antwort.content,
                             u"Status %d darf nicht angefasst werden" % code)

    def test_keine_doppelte_einbindung(self):
        u"""Bringt eine Vorlage die Module schon mit, hält sich die Middleware
        zurück - zwei Instanzen desselben Moduls zeichnen jeden Klick doppelt
        auf (belegt am selben Tag)."""
        roh = HttpResponse(b'<html><body><script src="/static/djangobase/js/'
                           b'aufzeichner_leiste.js?v=1"></script></body></html>')
        antwort = self._durch(roh)
        self.assertEqual(antwort.content.count(b"aufzeichner_leiste.js"), 1)

    def test_eigener_endpunkt_ausgenommen(self):
        u"""Der Steuer-Endpunkt liefert JSON, aber sicher ist sicher.

        Der Pfad wird ueber `Basiswurzel` gebildet, nicht fest geschrieben:
        Er haengt vom Praefix ab, unter dem das Projekt `djangobase.urls`
        einbindet (3DTools: `/help/`, sonst meist `/hilfe/`). Mit der festen
        Adresse griff der Ausschluss dort ins Leere, und die Aufzeichnung
        schrieb ihre eigene Abfrage mit (Befund 27.08.2026)."""
        from djangobase.basiswurzel import Basiswurzel
        antwort = self._durch(HttpResponse(FREMDE_SEITE),
                              pfad=Basiswurzel.weg() + "tests/aufzeichnung/")
        self.assertNotIn(b"aufzeichner_leiste.js", antwort.content)

    @override_settings(DJANGOBASE_AUFZEICHNUNG=False)
    def test_abschaltbar(self):
        antwort = self._durch(HttpResponse(FREMDE_SEITE))
        self.assertNotIn(b"aufzeichner_leiste.js", antwort.content)

    @override_settings(DJANGOBASE_AUFZEICHNUNG_AUS=["/kameras/"])
    def test_pfade_ausnehmbar(self):
        antwort = self._durch(HttpResponse(FREMDE_SEITE))
        self.assertNotIn(b"aufzeichner_leiste.js", antwort.content)
        # Andere Pfade weiterhin ja.
        andere = self._durch(HttpResponse(FREMDE_SEITE), pfad="/live/kalender/")
        self.assertIn(b"aufzeichner_leiste.js", andere.content)

    def test_kaputte_einbettung_laesst_die_seite_heil(self):
        u"""Die Aufzeichnung ist ein Werkzeug, kein Bestandteil der Anwendung -
        sie darf eine Seite unter keinen Umständen zerstören."""
        mw = _mw(HttpResponse(FREMDE_SEITE))
        mw.schnipsel = lambda: (_ for _ in ()).throw(RuntimeError("kaputt"))
        antwort = mw(self.rf.get("/kameras/"))
        self.assertEqual(antwort.status_code, 200)
        self.assertIn(b"<h1>Kameras</h1>", antwort.content)


class SelbsteintragTest(SimpleTestCase):
    u"""Die Middleware trägt sich selbst in MIDDLEWARE ein.

    Würde sie nur dokumentiert, müsste jedes der Projekte sie eintragen — und
    hätte bis dahin genau das gemeldete Problem."""

    def test_steht_in_der_kette(self):
        from django.conf import settings
        from djangobase.apps import AUFZEICHNUNG_MIDDLEWARE
        self.assertIn(AUFZEICHNUNG_MIDDLEWARE, list(settings.MIDDLEWARE),
                      u"djangobase.apps.ready() muss die Middleware nachtragen")

    def test_steht_hinter_allen_fremden(self):
        u"""Sie schreibt in den fertigen Antwort-Inhalt. Weiter vorn käme sie an
        Antworten, die spätere Middleware noch ersetzt (GZip etwa).

        NICHT „ganz am Ende" (Korrektur 21.08.2026): Seit die
        Cache-Header-Middleware dazukam, steht eine zweite djangoBase-Middleware
        dahinter — die setzt nur Header und ersetzt nichts. Verlangt ist, dass
        keine FREMDE Middleware nach ihr kommt; alles andere wäre eine Regel
        über die Reihenfolge zweier eigener Bausteine, die niemandem hilft."""
        from django.conf import settings
        from djangobase.apps import AUFZEICHNUNG_MIDDLEWARE
        kette = list(settings.MIDDLEWARE)
        i = kette.index(AUFZEICHNUNG_MIDDLEWARE)
        danach = [m for m in kette[i + 1:] if not m.startswith("djangobase.")]
        self.assertFalse(danach,
                         u"Nach der Aufzeichnungs-Middleware stehen fremde "
                         u"Middlewares: %s. Sie könnten die Antwort ersetzen, "
                         u"nachdem die Module eingehängt wurden." % danach)
