"""Hilfe -> Tests: Test-Übersicht mit Tabs nach Typ.

- ``test_befehle``  – ganze Suiten als Batch-Kommandos. An erster Stelle steht der
  Reiter „Alle": ein Knopf je Kategorie (Automated, Unit, Component, UI,
  Performance, Longrunner), der ALLE Tests dieser Art in EINEM Lauf fährt, plus
  einen für das ganze Projekt. Darunter Unter-Reiter je Kategorie mit den
  einzelnen Bereichen. Die Kategorien werden aus den Einträgen ABGELEITET (Art
  notfalls aus dem Kommando gelesen), damit der Reiter auch in den Projekten
  steht, die ihre ``test_befehle`` von Hand pflegen.
- ``test_discover`` – Einzeltest-Discovery pro Typ (Tabs Unit/Component/…), jeder
  Test einzeln per ``manage.py test <id>`` ausführbar.
- ``test_ui``       – Browser-/UI-Tests, laufen client-seitig (Iframe), Liste kommt
  aus der testcases.js; siehe Template.

Sicherheit: Es werden NUR bekannte (entdeckte) Test-IDs bzw. konfigurierte Befehle
ausgeführt – keine beliebigen Labels aus der Query.
"""
import re
import subprocess
import sys
import time
import unittest

from django.conf import settings
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..testbefehle import Testbefehle

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

#: Die Test-Arten und ihre Namen stehen an EINER Stelle (Testbefehle) - die
#: Seite leiht sie sich, statt eine zweite Liste zu fuehren, die auseinanderlaeuft.
ARTEN = Testbefehle.ARTEN
ARTNAMEN = Testbefehle.ARTNAMEN
KURZ = Testbefehle.KURZ


def _discover_ids(label):
    """Einzelne Test-IDs unter einem Label (z. B. 'tests.unit') ermitteln.

    Nutzt Djangos DiscoverRunner.build_suite – findet (rekursiv) alle test_*.py
    unter dem Label, anders als unittest.loadTestsFromName (das Pakete nicht aufklappt).
    """
    try:
        from django.test.runner import DiscoverRunner
        suite = DiscoverRunner(verbosity=0).build_suite([label])
    except Exception:  # noqa: BLE001  – Label fehlt/Import-Fehler -> einfach leer
        return []
    ids = []

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                tid = t.id()
                if "ModuleImportFailure" in tid or "LoadTestsFailure" in tid \
                        or tid.endswith("_FailedTest"):
                    continue
                ids.append(tid)

    walk(suite)
    return ids


def _kurz(test_id):
    """tests.unit.test_geo.GeoTest.test_distanz -> GeoTest.test_distanz"""
    teile = test_id.split(".")
    return ".".join(teile[-2:]) if len(teile) >= 2 else test_id


class TestsView(ZugriffMixin, View):
    """Hilfe -> Tests. Der Reiter „Alle" wird in JEDEM Projekt gebaut."""

    #: Wie lange ein Sammellauf hoechstens dauern darf. Der Einzellauf begnuegt
    #: sich mit den 10 Minuten aus ``_run``; „Alles" kann laenger brauchen, und
    #: ein Abbruch nach Zeitablauf sieht auf der Seite aus wie ein Fehlschlag.
    SAMMEL_FRIST = 3600
    #: Optionen von ``manage.py test``, auf die ein WERT folgt - deren Wert ist
    #: kein Test-Label (``-v 2`` waere sonst das Label „2").
    WERT_OPTIONEN = {"-v", "--verbosity", "--settings", "--pythonpath", "-t",
                     "--top-level-directory", "--testrunner", "--tag",
                     "--exclude-tag", "--parallel", "-k", "--shuffle",
                     "--durations", "--pdb"}

    # ------------------------------------------------------- Reiter „Alle"

    @classmethod
    def _kategorien_alle(cls, befehle):
        """Der Reiter „Alle": je Kategorie ein Sammelknopf + seine Einzel-Suiten.

        WIRD ABGELEITET, NICHT VORAUSGESETZT (Korrektur 17.08.2026): Die erste
        Fassung erwartete fertige Sammel-Eintraege aus
        ``djangobase.testbefehle.Testbefehle``. Damit hatten ihn genau die
        Projekte NICHT, die ihre ``test_befehle`` von Hand pflegen — WalkHop,
        NoiseSpy, HumanBodyWeb, shortlongx. Jetzt liest die Seite Art und Ziel
        notfalls aus dem Kommando (``manage.py test app.tests.unit`` -> „unit"),
        und der Reiter steht ueberall.

        Zurueck kommt ``(alles, arten, rest)``: der Eintrag fuer das ganze
        Projekt, die Unter-Reiter, und die Liste fuer den Suiten-Reiter."""
        if not befehle:
            return None, [], befehle
        angereichert, nach_art, ohne_art = [], {}, []
        for b in befehle:
            # Dictionary gewollt: angereicherte Kopie, das Original bleibt heil.
            e = dict(b)
            e["ziel"] = b.get("ziel") or " ".join(cls._ziele(b.get("cmd")))
            e["art"] = b.get("art") or cls._art(e["ziel"])
            angereichert.append(e)
            if e["art"]:
                nach_art.setdefault(e["art"], []).append(e)
            else:
                ohne_art.append(e)
        python = cls._python(befehle)
        alles = cls._sammel(python, "alles", "Alles — jede Art, jede App", [])
        arten = []
        for art in ARTEN:
            dabei = nach_art.get(art) or []
            if not dabei:
                continue
            ziele = [z for e in dabei for z in (e["ziel"] or "").split() if z]
            arten.append({"art": art, "kurz": KURZ.get(art, art.capitalize()),
                          "sammel": cls._sammel(python, art,
                                                "Alle %s" % ARTNAMEN.get(art, art),
                                                ziele),
                          "befehle": dabei})
        if ohne_art:
            arten.append({"art": "apps", "kurz": "Nach App", "sammel": None,
                          "befehle": ohne_art})
        return alles, arten, angereichert

    @classmethod
    def _sammel(cls, python, art, name, ziele):
        """Ein Sammelbefehl - alle Ziele einer Art in EINEM Lauf.

        Ein Lauf statt sechs heisst auch: die Testdatenbank wird einmal
        aufgebaut, nicht sechsmal."""
        # Dictionary gewollt: dasselbe Format wie DJANGOBASE["test_befehle"],
        # damit ``get()`` es ohne Sonderweg ausfuehren kann.
        return {"slug": "sammel-" + art, "name": name, "art": art,
                "ziel": " ".join(ziele), "anzahl": len(ziele),
                "frist": cls.SAMMEL_FRIST,
                "cmd": [python, "manage.py", "test"] + list(ziele)
                       + ["--noinput", "-v", "2"]}

    @classmethod
    def _sammelbefehle(cls, alles, arten):
        """Alle abgeleiteten Eintraege - fuer die Ausfuehrung per ``?run=``."""
        aus = [alles] if alles else []
        return aus + [a["sammel"] for a in arten if a.get("sammel")]

    @staticmethod
    def _python(befehle):
        """Der Interpreter, mit dem das Projekt seine Tests faehrt.

        Aus den vorhandenen Eintraegen genommen, nicht geraten: In mehreren
        Projekten steht dort ein fester venv-Pfad, und ``sys.executable`` ist
        beim Server ein anderer."""
        for b in befehle:
            cmd = b.get("cmd") or []
            if cmd and str(cmd[0]).lower() not in ("python", "python3"):
                return str(cmd[0])
        return sys.executable

    @classmethod
    def _ziele(cls, cmd):
        """Die Test-Labels eines Kommandos (alles nach ``test``, ohne Optionen)."""
        toks = [str(t) for t in (cmd or [])]
        if "test" not in toks:
            return []
        aus, vorher = [], ""
        for t in toks[toks.index("test") + 1:]:
            if t.startswith("-"):
                vorher = t
                continue
            if vorher in cls.WERT_OPTIONEN:     # der Wert der Option, kein Label
                vorher = ""
                continue
            vorher = ""
            aus.append(t)
        return aus

    @staticmethod
    def _art(ziel):
        """„search.tests.chat.unit" -> „unit"; „tracker" -> None."""
        for teil in re.split(r"[.\\/\s]+", ziel or ""):
            if teil in ARTEN:
                return teil
        return None

    @staticmethod
    def _gruppen(befehle):
        """Suiten nach ``gruppe`` buendeln - Reihenfolge wie eingetragen.

        Eintraege OHNE ``gruppe`` landen zusammen unter „Test-Suiten (Batch)":
        Projekte, die ihre Liste von Hand pflegen, sehen die Seite damit
        unveraendert. Wer ``djangobase.testbefehle.Testbefehle`` benutzt,
        bekommt je Bereich eine eigene Karte (Kriterium 17: keine flache Liste
        aus hundert Eintraegen)."""
        aus, nach_name = [], {}
        for b in befehle:
            name = b.get("gruppe") or "Test-Suiten (Batch)"
            if name not in nach_name:
                # Dictionary gewollt: geht unveraendert in die Vorlage.
                nach_name[name] = {"name": name, "befehle": []}
                aus.append(nach_name[name])
            nach_name[name]["befehle"].append(b)
        return aus

    def get(self, request):
        c = conf()
        befehle = c.get("test_befehle", []) or []
        discover = c.get("test_discover", []) or []
        ui = c.get("test_ui") or None

        # Kategorien (Tabs) mit ihren Einzeltests aufbauen
        kategorien = []
        bekannte_ids = set()
        for d in discover:
            tests = []
            for label in d.get("labels", []):
                for tid in _discover_ids(label):
                    tests.append({"id": tid, "kurz": _kurz(tid)})
                    bekannte_ids.add(tid)
            tests.sort(key=lambda t: t["id"])
            kategorien.append({"typ": d.get("typ", "Tests"), "tests": tests,
                               "anzahl": len(tests)})

        alles, alle_arten, suiten = self._kategorien_alle(befehle)

        slug = request.GET.get("run")
        ergebnis = None
        if slug:
            # Die abgeleiteten Sammelbefehle sind aus den konfigurierten
            # Eintraegen gebaut, nicht aus der Query - deshalb ebenso sicher.
            # Eigene Eintraege haben Vorrang, falls ein Projekt denselben slug fuehrt.
            kandidaten = list(befehle) + self._sammelbefehle(alles, alle_arten)
            b = next((x for x in kandidaten if x.get("slug") == slug), None)
            if b:
                ergebnis = self._run(b["cmd"], b.get("name", slug), b.get("frist"))
            elif slug in bekannte_ids:                      # einzelner Test (nur bekannte IDs)
                cmd = [sys.executable, "manage.py", "test", slug, "--noinput", "-v", "2"]
                ergebnis = self._run(cmd, _kurz(slug))

        return render(request, "djangobase/hilfe/tests.html", {
            "aktiv": "tests",
            "befehle": befehle,
            "alles": alles,
            "alle_arten": alle_arten,
            "suiten": suiten,
            "suiten_gruppen": self._gruppen(suiten),
            "kategorien": kategorien,
            "ui": ui,
            "ergebnis": ergebnis,
            "aktiver_slug": slug,
            "aktiver_tab": request.GET.get("tab", ""),
            "aktiver_unter": request.GET.get("unter", ""),
        })

    def _run(self, cmd, name, frist=None):
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=int(frist or 600),
                               encoding="utf-8", errors="replace",
                               cwd=str(settings.BASE_DIR), creationflags=_NO_WINDOW)
            out, err, rc = r.stdout or "", r.stderr or "", r.returncode
        except Exception as exc:  # noqa: BLE001
            out, err, rc = "", str(exc), -1
        return {
            "name": name,
            "cmd": " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd),
            "rc": rc, "ok": rc == 0,
            "out": out[-40000:], "err": err[-40000:],
            "dauer": round(time.time() - t0, 1),
        }
