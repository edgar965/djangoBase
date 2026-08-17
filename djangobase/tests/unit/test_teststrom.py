# -*- coding: utf-8 -*-
u"""Der Live-Lauf: Zeilenleser, Zielpruefung, Ereignisstrom.

Der Zeilenleser ist die unangenehmste Stelle des Live-Laufs, und jeder Fall hier
ist ein Fehler, der WIRKLICH aufgetreten ist (17.08.2026, Projekt assistant):
Name und Ergebnis in getrennten Zeilen, Zeitstempel mitten in der Zeile, statt
des Namens der Docstring, und das abschliessende „OK", das dem letzten Eintrag
des ``--durations``-Blocks ein zweites Ergebnis verpasste.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.testsperre import Laufsperre
from djangobase.teststrom import Teststrom
from djangobase.testtoeter import Toeter
from djangobase.testzeilen import Testzeilen
from djangobase.testziele import Testziele


class TestzeilenTests(SimpleTestCase):

    def setUp(self):
        self.leser = Testzeilen()

    def test_name_und_ergebnis_in_einer_zeile(self):
        e = self.leser.lesen("test_x (a.b.C.test_x) ... ok")
        self.assertEqual((e["id"], e["status"]), ("a.b.C.test_x", "pass"))

    def test_ergebnis_in_der_folgezeile(self):
        u"""Der Normalfall bei Projekten mit Zeitstempel-Praefix."""
        self.assertIsNone(self.leser.lesen(
            "2026-08-17 21:31:50 test_y (a.b.C.test_y) ..."))
        e = self.leser.lesen("2026-08-17 21:31:50 ok")
        self.assertEqual((e["id"], e["status"]), ("a.b.C.test_y", "pass"))

    def test_docstring_statt_name(self):
        u"""-v 2 zeigt die erste Docstring-Zeile — der Name steht davor."""
        self.leser.lesen("2026-08-17 21:34:21 test_z (a.b.C.test_z) ...")
        e = self.leser.lesen("2026-08-17 21:34:21 Zeigt die Route ins Leere? "
                             "Dann ist der Endpunkt tot. ... 2026-08-17 21:34:21 ok")
        self.assertEqual((e["id"], e["status"]), ("a.b.C.test_z", "pass"))

    def test_fehler_und_uebersprungen(self):
        self.assertEqual(self.leser.lesen("test_a (a.b.C.test_a) ... FAIL")["status"],
                         "fail")
        self.assertEqual(self.leser.lesen("test_b (a.b.C.test_b) ... ERROR")["status"],
                         "error")
        self.assertEqual(self.leser.lesen("test_c (a.b.C.test_c) ... skipped")["status"],
                         "skip")

    def test_auswertungsteil_zaehlt_nicht_mit(self):
        u"""Im --durations-Block steht jeder Test nochmal; „OK" gehoert dem Lauf."""
        self.leser.lesen("test_d (a.b.C.test_d) ... ok")
        self.assertIsNone(self.leser.lesen("Slowest test durations"))
        self.assertIsNone(self.leser.lesen("0.005s     test_d (a.b.C.test_d)"))
        self.assertIsNone(self.leser.lesen("OK"))


class TestzieleTests(SimpleTestCase):

    def setUp(self):
        self.ziele = Testziele(
            bekannte_ids={"app.tests.unit.test_x.K.test_y"},
            befehle=[{"slug": "alle-unit", "ziel": "app.tests.unit x.tests.unit"}],
            labels={"app.tests.component"})

    def test_bekannte_id_und_label(self):
        ziele, verworfen = self.ziele.pruefen(
            ["app.tests.unit.test_x.K.test_y", "app.tests.component"])
        self.assertEqual(len(ziele), 2)
        self.assertEqual(verworfen, 0)

    def test_slug_wird_zu_seinen_zielen(self):
        ziele, _ = self.ziele.pruefen(["alle-unit"])
        self.assertEqual(ziele, ["app.tests.unit", "x.tests.unit"])

    def test_unbekanntes_wird_verworfen_und_gezaehlt(self):
        ziele, verworfen = self.ziele.pruefen(["erfunden.tests.unit", "app.tests"])
        self.assertEqual(ziele, [])
        self.assertEqual(verworfen, 2)

    def test_form_wird_geprueft(self):
        u"""Ein Eintrag mit Leerzeichen oder „-" waere ein zusaetzliches Argument."""
        ziele, verworfen = self.ziele.pruefen(
            ["app.tests.unit.test_x.K.test_y --keepdb", "--noinput", "a b"])
        self.assertEqual(ziele, [])
        self.assertEqual(verworfen, 3)

    def test_ohne_ziel_kein_kommando(self):
        cmd, ziele, verworfen = self.ziele.befehl(["quatsch"], sys.executable)
        self.assertIsNone(cmd)
        self.assertEqual((ziele, verworfen), ([], 1))

    def test_longrunner_bekommt_den_tag(self):
        z = Testziele(bekannte_ids={"app.tests.longrunner.test_x.K.test_y"})
        cmd, _z, _v = z.befehl(["app.tests.longrunner.test_x.K.test_y"],
                               sys.executable)
        self.assertIn("--tag=longrunner", cmd)

    def test_doppelte_nur_einmal(self):
        ziele, _ = self.ziele.pruefen(["app.tests.component", "app.tests.component"])
        self.assertEqual(ziele, ["app.tests.component"])

    def test_name_nennt_verworfene(self):
        self.assertEqual(Testziele.name(["a", "b"], 1), "Auswahl: 2 Ziele (1 verworfen)")
        self.assertEqual(Testziele.name(["a"], 0), "Auswahl: 1 Ziel")


class TeststromTests(SimpleTestCase):
    u"""Der Ereignisstrom - an einem Kunst-Prozess, nicht an echten Tests.

    Gefahren wird ein Python-Einzeiler, der die Ausgabe von ``manage.py test``
    nachstellt. Damit ist der Test in Millisekunden durch und prueft trotzdem
    den ganzen Weg: Popen, Zeilen lesen, Ereignisse bilden, Abschluss.
    """

    def _strom(self, ausgabe):
        code = "\n".join("print(%r)" % z for z in ausgabe)
        saetze = list(Teststrom().fahren([sys.executable, "-c", code], "Probe"))
        return [json.loads(s) for s in saetze]

    def test_ereignisfolge(self):
        ereignisse = self._strom(["System check identified no issues (0 silenced).",
                                  "test_x (a.b.C.test_x) ... ok",
                                  "test_y (a.b.C.test_y) ... FAIL",
                                  "Ran 2 tests in 0.1s"])
        arten = [e["type"] for e in ereignisse]
        self.assertEqual(arten[0], "start")
        self.assertEqual(arten[-1], "summary")
        fortschritt = [e for e in ereignisse if e["type"] == "progress"]
        self.assertEqual([(e["id"], e["status"]) for e in fortschritt],
                         [("a.b.C.test_x", "pass"), ("a.b.C.test_y", "fail")])
        schluss = ereignisse[-1]
        self.assertEqual((schluss["total"], schluss["passed"], schluss["failed"]),
                         (2, 1, 1))
        self.assertTrue(schluss["ok"])          # der Kunst-Prozess endet mit 0

    def test_sonstige_zeilen_kommen_als_log(self):
        ereignisse = self._strom(["Creating test database for alias 'default'..."])
        logs = [e["line"] for e in ereignisse if e["type"] == "log"]
        self.assertIn("Creating test database for alias 'default'...", logs)

    def test_kommando_startet_nicht(self):
        u"""Kein gueltiges Programm: ein `error`-Satz, keine Ausnahme."""
        ereignisse = [json.loads(s) for s in
                      Teststrom().fahren(["gibt-es-nicht-hoffentlich"], "Probe")]
        self.assertEqual(ereignisse[-1]["type"], "error")


class LaufsperreTests(SimpleTestCase):
    u"""EIN Lauf zur Zeit — serverseitig, nicht im Browser.

    Die erste Fassung sperrte nur die Knoepfe in ``tests_strom.js``: Ein zweiter
    Tab wusste davon nichts und startete einen zweiten Lauf auf derselben
    Testdatenbank.
    """

    def setUp(self):
        # Im Projekt, nicht in System-Temp (harte Vorgabe).
        self.pfad = (Path(__file__).resolve().parents[3]
                     / ".pruef_laufsperre.lock")
        self.pfad.unlink(missing_ok=True)

    def tearDown(self):
        self.pfad.unlink(missing_ok=True)

    def test_zweiter_wird_abgewiesen(self):
        erster = Laufsperre(self.pfad)
        self.assertTrue(erster.belegen("A")[0])
        frei, grund = Laufsperre(self.pfad).belegen("B")
        self.assertFalse(frei)
        self.assertIn("läuft schon", grund)
        erster.freigeben()
        self.assertTrue(Laufsperre(self.pfad).belegen("B")[0])

    def test_sperre_eines_toten_servers_wird_uebernommen(self):
        u"""Nach einem harten Server-Ende bleibt die Datei liegen."""
        self.pfad.write_text(json.dumps(
            {"name": "Geist", "seit": time.time(), "server_pid": 999999}),
            encoding="utf-8")
        self.assertIsNone(Laufsperre(self.pfad).zustand())
        self.assertTrue(Laufsperre(self.pfad).belegen("Neu")[0])

    def test_alte_sperre_verfaellt(self):
        self.pfad.write_text(json.dumps(
            {"name": "Alt", "seit": time.time() - Laufsperre.FRIST - 10,
             "server_pid": os.getpid()}), encoding="utf-8")
        self.assertIsNone(Laufsperre(self.pfad).zustand())

    def test_lebt_erkennt_beendete_prozesse(self):
        u"""Windows: OpenProcess allein genuegt nicht (Handle-Zombie)."""
        self.assertTrue(Laufsperre.lebt(os.getpid()))
        self.assertFalse(Laufsperre.lebt(999999))
        self.assertFalse(Laufsperre.lebt(0))


class ToeterTests(SimpleTestCase):
    u"""Der ganze Baum muss weg - ein Testlauf hat Kinder."""

    def test_kind_stirbt_mit(self):
        code = "\n".join([
            "import subprocess, sys, time",
            "k = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)'])",
            "print(k.pid, flush=True)",
            "time.sleep(60)",
        ])
        eltern = subprocess.Popen([sys.executable, "-c", code],
                                  stdout=subprocess.PIPE, text=True)
        kind = int(eltern.stdout.readline().strip())
        self.assertTrue(Laufsperre.lebt(kind))
        Toeter.prozess(eltern)
        # Kurz warten: `taskkill /T` arbeitet nebenlaeufig.
        for _ in range(40):
            if not Laufsperre.lebt(kind):
                break
            time.sleep(0.25)
        self.assertFalse(Laufsperre.lebt(kind),
                         "Kindprozess hat den Toeter ueberlebt")
        self.assertIsNotNone(eltern.poll())


class NotbremseTests(SimpleTestCase):
    u"""Ein Lauf, der haengt und nichts ausgibt, muss trotzdem enden.

    Der Fall, den das ``finally`` NICHT abdeckt: ``readline()`` blockiert, also
    kommt der Generator nie zum naechsten ``yield`` und merkt weder Frist noch
    Verbindungsabbruch.
    """

    def setUp(self):
        self.pfad = (Path(__file__).resolve().parents[3]
                     / ".pruef_notbremse.lock")
        self.pfad.unlink(missing_ok=True)

    def tearDown(self):
        self.pfad.unlink(missing_ok=True)

    def test_frist_beendet_den_haenger(self):
        code = "\n".join([
            "import time",
            "print('test_x (a.b.C.test_x) ... ok', flush=True)",
            "time.sleep(120)",
        ])
        strom = Teststrom(sperre=Laufsperre(self.pfad))
        begonnen = time.monotonic()
        saetze = [json.loads(x) for x in
                  strom.fahren([sys.executable, "-c", code], "Haenger", frist=5)]
        gebraucht = time.monotonic() - begonnen
        self.assertLess(gebraucht, 60, "Notbremse hat nicht gegriffen")
        arten = [s["type"] for s in saetze]
        self.assertIn("progress", arten)          # die eine Zeile kam an
        self.assertIn("error", arten)             # Frist gemeldet
        self.assertEqual(arten[-1], "summary")
        # Und die Sperre ist wieder frei, sonst blockiert sie eine Stunde.
        self.assertFalse(self.pfad.exists())
