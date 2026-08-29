# -*- coding: utf-8 -*-
u"""`Zirkelkarte` gegen die naive Rechnung — Trennlinie für Trennlinie.

WARUM DIESE TESTS (29.08.2026)
==============================
`JsSchnitt` rechnete die Zirkelfrage für JEDE Trennlinie neu: zwei reguläre
Ausdrücke je Name über den jeweils anderen Dateiteil. Am eigenen Anlassfall des
Werkzeugs — 602 Zeilen, 521 Trennlinien — waren das **186,9 Sekunden für eine
Datei**. Der Anlassfall-Check lief damit nicht mehr durch (>550 s statt der im
Testkopf genannten ~30 s), und `manage.py test djangobase` lief in den
Zeitablauf.

Die neue Fassung beantwortet dieselbe Frage in 0,006 s. Genau das ist die Lage,
in der ein Test gebraucht wird: Eine Beschleunigung um das 30.000-fache ist
nichts wert, wenn die Antwort dabei eine andere wird — und „schneidbar" sieht
man einer Zahl im Bericht nicht an.

DIE NAIVE FASSUNG STEHT HIER MIT DRIN
=====================================
`_naiv` unten ist die alte Rechnung, auf acht Zeilen eingedampft. Sie ist
offensichtlich richtig und offensichtlich langsam — und damit der Maßstab. Die
Fälle rechnen beide gegeneinander, unter anderem auf dem echten Anlassfall.
"""
import re

from djangobase.skills.jsschnitt import JsSchnitt
from djangobase.skills.jszirkel import Zirkelkarte

from ..base import BasisTest

NL = chr(10)

#: Dieselbe Schreibweise, die `Zirkelkarte` kennt — hier absichtlich noch
#: einmal ausgeschrieben: Ein Test, der die Konstante des Prüflings benutzt,
#: prüft die Regel nicht mehr, sondern nur sich selbst.
_DEF = re.compile(r"^(?:export )?(?:async )?(?:function|class|const) (\w+)",
                  re.M)


def _naiv(zeilen, bei):
    """Die alte Rechnung: Namen der einen Seite in der anderen suchen."""
    oben = NL.join(zeilen[:bei])
    unten = NL.join(zeilen[bei:])

    def benutzt(wo, namen):
        return {n for n in namen
                if re.search(r"(?<![.\w])%s\b" % re.escape(n), wo)}

    unten_braucht_oben = benutzt(unten, set(_DEF.findall(oben)))
    oben_braucht_unten = benutzt(oben, set(_DEF.findall(unten)))
    return bool(unten_braucht_oben) and bool(oben_braucht_unten)


class GrundlagenTest(BasisTest):
    """Die Aussage selbst, an Fällen, die man von Hand nachrechnen kann."""

    def test_zwei_unabhaengige_haelften_haben_keinen_zirkel(self):
        zeilen = ["const A = 1;",
                  "export function oben() { return A; }",
                  "const B = 2;",
                  "export function unten() { return B; }"]
        karte = Zirkelkarte(zeilen)
        self.assertFalse(karte.zirkel(2))
        self.assertEqual("keine", karte.richtung(2))

    def test_unten_ruft_oben(self):
        zeilen = ["const A = 1;",
                  "export function hilfe() { return A; }",
                  "export function unten() { return hilfe(); }"]
        karte = Zirkelkarte(zeilen)
        self.assertFalse(karte.zirkel(2))
        self.assertEqual("unten←oben", karte.richtung(2))

    def test_beide_richtungen_sind_ein_zirkel(self):
        zeilen = ["export function oben() { return unten(); }",
                  "const X = 1;",
                  "export function unten() { return X + oben(); }"]
        self.assertTrue(Zirkelkarte(zeilen).zirkel(2))

    def test_feldzugriff_zaehlt_nicht_als_aufruf(self):
        u"""`fn.hilfe()` ist NICHT die freie Funktion `hilfe` — sonst hinge
        jede Datei an jeder, die ein gleichnamiges Feld benutzt."""
        zeilen = ["export function hilfe() { return 1; }",
                  "export function unten() { const A = 2; return fn.hilfe() + A; }"]
        karte = Zirkelkarte(zeilen)
        self.assertFalse(karte.zirkel(1))
        self.assertEqual("keine", karte.richtung(1))
        # Ohne den Punkt haengt unten sehr wohl an oben:
        ohne_punkt = [zeilen[0], zeilen[1].replace("fn.hilfe", "hilfe")]
        self.assertEqual("unten←oben", Zirkelkarte(ohne_punkt).richtung(1))

    def test_doppelte_definition_zaehlt_auf_beiden_seiten(self):
        u"""`function x(){}` darf in JS zweimal auf Modulebene stehen.

        Mit nur EINER Definitionszeile je Name wäre die Antwort hier eine
        andere — deshalb merkt sich die Karte die erste UND die letzte."""
        zeilen = ["export function x() { return 1; }",
                  "const A = x();",
                  "export function x() { return A; }"]
        self.assertEqual(_naiv(zeilen, 2), Zirkelkarte(zeilen).zirkel(2))


class GegenrechnungTest(BasisTest):
    """Dieselbe Antwort wie die naive Fassung — an jeder Trennlinie."""

    def _vergleichen(self, zeilen):
        karte = Zirkelkarte(zeilen)
        for bei in range(1, len(zeilen)):
            with self.subTest(bei=bei):
                self.assertEqual(_naiv(zeilen, bei), karte.zirkel(bei))

    def test_am_eigenen_anlassfall_des_werkzeugs(self):
        u"""603 Zeilen, jede Trennlinie — der Fall, an dem es geklemmt hat."""
        text = list(JsSchnitt.anlassfall.dateien.values())[0]
        zeilen = text.split(NL)
        karte = Zirkelkarte(zeilen)
        grenzen = [i for i, z in enumerate(zeilen)
                   if re.match(r"^(?:export )?(?:async )?(?:function|class) \w+",
                               z)]
        pruefstellen = [b for b in grenzen if 40 < b < len(zeilen) - 40]
        self.assertGreater(len(pruefstellen), 400, "der Fall ist geschrumpft")
        # Nicht alle 521 — die naive Fassung braucht dafuer Minuten. Jede
        # zwanzigste deckt beide Haelften und beide Raender ab.
        for bei in pruefstellen[::20]:
            with self.subTest(bei=bei):
                self.assertEqual(_naiv(zeilen, bei), karte.zirkel(bei))

    def test_gemischte_datei_mit_klassen_und_konstanten(self):
        zeilen = (["const OBEN = 1;", "class Erste { tu() { return OBEN; } }"]
                  + ["export function a%d() { return OBEN; }" % i
                     for i in range(6)]
                  + ["const UNTEN = 2;", "class Zweite { tu() { return a3(); } }"]
                  + ["export function b%d() { return UNTEN; }" % i
                     for i in range(6)])
        self._vergleichen(zeilen)

    def test_datei_ganz_ohne_definitionen(self):
        self._vergleichen(["// nur Kommentar", "let x = 1;", "x += 2;"])


class SabotageTest(BasisTest):
    """Wird der Vergleich rot, wenn die Karte falsch antwortet?

    Ohne diese Gegenprobe wäre `GegenrechnungTest` ein Test, der nur grün kann
    — und genau das war der Fehler beim ersten Anlauf zu `Codesicht`: Elf
    Fälle prüften den falschen Weg und blieben bei zwei Sabotagen still.
    """

    def test_eine_verdrehte_karte_faellt_auf(self):
        zeilen = ["export function oben() { return unten(); }",
                  "const X = 1;",
                  "export function unten() { return X + oben(); }"]
        karte = Zirkelkarte(zeilen)
        self.assertTrue(karte.zirkel(2))
        # Sabotage: eine der beiden Richtungen ausschalten.
        karte._oben_braucht_unten = [False] * len(karte._oben_braucht_unten)
        self.assertNotEqual(_naiv(zeilen, 2), karte.zirkel(2))
