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

from djangobase.tests.konform.quellen import TABU, dateien, text_von, wurzel  # noqa: F401

#: DATEINAMEN, die legitim ein eigenes ``<html>`` haben: E-Mails, PDF-Vorlagen,
#: Fehlerseiten (die Sidebar braucht einen Kontext, den es dort nicht gibt).
#:
#: ``login``/``logout`` kam am 21.08.2026 dazu: Die Anmeldeseite läuft VOR der
#: Anmeldung. Eine Seitenleiste mit Menü, Konto und Versionsnummer hätte dort
#: nichts anzuzeigen — genau wie auf einer Fehlerseite.
EIGEN_ERLAUBT = ("mail", "email", "pdf", "druck", "print", "400.html",
                 "403.html", "404.html", "500.html", "base",
                 "login", "logout")

#: ORDNER, in denen dasselbe gilt. Getrennt von den Dateinamen, weil ein
#: Teilstring wie „mail“ sonst im PFAD jedes Projekts mit einer Mail-App steht
#: und die ganze App von der Prüfung ausnähme.
EIGEN_ERLAUBT_ORDNER = ("/registration/", "/allauth/", "/account/")

_EXTENDS = re.compile(r"{%\s*extends\s+[\"']?([^\"'%\s]+)")
_HTML_TAG = re.compile(r"<html\b", re.IGNORECASE)

#: Eine CSS-Regel, deren Selektor ``pre`` oder ``code`` nennt.
#:
#: FEHLALARM VOM 21.08.2026: Die erste Fassung suchte ``\b(pre|code)\b[^{}]*\{``
#: im ganzen Dokument. In ``chat_personal.html`` stand in einem JS-Kommentar
#: „Code wie in chat.html, hier dupliziert …“ — und dahinter ``function
#: showContextWarning(data) {``. Gemeldet wurde ein Kontrastfehler in einer
#: Datei ohne jeden ``<pre>``-Stil. Deshalb jetzt zweistufig: erst der
#: ``<style>``-Block, dann eine Regel, deren Selektor in EINER Zeile steht.
_STILBLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_PRE_STIL = re.compile(
    r"(?:\A|[};\n])[ \t]*([^{}\n;]*(?<![\w-])(?:pre|code)(?![\w-])[^{}\n;]*)"
    r"\{([^}]*)\}", re.IGNORECASE)


def _vorlagen():
    return dateien(".html")


def _stil_regeln(text):
    u"""[(selektor, block)] aller ``pre``/``code``-Regeln in ``<style>``."""
    aus = []
    for stil in _STILBLOCK.findall(text):
        for treffer in _PRE_STIL.finditer(stil):
            aus.append((treffer.group(1).strip(), treffer.group(2)))
    return aus


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
            if any(w in pfad.name.lower() for w in EIGEN_ERLAUBT):
                continue
            weg = str(pfad).replace("\\", "/").lower()
            if any(w in weg for w in EIGEN_ERLAUBT_ORDNER):
                continue
            text = text_von(pfad)
            if text is None:
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
        u"""Kein Skip: „nicht benutzt" ist ein ERGEBNIS, kein Ausfall.

        Hier stand ``skipTest("keine fa-*-Icons im Projekt")``. Ein
        übersprungener Test meldet grün, ohne etwas geprüft zu haben —
        und dann sieht niemand, ob die Bedingung noch stimmt oder ob der
        Sucher kaputt ist. Die Frage ist eine einzige Zusicherung: Wer
        ``fa-*`` benutzt, muss die Schrift einbinden. Wer sie nicht
        benutzt, erfüllt das ebenfalls.
        """
        wo = self._benutzt("fa-")
        self.assertTrue(
            wo is None
            or self._eingebunden("fontawesome")
            or self._eingebunden("font-awesome"),
            u"%s nutzt fa-*-Icons, aber FontAwesome ist nirgends eingebunden — "
            u"dort stehen leere Kästchen." % (wo.name if wo else "?"))


class KontrastTest(SimpleTestCase):
    u"""Kein Codeblock ohne gesetzte Schriftfarbe."""

    def test_pre_und_code_setzen_ihre_farbe(self):
        u"""Ein ``<pre>``-Stil, der Hintergrund und Rahmen setzt, aber keine
        ``color``, steht auf dunklem Grund dunkel auf dunkel."""
        ohne = []
        for pfad in _vorlagen():
            text = text_von(pfad)
            if text is None:
                continue
            for selektor, block in _stil_regeln(text):
                # Nur Regeln, die überhaupt Farben anfassen - reine
                # Abstandsregeln brauchen keine Schriftfarbe.
                if "background" not in block.lower():
                    continue
                if "color:" in block.lower().replace("background-color:", ""):
                    continue
                ohne.append((pfad.name, "%s { %s"
                             % (selektor, " ".join(block.split())[:50])))
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
        regeln = _stil_regeln("<style>pre { background: #111; padding: 6px; }</style>")
        self.assertEqual(len(regeln), 1)
        self.assertNotIn("color:", regeln[0][1].replace("background-color:", ""))

    def test_pre_mit_farbe_ist_still(self):
        regeln = _stil_regeln("<style>pre { background:#111; color:#eee; }</style>")
        self.assertEqual(len(regeln), 1)
        self.assertIn("color:", regeln[0][1].replace("background-color:", ""))

    def test_prosa_wird_nicht_als_stil_gelesen(self):
        u"""Der Fehlalarm vom 21.08.2026: ein Kommentar mit dem Wort „Code“,
        gefolgt von einem beliebigen Block. Ohne diese Gegenprobe schleicht er
        sich beim nächsten Umbau des Musters wieder ein."""
        quelle = ('<script>\n'
                  '/* Code wie in chat.html, hier dupliziert weil beide\n'
                  ' * Templates sich kein Skript teilen. */\n'
                  'function zeigen(daten) { var banner = "background"; }\n'
                  '</script>')
        self.assertEqual(_stil_regeln(quelle), [])

    def test_regel_ausserhalb_von_style_zaehlt_nicht(self):
        u"""Ein ``pre { … }`` im Fließtext einer Hilfeseite ist Doku, kein Stil."""
        self.assertEqual(_stil_regeln("<p>Beispiel: pre { background: #111; }</p>"), [])

    def test_mehrzeiliger_stil_wird_gefunden(self):
        u"""Die übliche Schreibweise — sonst prüfte das Muster nur Einzeiler."""
        quelle = ("<style>\n  pre {\n    background: #0d1626;\n"
                  "    border: 1px solid #333;\n  }\n</style>")
        self.assertEqual(len(_stil_regeln(quelle)), 1)
