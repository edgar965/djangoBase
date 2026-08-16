# -*- coding: utf-8 -*-
u"""Tests der Frontend-Werkzeuge in Skills2 (jsbefunde, jsfaenger, jswaisen, …).

WARUM MIT GEGENPROBE: Ein Pruefwerkzeug, das nie etwas findet, faellt niemandem
auf - es sieht aus wie ein sauberes Projekt. Deshalb gehoert zu jedem Werkzeug
BEIDES: eine Datei mit dem Fehler (muss gefunden werden) und eine ohne (darf
nicht gefunden werden).

Die Faelle hier sind genau die, die im 3DTools-Durchgang echte Ausfaelle waren:
* ein Import in eine Datei, die es nicht gibt (Kleider-Anpassung tot),
* ein Modul, das sich anmeldet, aber niemand laedt (Fotoanalyse tot),
* ein gerufener Registername ohne Anmeldung (drei Zweige still ausgefallen),
* ein Abruf ohne try-Block (Serverfehler blieb stumm),
* ein `fetch` ohne `.ok`-Pruefung (HTML-Fehlerseite als JSON gelesen).
"""
import shutil
import tempfile
from pathlib import Path

from django.test import override_settings

from djangobase.skills2 import werkzeug_finden

from ..base import BasisTest


class FrontendBasis(BasisTest):
    """Legt ein Mini-Projekt mit static/ und templates/ an."""

    def projekt(self, dateien):
        ordner = Path(tempfile.mkdtemp(prefix="skills2_js_"))
        self.addCleanup(shutil.rmtree, ordner, True)
        for name, inhalt in dateien.items():
            pfad = ordner / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
        return ordner

    def laufen(self, slug, dateien):
        ordner = self.projekt(dateien)
        with override_settings(BASE_DIR=str(ordner)):
            return werkzeug_finden(slug).laufen()

    def orte(self, ergebnis):
        return " ".join(z.get("ort", "") + " " + str(z.get("art", ""))
                        for z in ergebnis.zeilen)


#: Eine Vorlage, die genau eine Datei laedt - der Einstiegspunkt.
VORLAGE = """{% load static %}
<script type="module" src="{% static 'einstieg.js' %}?v=1"></script>
"""


class JsWaisenTest(FrontendBasis):

    def test_findet_waise_mit_anmeldung(self):
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "export const a = 1;\n",
            "static/verwaist.js": "fn.applyFacialExpression = () => {};\n",
        })
        self.assertIn("verwaist.js", self.orte(ergebnis))
        self.assertIn("verwaist + angemeldet", self.orte(ergebnis))

    def test_geladene_datei_ist_kein_befund(self):
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "import './helfer.js';\n",
            "static/helfer.js": "export const b = 2;\n",
        })
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))

    def test_findet_import_ins_leere(self):
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "import { X } from './gibtesnicht.js';\n",
        })
        self.assertIn("Import ins Leere", self.orte(ergebnis))

    def test_erwaehnung_im_kommentar_ist_kein_import(self):
        u"""Der Fall, der beim Bau Fehlalarm ausloeste: Ein Kommentar, der einen
        Import ERWAEHNT (`await import('../model_generator.js')`)."""
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "// frueher: await import('./weg.js')\n"
                                  "export const c = 3;\n",
        })
        self.assertNotIn("Import ins Leere", self.orte(ergebnis))


class JsRegistrierungTest(FrontendBasis):

    def test_findet_gerufen_ohne_anmeldung(self):
        ergebnis = self.laufen("jsregistrierung", {
            "static/ruft.js": "fn.startWizard();\n",
        })
        self.assertIn("startWizard", self.orte(ergebnis)
                      + " ".join(z.get("name", "") for z in ergebnis.zeilen))

    def test_angemeldet_und_gerufen_ist_kein_fehler(self):
        ergebnis = self.laufen("jsregistrierung", {
            "static/meldet.js": "fn.startWizard = () => {};\n",
            "static/ruft.js": "fn.startWizard();\n",
        })
        arten = [z["art"] for z in ergebnis.zeilen]
        self.assertNotIn("gerufen, NICHT angemeldet", arten)


class JsFaengerTest(FrontendBasis):

    OHNE = ("export async function laden() {\n"
            "    const d = await Serverabruf.json('/api/x/');\n"
            "    return d;\n}\n")
    MIT = ("export async function laden() {\n"
           "    try {\n"
           "        const d = await Serverabruf.json('/api/x/');\n"
           "        return d;\n"
           "    } catch (fehler) {\n"
           "        return null;\n"
           "    }\n}\n")

    def test_findet_aufruf_ohne_try(self):
        ergebnis = self.laufen("jsfaenger", {"static/a.js": self.OHNE})
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))

    def test_aufruf_im_try_ist_kein_befund(self):
        ergebnis = self.laufen("jsfaenger", {"static/a.js": self.MIT})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))

    def test_mehrzeiliger_template_string_verschiebt_das_blockende_nicht(self):
        u"""Der Fehlalarm, an dem der Klammerzaehler gebaut wurde: Eine Zeile im
        Template-String enthaelt `${…}`; ohne Gedaechtnis galt der try-Block
        vorzeitig als beendet und der gefangene Aufruf als offen."""
        inhalt = ("export async function laden(x) {\n"
                  "    try {\n"
                  "        const s = `<span>${x}</span>\n"
                  "            <b>${x}</b>`;\n"
                  "        const d = await Serverabruf.json('/api/x/');\n"
                  "        return d + s;\n"
                  "    } catch (fehler) {\n"
                  "        return null;\n"
                  "    }\n}\n")
        ergebnis = self.laufen("jsfaenger", {"static/a.js": inhalt})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))


class JsBefundeTest(FrontendBasis):

    def arten(self, ergebnis):
        return " ".join(str(z.get("art", "")) for z in ergebnis.zeilen)

    def test_findet_fetch_ohne_ok_pruefung(self):
        ergebnis = self.laufen("jsbefunde", {
            "static/a.js": "async function f() {\n"
                           "    const r = await fetch('/api/x/');\n"
                           "    const d = await r.json();\n"
                           "    return d;\n}\n",
        })
        self.assertIn("Antwort ohne .ok-Pruefung", self.arten(ergebnis))

    def test_ok_pruefung_hinter_mehrzeiligem_optionsobjekt_zaehlt(self):
        u"""Fehlalarm-Gegenprobe: Das Fenster muss ab dem ENDE der
        fetch-Anweisung zaehlen, nicht ab ihrer ersten Zeile."""
        ergebnis = self.laufen("jsbefunde", {
            "static/a.js": "async function f() {\n"
                           "    const r = await fetch('/api/x/', {\n"
                           "        method: 'POST',\n"
                           "        headers: { 'Content-Type': 'a/b' },\n"
                           "        body: '{}',\n"
                           "    });\n"
                           "    if (!r.ok) throw new Error('kaputt');\n"
                           "    return r.json();\n}\n",
        })
        self.assertNotIn("Antwort ohne .ok-Pruefung", self.arten(ergebnis))

    def test_django_vergleich_in_vorlage_ist_kein_javascript_befund(self):
        u"""Der teuerste Fehlalarm des Werkzeugs: `<script src=…></script>` in
        EINER Zeile liess die ganze Vorlage als JavaScript gelten - 107
        Django-Vergleiche erschienen als Befund."""
        ergebnis = self.laufen("jsbefunde", {
            "templates/seite.html":
                '<script src="/static/x.js"></script>\n'
                "{% if job.status == 'complete' %}fertig{% endif %}\n",
        })
        self.assertNotIn("Vergleich mit ==", self.arten(ergebnis))

    def test_dauerlaeufer_mit_marker_ist_kein_befund(self):
        ergebnis = self.laufen("jsbefunde", {
            "static/a.js": "// dauerhaft gewollt: Absturzsicherung.\n"
                           "// Beim regulaeren Verlassen greift beforeunload.\n"
                           "setInterval(sichern, 30000);\n",
        })
        self.assertNotIn("setInterval ohne Abbruch", self.arten(ergebnis))

    def test_dauerlaeufer_ohne_marker_ist_ein_befund(self):
        ergebnis = self.laufen("jsbefunde", {
            "static/a.js": "setInterval(sichern, 30000);\n",
        })
        self.assertIn("setInterval ohne Abbruch", self.arten(ergebnis))


class JsFunktionenTest(FrontendBasis):

    def lange(self, zeilen):
        rumpf = "\n".join("    const x%d = %d;" % (i, i) for i in range(zeilen))
        return "function gross() {\n%s\n}\n" % rumpf

    def test_findet_lange_funktion(self):
        ergebnis = self.laufen("jsfunktionen", {"static/a.js": self.lange(120)})
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))
        self.assertEqual(ergebnis.zeilen[0]["name"], "gross()")

    def test_kurze_funktion_ist_kein_befund(self):
        ergebnis = self.laufen("jsfunktionen", {"static/a.js": self.lange(10)})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))

    def test_grenze_aus_den_einstellungen(self):
        ordner = self.projekt({"static/a.js": self.lange(40)})
        with override_settings(BASE_DIR=str(ordner),
                               DJANGOBASE={"skills2_funktionsgrenze": 20}):
            self.assertEqual(len(werkzeug_finden("jsfunktionen").laufen().zeilen), 1)


class JsSyntaxTest(FrontendBasis):

    def test_findet_kaputten_import(self):
        u"""Der Fall, der das Werkzeug ausgeloest hat: eine Import-Zeile MITTEN
        in einem mehrzeiligen Import. `node --check` auf .js ist dabei gruen."""
        if not shutil.which("node"):
            self.skipTest("node nicht im PATH")
        ergebnis = self.laufen("jssyntax", {
            "static/kaputt.js": "import { a, b,\n"
                                "import { C } from './c.js';\n"
                                "         d } from './x.js';\n",
            "static/heil.js": "import { C } from './c.js';\nexport const e = 1;\n",
        })
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))
        self.assertIn("kaputt.js", ergebnis.zeilen[0]["ort"])

    def test_ohne_node_kein_falsches_gruen(self):
        u"""Fehlt Node, darf das Werkzeug NICHT sagen, alles sei in Ordnung."""
        ergebnis = self.laufen("jssyntax", {"static/a.js": "export const a = 1;\n"})
        if shutil.which("node"):
            self.assertIn("geprueft", ergebnis.zusammenfassung)
        else:
            self.assertIn("node nicht gefunden", ergebnis.zusammenfassung)
