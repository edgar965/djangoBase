# -*- coding: utf-8 -*-
u"""Erben die Vorlagen den Rahmen — und halten sie seine Konventionen ein?

DER AUFTRAG (Edgar, 21.08.2026): „mach alle"
============================================
Drei der vorgeschlagenen Prüfungen:

    * Templates erben vom Rahmen (kein eigenes ``<html>``)
    * Icon-Konvention: Sidebar ``bi-*``, Seiteninhalt ``fa-*``
    * Kontrast: kein ``<pre>``/``<code>`` ohne gesetzte ``color``

WARUM DAS ERBEN ZÄHLT
=====================
Eine Seiten-Vorlage mit eigenem ``<html>`` fällt aus der Anwendung heraus: keine
Seitenleiste, kein Menü, keine Versionsnummer — und seit dem 21.08.2026 auch
keine Testaufzeichnung im Menü. Man kommt von dort nirgends mehr hin. Das
passiert nicht aus Absicht, sondern beim schnellen Anlegen einer neuen Seite.

ICONS
=====
Die Sidebar beschriftet mit Bootstrap Icons (``bi-*``), Seiteninhalte mit
FontAwesome (``fa-*``). Wer im Inhalt ``bi-*`` benutzt, sieht ein leeres
Kästchen, sobald ein Projekt die Bootstrap-Icon-Schrift nicht lädt — und
umgekehrt. Geprüft wird deshalb nicht „welches ist schöner", sondern ob die
verwendete Familie auch eingebunden ist.

KONTRAST
========
Ein ``<pre>`` ohne gesetzte ``color`` erbt die Schriftfarbe des Browsers, nicht
die des Themes — auf dunklem Grund steht es dann dunkel auf dunkel. Beim Einbau
neuer Befund-Abschnitte ist das in diesem Projekt zweimal passiert.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TABU = {"node_modules", "__pycache__", "venv", "pythonVENV", ".git",
        "site-packages", "migrations"}

#: Vorlagen, die legitim ein eigenes ``<html>`` haben: E-Mails, PDF-Vorlagen,
#: Fehlerseiten (die Sidebar braucht einen Kontext, den es dort nicht gibt).
EIGEN_ERLAUBT = ("mail", "email", "pdf", "druck", "print", "400.html",
                 "403.html", "404.html", "500.html", "base")

_EXTENDS = re.compile(r"{%\s*extends\s+[\"']?([^\"'%\s]+)")
_HTML_TAG = re.compile(r"<html\b", re.IGNORECASE)
_PRE_STIL = re.compile(r"\b(pre|code)\b[^{}]*\{([^}]*)\}", re.IGNORECASE)


def _vorlagen():
    wurzel = Path(getattr(settings, "BASE_DIR", "."))
    eigen = Path(__file__).resolve().parents[2]
    for pfad in wurzel.rglob("*.html"):
        if TABU & set(pfad.parts):
            continue
        if eigen in pfad.parents:
            continue
        yield pfad


def _teilvorlage(pfad):
    u"""Beginnt der Dateiname mit ``_``? Dann ist es ein Include, kein Seiten-Template."""
    return pfad.name.startswith("_")


class ErbenTest(SimpleTestCase):
    u"""Jede Seiten-Vorlage endet im djangoBase-Rahmen."""

    def test_keine_seite_mit_eigenem_html(self):
        eigene = []
        for pfad in _vorlagen():
            if _teilvorlage(pfad):
                continue
            name = pfad.name.lower()
            if any(w in name for w in EIGEN_ERLAUBT):
                continue
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _HTML_TAG.search(text) and not _EXTENDS.search(text):
                eigene.append(pfad)
        if eigene:
            self.fail(
                u"%d Seiten-Vorlagen bringen ein eigenes <html> mit und erben "
                u"nichts:\n%s\n\nSie zeigen weder Seitenleiste noch Menü noch "
                u"Versionsnummer — man kommt von dort nirgends mehr hin. "
                u"Erwartet: {%% extends \"djangobase/base.html\" %%} (oder die "
                u"Projekt-Basis, die davon erbt)."
                % (len(eigene), "\n".join("    " + p.name for p in eigene[:10])))

    def test_erb_ketten_enden_bei_djangobase(self):
        u"""Eine Kette, die im Nichts endet, wirft erst beim Aufruf der Seite —
        also womöglich erst beim Nutzer."""
        namen = {}
        for pfad in _vorlagen():
            namen.setdefault(pfad.name, pfad)
        offen = []
        for pfad in _vorlagen():
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            m = _EXTENDS.search(text)
            if not m:
                continue
            ziel = m.group(1)
            if ziel.startswith("djangobase/") or "{{" in ziel or "{%" in ziel:
                continue                       # djangoBase oder dynamisch
            if Path(ziel).name not in namen:
                offen.append((pfad.name, ziel))
        self.assertFalse(offen,
                         u"Diese Vorlagen erben von etwas, das im Projekt nicht "
                         u"zu finden ist: %s"
                         % "; ".join("%s → %s" % (a, b) for a, b in offen[:8]))


class IconsTest(SimpleTestCase):
    u"""Die benutzte Icon-Familie muss auch geladen sein."""

    def _benutzt(self, praefix):
        muster = re.compile(r'class\s*=\s*["\'][^"\']*\b%s[a-z0-9-]+' % praefix)
        for pfad in _vorlagen():
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if muster.search(text):
                return pfad
        return None

    def _eingebunden(self, brocken):
        for muster in ("*.html",):
            for pfad in _vorlagen():
                try:
                    text = pfad.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if brocken in text:
                    return True
        # Auch der djangoBase-Rahmen zählt - er bringt Bootstrap Icons mit.
        rahmen = (Path(__file__).resolve().parents[2] / "templates" / "djangobase")
        for pfad in rahmen.rglob("*.html"):
            if brocken in pfad.read_text(encoding="utf-8", errors="replace"):
                return True
        return False

    def test_bootstrap_icons_geladen_wenn_benutzt(self):
        wo = self._benutzt("bi-")
        if wo is None:
            self.skipTest("keine bi-*-Icons im Projekt")
        self.assertTrue(self._eingebunden("bootstrap-icons"),
                        u"%s nutzt bi-*-Icons, aber die Bootstrap-Icon-Schrift "
                        u"ist nirgends eingebunden — dort stehen leere "
                        u"Kästchen." % wo.name)

    def test_fontawesome_geladen_wenn_benutzt(self):
        wo = self._benutzt("fa-")
        if wo is None:
            self.skipTest("keine fa-*-Icons im Projekt")
        self.assertTrue(
            self._eingebunden("fontawesome") or self._eingebunden("font-awesome"),
            u"%s nutzt fa-*-Icons, aber FontAwesome ist nirgends eingebunden — "
            u"dort stehen leere Kästchen." % wo.name)


class KontrastTest(SimpleTestCase):
    u"""Kein Codeblock ohne gesetzte Schriftfarbe."""

    def test_pre_und_code_setzen_ihre_farbe(self):
        u"""Ein ``<pre>``-Stil, der Hintergrund und Rahmen setzt, aber keine
        ``color``, steht auf dunklem Grund dunkel auf dunkel."""
        ohne = []
        for pfad in _vorlagen():
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for treffer in _PRE_STIL.finditer(text):
                block = treffer.group(2)
                # Nur Regeln, die überhaupt Farben anfassen - reine
                # Abstandsregeln brauchen keine Schriftfarbe.
                if "background" not in block.lower():
                    continue
                if "color:" in block.lower().replace("background-color:", ""):
                    continue
                ohne.append((pfad.name, treffer.group(0)[:60].replace("\n", " ")))
        if ohne:
            self.fail(
                u"%d Codeblock-Stile setzen einen Hintergrund, aber keine "
                u"Schriftfarbe:\n%s\n\nAuf dunklem Grund steht der Inhalt dann "
                u"dunkel auf dunkel. Immer beides setzen."
                % (len(ohne), "\n".join("    %s: %s" % (a, b) for a, b in ohne[:10])))


class GegenprobeTest(SimpleTestCase):
    u"""Greifen die Muster?"""

    def test_extends_wird_erkannt(self):
        self.assertTrue(_EXTENDS.search('{% extends "djangobase/base.html" %}'))
        self.assertTrue(_EXTENDS.search("{% extends 'dashboard/base.html' %}"))

    def test_eigenes_html_wird_erkannt(self):
        self.assertTrue(_HTML_TAG.search("<!doctype html><html lang='de'>"))

    def test_teilvorlagen_bleiben_draussen(self):
        self.assertTrue(_teilvorlage(Path("_tabelle.html")))
        self.assertFalse(_teilvorlage(Path("kurse.html")))

    def test_farbloser_pre_stil_wird_erkannt(self):
        treffer = list(_PRE_STIL.finditer("pre { background: #111; padding: 6px; }"))
        self.assertTrue(treffer)
        self.assertNotIn("color:", treffer[0].group(2).replace("background-color:", ""))

    def test_pre_mit_farbe_ist_still(self):
        treffer = list(_PRE_STIL.finditer("pre { background:#111; color:#eee; }"))
        self.assertTrue(treffer)
        self.assertIn("color:", treffer[0].group(2).replace("background-color:", ""))
