# -*- coding: utf-8 -*-
u"""Statik unter einer Adresse, die die Fassung trägt.

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
from django.test import RequestFactory, SimpleTestCase

from djangobase.fassungsstatik import Fassungsstatik


class DieFassungIstEineDateizeit(SimpleTestCase):

    def test_sie_ist_eine_zahl_groesser_null(self):
        u"""Null hiesse „kein Statik-Ordner gefunden" — dann wäre jede
        Adresse gleich und der ganze Aufwand umsonst."""
        self.assertGreater(Fassungsstatik.fassung(), 0)

    def test_zweimal_fragen_kostet_keinen_zweiten_durchlauf(self):
        u"""Ein Durchlauf über den Baum kostet gemessene 17 ms — je
        Seitenaufruf wäre das die teuerste Zeile der Vorlage."""
        Fassungsstatik.fassung()
        geprueft = Fassungsstatik._geprueft
        Fassungsstatik.fassung()
        self.assertEqual(Fassungsstatik._geprueft, geprueft)

    def test_sie_steckt_im_pfad_nicht_in_der_abfrage(self):
        u"""DER GANZE PUNKT: Ein relativer Import erbt den Pfad, die Abfrage
        nicht."""
        pfad = Fassungsstatik.pfad('viewer/viewer/index.js')
        self.assertNotIn('?', pfad)
        self.assertTrue(pfad.startswith('/statik/v-'), pfad)
        self.assertTrue(pfad.endswith('/viewer/viewer/index.js'), pfad)

    def test_ein_fuehrender_schraegstrich_stoert_nicht(self):
        self.assertEqual(Fassungsstatik.pfad('/viewer/x.js'),
                         Fassungsstatik.pfad('viewer/x.js'))


class WasAusgeliefertWird(SimpleTestCase):

    def setUp(self):
        self.anfrage = RequestFactory().get('/statik/v-1/viewer/viewer/index.js')

    def test_eine_vorhandene_datei_kommt(self):
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1,
                                            'viewer/viewer/index.js')
        self.assertEqual(antwort.status_code, 200)
        antwort.close()

    def test_mit_einem_jahr_und_immutable(self):
        u"""Die Adresse trägt die Fassung — ändert sich die Datei, ändert
        sich die Adresse. Dann darf die alte ewig liegen bleiben."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1,
                                            'viewer/viewer/index.js')
        steuerung = antwort['Cache-Control']
        antwort.close()
        self.assertIn('immutable', steuerung)
        self.assertIn('max-age=', steuerung)

    def test_und_mit_dem_richtigen_typ(self):
        u"""Ohne `text/javascript` weist der Browser das Modul ab —
        „Failed to load module script: … MIME type of text/plain"."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1,
                                            'viewer/viewer/index.js')
        typ = antwort['Content-Type']
        antwort.close()
        self.assertIn('javascript', typ)

    def test_eine_alte_fassung_wird_trotzdem_bedient(self):
        u"""Eine Seite, die VOR einer Änderung geladen wurde, holt ihre
        restlichen Module unter der alten Zahl nach. Wer hier auf Gleichheit
        prüft, bricht genau diese Seite mitten im Laden ab."""
        antwort = Fassungsstatik.ausliefern(self.anfrage, 1,
                                            'viewer/viewer/index.js')
        self.assertEqual(antwort.status_code, 200)
        antwort.close()
        self.assertNotEqual(1, Fassungsstatik.fassung())


class WasNichtAusgeliefertWerdenDarf(SimpleTestCase):
    u"""Der Pfad kommt aus der Adresszeile — hier wird scharf geprüft."""

    def setUp(self):
        self.anfrage = RequestFactory().get('/statik/v-1/x')

    def _wirft(self, pfad):
        with self.assertRaises(Http404, msg=u'%r wurde ausgeliefert!' % pfad):
            Fassungsstatik.ausliefern(self.anfrage, 1, pfad)

    def test_ein_ausbruch_nach_oben(self):
        self._wirft('../../../../etc/passwd')

    def test_ein_ausbruch_in_der_mitte(self):
        u"""`normpath` VOR der Prüfung: Sonst sieht das hier harmlos aus."""
        self._wirft('viewer/../../../ui/settings/__init__.py')

    def test_ein_rueckwaertsschraegstrich_auch_nicht(self):
        u"""Windows-Pfadtrenner — sonst geht der Ausbruch unter Windows
        durch, während der Test unter Linux grün bleibt."""
        self._wirft('..\\..\\ui\\settings\\__init__.py')

    def test_eine_datei_die_es_nicht_gibt(self):
        self._wirft('viewer/gibtesnicht.js')

    def test_ein_leerer_pfad(self):
        self._wirft('')

    def test_ein_ordner_ist_keine_datei(self):
        self._wirft('viewer')


class DieAdresseLiegtNichtUnterStaticUrl(SimpleTestCase):
    u"""Sonst fängt der Statik-Handler von `runserver` sie ab, bevor die
    URL-Zuordnung sie überhaupt sieht — und alles endet in einer 404."""

    def test_das_praefix_ist_ein_anderes(self):
        from django.conf import settings
        statik = (getattr(settings, 'STATIC_URL', '/static/') or '/static/')
        self.assertFalse(
            Fassungsstatik.pfad('x.js').startswith(statik),
            u'%s liegt unter STATIC_URL — der Statik-Handler kommt zuerst.'
            % Fassungsstatik.PRAEFIX)


class DerBaumWirdWirklichAbgesucht(SimpleTestCase):

    def test_es_gibt_mindestens_einen_ordner(self):
        u"""Ohne Ordner wäre die Fassung immer 0 und die Prüfung oben
        grün, ohne etwas zu prüfen."""
        ordner = Fassungsstatik._ordner()
        self.assertTrue(ordner)
        for o in ordner:
            self.assertTrue(os.path.isdir(o), o)
