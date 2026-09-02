# -*- coding: utf-8 -*-
u"""LsKonfig: Vorgaben, Formular, Datei, Abdruck, pyrightconfig."""
import json
import tempfile
import unittest
from pathlib import Path

from djangobase.umbau.ls_konfig import AUSSCHLUESSE, REGELN, LsKonfig


class Formular(dict):
    def getlist(self, k):
        v = self.get(k, [])
        return v if isinstance(v, list) else [v]


class LsKonfigTest(unittest.TestCase):

    def test_vorgaben_sind_vollstaendig(self):
        k = LsKonfig()
        self.assertEqual(k.modus, "basic")
        self.assertEqual(k.werkzeug, "auto")
        self.assertEqual(set(k.regeln), {r for r, _s, _t in REGELN})
        self.assertEqual(set(k.ausschluss), {a for a, _m, _v, _l in AUSSCHLUESSE})
        self.assertEqual(k.regeln["reportAttributeAccessIssue"], "none")

    def test_rundreise_ueber_die_datei(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "konfig.json"
            k = LsKonfig({"modus": "strict", "pfade": ["brain"], "deckel": 42})
            k.speichern(pfad)
            geladen = LsKonfig.laden(pfad)
            self.assertEqual(geladen.als_dict(), k.als_dict())
            self.assertEqual(LsKonfig.laden(Path(d) / "fehlt.json").modus, "basic")

    def test_formular_liest_listen_und_haken(self):
        daten = Formular({"werkzeug": "pyright", "modus": "standard", "stufe": "error",
                          "pfade": ["brain", "depot"], "ausschluss": ["tests"],
                          "regel_reportUnusedImport": "none", "deckel": "9999",
                          "zeitlimit": "5"})
        k = LsKonfig.aus_formular(daten, LsKonfig())
        self.assertEqual(k.werkzeug, "pyright")
        self.assertEqual(k.pfade, ["brain", "depot"])
        self.assertTrue(k.ausschluss["tests"])
        self.assertFalse(k.ausschluss["venv"], "nicht mitgeschickte Haken sind aus")
        self.assertEqual(k.regeln["reportUnusedImport"], "none")
        self.assertEqual(k.deckel, 5000, "Deckel wird auf den Bereich begrenzt")
        self.assertEqual(k.zeitlimit, 10)
        self.assertFalse(k.stubs)

    def test_unbekannte_werte_fallen_auf_die_vorgabe(self):
        k = LsKonfig.aus_formular(Formular({"werkzeug": "mypy", "modus": "x"}), LsKonfig())
        self.assertEqual((k.werkzeug, k.modus), ("auto", "basic"))

    def test_projektliste_wirkt_auf_muster_und_abdruck_aber_nicht_auf_die_datei(self):
        k = LsKonfig({"zusatz": ["**/sicherung", "werkzeug/netz_*.py"]})
        self.assertIn("werkzeug/netz_*.py", k.ausschluss_muster())
        self.assertNotIn("zusatz", k.als_dict(),
                         u"die Liste steht im Projekt, nicht in der konfig.json")
        self.assertNotEqual(k.abdruck(), LsKonfig().abdruck())
        # Doppelt genannte Muster stehen nur einmal in der Konfiguration.
        doppelt = LsKonfig({"zusatz": ["**/migrations"]})
        self.assertEqual(doppelt.ausschluss_muster().count("**/migrations"), 1)
        # Ein POST verliert die Liste nicht - sie kommt aus ``alt``.
        neu = LsKonfig.aus_formular(Formular({"modus": "strict"}), k)
        self.assertEqual(neu.zusatz, k.zusatz)

    def test_abdruck_haengt_an_den_laufoptionen_nicht_an_der_anzeige(self):
        a = LsKonfig()
        self.assertEqual(a.abdruck(), LsKonfig().abdruck())
        self.assertNotEqual(a.abdruck(), LsKonfig({"modus": "strict"}).abdruck())
        # Anzeigefelder aendern das Ergebnis nicht - sonst kostete jeder
        # umgelegte Filter einen neuen Lauf.
        for feld, wert in (("deckel", 501), ("stufe", "error"),
                           ("zeitlimit", 60), ("js_stumm", [])):
            self.assertEqual(a.abdruck(), LsKonfig({feld: wert}).abdruck(), feld)

    def test_js_regeln_stummschalten(self):
        self.assertIn("TS2339", LsKonfig().js_stumm, u"DOM-Rauschen ist in der Vorgabe aus")
        k = LsKonfig.aus_formular(Formular({"js_stumm": ["TS2304"]}), LsKonfig())
        self.assertEqual(k.js_stumm, ["TS2304"])
        leer = LsKonfig.aus_formular(Formular({}), LsKonfig())
        self.assertEqual(leer.js_stumm, [], u"kein Haken = nichts stumm")

    def test_pyrightconfig_mit_absoluten_pfaden_und_venv(self):
        k = LsKonfig({"pfade": ["brain"], "python": r"C:\p\venv\Scripts\python.exe"})
        cfg = k.als_pyrightconfig(r"C:\p", extra=[r"C:\p\web"])
        self.assertEqual(cfg["include"], [str(Path(r"C:\p") / "brain")])
        self.assertEqual((cfg["venvPath"], cfg["venv"]), (r"C:\p", "venv"))
        self.assertIn(r"C:\p\web", cfg["extraPaths"])
        self.assertIn("**/migrations", cfg["exclude"])
        self.assertNotIn("**/tests", cfg["exclude"])
        # Mit Ablage-Ordner: Muster bekommen den Weg zur Wurzel vorangestellt.
        cfg2 = k.als_pyrightconfig(r"C:\p", ablage=r"C:\p\web\.cache\umbau\ls")
        self.assertEqual(cfg2["include"], ["../../../../brain"])
        self.assertIn("../../../../**/migrations", cfg2["exclude"])
        self.assertEqual(cfg["reportUndefinedVariable"], "error")
        json.dumps(cfg)                                  # muss serialisierbar sein

    def test_lsp_einstellungen_je_abschnitt(self):
        e = LsKonfig().als_lsp_einstellungen(r"C:\p")
        self.assertIn("python", e)
        self.assertIn("python.analysis", e)
        self.assertEqual(e["python.analysis"]["typeCheckingMode"], "basic")
        self.assertEqual(e["python.analysis"]["diagnosticSeverityOverrides"]
                         ["reportUndefinedVariable"], "error")
