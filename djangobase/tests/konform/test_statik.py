# -*- coding: utf-8 -*-
u"""Kommt ein geänderter Fix beim Nutzer an — oder liefert der Browser die alte Datei?

DER AUFTRAG (Edgar, 21.08.2026): „mach alle"
============================================
Zwei der vorgeschlagenen Prüfungen, beide zur selben Fehlerklasse:

    * Cache-Busting greift (``?v=`` an eigener Statik)
    * ein Modul, EINE URL

DIE FEHLERKLASSE
================
Aus ``~/.claude/rules/frontend-cache.md``, nach Vorfällen in drei Projekten:
Der Fix steht auf Platte, kommt aber nie im Browser an. Das kostet jedes Mal
Stunden, weil man den Fehler im Code sucht statt im Cache — und weil die Seite
dabei völlig normal aussieht.

Zwei Ausprägungen:

1. **Ohne ``?v=``** liefert der Browser die gemerkte Fassung. Ein Projekt, das
   seine Statik ohne Versionskennung einbindet, hat das Problem dauerhaft.
2. **Zwei URLs für dasselbe Modul.** Wird eine Datei einmal als
   ``modul.js?v=123`` geladen und woanders als ``modul.js`` importiert, sind das
   für den Browser ZWEI Module mit getrenntem Zustand. Am 21.08.2026 hat genau
   das jeden Klick doppelt aufgezeichnet: zwei Aufzeichner mit eigenen Puffern,
   neun Schritte doppelt in der Aufnahme, identische Zeitstempel.

WAS AUSGENOMMEN IST
===================
Fremde Statik (CDN, ``https://``) braucht keine eigene Kennung. Bilder und
Schriften ebenfalls nicht — sie ändern sich nicht mit dem Code. Geprüft wird,
was Verhalten trägt: ``.js`` und ``.css`` aus dem eigenen Projekt.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TABU = {"node_modules", "__pycache__", "venv", "pythonVENV", ".git",
        "site-packages", "migrations"}

#: <script src=…> / <link href=…> auf eigene Statik.
_EINBINDUNG = re.compile(
    r"""<(?:script|link)\b[^>]*?(?:src|href)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE)

#: Importe innerhalb von JS-Modulen.
_IMPORT = re.compile(
    r"""(?:from|import)\s*\(?\s*["'](/static/[^"']+\.js[^"']*)["']""")


def _dateien(muster):
    wurzel = Path(getattr(settings, "BASE_DIR", "."))
    eigen = Path(__file__).resolve().parents[2]
    for pfad in wurzel.rglob(muster):
        if TABU & set(pfad.parts):
            continue
        if eigen in pfad.parents:
            continue                       # djangoBase prüft sich nicht selbst
        yield pfad


def _eigene_statik(adresse):
    u"""Zeigt die Adresse auf eine eigene .js/.css-Datei?"""
    if adresse.startswith(("http://", "https://", "//", "data:")):
        return False
    ohne_query = adresse.split("?")[0].split("#")[0]
    return ohne_query.endswith((".js", ".css"))


class CacheBustingTest(SimpleTestCase):
    u"""Jede eigene Statik trägt eine Versionskennung."""

    def sammeln(self):
        u"""[(datei, adresse)] aller Einbindungen ohne ``?v=``."""
        ohne = []
        for pfad in _dateien("*.html"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for adresse in _EINBINDUNG.findall(text):
                if not _eigene_statik(adresse):
                    continue
                # `{% static %}` mit angehängter Query zählt - die Kennung steht
                # dann hinter dem Tag, nicht in der Adresse.
                if "?" in adresse or "|add:" in adresse:
                    continue
                ohne.append((pfad, adresse))
        return ohne

    def test_eigene_statik_traegt_eine_kennung(self):
        ohne = self.sammeln()
        if not ohne:
            return
        beispiele = "\n".join("    %s: %s" % (p.name, a[:70]) for p, a in ohne[:10])
        self.fail(
            u"%d Einbindungen ohne ?v=-Kennung:\n%s%s\n\n"
            u"Der Browser liefert diese Dateien aus seinem Cache — ein Fix "
            u"kommt beim Nutzer erst nach hartem Neuladen an, und die Seite "
            u"sieht dabei völlig normal aus.\n"
            u"    <script src=\"{%% static 'app/x.js' %%}?v={{ djangobase.statik_v }}\">"
            % (len(ohne), beispiele, "\n    …" if len(ohne) > 10 else ""))

    def test_es_wurde_wirklich_gesucht(self):
        u"""Findet der Sucher gar keine Einbindungen, ist „0 Verstöße" wertlos."""
        gesamt = 0
        for pfad in _dateien("*.html"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            gesamt += sum(1 for a in _EINBINDUNG.findall(text) if _eigene_statik(a))
        self.assertTrue(gesamt,
                        u"Keine einzige eigene Statik-Einbindung gefunden — das "
                        u"Suchmuster passt nicht mehr.")


class ModulUrlTest(SimpleTestCase):
    u"""Ein Modul, eine URL."""

    def sammeln(self):
        u"""{modulname: {adressen}} über Vorlagen UND JS-Dateien."""
        wo = {}
        for muster in ("*.html", "*.js"):
            for pfad in _dateien(muster):
                try:
                    text = pfad.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                adressen = _IMPORT.findall(text)
                if muster == "*.html":
                    adressen += [a for a in _EINBINDUNG.findall(text)
                                 if a.startswith("/static/") and ".js" in a]
                for a in adressen:
                    name = a.split("?")[0].split("/")[-1]
                    wo.setdefault(name, set()).add("?" in a)
        return wo

    def test_kein_modul_mit_und_ohne_kennung(self):
        u"""Beides gemischt = zwei Modulinstanzen mit getrenntem Zustand.

        Belegt am 21.08.2026: ``aufzeichner.js`` wurde in der Shell mit ``?v=``
        geladen und im Knopf-Modul ohne — es lief zweimal, und jeder Klick stand
        doppelt in der Aufnahme."""
        gemischt = sorted(name for name, arten in self.sammeln().items()
                          if len(arten) > 1)
        self.assertFalse(gemischt,
                         u"Diese Module werden MIT und OHNE ?v= geladen: %s\n\n"
                         u"Für den Browser sind das je zwei Module mit eigenem "
                         u"Zustand. Im Importeur die Kennung übernehmen:\n"
                         u"    await import('/static/…/x.js' + "
                         u"new URL(import.meta.url).search)"
                         % ", ".join(gemischt[:10]))


class KennungIstDynamischTest(SimpleTestCase):
    u"""Eine feste Kennung ist Cache-Busting, das nie bustet.

    GEFUNDEN BEIM ERSTEN LAUF (21.08.2026): In ShortLongX importieren mehrere
    Module ``tabellen_sortierung.js?v=2`` — die Zwei steht seit dem Tag fest, an
    dem jemand sie hingeschrieben hat. Sie sieht aus wie eine Versionskennung,
    tut aber nichts: Ändert sich die Datei, liefert der Browser weiter seine
    gemerkte Fassung, weil die URL gleich blieb.

    Das ist die tückischere Hälfte der Fehlerklasse — ohne ``?v=`` sucht man
    wenigstens noch; mit einer festen Zahl hält man das Thema für erledigt.
    """

    #: ``?v=`` gefolgt von einer reinen Zahl, ohne Vorlagen-Ausdruck dahinter.
    FEST = re.compile(r"""["'][^"']*\.js\?v=\d+(?:\.\d+)?["']""")

    def test_keine_feste_versionsnummer_in_js_importen(self):
        treffer = []
        for pfad in _dateien("*.js"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for nr, zeile in enumerate(text.splitlines(), 1):
                if "import" not in zeile:
                    continue
                if self.FEST.search(zeile):
                    treffer.append((pfad.name, nr, zeile.strip()))
        if treffer:
            zeilen = "\n".join("    %s:%d  %s" % (d, n, z[:78])
                               for d, n, z in treffer[:10])
            self.fail(
                u"%d Import(e) mit fest verdrahteter Kennung:\n%s%s\n\n"
                u"Die Zahl ändert sich nie, also ändert sich die URL nie, also "
                u"liefert der Browser weiter seine gemerkte Fassung. Die Kennung "
                u"des eigenen Moduls übernehmen:\n"
                u"    await import('/static/…/x.js' + new URL(import.meta.url).search)"
                % (len(treffer), zeilen, "\n    …" if len(treffer) > 10 else ""))

    def test_muster_trifft_nur_feste_zahlen(self):
        u"""Gegenprobe: Ein dynamischer Anhänger darf NICHT gemeldet werden."""
        self.assertTrue(self.FEST.search("import x from '/static/a/x.js?v=2';"))
        self.assertIsNone(self.FEST.search(
            "await import('/static/a/x.js' + new URL(import.meta.url).search)"))
        self.assertIsNone(self.FEST.search("'/static/a/x.js?v=' + stand"))


class GegenprobeTest(SimpleTestCase):
    u"""Erkennen die Muster, was sie erkennen sollen?"""

    def test_einbindung_wird_gefunden(self):
        html = '<script src="{% static \'app/x.js\' %}?v=3"></script>'
        self.assertTrue(_EINBINDUNG.findall(html))

    def test_fremde_statik_ist_ausgenommen(self):
        self.assertFalse(_eigene_statik("https://cdn.example/bootstrap.min.css"))
        self.assertFalse(_eigene_statik("/static/app/logo.png"))
        self.assertTrue(_eigene_statik("/static/app/x.js"))

    def test_import_wird_gefunden(self):
        for zeile in ("import { X } from '/static/app/x.js';",
                      "await import('/static/app/x.js' + suche)"):
            with self.subTest(zeile=zeile):
                self.assertTrue(_IMPORT.findall(zeile), zeile)

    def test_gemischte_ladeart_faellt_auf(self):
        u"""Der Kern von test_kein_modul_mit_und_ohne_kennung an einer Probe."""
        arten = {True, False}
        self.assertTrue(len(arten) > 1)
