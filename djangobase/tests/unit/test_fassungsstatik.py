# -*- coding: utf-8 -*-
"""Statik unter einer Adresse, die die Fassung trägt.

WARUM ES DAS GIBT (05.09.2026)
==============================
ES-Module lösen `import … from './x.js'` gegen die Adresse des importierenden
Moduls auf — eine Fassungskennung in der ABFRAGE wird dabei nicht vererbt.
Die Einstiegsdatei kam also frisch, die Geschwister aus dem Zwischenspeicher.
Zweimal an einem Tag gesehen: einmal als leere Seite

    SyntaxError: The requested module './skinning.js' does not provide an
    export named 'skelettNachfuehren'

und einmal als stumm fehlende Funktion. Steht die Fassung im PFAD, erbt sie
sich über den ganzen Modulbaum.

DIE GEFÄHRLICHE HÄLFTE IST DIE AUSLIEFERUNG
===========================================
Der Pfad kommt aus der Adresszeile. `../../` darin ist kein Randfall,
sondern der erste Versuch — deshalb steht `WasNichtAusgeliefertWerdenDarf`
hier und nicht als Nachtrag.
"""

import os

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings

from djangobase.fassungsstatik import Fassungsstatik

from ..wegwerfordner import Wegwerfordner


class MitEigenemStatikbaum(SimpleTestCase):
    """Ein eigener ``STATICFILES_DIRS``-Ordner mit ``viewer/viewer/index.js``.

    BIS ZUM 18.09.2026 hingen diese Pruefungen am WIRT: Sie erwarteten die
    Datei aus 3DTools und irgendeinen Statik-Ordner in dessen Einstellungen.
    Im Pruef-Wirt von djangoBase gab es beides nicht — neun rote Faelle,
    die nichts ueber den Code sagten. Jetzt bringt jeder Fall seinen Baum
    mit; ``vergessen()`` sorgt dafuer, dass die gemerkte Fassung des
    vorigen Falls nicht weiterlebt.
    """

    databases = []
    DATEI = "viewer/viewer/index.js"

    def setUp(self):
        self.ordner = Wegwerfordner.neu("statik_")
        datei = self.ordner / self.DATEI
        datei.parent.mkdir(parents=True)
        datei.write_text("export const x = 1;\n", encoding="utf-8")
        self._einstellungen = override_settings(STATICFILES_DIRS=[str(self.ordner)])
        self._einstellungen.enable()
        self.addCleanup(self._einstellungen.disable)
        Fassungsstatik.vergessen()
        self.addCleanup(Fassungsstatik.vergessen)


class DieFassungIstEineDateizeit(MitEigenemStatikbaum):
    def test_sie_ist_eine_zahl_groesser_null(self):
        """Null hiesse „kein Statik-Ordner gefunden" — dann wäre jede
        Adresse gleich und der ganze Aufwand umsonst."""
        self.assertGreater(Fassungsstatik.fassung(), 0)

    def test_zweimal_fragen_kostet_keinen_zweiten_durchlauf(self):
        """Ein Durchlauf über den Baum kostet gemessene 17 ms — je
        Seitenaufruf wäre das die teuerste Zeile der Vorlage."""
        Fassungsstatik.fassung()
        geprueft = Fassungsstatik._geprueft
        Fassungsstatik.fassung()
        self.assertEqual(Fassungsstatik._geprueft, geprueft)

    def test_sie_steckt_im_pfad_nicht_in_der_abfrage(self):
        """DER GANZE PUNKT: Ein relativer Import erbt den Pfad, die Abfrage
        nicht."""
        pfad = Fassungsstatik.pfad("viewer/viewer/index.js")
        self.assertNotIn("?", pfad)
        self.assertTrue(pfad.startswith("/statik/v-"), pfad)
        self.assertTrue(pfad.endswith("/viewer/viewer/index.js"), pfad)

    def test_ein_fuehrender_schraegstrich_stoert_nicht(self):
        self.assertEqual(Fassungsstatik.pfad("/viewer/x.js"), Fassungsstatik.pfad("viewer/x.js"))


class WasAusgeliefertWird(MitEigenemStatikbaum):
    def setUp(self):
        super().setUp()
        self.anfrage = RequestFactory().get("/statik/v-1/viewer/viewer/index.js")

    def test_eine_vorhandene_datei_kommt(self):
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1, "viewer/viewer/index.js")
        self.assertEqual(antwort.status_code, 200)
        antwort.close()

    def test_mit_einem_jahr_und_immutable(self):
        """Die Adresse trägt die Fassung — ändert sich die Datei, ändert
        sich die Adresse. Dann darf die alte ewig liegen bleiben."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1, "viewer/viewer/index.js")
        steuerung = antwort["Cache-Control"]
        antwort.close()
        self.assertIn("immutable", steuerung)
        self.assertIn("max-age=", steuerung)

    def test_und_mit_dem_richtigen_typ(self):
        """Ohne `text/javascript` weist der Browser das Modul ab —
        „Failed to load module script: … MIME type of text/plain"."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1, "viewer/viewer/index.js")
        typ = antwort["Content-Type"]
        antwort.close()
        self.assertIn("javascript", typ)

    def test_eine_alte_fassung_wird_trotzdem_bedient(self):
        """Eine Seite, die VOR einer Änderung geladen wurde, holt ihre
        restlichen Module unter der alten Zahl nach. Wer hier auf Gleichheit
        prüft, bricht genau diese Seite mitten im Laden ab."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1, "viewer/viewer/index.js")
        self.assertEqual(antwort.status_code, 200)
        antwort.close()
        self.assertNotEqual(1, Fassungsstatik.fassung())


class WasNichtAusgeliefertWerdenDarf(MitEigenemStatikbaum):
    """Der Pfad kommt aus der Adresszeile — hier wird scharf geprüft."""

    def setUp(self):
        super().setUp()
        self.anfrage = RequestFactory().get("/statik/v-1/x")

    def _wirft(self, pfad):
        with self.assertRaises(Http404, msg="%r wurde ausgeliefert!" % pfad):
            Fassungsstatik.ausliefern(self.anfrage, 1, pfad)

    def test_ein_ausbruch_nach_oben(self):
        self._wirft("../../../../etc/passwd")

    def test_ein_ausbruch_in_der_mitte(self):
        """`normpath` VOR der Prüfung: Sonst sieht das hier harmlos aus."""
        self._wirft("viewer/../../../ui/settings/__init__.py")

    def test_ein_rueckwaertsschraegstrich_auch_nicht(self):
        """Windows-Pfadtrenner — sonst geht der Ausbruch unter Windows
        durch, während der Test unter Linux grün bleibt."""
        self._wirft("..\\..\\ui\\settings\\__init__.py")

    def test_eine_datei_die_es_nicht_gibt(self):
        self._wirft("viewer/gibtesnicht.js")

    def test_ein_leerer_pfad(self):
        self._wirft("")

    def test_ein_ordner_ist_keine_datei(self):
        self._wirft("viewer")


class DieAdresseLiegtNichtUnterStaticUrl(SimpleTestCase):
    """Sonst fängt der Statik-Handler von `runserver` sie ab, bevor die
    URL-Zuordnung sie überhaupt sieht — und alles endet in einer 404."""

    def test_das_praefix_ist_ein_anderes(self):
        from django.conf import settings

        statik = getattr(settings, "STATIC_URL", "/static/") or "/static/"
        self.assertFalse(
            Fassungsstatik.pfad("x.js").startswith(statik),
            "%s liegt unter STATIC_URL — der Statik-Handler kommt zuerst." % Fassungsstatik.PRAEFIX,
        )


class DerBaumWirdWirklichAbgesucht(MitEigenemStatikbaum):
    def test_es_gibt_mindestens_einen_ordner(self):
        """Ohne Ordner wäre die Fassung immer 0 und die Prüfung oben
        grün, ohne etwas zu prüfen."""
        ordner = Fassungsstatik._ordner()
        self.assertIn(str(self.ordner), ordner)
        for o in ordner:
            self.assertTrue(os.path.isdir(o), o)

    def test_eine_neue_datei_aendert_die_fassung(self):
        """Die Gegenprobe: Die Zahl haengt wirklich an den Dateien."""
        vorher = Fassungsstatik.fassung()
        neu = self.ordner / "spaeter.js"
        neu.write_text("// spaeter\n", encoding="utf-8")
        os.utime(neu, (vorher + 100, vorher + 100))
        Fassungsstatik.vergessen()
        self.assertEqual(Fassungsstatik.fassung(), vorher + 100)
