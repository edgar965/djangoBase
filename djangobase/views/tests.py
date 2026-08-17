"""Hilfe -> Tests: Test-Übersicht mit Tabs nach Typ.

- ``test_befehle``  – ganze Suiten als Batch-Kommandos. An erster Stelle steht der
  Reiter „Alle": ein Knopf je Kategorie (Automated, Unit, Component, UI,
  Performance, Longrunner), der ALLE Tests dieser Art in EINEM Lauf fährt, plus
  einen für das ganze Projekt. Darunter Unter-Reiter je Kategorie mit den
  einzelnen Bereichen.
- ``test_discover`` – Einzeltest-Discovery pro Typ (Tabs Unit/Component/…), jeder
  Test einzeln per ``manage.py test <id>`` ausführbar. Fehlt der Schlüssel, wird
  er aus denselben ``test_befehle`` abgeleitet.
- ``test_ui``       – Browser-/UI-Tests, laufen client-seitig (Iframe), Liste kommt
  aus der testcases.js; siehe Template.

Sicherheit: Es werden NUR bekannte (entdeckte) Test-IDs bzw. konfigurierte Befehle
ausgeführt – keine beliebigen Labels aus der Query.

DREI AUFGABEN, DREI DATEIEN (17.08.2026)
========================================
Diese Datei war auf 399 Zeilen gewachsen, weil sie Herleitung, Ausführung und
Darstellung zugleich trug. Jetzt:

    testkategorien.Kategorien   was sich aus ``test_befehle`` ableiten lässt
    testlauf.Testlauf           Kommando fahren + Laufzeiten festhalten
    testtabelle.Testtabelle     EINE Tabelle für alle Testcase-Listen
"""
import logging
import unittest

from django.shortcuts import render
from django.urls import reverse
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..testbefehle import Testbefehle
from ..testhistorie import Testhistorie
from ..testkategorien import Kategorien
from ..testlauf import Testlauf
from ..testtabelle import Testtabelle

log = logging.getLogger("django")


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

    #: So lange gilt eine einmal ermittelte Testliste. Die Discovery importiert
    #: jedes Testmodul; bei dreissig Labels kostet das mehrere Sekunden, und die
    #: Liste aendert sich nur, wenn jemand eine Testdatei anlegt.
    DISCOVER_FRIST = 600

    @classmethod
    def _ids_gecacht(cls, label):
        u"""Test-IDs eines Labels, kurz zwischengespeichert.

        Ohne den Zwischenspeicher laedt JEDER Aufruf von /hilfe/tests/ alle
        Testmodule neu — im Projekt assistant sind das ueber dreissig Labels.
        Der Cache liegt in Djangos Cache-Rahmen (Vorgabe: im Speicher des
        Prozesses), nicht in einer Modulvariablen: veraenderlicher Zustand auf
        Modulebene gilt fuer ALLE Anfragen gleichzeitig.
        """
        from django.core.cache import cache
        schluessel = "djangobase:testids:%s" % label
        ids = cache.get(schluessel)
        if ids is None:
            ids = _discover_ids(label)
            cache.set(schluessel, ids, cls.DISCOVER_FRIST)
        return ids

    #: So lange gilt die aus dem Dateibestand abgeleitete Befehlsliste.
    BEFEHLE_FRIST = 600

    @classmethod
    def _befehle_abgeleitet(cls):
        u"""``test_befehle`` aus dem Dateibestand - wenn das Projekt keine pflegt.

        VORGABE FUER ALLE (Ansage 17.08.2026: „aktiviere das per default für alle
        in djangoBase!"). Ohne das war die Seite in jedem Konsumenten leer, der
        den Schluessel nicht gesetzt hat — und damit gab es dort auch keine
        Laufzeiten je Testcase. :class:`~.testbefehle.Testbefehle` sucht die
        ``tests``-Ordner unter ``BASE_DIR`` und baut je App und Art einen Eintrag;
        genau das hatte der assistant von Hand in seinen Einstellungen stehen.

        Ein Projekt, das ``DJANGOBASE["test_befehle"]`` setzt, behaelt seine
        Liste — die Vorgabe greift nur, wo nichts steht.
        """
        from django.core.cache import cache
        from django.conf import settings
        gecacht = cache.get("djangobase:testbefehle")
        if gecacht is not None:
            return gecacht
        try:
            befehle = Testbefehle(settings.BASE_DIR).liste()
        except Exception:  # noqa: BLE001
            # Nicht stumm: Bleibt die Seite leer, soll im Log stehen, warum.
            log.exception("test_befehle konnten nicht aus dem Dateibestand "
                          "abgeleitet werden — die Tests-Seite bleibt leer")
            befehle = []
        cache.set("djangobase:testbefehle", befehle, cls.BEFEHLE_FRIST)
        return befehle

    # ------------------------------------------------------------------ Seite

    def get(self, request):
        c = conf()
        befehle = c.get("test_befehle", []) or self._befehle_abgeleitet()
        ui = c.get("test_ui") or None
        kat = Kategorien(befehle)
        discover = c.get("test_discover", []) or kat.discover()

        kategorien, bekannte_ids = self._einzeltests(discover)
        slug = request.GET.get("run")
        ergebnis = self._lauf(slug, kat, befehle, bekannte_ids)

        # Laufzeiten NACH dem Lauf lesen, damit der gerade gefahrene Test seine
        # frische Zahl schon zeigt.
        #
        # ALLE Testcase-Listen der Seite kommen von HIER. Vorher hatte jede ihr
        # eigenes Markup, und beim Umbau auf die sortierbare Tabelle blieb eine
        # zurueck („warum gibt es kein Test Seiten template, wo du das nur einmal
        # aenderst??", 17.08.2026). Jetzt: eine Tabellen-Definition
        # (``Testtabelle``), eine Karte (``_testkarte.html``), vier Aufrufe.
        historie = Testhistorie()
        tabellen = Testtabelle(historie, aktiver_slug=slug or "",
                               tab=request.GET.get("tab", ""))
        for k in kategorien:
            k["karte"] = {"titel": "%s-Tests" % k["typ"], "anzahl": k["anzahl"],
                          "icon": "bi-list-check",
                          "tabelle": tabellen.aus_tests(k)}
        # EINMAL gruppieren und dieselben Objekte weitergeben: Ein zweiter Aufruf
        # von ``gruppen()`` baut neue Dictionaries, und die Karte haette an
        # Objekten gehangen, die die Vorlage nie sieht.
        gruppen = kat.gruppen()
        for g in gruppen:
            g["karte"] = {
                "titel": g["name"], "anzahl": len(g["befehle"]),
                "icon": "bi-collection-play",
                "tabelle": tabellen.aus_befehlen(
                    g["befehle"],
                    key="test-suiten-%s" % Kategorien.schluessel(g["name"]),
                    tab="Suiten")}
        for a in kat.arten:
            a["karte"] = {
                "titel": "Einzeln", "anzahl": len(a["befehle"]),
                "icon": "bi-list-check",
                "tabelle": tabellen.aus_befehlen(
                    a["befehle"], key="test-alle-%s" % a["art"],
                    tab="Alle", unter=a["art"])}

        return render(request, "djangobase/hilfe/tests.html", {
            "aktiv": "tests",
            "befehle": befehle,
            "alles": kat.alles,
            "alle_arten": kat.arten,
            "suiten": kat.suiten,
            "suiten_gruppen": gruppen,
            "kategorien": kategorien,
            "ui": ui,
            # Die UI-Tests stehen in ``testcases.js``, nicht im Server — die
            # Zeilen baut das JavaScript. Von hier kommen nur die KOPFZEILE
            # (dieselben Spalten wie ueberall) und die bisherigen Laufzeiten.
            "ui_karte": {"titel": "UI-Tests", "icon": "bi-window",
                         "hinweis": "laufen im Browser (Iframe)",
                         "tabelle": tabellen.tabelle([], key="tests-ui-browser",
                                                     tab="UI",
                                                     leer="Lade Test-Liste …")},
            "ui_historie": {k: v for k, v in historie.daten["tests"].items()
                            if k.startswith("ui:")},
            # Alles, was `static/djangobase/js/tests_ui.js` braucht - im DOM und
            # nicht als Template-Variable, damit das Skript eine eigene Datei
            # bleiben kann (das Template war auf 420 Zeilen gewachsen).
            "ui_config": {"runner": (ui or {}).get("runner", ""),
                          "cases": (ui or {}).get("cases", ""),
                          "seiten": (ui or {}).get("seiten", {}),
                          "dauerUrl": reverse("djangobase:tests_dauer")},
            "ergebnis": ergebnis,
            # Ziel der Combo-Box „Verschieben" (siehe tests_verschieben.js).
            "verschieben_url": reverse("djangobase:tests_verschieben"),
            "aktiver_slug": slug,
            "aktiver_tab": request.GET.get("tab", ""),
            "aktiver_unter": request.GET.get("unter", ""),
        })

    # ------------------------------------------------------------- Bausteine

    def _einzeltests(self, discover):
        """Die Reiter je Typ mit ihren Einzeltests - und alle bekannten IDs."""
        kategorien, bekannte = [], set()
        for d in discover:
            tests = []
            for label in d.get("labels", []):
                for tid in self._ids_gecacht(label):
                    tests.append({"id": tid, "kurz": _kurz(tid)})
                    bekannte.add(tid)
            tests.sort(key=lambda t: t["id"])
            kategorien.append({"typ": d.get("typ", "Tests"), "tests": tests,
                               "anzahl": len(tests)})
        return kategorien, bekannte

    @staticmethod
    def _lauf(slug, kat, befehle, bekannte_ids):
        u"""Den angeforderten Lauf fahren - oder None.

        NUR konfigurierte Befehle und ENTDECKTE Test-IDs; ein Label aus der Query
        wird nie ausgefuehrt. Die abgeleiteten Sammelbefehle sind aus den
        konfigurierten Eintraegen gebaut und deshalb ebenso sicher.
        """
        if not slug:
            return None
        laeufer = Testlauf()
        # Eigene Eintraege haben Vorrang, falls ein Projekt denselben slug fuehrt.
        kandidaten = list(befehle) + kat.sammelbefehle()
        b = next((x for x in kandidaten if x.get("slug") == slug), None)
        if b:
            return laeufer.fahren(b["cmd"], b.get("name", slug), b.get("frist"),
                                  slug=slug)
        if slug in bekannte_ids:
            cmd = [Kategorien.python(befehle), "manage.py", "test", slug,
                   "--noinput", "-v", "2"]
            return laeufer.fahren(cmd, _kurz(slug))
        return None
