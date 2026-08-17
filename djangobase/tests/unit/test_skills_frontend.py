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
from django.urls import path

from djangobase.skills import werkzeug_finden

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

    def test_laeufer_ist_keine_waise(self):
        u"""Node-Skripte und Bau-Konfigurationen MUESSEN unerreichbar sein.

        Vorher standen `vite.config.js`, `playwright.config.js` und ein
        Playwright-Test unter „laedt niemand" — mit der Abhilfe „importieren
        oder loeschen". Ein Loeschvorschlag fuer lebenden Code ist die teuerste
        Sorte Fehlalarm.
        """
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "export const a = 1;\n",
            "playwright.config.js": "module.exports = { testDir: '.' };\n",
            "vite.config.js": "import { defineConfig } from 'vite';\n"
                              "export default defineConfig({});\n",
            "test_lauf.js": "const { test } = require('@playwright/test');\n",
            "werkzeug.js": "const p = process.env.PORT;\n",
        })
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))
        self.assertIn("4 Laeufer nicht gezaehlt", ergebnis.zusammenfassung)

    def test_echte_waise_bleibt_trotz_laeufer_erkennung(self):
        u"""Gegenprobe: Ein Browser-Modul ohne Node-Merkmale bleibt ein Befund."""
        ergebnis = self.laufen("jswaisen", {
            "templates/seite.html": VORLAGE,
            "static/einstieg.js": "export const a = 1;\n",
            "static/tot.js": "export function nie() { return 1; }\n",
        })
        self.assertIn("tot.js", self.orte(ergebnis))


class FrontendadressenTest(FrontendBasis):
    u"""Der Fall: acht Aufrufe auf eine Adresse, die es nicht gibt.

    Die Kontextmenues zweier Listen riefen `/api/character/garment/manage/` —
    diesen Endpunkt gab es nicht. Vier tote Menuepunkte, ohne Hinweis fuer den
    Benutzer, bei HTTP 200.

    Die Tests hier pruefen vor allem die FEHLALARME weg: Die erste Fassung des
    Werkzeugs meldete 13 Adressen, davon 12 falsch.
    """

    def laufen_mit_urls(self, dateien):
        u"""Wie `laufen`, aber mit der URL-Konfiguration dieses Testmoduls."""
        from django.test import override_settings as ueberschreiben
        with ueberschreiben(ROOT_URLCONF=__name__):
            return self.laufen("frontendadressen", dateien)

    def test_findet_unbekannte_adresse(self):
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "await fetch('/api/gibtesnicht/');\n",
        })
        self.assertIn("/api/gibtesnicht/", str(ergebnis.zeilen))

    def test_bekannte_adresse_ist_kein_befund(self):
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "await fetch('/api/da/');\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_konstante_ist_kein_aufruf(self):
        u"""`static ENDPUNKT = '/api/x/'` ist ein Anfang, keine Adresse."""
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "class X { static ENDPUNKT = '/api/gibtesnicht/'; }\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_verkettung_ueber_zeilen_ist_kein_befund(self):
        u"""Der Zusatz stand 42 Leerzeichen eingerueckt in der naechsten Zeile —
        mit einem zu kleinen Suchfenster blieb genau das ein Fehlalarm."""
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "await fetch('/api/da/'\n"
                           + " " * 42 + "+ encodeURIComponent(name) + '/');\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_kommentar_ist_kein_befund(self):
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "// await fetch('/api/gibtesnicht/');\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_platzhalter_wird_probiert(self):
        u"""Ohne mehrere Kandidaten meldet jede `<uuid:...>`-Route Fehlalarm."""
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "await fetch(`/api/auftrag/${id}/`);\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_alle_stellen_werden_gezaehlt(self):
        ergebnis = self.laufen_mit_urls({
            "static/a.js": "fetch('/api/weg/');\nfetch('/api/weg/');\n",
            "static/b.js": "fetch('/api/weg/');\n",
        })
        self.assertEqual(ergebnis.zeilen[0]["stellen"], 3, str(ergebnis.zeilen))


class VorlagenblockTest(FrontendBasis):
    u"""Der Fall: `{% block extra_styles %}`, den `base.html` nicht kennt.

    Django verwirft ihn still. In 3DTools verschwand so der ganze Stilblock einer
    Seite — 180 Vorschaubilder waren danach 0x0 Pixel gross, bei HTTP 200.
    """

    ELTERN = ("<html><head>{% block extra_head %}{% endblock %}</head>"
              "<body>{% block content %}{% endblock %}</body></html>\n")

    def test_findet_unbekannten_block(self):
        ergebnis = self.laufen("vorlagenblock", {
            "templates/base.html": VorlagenblockTest.ELTERN,
            "templates/seite.html": '{% extends "base.html" %}\n'
                                    "{% block extra_styles %}<style>"
                                    ".x{color:red}</style>{% endblock %}\n",
        })
        self.assertIn("extra_styles", self.orte(ergebnis) + str(ergebnis.zeilen))

    def test_bekannter_block_ist_kein_befund(self):
        ergebnis = self.laufen("vorlagenblock", {
            "templates/base.html": VorlagenblockTest.ELTERN,
            "templates/seite.html": '{% extends "base.html" %}\n'
                                    "{% block extra_head %}<style>"
                                    ".x{color:red}</style>{% endblock %}\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_geschachtelter_block_ist_kein_befund(self):
        u"""Die entscheidende Unterscheidung.

        Ein Block INNERHALB eines bekannten Blocks wird an seiner Stelle
        gerendert — er ist eine Erweiterungsstelle fuer eigene Kinder. Ohne diese
        Regel meldete die Pruefung im echten Projekt 11 statt 1 Fundstelle, und
        `character_viewer.html` (acht solche Bloecke) haette wie ein Fehler
        ausgesehen.
        """
        ergebnis = self.laufen("vorlagenblock", {
            "templates/base.html": VorlagenblockTest.ELTERN,
            "templates/seite.html": '{% extends "base.html" %}\n'
                                    "{% block content %}\n"
                                    "  {% block werkzeugleiste %}Knoepfe"
                                    "{% endblock %}\n"
                                    "{% endblock %}\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_block_der_grosseltern_zaehlt(self):
        u"""`extends`-Ketten werden verfolgt, nicht nur eine Ebene."""
        ergebnis = self.laufen("vorlagenblock", {
            "templates/base.html": VorlagenblockTest.ELTERN,
            "templates/mitte.html": '{% extends "base.html" %}\n'
                                    "{% block content %}{% endblock %}\n",
            "templates/seite.html": '{% extends "mitte.html" %}\n'
                                    "{% block extra_head %}<style>"
                                    ".x{color:red}</style>{% endblock %}\n",
        })
        self.assertEqual(ergebnis.zeilen, [], str(ergebnis.zeilen))

    def test_fehlende_elternvorlage_wird_gemeldet(self):
        ergebnis = self.laufen("vorlagenblock", {
            "templates/seite.html": '{% extends "gibtesnicht.html" %}\n'
                                    "{% block content %}x{% endblock %}\n",
        })
        self.assertIn("Elternvorlage fehlt", str(ergebnis.zeilen))


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

    # ------------------------------------------------------------ Aufrufkette

    def test_einzeiliges_try_catch_zaehlt(self):
        u"""`try { await x(); } catch (e) { … }` in EINER Zeile.

        Bis zum 17.08.2026 fiel diese Form durch: `_blockende` sah die Zeile
        nach der oeffnenden an und fand nie ein Ende. Genau so faengt
        `properties.js` in 3DTools seinen Aufruf von `fetchMorphDefs()` — der
        Abruf galt deshalb als ungedeckt.
        """
        ergebnis = self.laufen("jsfaenger", {"static/a.js":
            "export async function laden() {\n"
            "    try { const d = await Serverabruf.json('/api/x/'); return d; }\n"
            "    catch (fehler) { return null; }\n}\n"})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))

    def test_aufrufer_deckt_den_helfer(self):
        u"""Der Fall, der 18 von 20 Zeilen zu Fehlalarmen machte."""
        ergebnis = self.laufen("jsfaenger", {"static/a.js":
            "async function _helfer(u) {\n"
            "    const d = await Serverabruf.json(u);\n"
            "    return d;\n}\n"
            "\n"
            "export async function zeigen(u) {\n"
            "    try { return await _helfer(u); } catch (e) { return null; }\n"
            "}\n"})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))
        self.assertIn("1 über den Aufrufer gedeckt", ergebnis.zusammenfassung)

    def test_ungefangener_aufrufer_bleibt_ein_befund(self):
        u"""Gegenprobe zum vorigen Test: Faengt der Aufrufer NICHT, bleibt es
        offen — und die Meldung nennt die Stelle, an der die Kette abreisst."""
        ergebnis = self.laufen("jsfaenger", {"static/a.js":
            "async function _helfer(u) {\n"
            "    const d = await Serverabruf.json(u);\n"
            "    return d;\n}\n"
            "\n"
            "export async function zeigen(u) {\n"
            "    return await _helfer(u);\n"
            "}\n"})
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))
        self.assertIn("_helfer", ergebnis.zeilen[0]["aufrufer"])

    def test_gleichnamige_methode_woanders_deckt_nicht(self):
        u"""`load()` heisst auch die Methode von Three.js' GLTFLoader.

        Eine Datei, die den Namen weder importiert noch ueber eine Sammelstelle
        sieht, darf nicht ueber den Befund entscheiden — in 3DTools galt
        `gltfLoader.load(...)` kurzzeitig als der „Aufrufer" (17.08.2026).
        """
        ergebnis = self.laufen("jsfaenger", {
            "static/a.js": "export class Figur {\n"
                           "    async load() {\n"
                           "        const d = await Serverabruf.json('/api/x/');\n"
                           "        return d;\n"
                           "    }\n}\n",
            # Kein Import von a.js, keine Sammelstelle: fremdes `load`.
            "static/fremd.js": "const lader = new GLTFLoader();\n"
                               "export function holen(u) {\n"
                               "    try { lader.load(u); } catch (e) {}\n"
                               "}\n"})
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))

    def test_name_in_einer_meldung_ist_kein_aufruf(self):
        u"""`throw new Error('laden() must be called first')` zaehlte als
        ungefangener Aufruf — der Name steht dort in einer Zeichenkette."""
        ergebnis = self.laufen("jsfaenger", {"static/a.js":
            "let _wert = null;\n"
            "export async function laden(u) {\n"
            "    _wert = await Serverabruf.json(u);\n"
            "    return _wert;\n}\n"
            "\n"
            "export function wert() {\n"
            "    if (!_wert) throw new Error('laden() must be called first');\n"
            "    return _wert;\n}\n"})
        # Kein echter Aufrufer vorhanden -> offen, aber mit DIESER Begruendung.
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))
        self.assertIn("kein Aufrufer gefunden", ergebnis.zeilen[0]["aufrufer"])

    def test_sammelstelle_zaehlt_als_sichtweg(self):
        u"""`fn.X = X` traegt den Namen ohne Import weiter.

        In 3DTools ruft `save_load.js` `fn.CharacterInstance.fromJSON(...)`,
        ohne `character.js` zu importieren. Ohne diesen Weg hiess es „kein
        Aufrufer gefunden", und ein gedeckter Abruf stand als Befund da.
        """
        ergebnis = self.laufen("jsfaenger", {
            "static/a.js": "export class Figur {\n"
                           "    async netzHolen() {\n"
                           "        const d = await Serverabruf.json('/api/x/');\n"
                           "        return d;\n"
                           "    }\n}\n"
                           "fn.Figur = Figur;\n",
            "static/b.js": "export async function aufbauen() {\n"
                           "    const f = new fn.Figur();\n"
                           "    try { await f.netzHolen(); } catch (e) {}\n"
                           "}\n"})
        self.assertEqual(ergebnis.zeilen, [], self.orte(ergebnis))

    def test_allerweltsname_geht_nicht_ueber_die_sammelstelle(self):
        u"""Gegenprobe zum vorigen Test: Bei `load()` zaehlt nur der Import-Weg.

        In 3DTools wurde `_loadHairForCharacter()` zum „Aufrufer" der
        Netz-Ladefunktion, weil in dessen Naehe ein fremdes `load()` steht — eine
        Kette, die es nicht gibt (17.08.2026). Hier faengt `b.js` woertlich
        genauso wie oben, und der Befund bleibt trotzdem stehen: Der Name ist zu
        haeufig, um ihn ueber eine Sammelstelle zuzuordnen."""
        ergebnis = self.laufen("jsfaenger", {
            "static/a.js": "export class Figur {\n"
                           "    async load() {\n"
                           "        const d = await Serverabruf.json('/api/x/');\n"
                           "        return d;\n"
                           "    }\n}\n"
                           "fn.Figur = Figur;\n",
            "static/b.js": "export async function aufbauen() {\n"
                           "    const f = new fn.Figur();\n"
                           "    try { await f.load(); } catch (e) {}\n"
                           "}\n"})
        self.assertEqual(len(ergebnis.zeilen), 1, self.orte(ergebnis))


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

    def test_marker_im_dateikopf_nimmt_die_ganze_datei_aus(self):
        u"""Eine Debugseite, deren Konsolenausgabe ihr Ergebnis IST.

        Vorher brauchte das einen Pfad, der im Pruefer hart eingetragen war —
        beim naechsten Projekt raet der. Jetzt steht die Begruendung in der
        Datei, die es betrifft.
        """
        ergebnis = self.laufen("jsbefunde", {
            "templates/debug.html":
                "{% comment %}\n"
                "  Debugseite: die Konsolenausgabe IST das Ergebnis, die\n"
                "  Meldungen sind dauerhaft gewollt.\n"
                "{% endcomment %}\n"
                "<script>\n"
                "  console.log('Schritt 1');\n"
                "  console.log('Schritt 2');\n"
                "</script>\n",
        })
        self.assertNotIn("console.log", self.arten(ergebnis))

    def test_ohne_marker_bleibt_console_log_ein_befund(self):
        u"""Gegenprobe zum Kopf-Vermerk."""
        ergebnis = self.laufen("jsbefunde", {
            "templates/debug.html": "<script>\n  console.log('Schritt 1');\n"
                                    "</script>\n",
        })
        self.assertIn("console.log", self.arten(ergebnis))


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


# --------------------------------------------------------------------------
# URL-Konfiguration NUR fuer FrontendadressenTest: `ROOT_URLCONF=__name__`
# laesst Django dieses Modul als URLconf lesen. So haengen die Tests nicht am
# Bestand des Test-Hosts, und `<uuid:...>` ist als Fall abgedeckt.
def _leer(request):                                          # pragma: no cover
    from django.http import HttpResponse
    return HttpResponse("")


urlpatterns = [
    path("api/da/", _leer, name="da"),
    path("api/auftrag/<uuid:kennung>/", _leer, name="auftrag"),
]
