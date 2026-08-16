"""Hilfe -> Tests: Test-Übersicht mit Tabs nach Typ.

- ``test_befehle``  – ganze Suiten als Batch-Kommandos (Tab „Suiten").
- ``test_discover`` – Einzeltest-Discovery pro Typ (Tabs Unit/Component/…), jeder
  Test einzeln per ``manage.py test <id>`` ausführbar.
- ``test_ui``       – Browser-/UI-Tests, laufen client-seitig (Iframe), Liste kommt
  aus der testcases.js; siehe Template.

Sicherheit: Es werden NUR bekannte (entdeckte) Test-IDs bzw. konfigurierte Befehle
ausgeführt – keine beliebigen Labels aus der Query.
"""
import subprocess
import sys
import time
import unittest

from django.conf import settings
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


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

        slug = request.GET.get("run")
        ergebnis = None
        if slug:
            b = next((x for x in befehle if x.get("slug") == slug), None)
            if b:
                ergebnis = self._run(b["cmd"], b.get("name", slug))
            elif slug in bekannte_ids:                      # einzelner Test (nur bekannte IDs)
                cmd = [sys.executable, "manage.py", "test", slug, "--noinput", "-v", "2"]
                ergebnis = self._run(cmd, _kurz(slug))

        return render(request, "djangobase/hilfe/tests.html", {
            "aktiv": "tests",
            "befehle": befehle,
            "suiten_gruppen": self._gruppen(befehle),
            "kategorien": kategorien,
            "ui": ui,
            "ergebnis": ergebnis,
            "aktiver_slug": slug,
            "aktiver_tab": request.GET.get("tab", ""),
        })

    def _run(self, cmd, name):
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
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
