# -*- coding: utf-8 -*-
u"""Sind die Hilfe-Seiten da, gefüllt und unter den richtigen Adressen?

DER AUFTRAG (Edgar, 21.08.2026): „mach alle"
============================================
Zwei der vorgeschlagenen Prüfungen:

    * Hilfe → Logs und Hilfe → Tests erreichbar UND gefüllt
    * deutsche Hilfe-URLs (/hilfe/versionen/, nicht /versions/)

WARUM „GEFÜLLT" DER EIGENTLICHE PUNKT IST
=========================================
Beide Seiten liefert djangoBase fertig — sie sind IMMER erreichbar, auch wenn
das Projekt nichts konfiguriert hat. Dann zeigen sie eine leere Tabelle, und
genau das sieht man ihnen nicht an: Wer unter Hilfe → Logs nachsieht, ob eine
Ausnahme fiel, und eine leere Seite bekommt, schließt daraus „keine Fehler" —
und liegt falsch, weil ``log_sources`` nie gesetzt wurde.

Dasselbe bei Hilfe → Tests: ohne ``test_befehle`` gibt es dort keine Suite zum
Starten, und die Projektkonvention „Test-Suite aus dem UI startbar" ist still
nicht erfüllt.

DIE ADRESSEN
============
djangoBase führt seine Seiten unter deutschen Slugs. Wer sie im eigenen Projekt
unter ``/versions/`` einhängt, hat zwei Adressen für dieselbe Seite — Lesezeichen
und Verweise in der Doku zeigen dann auf die eine, das Menü auf die andere.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

User = get_user_model()

#: Die Pflicht-Seiten und ihr deutscher Slug.
SEITEN = (("versionen", "/hilfe/versionen/"),
          ("logs", "/hilfe/logs/"),
          ("tests", "/hilfe/tests/"))


class HilfeSeitenTest(TestCase):
    u"""Erreichbar — und mit Inhalt."""

    @classmethod
    def setUpTestData(cls):
        cls.nutzer = User.objects.create_user(
            username="konform_hilfe", password="pw-konform-12345",
            is_staff=True, is_superuser=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.nutzer)

    def holen(self, name, pfad):
        try:
            adresse = reverse("djangobase:%s" % name)
        except NoReverseMatch:
            adresse = pfad
        return self.client.get(adresse, follow=True), adresse

    def test_alle_pflichtseiten_antworten(self):
        for name, pfad in SEITEN:
            with self.subTest(seite=name):
                antwort, adresse = self.holen(name, pfad)
                self.assertEqual(antwort.status_code, 200,
                                 u"%s liefert HTTP %d. djangoBase bringt die "
                                 u"Seite mit; ist djangobase.urls unter /hilfe/ "
                                 u"eingehängt?" % (adresse, antwort.status_code))

    def test_logs_seite_hat_quellen(self):
        u"""Ohne ``log_sources`` ist die Seite leer — und eine leere Logseite
        liest sich wie „keine Fehler"."""
        quellen = (getattr(settings, "DJANGOBASE", {}) or {}).get("log_sources")
        anbieter = (getattr(settings, "DJANGOBASE", {}) or {}).get("log_source_provider")
        self.assertTrue(quellen or anbieter,
                        u"Weder DJANGOBASE['log_sources'] noch "
                        u"['log_source_provider'] gesetzt. Hilfe → Logs zeigt "
                        u"dann dauerhaft nichts an, ohne das zu sagen.")

    def test_logs_seite_zeigt_beide_tabs(self):
        u"""Die Konvention nennt zwei: „Exceptions" und „Allgemein"."""
        antwort, adresse = self.holen("logs", "/hilfe/logs/")
        if antwort.status_code != 200:
            self.skipTest("%s nicht erreichbar" % adresse)
        html = antwort.content.decode("utf-8", "replace").lower()
        fehlend = [w for w in ("error", "django") if w not in html]
        self.assertFalse(fehlend,
                         u"Auf der Logs-Seite fehlt der Verweis auf %s. Erwartet "
                         u"werden die beiden Quellen django.log (Allgemein) und "
                         u"error.log (Exceptions)." % ", ".join(fehlend))

    def test_tests_seite_hat_befehle(self):
        u"""Ohne ``test_befehle`` gibt es im UI nichts zu starten — die
        Projektkonvention „Suite aus dem UI startbar" ist dann still unerfüllt."""
        befehle = (getattr(settings, "DJANGOBASE", {}) or {}).get("test_befehle")
        self.assertTrue(befehle,
                        u"DJANGOBASE['test_befehle'] ist leer. Hilfe → Tests "
                        u"zeigt dann keinen Startknopf für eine Suite.")

    def test_tests_seite_zeigt_ihre_reiter(self):
        antwort, adresse = self.holen("tests", "/hilfe/tests/")
        if antwort.status_code != 200:
            self.skipTest("%s nicht erreichbar" % adresse)
        html = antwort.content.decode("utf-8", "replace")
        self.assertIn("tab=", html,
                      u"Keine Reiter auf der Tests-Seite gefunden — sie wird "
                      u"vermutlich nicht von djangoBase gerendert.")


class DeutscheAdressenTest(TestCase):
    u"""Die Slugs sind Teil der Schnittstelle."""

    def test_deutsche_slugs_aufloesbar(self):
        for name, pfad in SEITEN:
            with self.subTest(seite=name):
                try:
                    adresse = reverse("djangobase:%s" % name)
                except NoReverseMatch:
                    self.fail(u"URL-Name „djangobase:%s“ ist nicht auflösbar. "
                              u"Ist djangobase.urls mit namespace='djangobase' "
                              u"eingehängt?" % name)
                self.assertEqual(adresse, pfad,
                                 u"„%s“ liegt unter %s statt unter %s. djangoBase "
                                 u"führt seine Seiten unter deutschen Slugs; zwei "
                                 u"Adressen für dieselbe Seite lassen Lesezeichen "
                                 u"und Doku auseinanderlaufen."
                                 % (name, adresse, pfad))

    def test_keine_englischen_dubletten(self):
        u"""``/versions/`` neben ``/versionen/`` wäre genau die Dublette, die
        der Slug vermeiden soll."""
        client = Client()
        for englisch in ("/hilfe/versions/", "/hilfe/settings/"):
            with self.subTest(pfad=englisch):
                self.assertEqual(client.get(englisch).status_code, 404,
                                 u"%s antwortet — eine englische Dublette der "
                                 u"deutschen Adresse." % englisch)


class GegenprobeTest(TestCase):
    u"""Prüfen die Regeln oben überhaupt etwas?"""

    def test_namensraum_existiert(self):
        u"""Ohne Namensraum fällt jeder ``reverse`` auf den festen Pfad zurück,
        und die Adressprüfung wäre eine Prüfung gegen sich selbst."""
        try:
            reverse("djangobase:versionen")
        except NoReverseMatch:
            self.fail(u"djangobase-URLs sind nicht mit namespace eingehängt — "
                      u"dann prüft test_deutsche_slugs_aufloesbar nichts.")

    def test_erfundene_seite_gibt_404(self):
        u"""Antwortet ALLES mit 200 (Catch-all-Route), wäre
        test_keine_englischen_dubletten wertlos."""
        self.assertEqual(Client().get("/hilfe/gibt-es-nicht-xyz/").status_code, 404)
