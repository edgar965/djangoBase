# -*- coding: utf-8 -*-
u"""Gegenprobe fuer `djangobase.cachekonzept`: jede Regel muss an ihrem Vorfall rot werden
und an der richtigen Schreibweise gruen bleiben (06.09.2026)."""
from django.test import SimpleTestCase, override_settings

from djangobase.cachekonzept import Cachekonzept


class VorlagenTest(SimpleTestCase):

    databases = []

    def _regeln(self, text):
        return sorted(b["regel"] for b in Cachekonzept.vorlage("seite.html", text))

    def test_modul_einstieg_mit_zeitstempel_faellt_auf(self):
        text = u'<script type="module" src="{% static \'viewer/index.js\' %}?t={% now "U" %}"></script>'
        self.assertEqual(self._regeln(text), ["modul-ueber-fassungspfad"])

    def test_modul_einstieg_mit_kennung_faellt_auf_auch_bei_anderer_reihenfolge(self):
        text = u'<script src="{% static "js/a.js" %}?v=3" type="module"></script>'
        self.assertEqual(self._regeln(text), ["modul-ueber-fassungspfad"])

    def test_dynamischer_import_mit_zeitstempel_faellt_auf(self):
        text = u"const m = await import('{% static \"js/bvh_player.js\" %}?t={% now \"U\" %}');"
        self.assertEqual(self._regeln(text), ["modul-ueber-fassungspfad"])

    def test_zeitstempel_an_stil_und_skript_faellt_auf(self):
        text = (u'<link rel="stylesheet" href="{% static \'css/seite.css\' %}?t={% now \'U\' %}">\n'
                u'<script src="{% static \'js/seite.js\' %}?t={% now \'U\' %}"></script>')
        self.assertEqual(self._regeln(text), ["kein-zeitstempel-an-statik", "kein-zeitstempel-an-statik"])

    def test_fassungspfad_und_statik_v_sind_richtig(self):
        text = (u'{% load fassung %}\n'
                u'<script type="module" src="{% fassungspfad \'viewer/index.js\' %}"></script>\n'
                u"const m = await import('{% fassungspfad \"js/x.js\" %}');\n"
                u'<link rel="stylesheet" href="{% static \'css/seite.css\' %}?v={{ djangobase.statik_v }}">\n'
                u'<script src="{% static \'js/seite.js\' %}?v=7"></script>')
        self.assertEqual(self._regeln(text), [])

    def test_zeitstempel_an_daten_adressen_ist_erlaubt(self):
        text = u"bvhUrl: '{% url \"serve_bvh\" job.id %}?t={% now \"U\" %}',"
        self.assertEqual(self._regeln(text), [])

    def test_kommentare_zaehlen_nicht(self):
        text = (u'{% comment %}<script type="module" src="{% static \'a.js\' %}?t=1">{% endcomment %}\n'
                u'{# {% static \'b.css\' %}?t={% now "U" %} #}\n'
                u'<!-- <script src="{% static \'c.js\' %}?t={% now "U" %}"></script> -->')
        self.assertEqual(self._regeln(text), [])

    def test_ort_nennt_die_zeile(self):
        text = u'\n\n<script type="module" src="{% static \'a.js\' %}?t={% now "U" %}"></script>'
        self.assertEqual(Cachekonzept.vorlage("seite.html", text)[0]["ort"], "seite.html:3")


class SkriptTest(SimpleTestCase):

    databases = []

    def test_kennung_in_importen_faellt_auf(self):
        text = u"import { a } from './a.js?v=3';\nconst b = await import('./b.js?t=123');"
        befunde = Cachekonzept.skript("x.js", text)
        self.assertEqual([b["ort"] for b in befunde], ["x.js:1", "x.js:2"])

    def test_import_ohne_kennung_ist_richtig(self):
        text = u"import { a } from './a.js';\nimport * as THREE from 'three';\nconst b = await import('./b.js');"
        self.assertEqual(Cachekonzept.skript("x.js", text), [])


class EinstellungenTest(SimpleTestCase):

    databases = []

    @override_settings(MIDDLEWARE=["x.NoCacheMiddleware"])
    def test_fehlende_und_pauschale_middleware_fallen_auf(self):
        regeln = sorted(b["regel"] for b in Cachekonzept.einstellungen()
                        if b["regel"] in ("html-no-store", "keine-nocache-middleware"))
        self.assertEqual(regeln, ["html-no-store", "keine-nocache-middleware"])

    def test_regeln_haben_titel_warum_und_wie(self):
        for regel in Cachekonzept.REGELN:
            self.assertTrue(regel.titel and regel.warum and regel.wie, regel.kennung)
        self.assertIsNone(Cachekonzept.regel("gibt-es-nicht"))
