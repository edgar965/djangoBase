# -*- coding: utf-8 -*-
"""Haelt das Projekt das Cache-Konzept ein — Seiten, Statik und ES-Module?

DER AUFTRAG (Edgar, 06.09.2026)
==============================
    „schreibe auch testcases … ganz normale djangoBase Testcases, die jede
     Seite ueberpruefen, ob das richtig drin ist, inkl. ES module"

WAS „JEDE SEITE" HIER HEISST
============================
Jede Vorlage des Projekts (``.html``) und jedes Skript (``.js``) — ohne
Datenbank und ohne Anmeldung, wie alle Konformitaetspruefungen. Eine Seite,
die nur mit Test-DB antwortet, wuerde die Pruefung Minuten kosten; die
Vorlage sagt dasselbe in Millisekunden. Die Regeln und ihre Vorgeschichte
stehen in ``djangobase/cachekonzept.py`` und auf Hilfe -> Cache; das
Befund-Werkzeug ``cachekonzept`` (Hilfe -> Skills) meldet dieselben Stellen.

Vier Pruefungen, je eine Regel, plus die Einstellungen:

    1. Kein ES-Modul-Einstieg ueber ``{% static %}?t=`` / ``?v=`` — der
       Fassungspfad muss es sein, sonst erben die Importe die Fassung nicht.
    2. Kein ``?t={% now %}`` an Skript- und Stildateien — das ist „nie cachen".
    3. Keine Kennung in JavaScript-Importen (ein Modul, eine Adresse).
    4. Middleware, Fassungspfad und ASGI-Huelle sind eingehaengt.
"""

from djangobase.cachekonzept import Cachekonzept
from djangobase.tests.konform.quellen import dateien, wurzel

from .basis import KonformTest

__all__ = ["CachekonzeptTest"]


def _text(pfad):
    try:
        return pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _kurz(pfad):
    try:
        return str(pfad.relative_to(wurzel())).replace("\\", "/")
    except ValueError:
        return str(pfad)


def _befunde(regel, endung, pruefer):
    raus = []
    for pfad in dateien(endung):
        raus.extend(b for b in pruefer(_kurz(pfad), _text(pfad)) if b["regel"] == regel)
    return raus


def _meldung(regel, befunde):
    r = Cachekonzept.regel(regel)
    zeilen = ["  %s  →  %s" % (b["ort"], b["was"]) for b in befunde[:12]]
    if len(befunde) > 12:
        zeilen.append("  … und %d weitere" % (len(befunde) - 12))
    return "%s\n%s\nWie: %s\nFundstellen:\n%s" % (r.titel, r.warum, r.wie, "\n".join(zeilen))


class CachekonzeptTest(KonformTest):
    """Jede Vorlage, jedes Skript, dazu die Einstellungen."""

    databases = []

    def test_es_module_kommen_ueber_den_fassungspfad(self):
        befunde = _befunde("modul-ueber-fassungspfad", ".html", Cachekonzept.vorlage)
        self.assertEqual(befunde, [], _meldung("modul-ueber-fassungspfad", befunde))

    def test_kein_zeitstempel_an_skript_und_stil(self):
        befunde = _befunde("kein-zeitstempel-an-statik", ".html", Cachekonzept.vorlage)
        self.assertEqual(befunde, [], _meldung("kein-zeitstempel-an-statik", befunde))

    def test_keine_kennung_in_javascript_importen(self):
        befunde = _befunde("keine-kennung-in-importen", ".js", Cachekonzept.skript)
        self.assertEqual(befunde, [], _meldung("keine-kennung-in-importen", befunde))

    def test_middleware_fassungspfad_und_asgi_huelle(self):
        befunde = Cachekonzept.einstellungen()
        zeilen = ["%s: %s — %s" % (b["ort"], b["was"], Cachekonzept.regel(b["regel"]).wie) for b in befunde]
        self.assertEqual(befunde, [], "Einstellungen gegen das Cache-Konzept:\n" + "\n".join(zeilen))

    def test_es_wurde_wirklich_gesucht(self):
        """Eine Pruefung ueber null Dateien ist keine Pruefung."""
        self.assertTrue(list(dateien(".html")), "Keine einzige Vorlage gefunden — stimmt die Wurzel?")
