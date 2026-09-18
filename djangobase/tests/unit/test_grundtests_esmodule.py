"""`GrundtestEsModule`: ein relativer Import über eine App-Grenze ist kein Loch.

DER ANLASS (19.09.2026, assistant)
==================================
``search/static/search/js/sys_stats_widget.js`` importiert seit dem 18.09.
``../../djangobase/js/system_stats.js`` — relativ, damit die Fassung aus dem
Pfad des Einstiegs (``/statik/v-<n>/…``) vererbt wird und das geteilte Modul
EIN Modul bleibt. Auf der Platte gibt es ``search/static/djangobase/`` nicht;
im Browser schon, weil der Static-Finder alle Apps unter ``/static/`` bzw.
``/statik/v-<n>/`` zusammenlegt. Der Grundtest rechnete nur mit der Platte
und meldete den Import als Loch.

Geprüft: ab dem ``static``-Ordner gerechnet, beantwortet der Finder die
Frage — genau wie die Auslieferung. Ein Import auf wirklich Fehlendes bleibt
ein Befund (Gegenprobe), ein Pfad, der aus ``static`` hinausführt, auch.
"""

from django.test import SimpleTestCase, override_settings

from djangobase.grundtests import _statisch_vorhanden

from ..wegwerfordner import Wegwerfordner


class UeberDieAppGrenze(SimpleTestCase):
    databases = []

    def setUp(self):
        self.ordner = Wegwerfordner.neu("esmodul_")
        widget = self.ordner / "app" / "static" / "app" / "js" / "widget.js"
        widget.parent.mkdir(parents=True)
        widget.write_text("import { K } from '../../geteilt/js/kern.js';\n", encoding="utf-8")
        self.widget = widget
        kern = self.ordner / "geteilt_static" / "geteilt" / "js" / "kern.js"
        kern.parent.mkdir(parents=True)
        kern.write_text("export const K = 1;\n", encoding="utf-8")
        einstellungen = override_settings(STATICFILES_DIRS=[str(self.ordner / "geteilt_static")])
        einstellungen.enable()
        self.addCleanup(einstellungen.disable)

    def test_der_finder_kennt_das_geteilte_modul(self):
        self.assertTrue(_statisch_vorhanden(self.widget, "../../geteilt/js/kern.js"))

    def test_was_es_nirgends_gibt_bleibt_ein_loch(self):
        self.assertFalse(_statisch_vorhanden(self.widget, "../../geteilt/js/fehlt.js"))

    def test_ein_pfad_aus_static_hinaus_zaehlt_nicht(self):
        self.assertFalse(_statisch_vorhanden(self.widget, "../../../../kern.js"))

    def test_ohne_static_im_pfad_gibt_es_nichts_zu_rechnen(self):
        datei = self.ordner / "werkzeug" / "js" / "probe.js"
        datei.parent.mkdir(parents=True)
        datei.write_text("", encoding="utf-8")
        self.assertFalse(_statisch_vorhanden(datei, "../../geteilt/js/kern.js"))
