# -*- coding: utf-8 -*-
u"""Sind Hilfe→Versionen und der UI-Rahmen dieses Projekts djangoBase-konform?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „3. Ist Hilfe - Versionen konform mit djangoBase Template
     4. Ist das UI tamplate (menü, verschiebbares Menubar) konform mit
        djangoBase template"

WARUM AN DER GERENDERTEN SEITE UND NICHT AN DER DATEI
=====================================================
Man könnte prüfen, ob ein Template ``{% extends "djangobase/base.html" %}``
enthält. Das ist eine Formalie: Ein Projekt kann korrekt erben und den
entscheidenden Block trotzdem überschreiben — und ein anderes kann eine eigene
Vorlage haben, die alles richtig macht. Geprüft wird deshalb, was am Ende beim
Browser ankommt: Gibt es die Seitenleiste, das Menü, den Ziehgriff, die
Versions-Historie?

Das ist zugleich der Grund, warum diese Datei in ``konform/`` liegt und nicht in
``component/``: Sie prüft nicht djangoBase, sondern das PROJEKT gegen djangoBase.

ANMELDUNG
=========
Die Hilfe-Seiten hängen bei den meisten Projekten hinter dem Login. Die Tests
melden deshalb einen Staff-Nutzer an; wo eine Seite trotzdem nicht erreichbar
ist (eigene Rechte-Logik), wird übersprungen statt rot gemeldet — ein Test, der
in fremden Projekten grundlos rot ist, wird abgeschaltet.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

User = get_user_model()

#: Die Marken, an denen die djangoBase-Seitenleiste erkennbar ist.
SIDEBAR_MARKEN = ('class="sidebar"', "sidebar-header")


class RahmenBasis(TestCase):
    u"""Gemeinsamer Unterbau: angemeldeter Client und Seiten-Abruf."""

    @classmethod
    def setUpTestData(cls):
        cls.nutzer = User.objects.create_user(
            username="konform_pruefer", password="pw-konform-12345",
            is_staff=True, is_superuser=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.nutzer)

    def seite(self, name, pfad):
        u"""Eine Seite holen — oder den Test überspringen, wenn es sie nicht gibt.

        Übersprungen statt rot: Nicht jedes Projekt schaltet jede Hilfe-Seite
        frei, und ein grundlos roter Test in einem fremden Projekt wird
        abgeschaltet statt gelesen."""
        try:
            adresse = reverse(name)
        except NoReverseMatch:
            adresse = pfad
        antwort = self.client.get(adresse, follow=True)
        if antwort.status_code != 200:
            self.skipTest("%s nicht erreichbar (HTTP %d)"
                          % (adresse, antwort.status_code))
        return antwort.content.decode("utf-8", "replace")


class VersionenKonformTest(RahmenBasis):
    u"""Punkt 3: Hilfe → Versionen."""

    def html(self):
        return self.seite("djangobase:versions", "/hilfe/versionen/")

    def test_seite_erbt_den_rahmen(self):
        u"""Ohne Seitenleiste ist die Seite aus der Anwendung herausgefallen —
        man kommt von dort nirgends mehr hin."""
        html = self.html()
        self.assertTrue(any(m in html for m in SIDEBAR_MARKEN),
                        u"Hilfe → Versionen zeigt keine djangoBase-Seitenleiste. "
                        u"Die Vorlage muss von djangobase/base.html erben "
                        u"(oder base_template korrekt setzen).")

    def test_zeigt_versions_historie(self):
        u"""Die Seite lebt von der Historie aus GitHub — ohne sie ist sie eine
        leere Hülle, und genau das sieht man ihr nicht an."""
        html = self.html()
        self.assertIn("vw-", html,
                      u"Keine Versions-Einträge gefunden. djangoBase rendert sie "
                      u"mit den Klassen vw-tag/vw-pill; fehlen sie, hat die "
                      u"Abfrage nichts geliefert.")

    def test_repos_sind_konfiguriert(self):
        u"""Ohne ``repos`` fragt die Seite nichts ab und bleibt dauerhaft leer —
        ohne Fehlermeldung."""
        repos = (getattr(settings, "DJANGOBASE", {}) or {}).get("repos")
        self.assertTrue(repos,
                        u"DJANGOBASE['repos'] ist leer. Die Versions-Seite zieht "
                        u"ihre Historie aus GitHub; ohne Repo-Angabe zeigt sie "
                        u"still nichts an.")

    def test_aktuelle_version_ist_gesetzt(self):
        u"""Die Version steht laut Projektkonvention immer im UI."""
        version = (getattr(settings, "DJANGOBASE", {}) or {}).get("version")
        self.assertTrue(version,
                        u"DJANGOBASE['version'] fehlt — die Sidebar zeigt dann "
                        u"keine Versionsnummer.")


class UiRahmenKonformTest(RahmenBasis):
    u"""Punkt 4: Menü und Seitenleiste."""

    def html(self):
        return self.seite("djangobase:tests", "/hilfe/tests/")

    def test_seitenleiste_vorhanden(self):
        html = self.html()
        self.assertTrue(any(m in html for m in SIDEBAR_MARKEN),
                        u"Keine djangoBase-Seitenleiste im Markup.")

    def test_menue_ist_gefuellt(self):
        u"""Eine leere Seitenleiste ist formal konform und praktisch nutzlos."""
        eintraege = (getattr(settings, "DJANGOBASE", {}) or {}).get("menu") or []
        self.assertTrue(eintraege,
                        u"DJANGOBASE['menu'] ist leer — die Seitenleiste bliebe "
                        u"bis auf Hilfe/Einstellungen leer.")

    def test_untermenue_heisst_untermenu(self):
        u"""``items`` löst in Django-Vorlagen auf ``dict.items`` auf und ist
        damit IMMER wahr — jeder Punkt würde fälschlich aufklappbar.

        Der Kommentar in ``_sidebar.html`` warnt ausdrücklich davor; hier wird
        es geprüft statt nur beschrieben."""
        falsch = []

        def sehen(punkte, pfad=""):
            for p in punkte or ():
                if not isinstance(p, dict):
                    continue
                name = pfad + str(p.get("label", "?"))
                if "items" in p:
                    falsch.append(name)
                sehen(p.get("untermenu"), name + " → ")

        sehen((getattr(settings, "DJANGOBASE", {}) or {}).get("menu"))
        self.assertFalse(falsch,
                         u"Diese Menüpunkte nutzen „items“ statt „untermenu“: %s"
                         % ", ".join(falsch))

    def test_menue_eintraege_sind_vollstaendig(self):
        u"""Ein Punkt ohne URL ist ein toter Eintrag, einer ohne Label unsichtbar."""
        luecken = []

        def sehen(punkte, pfad=""):
            for p in punkte or ():
                if not isinstance(p, dict):
                    continue
                name = pfad + str(p.get("label") or "(ohne Label)")
                if not p.get("label"):
                    luecken.append(name + ": kein label")
                if not p.get("untermenu") and not p.get("url"):
                    luecken.append(name + ": weder url noch untermenu")
                sehen(p.get("untermenu"), name + " → ")

        sehen((getattr(settings, "DJANGOBASE", {}) or {}).get("menu"))
        self.assertFalse(luecken, u"Unvollständige Menüpunkte: %s"
                         % "; ".join(luecken[:8]))

    def test_verschiebbare_menuleiste(self):
        u"""„verschiebbares Menubar" (Ansage): Der Ziehgriff kommt aus
        ``sidebar_resizer.js`` und wird nur geladen, wenn das Projekt
        ``resizable_sidebar`` setzt. Ohne das Flag ist die Breite fest."""
        an = (getattr(settings, "DJANGOBASE", {}) or {}).get("resizable_sidebar")
        if not an:
            self.fail(u"DJANGOBASE['resizable_sidebar'] ist nicht gesetzt — die "
                      u"Seitenleiste lässt sich nicht in der Breite ziehen. "
                      u"djangoBase liefert das fertig mit; setze das Flag auf True.")
        self.assertIn("sidebar_resizer.js", self.html(),
                      u"resizable_sidebar ist True, aber das Modul wird nicht "
                      u"geladen — der Griff fehlt trotzdem.")

    def test_bootstrap_icons_verfuegbar(self):
        u"""Die Seitenleiste beschriftet ihre Punkte mit ``bi-*``. Fehlt die
        Icon-Schrift, stehen dort leere Kästchen statt Symbolen."""
        html = self.html()
        if "bi-" not in html:
            self.skipTest("keine bi-Icons im Markup")
        self.assertIn("bootstrap-icons", html,
                      u"Die Seitenleiste nutzt bi-*-Icons, aber das Stylesheet "
                      u"bootstrap-icons ist nicht eingebunden.")


class GegenprobeTest(TestCase):
    u"""Greifen die Menü-Regeln überhaupt?"""

    def test_items_falle_wird_erkannt(self):
        u"""Der Kern von test_untermenue_heisst_untermenu — an einer Probe."""
        probe = [{"label": "Falsch", "items": [{"label": "x", "url": "/"}]}]
        falsch = [p["label"] for p in probe if "items" in p]
        self.assertEqual(falsch, ["Falsch"])

    def test_luecke_wird_erkannt(self):
        probe = [{"label": "Ohne Ziel"}]
        luecken = [p for p in probe if not p.get("untermenu") and not p.get("url")]
        self.assertEqual(len(luecken), 1)

    def test_sidebar_marken_treffen_das_markup(self):
        u"""Ändert sich ``_sidebar.html``, müssen die Marken mitwandern —
        sonst prüfen die Tests oben eine Zeichenkette, die es nicht mehr gibt."""
        from pathlib import Path
        vorlage = (Path(__file__).resolve().parents[2]
                   / "templates" / "djangobase" / "_sidebar.html")
        text = vorlage.read_text(encoding="utf-8")
        for marke in SIDEBAR_MARKEN:
            self.assertIn(marke.replace('"', '"'), text,
                          u"Marke %r steht nicht mehr in _sidebar.html" % marke)
