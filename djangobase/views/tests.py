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
from ..testkarten import Karten
from ..testkategorien import Kategorien
from ..testlauf import Testlauf
from ..testtabelle import Testtabelle
from ..testziele import Testziele

log = logging.getLogger("djangobase.tests")


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

    def post(self, request):
        u"""Die angehakten Fälle fahren — in EINEM Lauf.

        Kommt von den Knöpfen im Kartenkopf (``tests_auswahl.js``). POST und
        nicht GET: Bei „Alle auswählen" stehen hunderte Kennungen in der
        Anfrage, das sprengt jede URL — und ein Testlauf ist nichts, was ein
        Reload wiederholen soll.
        """
        return self.get(request, ids=request.POST.getlist("ids"))

    def get(self, request, ids=None):
        c = conf()
        befehle = c.get("test_befehle", []) or self._befehle_abgeleitet()
        ui = c.get("test_ui") or None
        kat = Kategorien(befehle)
        discover = c.get("test_discover", []) or kat.discover()

        kategorien, bekannte_ids = self._einzeltests(
            discover, mit_djangobase=bool(c.get("tests_djangobase_sichtbar")))
        slug = request.GET.get("run")
        # Die Sammel-Labels der Karten („Alle ausführen" im Kartenkopf) VOR dem
        # Lauf bilden — sie sind erlaubte Laufziele. Die Karten selbst entstehen
        # erst danach, sonst zeigte der gerade gefahrene Test seine alte Zeit.
        labels = {Karten.label(k.get("tests") or []) for k in kategorien}
        labels.discard("")
        if ids:
            ergebnis = self._lauf_auswahl(ids, kat, befehle,
                                          bekannte_ids, labels)
        else:
            ergebnis = self._lauf(slug, kat, befehle, bekannte_ids, labels)

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
        # EINE Karte je Kategorie; die Gliederung nach Bereich steckt in der
        # Tabelle (Spalte „Bereich", Zeilen danach vorsortiert) — Ansage
        # 17.08.2026: „Eine Tabelle je Kategorie, aber der Bereich ist nochmal
        # extra markiert in der Tabelle".
        karten = Karten(tabellen)
        for k in kategorien:
            k["karten"] = karten.je_kategorie(
                k.get("tests") or [], titel="%s-Tests" % k["typ"],
                key="tests-%s" % Kategorien.schluessel(k["typ"]), tab=k["typ"])
        # EINMAL gruppieren und dieselben Objekte weitergeben: Ein zweiter Aufruf
        # von ``gruppen()`` baut neue Dictionaries, und die Karte haette an
        # Objekten gehangen, die die Vorlage nie sieht.
        gruppen = kat.gruppen()
        for g in gruppen:
            g["karten"] = karten.eine(
                tabellen.aus_befehlen(
                    g["befehle"],
                    key="test-suiten-%s" % Kategorien.schluessel(g["name"]),
                    tab="Suiten"),
                titel=g["name"], anzahl=len(g["befehle"]))
        # Reiter „Alle": je Kategorie ihre TESTFAELLE, nicht ihre Suiten.
        # Gemeldet am 17.08.2026: „die Alle Seite enthält nicht alle tests!" und
        # „die verschieben Spalte hat keine Combo Box, ist also nutzlos" — beides
        # dasselbe: Dort standen die Suiten (ganze Ordner), und eine Suite hat
        # keine verschiebbare Datei. Mit den Faellen ist die Liste vollstaendig
        # UND die Combo-Box da.
        nach_typ = {k["typ"]: k for k in kategorien}
        for a in kat.arten:
            faelle = nach_typ.get(a["kurz"])
            if faelle is None:
                # „Nach App" ist keine Art, sondern der Rest: Eintraege, deren
                # Ziel keine erkennbare Kategorie traegt. Dafuer gibt es keine
                # Einzelfall-Liste — hier stehen die Suiten selbst, sonst waere
                # die Karte leer und der Bereich unsichtbar.
                a["karten"] = karten.eine(
                    tabellen.aus_befehlen(a["befehle"],
                                          key="test-alle-%s" % a["art"],
                                          tab="Alle"),
                    titel="%s — Suiten" % a["kurz"], anzahl=len(a["befehle"]))
                continue
            a["karten"] = karten.je_kategorie(
                faelle.get("tests") or [],
                titel="%s — Testfälle" % a["kurz"],
                key="test-alle-%s" % a["art"], tab="Alle")

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
            # Ziel des LIVE-Laufs (tests_strom.js). Steht als json_script im
            # DOM, damit das Skript eine eigene Datei bleibt.
            "strom_url": reverse("djangobase:tests_strom"),
            # Ziel der Nummern-Spalte (tests_nummer.js).
            "nummer_url": reverse("djangobase:tests_nummer"),
            "aktiver_slug": slug,
            "aktiver_tab": request.GET.get("tab", ""),
            "aktiver_unter": request.GET.get("unter", ""),
        })

    # ------------------------------------------------------------- Bausteine

    @classmethod
    def _einzeltests(cls, discover, mit_djangobase=False):
        u"""Die Reiter je Typ mit ihren Einzeltests - und alle bekannten IDs.

        ``mit_djangobase`` schaltet die Faelle zu, die djangoBase SELBST
        mitbringt (Grundtests, Endpunktprobe). Sie laufen im Wirt-Projekt mit,
        gehoeren aber nicht zu seinem Code — und standen in der Liste ganz oben
        im Weg. Vorgabe deshalb AUS, Schalter unter Einstellungen → djangoBase
        (Ansage 17.08.2026).
        """
        from ..testverschieben import Verschieber
        kategorien, bekannte = [], set()
        for d in discover:
            tests = []
            for label in d.get("labels", []):
                for tid in cls._ids_gecacht(label):
                    if not mit_djangobase and Verschieber.aus_djangobase(tid):
                        continue
                    tests.append({"id": tid, "kurz": _kurz(tid)})
                    bekannte.add(tid)
            tests.sort(key=lambda t: t["id"])
            kategorien.append({"typ": d.get("typ", "Tests"), "tests": tests,
                               "anzahl": len(tests)})
        return kategorien, bekannte

    @staticmethod
    def _lauf_auswahl(ids, kat, befehle, bekannte_ids, labels=()):
        u"""Mehrere angehakte Einträge in EINEM ``manage.py test``-Aufruf.

        Geprüft wird in :class:`~.testziele.Testziele` — dieselbe Stelle, die
        auch der Live-Lauf (``/hilfe/tests/strom/``) benutzt. Zwei Prüfungen für
        dieselbe Frage („was darf in die Kommandozeile?") laufen auseinander.
        """
        auswahl = Testziele(bekannte_ids, befehle, kat.sammelbefehle(), labels)
        cmd, ziele, verworfen = auswahl.befehl(ids, Kategorien.python(befehle))
        if not cmd:
            # Dictionary gewollt: dasselbe Format wie ein echter Lauf, damit die
            # Vorlage nichts Zusätzliches können muss.
            return {"name": "Auswahl", "cmd": "", "rc": -1, "ok": False,
                    "out": "", "dauer": 0.0, "dauer_text": "0,00 s", "dauern": 0,
                    "err": "Keine gültige Auswahl — %d Einträge verworfen."
                           % verworfen}
        return Testlauf().fahren(cmd, Testziele.name(ziele, verworfen),
                                 Kategorien.SAMMEL_FRIST)

    @staticmethod
    def _lauf(slug, kat, befehle, bekannte_ids, labels=()):
        u"""Den angeforderten Lauf fahren - oder None.

        NUR konfigurierte Befehle, ENTDECKTE Test-IDs und die Sammel-Labels der
        Karten; ein Label aus der Query wird nie ausgefuehrt. Die abgeleiteten
        Sammelbefehle sind aus den konfigurierten Eintraegen gebaut und deshalb
        ebenso sicher, die Karten-Labels aus den entdeckten IDs.
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
        if slug in bekannte_ids or slug in (labels or ()):
            cmd = [Kategorien.python(befehle), "manage.py", "test", slug,
                   "--noinput", "-v", "2"]
            # Ein Karten-Label faehrt viele Faelle - es braucht die lange Frist.
            frist = None if slug in bekannte_ids else Kategorien.SAMMEL_FRIST
            return laeufer.fahren(cmd, _kurz(slug), frist)
        return None
