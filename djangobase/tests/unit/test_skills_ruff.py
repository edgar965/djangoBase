# -*- coding: utf-8 -*-
"""ruff als Werkzeug — Linter und Formatierer unter einem Knopf.

DIE ANSAGE (Edgar, 18.09.2026)
==============================
    „mach das in djangoBase" — nach der Frage, ob der Prüflauf aus
    gunSlinger (ruff, mypy, Suite, Strukturregeln) auch hier Sinn hat.
    Drei davon gab es schon; ruff fehlte.

WAS HIER GEPRÜFT WIRD
=====================
Nicht, ob ruff richtig misst — das tut ruff selbst. Sondern, ob das
Werkzeug die Antworten richtig einordnet: Gewicht je Regel, die
Ausnahme für Befunde, die ein anderes Werkzeug führt, die Wahl der
Regelquelle (Projekt vor Vorgabe) und der ehrliche dritte Zustand,
wenn ruff fehlt.

BDD - GEGEBEN / DANN
====================
    EinUndefinierterName        ... ist ein Fehler, mit Zeile und Code
    EinSyntaxfehler             ... ist ein Fehler, auch ohne Regelcode
    DieZielversion              ... ist die des laufenden Interpreters
    EineUngeformteDatei         ... ist ein Hinweis von `ruff format`
    EineUnbenutzteEinfuhr       ... wird gezählt, nicht gelistet
    EinProjektMitEigenenRegeln  ... schlägt die Vorgabe
    DieVorgabe                  ... liegt im Paket und ist gültiges TOML
    DerEigeneAnlassfall         ... wird gefunden
    RuffFehlt                   ... ist ein Fehler, kein leeres Grün
"""

import importlib.util
import unittest
from unittest import mock

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund
from djangobase.skills.ruffbefunde import RuffBefunde

from ..base import BasisTest
from .test_neue_werkzeuge import WerkzeugBasis

#: Drei Zustaende statt zwei (siehe test_skills_codequalitaet.py): Fehlt
#: ruff in der Umgebung, sagt ein uebersprungener Fall die Wahrheit —
#: ein roter luegt.
BRAUCHT_RUFF = unittest.skipIf(
    importlib.util.find_spec("ruff") is None, "ruff ist nicht installiert — siehe Extra „codequalitaet“"
)

KAPUTT = "import os\n\n\ndef lesen(pfad):\n    return offen(pfad).read()\n"
GEFORMT = "def lesen(pfad):\n    return open(pfad).read()\n"
KRUMM = "x = {'a':1,'b':2}\n"


class DasWerkzeugIstAngemeldet(BasisTest):
    def test_es_ist_ueber_den_slug_zu_finden(self):
        self.assertIsInstance(werkzeug_finden("ruff"), RuffBefunde)

    def test_es_steht_direkt_hinter_code_qualitaet(self):
        """Dasselbe Prinzip (Standardwerkzeuge statt eigener Messung) —
        deshalb nebeneinander."""
        from djangobase.skills import werkzeuge

        slugs = [w.slug for w in werkzeuge()]
        self.assertEqual(slugs.index("ruff"), slugs.index("code-qualitaet") + 1)


@BRAUCHT_RUFF
class EinUndefinierterName(WerkzeugBasis):
    """Gegeben: ``offen(pfad)`` — den Namen gibt es nicht."""

    def test_er_ist_ein_fehler_mit_zeile_und_code(self):
        zeilen = self.projekt({"a.py": KAPUTT}).fahren(RuffBefunde)
        fehler = [z for z in zeilen if z["schwere"] == Befund.FEHLER]
        self.assertEqual(len(fehler), 1, zeilen)
        self.assertEqual(fehler[0]["ort"], "a.py:5")
        self.assertIn("F821", fehler[0]["befund"])
        self.assertIn("offen", fehler[0]["befund"])

    def test_die_schwersten_stehen_oben(self):
        zeilen = self.projekt({"a.py": KAPUTT, "b.py": KRUMM}).fahren(RuffBefunde)
        self.assertEqual(zeilen[0]["schwere"], Befund.FEHLER, zeilen)
        self.assertEqual(zeilen[-1]["schwere"], Befund.HINWEIS, zeilen)


@BRAUCHT_RUFF
class EinSyntaxfehler(WerkzeugBasis):
    """Gegeben: ``def (:`` — die Datei läuft gar nicht.

    ruff meldet das ohne Regelcode (``invalid-syntax``); ein Werkzeug, das
    nur nach Codes gewichtet, hätte daraus eine Warnung gemacht.
    """

    def test_er_ist_ein_fehler(self):
        zeilen = self.projekt({"kaputt.py": "def (:\n"}).fahren(RuffBefunde)
        fehler = [z for z in zeilen if z["schwere"] == Befund.FEHLER]
        self.assertTrue(fehler, zeilen)
        self.assertEqual(fehler[0]["befund"], "Syntaxfehler")
        self.assertTrue(fehler[0]["ort"].startswith("kaputt.py:1"), fehler)


class DieZielversion(WerkzeugBasis):
    """Gegeben: die Vorgabe kennt keine Zielversion.

    DER FEHLALARM (18.09.2026): Mit festem ``py310`` meldete ruff im
    assistant (Python 3.14) 58 „Syntaxfehler" — Zeilenumbrüche in
    f-Strings, die es seit 3.12 gibt. Das Werkzeug läuft im Interpreter des
    Projekts; dessen Version ist die richtige.
    """

    def _befehle(self, dateien):
        """Die Befehlszeilen, die das Werkzeug absetzen würde."""
        import subprocess

        werkzeug = RuffBefunde()
        projekt = self.projekt(dateien)
        from ..wegwerfordner import Wegwerfordner

        Wegwerfordner.ansetzen(werkzeug, projekt.ordner)
        befehle = []

        def attrappe(befehl, **_rest):
            befehle.append(befehl)
            return subprocess.CompletedProcess(befehl, 0, "[]", "")

        with (
            mock.patch("djangobase.skills.ruffbefunde.subprocess.run", side_effect=attrappe),
            mock.patch("djangobase.skills.ruffbefunde.importlib.util.find_spec", return_value=object()),
        ):
            werkzeug.laufen()
        return befehle

    def test_mit_der_vorgabe_wird_sie_uebergeben(self):
        import sys

        erwartet = "py%d%d" % sys.version_info[:2]
        for befehl in self._befehle({"a.py": GEFORMT}):
            self.assertIn("--target-version", befehl)
            self.assertEqual(befehl[befehl.index("--target-version") + 1], erwartet)
            self.assertIn("--config", befehl)

    def test_mit_eigenen_regeln_bleibt_es_bei_denen(self):
        """Ein Projekt darf bewusst älter zielen — dann keine Übersteuerung."""
        befehle = self._befehle({"a.py": GEFORMT, "ruff.toml": "line-length = 100\n"})
        self.assertTrue(befehle)
        for befehl in befehle:
            self.assertNotIn("--target-version", befehl)
            self.assertNotIn("--config", befehl)

    def test_ein_ruff_das_die_version_nicht_kennt_laeuft_ohne_sie(self):
        import subprocess

        werkzeug = RuffBefunde()
        projekt = self.projekt({"a.py": GEFORMT})
        from ..wegwerfordner import Wegwerfordner

        Wegwerfordner.ansetzen(werkzeug, projekt.ordner)
        befehle = []

        def attrappe(befehl, **_rest):
            befehle.append(befehl)
            if "--target-version" in befehl:
                return subprocess.CompletedProcess(
                    befehl, 2, "", "error: invalid value 'py399' for '--target-version'"
                )
            return subprocess.CompletedProcess(befehl, 0, "[]", "")

        with (
            mock.patch("djangobase.skills.ruffbefunde.subprocess.run", side_effect=attrappe),
            mock.patch("djangobase.skills.ruffbefunde.importlib.util.find_spec", return_value=object()),
        ):
            ergebnis = werkzeug.laufen()
        self.assertEqual(ergebnis.hinweis, "")
        self.assertNotIn("--target-version", befehle[-1])


@BRAUCHT_RUFF
class EineUngeformteDatei(WerkzeugBasis):
    """Gegeben: einfache Anführungszeichen, kein Leerraum nach dem Komma."""

    def test_sie_ist_ein_hinweis_von_ruff_format(self):
        zeilen = self.projekt({"krumm.py": KRUMM}).fahren(RuffBefunde)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertEqual(zeilen[0]["schwere"], Befund.HINWEIS)
        self.assertEqual(zeilen[0]["ort"], "krumm.py")
        self.assertIn("ruff format", zeilen[0]["befund"])

    def test_eine_geformte_datei_ist_kein_befund(self):
        self.assertEqual(self.projekt({"gut.py": GEFORMT}).fahren(RuffBefunde), [])

    def test_im_leeren_findet_es_nichts(self):
        self.assertEqual(self.projekt({}).fahren(RuffBefunde), [])


@BRAUCHT_RUFF
class EineUnbenutzteEinfuhr(WerkzeugBasis):
    """Gegeben: ``import os`` ohne Verwendung — das führt `tote-importe`."""

    def test_sie_wird_gezaehlt_nicht_gelistet(self):
        werkzeug = RuffBefunde()
        projekt = self.projekt({"a.py": "import os\n"})
        from ..wegwerfordner import Wegwerfordner

        ergebnis = Wegwerfordner.ansetzen(werkzeug, projekt.ordner).laufen()
        self.assertEqual(ergebnis.zeilen, [])
        self.assertIn("1× F401 → tote-importe", ergebnis.zusammenfassung)

    def test_in_einer_fassade_ist_sie_gar_keiner(self):
        """``__init__.py`` führt Namen ein, damit andere sie importieren —
        die Vorgabe nimmt F401 dort aus."""
        werkzeug = RuffBefunde()
        projekt = self.projekt({"paket/__init__.py": "from os import path\n"})
        from ..wegwerfordner import Wegwerfordner

        ergebnis = Wegwerfordner.ansetzen(werkzeug, projekt.ordner).laufen()
        self.assertEqual(ergebnis.zeilen, [])
        self.assertNotIn("F401", ergebnis.zusammenfassung)


@BRAUCHT_RUFF
class EinProjektMitEigenenRegeln(WerkzeugBasis):
    """Gegeben: eine ``ruff.toml`` im Projekt, die F821 abschaltet.

    Die Gegenprobe steht in ``EinUndefinierterName``: Ohne die Datei ist
    derselbe Code ein Fehler. Verschwindet er MIT ihr, hat die Datei des
    Projekts gegriffen — und nicht die Vorgabe.
    """

    def test_sie_schlaegt_die_vorgabe(self):
        werkzeug = RuffBefunde()
        projekt = self.projekt({"a.py": KAPUTT, "ruff.toml": '[lint]\nignore = ["F821", "F401"]\n'})
        from ..wegwerfordner import Wegwerfordner

        ergebnis = Wegwerfordner.ansetzen(werkzeug, projekt.ordner).laufen()
        self.assertEqual(ergebnis.zeilen, [], ergebnis.zeilen)
        self.assertIn("Regeln: ruff.toml des Projekts", ergebnis.zusammenfassung)

    def test_auch_ueber_pyproject(self):
        werkzeug = RuffBefunde()
        projekt = self.projekt(
            {"a.py": KAPUTT, "pyproject.toml": '[tool.ruff.lint]\nignore = ["F821", "F401"]\n'}
        )
        from ..wegwerfordner import Wegwerfordner

        ergebnis = Wegwerfordner.ansetzen(werkzeug, projekt.ordner).laufen()
        self.assertEqual(ergebnis.zeilen, [], ergebnis.zeilen)
        self.assertIn("pyproject.toml des Projekts", ergebnis.zusammenfassung)

    def test_ein_pyproject_ohne_ruff_abschnitt_zaehlt_nicht(self):
        werkzeug = RuffBefunde()
        projekt = self.projekt({"a.py": KAPUTT, "pyproject.toml": '[project]\nname = "x"\n'})
        from ..wegwerfordner import Wegwerfordner

        ergebnis = Wegwerfordner.ansetzen(werkzeug, projekt.ordner).laufen()
        self.assertEqual(len(ergebnis.zeilen), 1, ergebnis.zeilen)
        self.assertIn("djangoBase-Vorgabe", ergebnis.zusammenfassung)


class DieVorgabe(BasisTest):
    """Gegeben: ``djangobase/ruff_vorgabe.toml`` — die Regeln für alle ohne eigene."""

    def test_sie_liegt_im_paket(self):
        self.assertTrue(RuffBefunde.VORGABE.is_file(), RuffBefunde.VORGABE)
        self.assertEqual(RuffBefunde.VORGABE.parent.name, "djangobase")

    def test_sie_ist_gueltiges_toml_mit_den_fuenf_regelfamilien(self):
        try:
            import tomllib
        except ImportError:  # Python 3.10
            self.skipTest("tomllib gibt es erst ab Python 3.11")
        daten = tomllib.loads(RuffBefunde.VORGABE.read_text(encoding="utf-8"))
        self.assertEqual(daten["line-length"], 110)
        for familie in ("E", "F", "I", "B", "UP"):
            self.assertIn(familie, daten["lint"]["select"])

    def test_sie_wird_mit_dem_paket_ausgeliefert(self):
        """Sonst fehlt sie bei ``pip install`` ohne ``-e``."""
        from pathlib import Path

        pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
        self.assertIn('"ruff_vorgabe.toml"', pyproject.read_text(encoding="utf-8"))


@BRAUCHT_RUFF
class DerEigeneAnlassfall(WerkzeugBasis):
    """Gegeben: Der Fall, den das Werkzeug bei sich trägt."""

    def test_er_wird_gefunden(self):
        fall = RuffBefunde.anlassfall
        zeilen = self.projekt(fall.dateien).fahren(RuffBefunde)
        self.assertEqual(fall.urteil(zeilen), "", zeilen)


class RuffFehlt(WerkzeugBasis):
    """Gegeben: ruff ist in der Umgebung nicht installiert.

    Dann ist das Ergebnis ein FEHLER mit dem Installationshinweis — nicht
    eine leere Tabelle, die aussieht wie ein sauberes Projekt.
    """

    def test_das_ergebnis_nennt_den_grund(self):
        werkzeug = RuffBefunde()
        projekt = self.projekt({"a.py": KAPUTT})
        from ..wegwerfordner import Wegwerfordner

        Wegwerfordner.ansetzen(werkzeug, projekt.ordner)
        with mock.patch("djangobase.skills.ruffbefunde.importlib.util.find_spec", return_value=None):
            ergebnis = werkzeug.laufen()
        self.assertEqual(ergebnis.zeilen, [])
        self.assertIn("FEHLER", ergebnis.hinweis)
        self.assertIn("pip install ruff", ergebnis.hinweis)

    def test_der_anlassfall_check_meldet_ihn_als_grund_nicht_als_blind(self):
        """Vorher hiess das „blind: 0 statt 2" — der Grund stand nirgends."""
        from djangobase.skills.anlassfall_check import Probelauf

        projekt = self.projekt(RuffBefunde.anlassfall.dateien)
        with mock.patch("djangobase.skills.ruffbefunde.importlib.util.find_spec", return_value=None):
            lauf = Probelauf(RuffBefunde, projekt.ordner).fahren()
        self.assertIn("ruff ist nicht installiert", lauf.fehler)
