# -*- coding: utf-8 -*-
u"""Sind die Hilfe-Seiten eingehängt, konfiguriert und unter deutschen Adressen?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „Hilfe → Logs und Hilfe → Tests erreichbar und gefüllt"
    „deutsche Hilfe-URLs (/hilfe/versionen/, nicht /versions/)"

    Nachtrag: „lösche alle testcases die eine test db brauchen, überleg dir was
    anderes!"

OHNE DATENBANK — UND WARUM DAS HIER SOGAR BESSER IST
====================================================
Die erste Fassung meldete einen Staff-Nutzer an und rief die Seiten mit dem
Test-Client ab. Das braucht eine Test-Datenbank: Django legt sie an, migriert
sie und wirft sie weg — Minuten für eine Frage, die keine Daten betrifft.

Geprüft wird deshalb ohne DB, und zwar an drei Stellen, die zusammen dasselbe
aussagen:

    1. Die Adresse löst auf (``reverse``) — die URLs sind eingehängt.
    2. Sie zeigt auf eine djangoBase-View (``resolve``) — es ist wirklich die
       gelieferte Seite und nicht eine gleichnamige eigene.
    3. Die Seite hat, womit sie sich füllt (``log_sources``, ``test_befehle``).

Punkt 3 ist der eigentliche Kern: Beide Seiten liefert djangoBase fertig, sie
antworten also IMMER. Ohne Konfiguration zeigen sie eine leere Tabelle — und
eine leere Logseite liest sich wie „keine Fehler".
"""
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

#: Die Pflicht-Seiten und ihr deutscher Slug.
SEITEN = (("versionen", "/hilfe/versionen/"),
          ("logs", "/hilfe/logs/"),
          ("tests", "/hilfe/tests/"))


def _djangobase(*schluessel):
    d = getattr(settings, "DJANGOBASE", {}) or {}
    return [d.get(s) for s in schluessel]


class AdressenTest(SimpleTestCase):
    u"""Eingehängt, deutsch benannt, und auf djangoBase zeigend."""

    databases = []          # ausdrücklich keine: dieser Test fasst nie Daten an

    def test_alle_pflichtseiten_sind_eingehaengt(self):
        for name, pfad in SEITEN:
            with self.subTest(seite=name):
                try:
                    reverse("djangobase:%s" % name)
                except NoReverseMatch:
                    self.fail(u"„djangobase:%s“ löst nicht auf. Ist "
                              u"djangobase.urls unter /hilfe/ mit "
                              u"namespace='djangobase' eingehängt?" % name)

    def test_deutsche_slugs(self):
        u"""Zwei Adressen für dieselbe Seite lassen Lesezeichen und Doku
        auseinanderlaufen."""
        for name, pfad in SEITEN:
            with self.subTest(seite=name):
                try:
                    adresse = reverse("djangobase:%s" % name)
                except NoReverseMatch:
                    self.skipTest("nicht eingehängt - siehe Test darüber")
                self.assertEqual(adresse, pfad,
                                 u"„%s“ liegt unter %s statt unter %s."
                                 % (name, adresse, pfad))

    def test_adressen_zeigen_auf_djangobase(self):
        u"""``reverse`` sagt nur, dass ein Name existiert. Erst ``resolve``
        sagt, WER dahinter steht — eine eigene View unter demselben Namen wäre
        genau die stille Abweichung, um die es hier geht."""
        for name, pfad in SEITEN:
            with self.subTest(seite=name):
                try:
                    treffer = resolve(pfad)
                except Resolver404:
                    self.fail(u"%s ist nicht auflösbar." % pfad)
                modul = getattr(treffer.func, "__module__", "")
                eigen = getattr(getattr(treffer.func, "view_class", None),
                                "__module__", "")
                self.assertTrue("djangobase" in modul or "djangobase" in eigen,
                                u"%s wird von %r bedient, nicht von djangoBase."
                                % (pfad, modul or eigen))

    def test_keine_englischen_dubletten(self):
        u"""``/versions/`` neben ``/versionen/`` wäre die Dublette, die der
        deutsche Slug vermeiden soll."""
        for englisch in ("/hilfe/versions/", "/hilfe/settings/",
                         "/hilfe/logs-clear/"):
            with self.subTest(pfad=englisch):
                try:
                    treffer = resolve(englisch)
                except Resolver404:
                    continue                    # so soll es sein
                self.fail(u"%s ist auflösbar (%s) — eine englische Dublette."
                          % (englisch, getattr(treffer.func, "__name__", "?")))


class KonfigurationTest(SimpleTestCase):
    u"""„Gefüllt" — der Teil, den man der Seite nicht ansieht."""

    databases = []

    def test_logs_seite_hat_quellen(self):
        quellen, anbieter = _djangobase("log_sources", "log_source_provider")
        self.assertTrue(quellen or anbieter,
                        u"Weder DJANGOBASE['log_sources'] noch "
                        u"['log_source_provider'] gesetzt. Hilfe → Logs zeigt "
                        u"dann dauerhaft nichts an, ohne das zu sagen — und "
                        u"eine leere Logseite liest sich wie „keine Fehler“.")

    def test_logs_quellen_zeigen_auf_vorhandene_dateien(self):
        u"""Ein Eintrag auf eine Datei, die es nicht gibt, ergibt einen leeren
        Tab — ununterscheidbar von „keine Zeilen"."""
        from pathlib import Path
        quellen, anbieter = _djangobase("log_sources", "log_source_provider")
        if anbieter:
            self.skipTest("Quellen kommen dynamisch aus %r" % anbieter)
        if not quellen:
            self.skipTest("keine Quellen - siehe Test darüber")
        basis = Path(getattr(settings, "BASE_DIR", "."))
        fehlend = []
        for eintrag in quellen:
            # DREI SCHREIBWEISEN (Korrektur 21.08.2026): djangoBase nimmt
            # Tupel ``(slug, name, datei, ...)``, Dicts und blosse Pfade an.
            # Die erste Fassung dieser Pruefung nahm bei einem Tupel das GANZE
            # Tupel als Pfad und meldete es als „zeigt ins Leere" - ein
            # Fehlalarm auf eine voellig korrekte Konfiguration.
            if isinstance(eintrag, (list, tuple)):
                pfad = eintrag[2] if len(eintrag) > 2 else None
            elif isinstance(eintrag, dict):
                pfad = eintrag.get("path") or eintrag.get("datei")
            else:
                pfad = eintrag
            if not pfad:
                continue
            p = Path(str(pfad))
            if not p.is_absolute():
                p = basis / p
            if not p.exists() and not p.parent.exists():
                fehlend.append(str(pfad))
        self.assertFalse(fehlend,
                         u"Diese Log-Quellen zeigen ins Leere: %s"
                         % ", ".join(fehlend[:5]))

    @staticmethod
    def _befehle():
        u"""Was die Seite WIRKLICH anzeigt: Konfiguration oder Ableitung.

        DER PRUEFLING WAR UEBERHOLT (26.08.2026)
        ========================================
        Hier stand nur ``DJANGOBASE['test_befehle']``. Seit dem 17.08.2026
        („aktiviere das per default für alle in djangoBase!") leitet
        :meth:`TestsView._befehle_abgeleitet` die Liste aus dem
        Dateibestand ab, wenn ein Projekt keine pflegt — CamTrack bekommt
        so sechs Suiten, ohne einen Schluessel zu setzen.

        Die Pruefung meldete also „Hilfe → Tests zeigt keinen Startknopf"
        fuer eine Seite, die sechs davon zeigt. Sie fragt jetzt dieselbe
        Stelle wie die Ansicht.
        """
        (aus_konfig,) = _djangobase("test_befehle")
        if aus_konfig:
            return aus_konfig
        from djangobase.views.tests import TestsView
        return TestsView._befehle_abgeleitet()

    def test_tests_seite_hat_befehle(self):
        u"""Ohne Befehle gibt es im UI nichts zu starten — die
        Konvention „Suite aus dem UI startbar" ist dann still unerfüllt."""
        self.assertTrue(
            self._befehle(),
            u"Weder DJANGOBASE['test_befehle'] noch die Ableitung aus dem "
            u"Dateibestand liefern etwas. Hilfe → Tests zeigt dann keinen "
            u"Startknopf für eine Suite.")

    def test_testbefehle_sind_vollstaendig(self):
        u"""Ein Eintrag ohne ``cmd`` ist ein Knopf, der nichts tut."""
        befehle = self._befehle()
        self.assertTrue(befehle, u"keine Befehle - siehe Test darüber")
        luecken = []
        for b in befehle:
            if not isinstance(b, dict):
                luecken.append(repr(b)[:40])
                continue
            fehlt = [f for f in ("slug", "name", "cmd") if not b.get(f)]
            if fehlt:
                luecken.append("%s: ohne %s" % (b.get("slug") or b.get("name") or "?",
                                                ", ".join(fehlt)))
        self.assertFalse(luecken,
                         u"Unvollständige test_befehle: %s" % "; ".join(luecken[:5]))


class GegenprobeTest(SimpleTestCase):
    u"""Prüfen die Regeln überhaupt etwas?"""

    databases = []

    def test_erfundene_adresse_ist_nicht_aufloesbar(self):
        u"""Löste ALLES auf (Catch-all-Route), wäre die Dubletten-Prüfung
        wertlos."""
        with self.assertRaises(Resolver404):
            resolve("/hilfe/gibt-es-nicht-xyz/")

    def test_resolve_liefert_ein_modul(self):
        u"""Ohne ``__module__`` prüfte test_adressen_zeigen_auf_djangobase
        gegen eine leere Zeichenkette — und wäre immer grün."""
        treffer = resolve("/hilfe/versionen/")
        modul = getattr(treffer.func, "__module__", "")
        eigen = getattr(getattr(treffer.func, "view_class", None), "__module__", "")
        self.assertTrue(modul or eigen)
