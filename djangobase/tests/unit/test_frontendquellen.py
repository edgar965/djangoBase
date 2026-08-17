# -*- coding: utf-8 -*-
u"""Tests der gemeinsamen Frontend-Quellenliste.

ANLASS (17.08.2026): Die Ausschlussliste stand ACHTMAL im Paket, in VIER
Fassungen — die JS-Werkzeuge waren sich nicht einig, welche Dateien zum Projekt
gehoeren. Beim Zusammenlegen kamen drei Fallen heraus, jede einmal durchlebt:

1. **Eine lange Zeile macht keine erzeugte Datei.** Mit der Schwelle „irgendeine
   Zeile ueber 1.000 Zeichen" fielen zwei HANDGESCHRIEBENE Module heraus
   (`presets.js`, `smpl.js` — je ein CSS-Block als Template-String). Aufgefallen
   ist es daran, dass `jswaisen` danach vier Importe „ins Leere" meldete: Die
   Ziele waren nicht weg, sie waren nur nicht mehr geprueft.
2. **Die Probe schneidet ab.** Zeile 1 eines Vite-Buendels hat 221.758 Zeichen;
   in 64 KB steckt davon ein Stueck ohne Zeilenumbruch. Die Zaehlung sah EINE
   lange Zeile und gab die Datei frei — das Buendel stand mit 2.295 Befunden in
   der Liste. Dagegen die harte Grenze.
3. **Der Ordnername verdeckt.** `theatre`/`theatre-studio` standen in der Liste;
   der zweite Ordner enthielt kein Buendel, sondern eine handgeschriebene
   Debugseite mit 25 `console.log`, die niemand mehr lud.
"""
import shutil
import tempfile
from pathlib import Path

from djangobase.skills.frontendquellen import Frontendquellen

from ..base import BasisTest


class FrontendquellenTest(BasisTest):

    def projekt(self, dateien):
        ordner = Path(tempfile.mkdtemp(prefix="frontendquellen_"))
        self.addCleanup(shutil.rmtree, ordner, True)
        for name, inhalt in dateien.items():
            pfad = ordner / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
        return Frontendquellen(ordner)

    def kurz(self, quellen, *endungen):
        return [k for _p, k in quellen.paare(*endungen)]

    # ------------------------------------------------------------- Grundfaelle

    def test_findet_js_und_html(self):
        q = self.projekt({"static/a.js": "let a = 1;\n",
                          "templates/b.html": "<p>x</p>\n"})
        self.assertEqual(self.kurz(q, ".js"), ["static/a.js"])
        self.assertEqual(sorted(self.kurz(q, ".js", ".html")),
                         ["static/a.js", "templates/b.html"])

    def test_min_und_fremdordner_bleiben_draussen(self):
        q = self.projekt({"static/a.js": "let a = 1;\n",
                          "static/three.min.js": "x\n",
                          "static/vendor/lib.js": "x\n",
                          "node_modules/p/i.js": "x\n",
                          "staticfiles/a.js": "x\n"})
        self.assertEqual(self.kurz(q, ".js"), ["static/a.js"])

    def test_eigener_ausschluss_wird_beachtet(self):
        q = self.projekt({"static/a.js": "let a = 1;\n",
                          "TestKopie/b.js": "let b = 2;\n"})
        q.raus = {"TestKopie"}
        self.assertEqual(self.kurz(q, ".js"), ["static/a.js"])

    # ------------------------------------------------------ Erzeugter Code

    def test_buendel_mit_vielen_langen_zeilen_ist_erzeugt(self):
        q = self.projekt({"static/app.js": "\n".join(["x" * 1200] * 5)})
        self.assertEqual(self.kurz(q, ".js"), [])

    def test_eine_lange_zeile_ist_noch_kein_buendel(self):
        u"""Der Fall `presets.js`: ein CSS-Block als Template-String."""
        zeilen = ["const stil = `%s`;" % ("a" * 2200)] + ["let x = 1;"] * 40
        q = self.projekt({"static/presets.js": "\n".join(zeilen)})
        self.assertEqual(self.kurz(q, ".js"), ["static/presets.js"])

    def test_eine_sehr_lange_zeile_reicht(self):
        u"""Die Probe schneidet nach 64 KB ab — eine einzige Zeile von 221.758
        Zeichen kam dort als EIN Stueck an, und die Zaehlung gab das Buendel frei.
        Die harte Grenze faengt genau das."""
        q = self.projekt({"static/app.js": "var a=1;" + "b" * 30000})
        self.assertEqual(self.kurz(q, ".js"), [])

    def test_ordnername_theatre_schliesst_nicht_mehr_aus(self):
        u"""3DTools-Ordner haben in einer Bibliothek fuer sechs Projekte nichts
        zu suchen. Was dort liegt, entscheidet die Messung."""
        q = self.projekt({"static/theatre/handgeschrieben.js": "let a = 1;\n"})
        self.assertEqual(self.kurz(q, ".js"),
                         ["static/theatre/handgeschrieben.js"])

    def test_texte_liefert_zeilen(self):
        q = self.projekt({"static/a.js": "eins\nzwei\n"})
        self.assertEqual(q.texte(".js"), [("static/a.js", ["eins", "zwei", ""])])
