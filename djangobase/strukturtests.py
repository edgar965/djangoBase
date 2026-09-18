# -*- coding: utf-8 -*-
"""Strukturtests — die Strukturregeln als Test, nicht als Text.

DER UNTERSCHIED (gunSlinger, 18.09.2026)
========================================
Dort prüft ``tests/test_bdp_rules.py`` maschinell: eine Klasse je Datei,
Dateiname = Klassenname, höchstens 300 Zeilen, ein Testmodul je Klasse. Ein
Verstoß ist ROT. Hier stand dieselbe Regel seit Monaten in ``CLAUDE.md`` und in
``~/.claude/rules/struktur.md`` — und ``views.py`` wuchs auf 12.223 Zeilen.
Text wird gelesen, verstanden und im Eifer vergessen. Ein roter Test wird
behoben, weil er sonst jeden Lauf rot macht.

WAS HIER NICHT NEU GEBAUT WIRD
==============================
Die Prüfer gibt es: `skills.dateigroesse.Dateigroesse` misst CODE-Zeilen (nicht
Zeilen — 74 von 78 Befunden in shortlongx lagen an der Dokumentation im
Dateikopf), `skills.klassenjedatei.KlassenJeDatei` kennt die Fälle, in denen
mehrere Klassen zusammengehören (``models.py``, Attrappen, kleine Datenträger).
Diese Datei macht aus ihren Befunden Zusicherungen. Wer die Eichung ändern
will, ändert sie DORT — dann stimmen Werkzeugkasten und Test überein.

DIE RATSCHE
===========
Ein Projekt mit Bestand hat Verstöße. Ein Test, der ab Tag eins rot ist, wird
ab Tag zwei ignoriert (siehe ``grundtests._projektdateien``). Deshalb führt
das Projekt eine BESTANDSLISTE: die bekannten Verstöße, ausdrücklich
aufgeschrieben. Der Test ist rot für alles, was NICHT darauf steht — und rot
für jeden Eintrag, der KEIN Verstoß mehr ist (dann ist er zu streichen). Die
Liste kann nur schrumpfen, nie unbemerkt wachsen.

BENUTZUNG IM PROJEKT
====================
Eine Datei ``<app>/tests/automated/test_struktur.py`` mit::

    from djangobase.strukturtests import *      # noqa: F401,F403

Einstellungen in ``DJANGOBASE["struktur"]`` (alles optional)::

    "struktur": {
        "datei": 300, "klasse": 300, "js": 300,   # Code-Zeilen-Grenzen
        "funktion": 0,                             # 0 = Funktionen nicht prüfen (60 bei gunSlinger)
        "klassen_je_datei": True,
        "test_je_klasse": False,                   # gunSlinger-Regel: test_<modul>.py je Klasse
        "bestand": {                               # bekannte Verstöße (Ratsche), je Regel
            "groesse": ["app/views.py", "app/alt.py::Riese"],
            "klassen": ["app/sammlung.py"],
            "tests": ["app/dienst.py"],
        },
    }

Schlüssel im Bestand: ``pfad`` für eine Datei, ``pfad::Name`` für Klasse
oder Funktion — so, wie der Test sie in der Fehlermeldung ausgibt.
"""

import ast

from django.conf import settings
from django.test import SimpleTestCase

from .skills.befund import Befund
from .skills.dateigroesse import Dateigroesse
from .skills.klassenjedatei import KlassenJeDatei

__all__ = [
    "Strukturregeln",
    "StrukturtestDateigroesse",
    "StrukturtestKlassenJeDatei",
    "StrukturtestTestJeKlasse",
]


class Strukturregeln:
    """Liest ``DJANGOBASE["struktur"]``, baut die Werkzeuge, führt die Ratsche."""

    VORGABE = {
        "datei": 300,
        "klasse": 300,
        "js": 300,
        "funktion": 0,
        "klassen_je_datei": True,
        "test_je_klasse": False,
        "bestand": {},
    }

    #: Module, für die kein Testmodul verlangt wird: Django findet sie selbst,
    #: oder sie sind Prüfcode.
    OHNE_TEST = ("/migrations/", "/tests/", "/test_", "apps.py", "admin.py", "__init__.py")

    def __init__(self, cfg=None):
        if cfg is None:
            cfg = (getattr(settings, "DJANGOBASE", {}) or {}).get("struktur") or {}
        self.cfg = dict(self.VORGABE, **cfg)

    def bestand(self, regel):
        """Die Bestandsliste EINER Regel (``groesse``, ``klassen``, ``tests``)."""
        eintraege = (self.cfg["bestand"] or {}).get(regel) or []
        return {str(x).replace("\\", "/") for x in eintraege}

    def werkzeug(self, klasse):
        """Ein eingerichtetes Werkzeug — Tests setzen es auf einen Wegwerfordner."""
        return klasse()

    def ratsche(self, regel, verstoesse):
        """``(neu, veraltet)``: Verstöße ohne Bestandseintrag, Einträge ohne Verstoß.

        ``verstoesse``: ``{schluessel: beschreibung}`` oder eine Liste von Schlüsseln.
        """
        if not isinstance(verstoesse, dict):
            verstoesse = {v: v for v in verstoesse}
        bestand = self.bestand(regel)
        neu = sorted(text for schluessel, text in verstoesse.items() if schluessel not in bestand)
        return neu, sorted(bestand - set(verstoesse))

    @staticmethod
    def meldung(regel, kopf, neu, veraltet):
        zeilen = [kopf]
        if neu:
            zeilen.append("NEU (nicht in DJANGOBASE['struktur']['bestand']['%s']):" % regel)
            zeilen += ["  " + z for z in neu]
        if veraltet:
            zeilen.append("VERALTET (kein Verstoß mehr — aus dem Bestand streichen):")
            zeilen += ["  " + z for z in veraltet]
        return "\n".join(zeilen)


class _Strukturtest(SimpleTestCase):
    databases = []

    @classmethod
    def regeln(cls):
        return Strukturregeln()

    def pruefe_ratsche(self, regel, kopf, verstoesse):
        neu, veraltet = self.regeln().ratsche(regel, verstoesse)
        if neu or veraltet:
            self.fail(Strukturregeln.meldung(regel, kopf, neu, veraltet))


class StrukturtestDateigroesse(_Strukturtest):
    """Dateien, Klassen (und auf Wunsch Funktionen) über der Code-Zeilen-Grenze."""

    def test_nichts_ueber_der_groessengrenze(self):
        regeln = self.regeln()
        werkzeug = regeln.werkzeug(Dateigroesse)
        werkzeug.GRENZE_DATEI = int(regeln.cfg["datei"])
        werkzeug.GRENZE_KLASSE = int(regeln.cfg["klasse"])
        werkzeug.GRENZE_JS = int(regeln.cfg["js"])
        werkzeug.GRENZE_FUNKTION = int(regeln.cfg["funktion"]) or 10**9
        verstoesse = {}
        for zeile in werkzeug.laufen().zeilen:  # "datei" ist der Pfad relativ zur Wurzel
            pfad = str(zeile["datei"]).replace("\\", "/")
            if zeile["art"] in ("Datei", "JS-Modul"):
                schluessel, art = pfad, zeile["art"]
            else:
                schluessel, art = "%s::%s" % (pfad, zeile["name"]), zeile["art"]
            verstoesse[schluessel] = "%s (%s, %d Code-Zeilen > %d)" % (
                schluessel,
                art,
                zeile["code"],
                zeile["grenze"],
            )
        grenzen = {k: regeln.cfg[k] for k in ("datei", "klasse", "js", "funktion")}
        self.pruefe_ratsche("groesse", "Zu große Dateien/Klassen (Grenzen: %s)" % grenzen, verstoesse)


class StrukturtestKlassenJeDatei(_Strukturtest):
    """Mehr als eine eigenständige Klasse in einer Datei — nach der Eichung des Werkzeugs."""

    def test_eine_eigenstaendige_klasse_je_datei(self):
        regeln = self.regeln()
        if not regeln.cfg["klassen_je_datei"]:
            self.skipTest("DJANGOBASE['struktur']['klassen_je_datei'] ist aus")
        satz = regeln.werkzeug(KlassenJeDatei).pruefen()
        verstoesse = [b.ort.replace("\\", "/") for b in satz.befunde if b.gewicht == Befund.WARNUNG]
        self.pruefe_ratsche("klassen", "Dateien mit mehreren eigenständigen Klassen", verstoesse)


class StrukturtestTestJeKlasse(_Strukturtest):
    """Jede Klasse hat ein ``test_<modul>.py`` — die gunSlinger-Regel, hier auf Wunsch."""

    def test_jede_klasse_hat_ein_testmodul(self):
        regeln = self.regeln()
        if not regeln.cfg["test_je_klasse"]:
            self.skipTest("DJANGOBASE['struktur']['test_je_klasse'] ist aus")
        werkzeug = regeln.werkzeug(Dateigroesse)
        testmodule = {p.name for p in werkzeug.pfade("test_*.py")}
        verstoesse = []
        for datei in werkzeug.dateien():
            if any(m in "/" + datei.name for m in regeln.OHNE_TEST):
                continue
            if datei.baum is None or not any(isinstance(k, ast.ClassDef) for k in datei.baum.body):
                continue
            if "test_%s.py" % datei.pfad.stem not in testmodule:
                verstoesse.append(datei.name)
        self.pruefe_ratsche("tests", "Klassen ohne Testmodul test_<modul>.py", verstoesse)
