# -*- coding: utf-8 -*-
u"""Findet djangoBase seinen eigenen Einbindungs-Praefix?

DER BEFUND (27.08.2026, gemessen in 3DTools)
============================================
3DTools bindet djangoBase unter ``/help/`` ein, nicht unter ``/hilfe/``. Vier
mitgelieferte JS-Module hatten ``/hilfe/tests/aufzeichnung/`` fest im Text und
liefen damit bei JEDEM Seitenaufruf dreimal in eine 404 — ohne Fehlerseite,
ohne Eintrag im Fehlerlog. Gefunden wurde es erst durch eine Browserprobe, die
auf Antwortcodes >= 400 achtet; kein Test und kein Seitenaufruf sah es.

Serverseitig war dasselbe kaputt: Der Ausschluss „die Aufzeichnung zeichnet
sich nicht selbst auf" verglich gegen ``/hilfe/…`` und griff dort ins Leere.

WAS HIER GEPRUEFT WIRD
======================
Erstens die Rechnung selbst (`Basiswurzel.weg`), zweitens — und das ist der
eigentliche Waechter — dass in den ausgelieferten JS-Dateien KEINE Adresse mit
festem Praefix mehr steht. Ein Kommentar darf ``/hilfe/`` nennen, eine
Zuweisung nicht.
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.basiswurzel import Basiswurzel

#: Wo die mitgelieferten Module liegen.
JS = Path(__file__).resolve().parents[2] / "static" / "djangobase" / "js"

#: Eine Zeichenkette, die mit dem alten festen Praefix beginnt. Nur in
#: Anfuehrungszeichen — ein Kommentar darf den Pfad zur Erklaerung nennen.
FESTER_PFAD = re.compile(r"""['"]/hilfe/""")


class WurzelRechnungTest(SimpleTestCase):
    u"""`weg()` liefert den Praefix, unter dem die Routen wirklich haengen."""

    def test_wurzel_endet_auf_schraegstrich(self):
        wurzel = Basiswurzel.weg()
        self.assertTrue(wurzel.startswith("/"), wurzel)
        self.assertTrue(wurzel.endswith("/"), wurzel)

    def test_wurzel_passt_zur_echten_route(self):
        from django.urls import reverse
        self.assertEqual(reverse("djangobase:tests_aufzeichnung"),
                         Basiswurzel.weg() + "tests/aufzeichnung/")

    def test_unbekannter_anker_faellt_auf_hilfe_zurueck(self):
        u"""Lieber der historische Wert als ein falsch abgeschnittener Pfad."""
        anker = Basiswurzel.ANKER
        Basiswurzel.ANKER = "djangobase:gibtesnicht"
        try:
            self.assertEqual(Basiswurzel.weg(), Basiswurzel.ERSATZ)
        finally:
            Basiswurzel.ANKER = anker

    def test_verschobener_anker_faellt_zurueck(self):
        u"""Haengt die Ankerroute woanders, ist der Rueckschluss ungueltig."""
        weg = Basiswurzel.ANKERWEG
        Basiswurzel.ANKERWEG = "ganzwoanders/"
        try:
            self.assertEqual(Basiswurzel.weg(), Basiswurzel.ERSATZ)
        finally:
            Basiswurzel.ANKERWEG = weg


class KeineFestenAdressenTest(SimpleTestCase):
    u"""DER WAECHTER: kein ausgeliefertes Modul verdrahtet mehr ``/hilfe/``."""

    def test_kein_js_modul_verdrahtet_den_praefix(self):
        treffer = []
        for datei in sorted(JS.glob("*.js")):
            # `basiswurzel.js` selbst FUEHRT den Ersatzwert — das ist
            # die eine Stelle, an der er stehen darf.
            if datei.name == "basiswurzel.js":
                continue
            for nr, zeile in enumerate(
                    datei.read_text(encoding="utf-8").splitlines(), 1):
                if FESTER_PFAD.search(zeile):
                    treffer.append("%s:%d  %s" % (datei.name, nr,
                                                  zeile.strip()[:80]))
        self.assertEqual(treffer, [], "\n".join(
            ["Feste djangoBase-Adressen — in einem Projekt mit anderem "
             "Praefix sind das stille 404er. `Basiswurzel.weg(...)` benutzen:"]
            + treffer))

    def test_die_gegenprobe_wuerde_anschlagen(self):
        u"""Sabotage: Der Waechter muss den alten Zustand erkennen."""
        self.assertTrue(FESTER_PFAD.search(
            "const PFAD = '/hilfe/tests/aufzeichnung/';"))
        self.assertIsNone(FESTER_PFAD.search(
            "// frueher stand hier /hilfe/tests/aufzeichnung/"))
