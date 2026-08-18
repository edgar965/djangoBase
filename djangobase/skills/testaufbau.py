# -*- coding: utf-8 -*-
u"""Testaufbau - sind die Tests gegliedert und aus der Oberflaeche startbar?

    Kriterium 17: Testcases sauber unter Hilfe -> Tests, ueber djangoBase.
    Untermenues fuer Unit-, Component-, UI-Tests und Longrunner; bei grossen
    Projekten mehrere Unterseiten (wie im Projekt assistant).

ZWEI FRAGEN, NICHT EINE
=======================
1. Sind die Tests nach ihrer ART gegliedert? ``unit`` laeuft in Sekunden,
   ``longrunner`` in Minuten - liegen sie im selben Topf, laesst man entweder
   die schnellen ungenutzt oder wartet jedes Mal auf die langsamen.
2. Kommt man ohne Kommandozeile daran? Die Hilfe-Tests-Seite faehrt, was in
   ``DJANGOBASE["test_befehle"]`` steht. Ein Bereich, der dort fehlt, existiert
   fuer die Oberflaeche nicht - und wird deshalb selten gefahren.

ZWEI ANERKANNTE BAUFORMEN (beide im Projekt assistant zu sehen)
===============================================================
    mail/tests/{unit,component,ui}/…                  nach Art
    search/tests/<bereich>/{unit,component,ui,longrunner}/…   Bereich x Art

Die zweite ist die Antwort auf „grosses Projekt": je Bereich eine eigene
Gruppe, damit die Seite nicht zu einer Liste aus hundert Eintraegen wird.

DER TEUERSTE BEFUND IST DER PLATZHALTER
=======================================
Eine Testdatei ohne einzige Zusicherung meldet „gruen" und prueft nichts. Im
Ursprungsprojekt lagen 24 gleichnamige ``test_placeholder.py`` mit identischem
Rumpf - eine Gliederung, die es nur dem Namen nach gab.
"""
from .werkzeug import Ergebnis
from .basis import EigenesWerkzeug

__all__ = ["Testaufbau"]


class Testaufbau(EigenesWerkzeug):
    slug = "testaufbau"
    titel = "Tests: gegliedert und aus der Hilfe startbar"
    zweck = ("Prüft die vier Test-Arten (unit/component/ui/longrunner), leere "
             "Platzhalter und ob jeder Bereich über Hilfe → Tests startbar ist.")
    befund = ("24 gleichnamige Platzhalter-Dateien mit identischem Rumpf: eine "
              "Gliederung, die es nur dem Namen nach gab — und Tests, die man "
              "ohne Kommandozeile nicht starten kann.")
    abhilfe = ("Nach Art gliedern (bei großen Projekten Bereich × Art) und jeden "
               "Bereich in DJANGOBASE['test_befehle'] eintragen.")
    dauer = "3–8 s"
    kriterium = 17

    ARTEN = ("automated", "unit", "component", "ui", "performance", "longrunner")
    #: Ab so vielen Test-Bereichen lohnen eigene Gruppen/Unterseiten.
    VIEL = 4

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = "misst nur (wie die Testsuite gegliedert ist)"

    def laufen(self):
        dateien = [d for d in self.dateien()
                   if self._ist_testdatei(d) and self._ist_django_app(d)]
        zeilen = []
        zeilen += self._gliederung(dateien)
        zeilen += self._platzhalter(dateien)
        zeilen += self._startbar(dateien)
        rang = {"nicht startbar": 0, "Platzhalter": 1, "Art fehlt": 2,
                "ungegliedert": 3, "Umfang": 4}
        zeilen.sort(key=lambda z: (rang.get(z["art"], 9), z["stelle"]))
        return Ergebnis(
            ["art", "stelle", "befund", "abhilfe"], zeilen,
            "%d Testdateien geprüft, %d Punkte offen" % (len(dateien), len(zeilen)),
            "Die vier Arten sind kein Selbstzweck: Sie trennen, was in Sekunden "
            "läuft, von dem, was Minuten braucht — nur so fährt man die schnellen "
            "wirklich bei jeder Änderung.")

    @staticmethod
    def _ist_django_app(d):
        """Gehoert die Datei zu einer installierten App?

        Im Projektbaum liegen oft eigenstaendige Programme (bei assistant etwa
        ``diktator/`` — ein Windows-Diktiergeraet mit eigenen Prüfskripten). Von
        denen ``tests/unit/`` zu verlangen oder sie in ``test_befehle``
        einzutragen ist Unsinn: Der Django-Testlaeufer faehrt sie nie
        (17.08.2026)."""
        from django.conf import settings
        wurzel = d.name.split("/")[0]
        installiert = {a.split(".")[0] for a in settings.INSTALLED_APPS}
        return wurzel in installiert

    @staticmethod
    def _ist_testdatei(d):
        """Enthaelt die Datei wirklich Tests?

        NICHT nach dem Ordner gehen (Korrektur nach dem ersten Lauf,
        17.08.2026): ``__init__.py``, ``_konto_fixtures.py`` und
        ``tests_urls.py`` liegen im Test-Baum, sind aber Beiwerk — als
        „ungegliedert" gemeldet waren sie drei Fehlalarme von vierzehn."""
        kurz = d.name.rsplit("/", 1)[-1]
        if kurz == "__init__.py" or kurz.startswith("_"):
            return False
        # Der NAME entscheidet, nicht der Inhalt: Eine Datei, die ihre
        # Testklassen aus einer Bibliothek hereinholt (``from
        # djangobase.grundtests import *``), enthaelt weder „def test" noch
        # „TestCase" — sie ist trotzdem der Testeinstieg. Die erste Fassung
        # uebersah damit genau die neu angelegten Bereiche „automated" und
        # „performance" und meldete sie als fehlend (17.08.2026).
        return kurz.startswith("test_") or kurz.endswith("_test.py")

    # -------------------------------------------------------------- Gliederung

    def _gliederung(self, dateien):
        vorhanden, ungegliedert, bereiche = set(), [], set()
        for d in dateien:
            teile = d.name.split("/")
            arten = [t for t in teile if t in self.ARTEN]
            if arten:
                vorhanden.add(arten[0])
                if "tests" in teile:
                    i = teile.index("tests")
                    # tests/<bereich>/<art>/  -> Bereich x Art (grosses Projekt)
                    if teile[i + 1] not in self.ARTEN:
                        bereiche.add(teile[i + 1])
            elif "/tests" in "/" + d.name:
                ungegliedert.append(d.name)
        aus = []
        if not dateien:
            # „Keine Tests" ist nur dann ein Befund, wenn es etwas ZU testen
            # gibt. Auf einem leeren Verzeichnis war die Meldung ein Fehlalarm —
            # und genau den prüft die Gegenprobe „läuft auf leerem Projekt ohne
            # Befund" ab (17.08.2026).
            if not self.hat_code():
                return []
            return [{"art": "Art fehlt", "stelle": "(Projekt)",
                     "befund": "keine Testdateien gefunden",
                     "abhilfe": "tests/{unit,component,ui,longrunner}/ anlegen"}]
        for art in self.ARTEN:
            if art not in vorhanden:
                aus.append({"art": "Art fehlt", "stelle": "tests/%s/" % art,
                            "befund": "keine Tests dieser Art",
                            "abhilfe": {"automated": "Grundfunktion in Sekunden: "
                                                     "Seiten ohne 5xx, URLs, "
                                                     "Importe, Migrationen, "
                                                     "Logging — djangobase.grundtests",
                                        "unit": "reine Modul-Logik ohne DB",
                                        "component": "mit Datenbank",
                                        "ui": "Templates und Views (HTTP)",
                                        "performance": "Ladezeiten der wichtigen "
                                                       "Seiten messen und "
                                                       "protokollieren — "
                                                       "djangobase.leistungstests",
                                        "longrunner": "was Minuten braucht — "
                                                      "getrennt, damit der Rest "
                                                      "schnell bleibt"}[art]})
        for name in ungegliedert[:10]:
            aus.append({"art": "ungegliedert", "stelle": name,
                        "befund": "liegt in keinem der vier Art-Ordner",
                        "abhilfe": "in unit/component/ui/longrunner einsortieren"})
        # Der Umfang ist nur dann ein Befund, wenn die Seite die Bereiche NICHT
        # gruppiert. Sind Gruppen gesetzt (``gruppe``-Schluessel, etwa aus
        # djangobase.testbefehle), ist genau das schon erledigt - das weiter zu
        # melden waere ein Fehlalarm auf die eigene Loesung.
        if len(bereiche) >= self.VIEL and not self._hat_gruppen():
            aus.append({"art": "Umfang", "stelle": "Hilfe → Tests",
                        "befund": "%d Test-Bereiche (%s …) in einer flachen Liste"
                                  % (len(bereiche), ", ".join(sorted(bereiche)[:4])),
                        "abhilfe": "eigene Gruppe/Unterseite je Bereich — "
                                   "djangobase.testbefehle.Testbefehle setzt den "
                                   "gruppe-Schlüssel von selbst"})
        return aus

    @staticmethod
    def _hat_gruppen():
        from django.conf import settings
        befehle = ((getattr(settings, "DJANGOBASE", {}) or {})
                   .get("test_befehle") or [])
        return len({b.get("gruppe") for b in befehle if b.get("gruppe")}) > 1

    # -------------------------------------------------------------- Platzhalter

    def _platzhalter(self, dateien):
        """Testmethoden mit LEEREM Rumpf - nicht bloss ohne ``assert``.

        „Kein assert" war zu grob (Korrektur nach dem ersten Lauf): Ein
        Smoke-Test, der jedes Modul importiert, prueft sehr wohl etwas — die
        Ausnahme IST die Zusicherung. Ein Platzhalter dagegen hat einen Rumpf
        aus ``pass`` und Docstring; das war die Bauform der 24 gleichnamigen
        ``test_placeholder.py`` im Ursprungsprojekt."""
        import ast
        aus = []
        for d in dateien:
            if d.baum is None:
                continue
            leer = []
            for k in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                if not k.name.startswith("test"):
                    continue
                rumpf = [x for x in k.body
                         if not (isinstance(x, ast.Expr)
                                 and isinstance(getattr(x, "value", None), ast.Constant))]
                if not rumpf or all(isinstance(x, ast.Pass) for x in rumpf):
                    leer.append(k.name)
            if leer:
                aus.append({"art": "Platzhalter", "stelle": d.name,
                            "befund": "%d Testmethode(n) mit leerem Rumpf: %s"
                                      % (len(leer), ", ".join(leer[:3])),
                            "abhilfe": "echte Prüfung schreiben oder Datei löschen — "
                                       "grün ohne Aussage ist schlimmer als keine Datei"})
        return aus[:15]

    # ---------------------------------------------------------------- startbar

    def _startbar(self, dateien):
        """Ist jeder Test-Bereich ueber Hilfe -> Tests zu starten?"""
        from django.conf import settings
        cfg = (getattr(settings, "DJANGOBASE", {}) or {})
        befehle = cfg.get("test_befehle") or []
        if not befehle:
            return [{"art": "nicht startbar", "stelle": "DJANGOBASE['test_befehle']",
                     "befund": "nicht gesetzt — Hilfe → Tests kann nichts fahren",
                     "abhilfe": "je App/Bereich einen Eintrag {slug, name, cmd} "
                                "setzen (siehe djangoBase-Rezept)"}]
        text = " ".join(str(b.get("cmd", "")) + " " + str(b.get("slug", ""))
                        for b in befehle)
        apps = {d.name.split("/")[0] for d in dateien if "/" in d.name}
        aus = []
        for app in sorted(apps):
            if app and app not in text:
                aus.append({"art": "nicht startbar", "stelle": app,
                            "befund": "hat Tests, steht aber in keinem test_befehle-Eintrag",
                            "abhilfe": "Eintrag ergänzen — was man nicht per Knopf "
                                       "starten kann, fährt man selten"})
        # Sind die Arten einzeln startbar? Ein einziger Sammelbefehl je App
        # zwingt dazu, immer alles zu fahren - auch die Longrunner.
        if not any(a in text for a in self.ARTEN):
            aus.append({"art": "nicht startbar", "stelle": "Hilfe → Tests",
                        "befund": "kein Eintrag fährt eine einzelne Art",
                        "abhilfe": "je Art einen Eintrag (…test app.tests.unit), "
                                   "damit die schnellen ohne die Longrunner laufen"})
        return aus
