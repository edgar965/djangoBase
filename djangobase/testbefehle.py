# -*- coding: utf-8 -*-
u"""Testbefehle - die Eintraege fuer Hilfe -> Tests aus der Platte ableiten.

    Kriterium 17: Untermenues fuer Unit-, Component-, UI-Tests und Longrunner;
    bei grossen Projekten mehrere Gruppen (Bereich x Art).

WARUM ERZEUGT STATT GEPFLEGT
============================
Von Hand gepflegte ``test_befehle`` veralten sofort: Ein neuer Bereich bekommt
Tests, aber keinen Eintrag - und was man nicht per Knopf starten kann, faehrt
man selten. Diese Klasse liest stattdessen nach, was da IST, und baut die Liste
daraus. Ein neuer Ordner ``tests/unit`` erscheint beim naechsten Seitenaufruf.

Und sie traegt nur ein, was auch laeuft: ``manage.py test app.tests.unit``
scheitert, wenn es das Modul nicht gibt. Deshalb wird jeder Eintrag vorher auf
der Platte geprueft - ein Knopf, der zuverlaessig einen Fehler wirft, ist
schlimmer als kein Knopf.

ZWEI BAUFORMEN, BEIDE ERKANNT
=============================
    app/tests/{unit,component,ui,longrunner}/        nach Art
    app/tests/<bereich>/{unit,component,ui,…}/       Bereich x Art (grosse Apps)

Bei der zweiten entsteht je Bereich eine eigene Gruppe - sonst wird die Seite
eine Liste aus hundert Eintraegen.

Benutzung in ``settings.py``:

    from djangobase.testbefehle import Testbefehle
    DJANGOBASE = {
        ...
        "test_befehle": Testbefehle(BASE_DIR).liste(),
    }
"""
import sys
from pathlib import Path

__all__ = ["Testbefehle"]


class Testbefehle:
    """Baut die Eintraege fuer die Tests-Seite aus dem Dateibestand."""

    #: Reihenfolge = Anzeigereihenfolge: erst schnell, zuletzt langsam.
    #: ``automated`` steht vorn — es ist der Lauf, den man bei JEDER Aenderung
    #: fahren koennen muss (Grundfunktion, Sekunden, kein Netz/GPU).
    ARTEN = ("automated", "unit", "component", "ui", "performance", "longrunner")
    ARTNAMEN = {"automated": "Automated (Grundfunktion)", "unit": "Unit",
                "component": "Component", "ui": "UI",
                "performance": "Performance (Ladezeiten)",
                "longrunner": "Longrunner"}
    #: Ordner, die keine App sind.
    KEINE_APP = {"__pycache__", "static", "templates", "media", "logs", "venv",
                 "pythonVENV", ".venv", "node_modules", ".git", "docs", "tmp",
                 "vendor", "models", "migrations", "fixtures"}

    def __init__(self, basis, python=None, apps=None, verbose=True):
        self.basis = Path(str(basis))
        #: Der Interpreter, der die Tests faehrt - der des laufenden Servers.
        self.python = str(python or sys.executable)
        self._apps = apps
        self.verbose = verbose

    # ------------------------------------------------------------------ Aufbau

    def liste(self):
        """[{'slug','name','cmd','gruppe'}] - alles, was startbar ist."""
        aus = []
        for app in self.apps():
            aus.extend(self._fuer_app(app))
        return aus

    def apps(self):
        """Apps mit einem tests-Verzeichnis (oder eine feste Liste)."""
        if self._apps is not None:
            return [a for a in self._apps if (self.basis / a / "tests").is_dir()]
        aus = []
        for p in sorted(self.basis.iterdir()):
            if not p.is_dir() or p.name in self.KEINE_APP or p.name.startswith("."):
                continue
            if (p / "tests").is_dir() or (p / "tests.py").is_file():
                aus.append(p.name)
        return aus

    def _fuer_app(self, app):
        wurzel = self.basis / app / "tests"
        arten = [a for a in self.ARTEN if self._hat_tests(wurzel / a)]
        bereiche = self._bereiche(wurzel)
        aus = [self._eintrag(app, app, "Alles", app.capitalize())]
        # Bauform 1: app/tests/<art>/
        for art in arten:
            aus.append(self._eintrag(app, "%s.tests.%s" % (app, art),
                                     self.ARTNAMEN[art], app.capitalize()))
        # Bauform 2: app/tests/<bereich>/<art>/ - je Bereich eine Gruppe
        for bereich in bereiche:
            gruppe = "%s · %s" % (app.capitalize(), bereich)
            aus.append(self._eintrag(app, "%s.tests.%s" % (app, bereich),
                                     "Alles", gruppe))
            for art in self.ARTEN:
                if self._hat_tests(wurzel / bereich / art):
                    aus.append(self._eintrag(
                        app, "%s.tests.%s.%s" % (app, bereich, art),
                        self.ARTNAMEN[art], gruppe))
        return aus

    def _eintrag(self, app, ziel, was, gruppe):
        befehl = [self.python, "manage.py", "test", ziel, "--noinput"]
        if self.verbose:
            befehl += ["-v", "2"]
        # Dictionary gewollt: das ist das Eingabeformat von DJANGOBASE["test_befehle"].
        return {"slug": ziel.replace(".", "-"),
                "name": "%s · %s" % (gruppe, was) if gruppe != was else gruppe,
                "gruppe": gruppe, "cmd": befehl}

    # ------------------------------------------------------------------ Platte

    def _bereiche(self, wurzel):
        """Unterordner, die selbst nach Art gegliedert sind (grosse Apps)."""
        if not wurzel.is_dir():
            return []
        aus = []
        for p in sorted(wurzel.iterdir()):
            if not p.is_dir() or p.name in self.ARTEN or p.name in self.KEINE_APP:
                continue
            if any(self._hat_tests(p / a) for a in self.ARTEN) or self._hat_tests(p):
                aus.append(p.name)
        return aus

    @staticmethod
    def _hat_tests(ordner):
        """Liegt dort mindestens eine Testdatei? (sonst wirft der Befehl)"""
        if not ordner.is_dir():
            return False
        return any(p.name.startswith("test_") and p.suffix == ".py"
                   for p in ordner.rglob("test_*.py"))
