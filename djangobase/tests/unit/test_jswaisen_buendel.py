# -*- coding: utf-8 -*-
u"""Ein gebündeltes Frontend ist kein Friedhof.

DER ANLASS (3DTools, 01.09.2026)
================================
`jswaisen` meldete 44 Dateien, die „niemand laedt" — und alle 44 lagen
in `TheatreJS/src/`, einer Vite-Anwendung, die taeglich benutzt wird.
Die Vorlage laedt dort nur das fertige Buendel
(`static/theatre/theatre-app.js`); der Einstieg in den Quellbaum steht
in `vite.config.js`::

    input: path.resolve(__dirname, 'src/main.js')

Ein Werkzeug, das jede Datei eines gebuendelten Frontends als tot
meldet, ist die teuerste Sorte Fehlalarm: ein Loeschvorschlag fuer
lebenden Code (`~/.claude/rules/analysewerkzeuge.md`).

BDD - GEGEBEN / DANN
====================
    EinGebuendeltesFrontend   ... seine Module gelten als geladen
    EineEchteWaiseDaneben     ... wird trotzdem gemeldet
"""
from djangobase.skills.jswaisen import JsWaisen

from .test_neue_werkzeuge import WerkzeugBasis


class BuendelBasis(WerkzeugBasis):
    u"""Ein Miniprojekt mit Vite-Konfiguration, Einstieg und zwei Modulen."""

    KONFIG = (
        "import { defineConfig } from 'vite';\n"
        "import path from 'path';\n"
        "export default defineConfig({\n"
        "    build: {\n"
        "        rollupOptions: {\n"
        "            input: path.resolve(__dirname, 'src/main.js'),\n"
        "            output: { entryFileNames: 'app-buendel.js' },\n"
        "        },\n"
        "    },\n"
        "});\n")

    DATEIEN = {
        'frontend/vite.config.js': KONFIG,
        'frontend/src/main.js': "import { start } from './buehne.js';\n"
                                "start();\n",
        'frontend/src/buehne.js': "export function start() { return 1; }\n",
        # Die Vorlage kennt NUR das Buendel.
        'templates/seite.html':
            '<script type="module" src="/static/app-buendel.js"></script>\n',
        'static/app-buendel.js': "console.log('gebaut');\n",
    }

    def zeilen(self, zusatz=None):
        dateien = dict(self.DATEIEN)
        dateien.update(zusatz or {})
        return self.projekt(dateien).fahren(JsWaisen)

    @staticmethod
    def waisen(zeilen):
        return sorted(z['ort'] for z in zeilen if z['art'].startswith('verwaist'))


class EinGebuendeltesFrontend(BuendelBasis):
    u"""Gegeben: Vite baut aus `src/main.js`."""

    def test_einstieg_und_seine_module_gelten_als_geladen(self):
        offen = self.waisen(self.zeilen())
        self.assertNotIn('frontend/src/main.js', offen)
        self.assertNotIn('frontend/src/buehne.js', offen)

    def test_keine_importe_ins_leere(self):
        leer = [z for z in self.zeilen() if z['art'] == 'Import ins Leere']
        self.assertEqual(leer, [])


class EineEchteWaiseDaneben(BuendelBasis):
    u"""GEGENPROBE: Der Prüfer darf nicht blind geworden sein.

    Eine Datei im selben Quellbaum, die der Einstieg NICHT erreicht,
    ist weiterhin tot — genau dafuer gibt es das Werkzeug.
    """

    def test_sie_wird_gemeldet(self):
        offen = self.waisen(self.zeilen({
            'frontend/src/vergessen.js':
                "export function niemandRuftMich() { return 2; }\n"}))
        self.assertIn('frontend/src/vergessen.js', offen)
