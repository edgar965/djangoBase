# -*- coding: utf-8 -*-
u"""Groesse wird an CODE gemessen, nicht an Zeilen.

DER FEHLALARM (03.09.2026, shortlongx)
======================================
``dateigroesse`` meldete 239 Stellen. Von den 78 Datei-Befunden lagen **74**
allein an der Dokumentation: ``menue.py`` hat 781 Zeilen und davon 290 Code -
der Befund verlangte, eine Datei aufzuteilen, die unter der Grenze liegt.

Viele Dateien in diesen Projekten tragen ihre Herleitung im Kopf, manchmal
zweihundert Zeilen. Eine Groessenpruefung, die nur Zeilen zaehlt, verlangt das
Zerschneiden genau dieser Dokumentation.

Dasselbe bei ``klassen-je-datei``: Von 36 Warnungen waren **34** keine -
drei Attrappen-Module (wo mehrere Klassen zusammengehoeren) und 31 Dateien
unter 300 Code-Zeilen, bei denen Aufteilen die Uebersicht verschlechtert.

WAS HIER GEPRUEFT WIRD
======================
Beide Richtungen. Der Fehlalarm muss weg sein UND eine wirklich zu grosse
Datei muss weiter gemeldet werden.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.dateigroesse import Dateigroesse
from djangobase.skills.klassenjedatei import KlassenJeDatei
from djangobase.skills.werkzeug import Quelldatei

#: 400 Zeilen Herleitung, 10 Zeilen Code.
VIEL_DOKU = ('u"""\n' + "Begruendung, warum die Rundung so ist.\n" * 400 + '"""\n'
             + "".join("wert_%d = %d\n" % (i, i) for i in range(10)))

#: 400 Zeilen Code, keine Doku.
VIEL_CODE = "".join("wert_%d = %d\n" % (i, i) for i in range(400))


class _Groesse(Dateigroesse):
    u"""Sucht in einem Wegwerf-Verzeichnis statt im Projekt."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(self._ordner.rglob(muster))

    def frontendquellen(self):
        class _Leer:
            @staticmethod
            def paare(_endung):
                return []
        return _Leer()


class _Klassen(KlassenJeDatei):

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(self._ordner.rglob(muster))

    def projektdateien(self, endung=".py", **_weitere):
        return sorted(self._ordner.rglob("*" + endung))

    def kurz(self, datei):
        return Path(datei).name


def _lauf(klasse, dateien, **argumente):
    with tempfile.TemporaryDirectory() as ordner:
        for name, inhalt in dateien.items():
            ziel = Path(ordner) / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        werkzeug = klasse(ordner)
        return (werkzeug.laufen() if klasse is _Groesse
                else werkzeug.pruefen(**argumente))


class CodezeilenTest(SimpleTestCase):
    u"""Die Zaehlung selbst - Kommentare aus ``tokenize``, Docstrings aus AST."""

    def _zaehlen(self, text):
        u"""``(Code-Zeilen, Zeilen gesamt, Quelldatei)``.

        Die Werte werden NOCH IM Kontext geholt: ``Quelldatei`` liest träge,
        und nach dem ``with`` ist der Wegwerf-Ordner weg. ``text`` fängt den
        ``OSError`` still ab — die Zählung wäre dann überall 0, und der Test
        hätte nichts gemessen (genau so ist er beim Schreiben zuerst
        durchgefallen)."""
        with tempfile.TemporaryDirectory() as ordner:
            p = Path(ordner) / "x.py"
            p.write_text(text, encoding="utf-8")
            d = Quelldatei(p, Path(ordner))
            return d.codezeilen, d.zeilen, d

    def test_docstring_zaehlt_nicht_als_code(self):
        code, gesamt, _d = self._zaehlen('u"""eins\nzwei\ndrei"""\na = 1\n')
        self.assertEqual(code, 1, "nur ``a = 1`` ist Code")
        self.assertEqual(gesamt, 5)

    def test_kommentarzeile_zaehlt_nicht(self):
        code, _g, _d = self._zaehlen("# nur ein Kommentar\na = 1\n")
        self.assertEqual(code, 1)

    def test_kommentar_HINTER_code_laesst_die_zeile_code(self):
        u"""Sonst fällt jede gut kommentierte Zeile aus der Zählung."""
        code, _g, _d = self._zaehlen("a = 1  # erklaert\nb = 2  # erklaert\n")
        self.assertEqual(code, 2)

    def test_ein_string_in_einer_zuweisung_ist_code(self):
        u"""Nur ein ALLEIN stehendes Literal ist Dokumentation.

        Die aeltere, zeilenweise Heuristik prueft auf drei Anfuehrungszeichen
        am Zeilenanfang. Sie uebersieht das ``u``-Praefix und zaehlt danach
        ganze Codebloecke als Docstring - gemessen an einer Datei mit
        mindestens 406 Code-Zeilen, die sie mit 138 auswies."""
        code, _g, _d = self._zaehlen('TEXT = u"""eins\nzwei\ndrei"""\n')
        self.assertEqual(code, 3, "eine Zuweisung ist Code")

    def test_bereich_zaehlt_nur_seine_zeilen(self):
        _c, _g, d = self._zaehlen('def f():\n    """Doku"""\n'
                                  '    a = 1\n    b = 2\n')
        self.assertEqual(d.codezeilen_zwischen(1, 4), 3)


class DateigroesseTest(SimpleTestCase):

    def test_viel_doku_ist_kein_befund(self):
        erg = _lauf(_Groesse, {"lang.py": VIEL_DOKU})
        dateien = [z for z in erg.zeilen if z["art"] == "Datei"]
        self.assertEqual(dateien, [], "411 Zeilen, davon 10 Code")

    def test_die_zahl_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertuer."""
        erg = _lauf(_Groesse, {"lang.py": VIEL_DOKU})
        self.assertIn("nur durch Doku", erg.zusammenfassung)

    def test_viel_code_bleibt_ein_befund(self):
        u"""DIE GEGENPROBE: Der Waechter muss weiter anschlagen."""
        erg = _lauf(_Groesse, {"gross.py": VIEL_CODE})
        dateien = [z for z in erg.zeilen if z["art"] == "Datei"]
        self.assertEqual(len(dateien), 1, erg.zusammenfassung)
        self.assertEqual(dateien[0]["code"], 400)
        self.assertGreaterEqual(dateien[0]["gesamt"], 400)


class KlassenZusammenTest(SimpleTestCase):

    #: Zwei Klassen mit je gut 40 Zeilen - beide gelten als eigenstaendig.
    ZWEI_GROSSE = ("class Eine:\n"
                   + "".join("    a%d = %d\n" % (i, i) for i in range(45))
                   + "\n\nclass Andere:\n"
                   + "".join("    b%d = %d\n" % (i, i) for i in range(45)))

    def _warnungen(self, dateien):
        satz = _lauf(_Klassen, dateien)
        return [b for b in satz.befunde if b.gewicht == "warnung"]

    def test_kleine_datei_ist_kein_verstoss(self):
        u"""Unter 300 Code-Zeilen macht Aufteilen die Uebersicht schlechter."""
        self.assertEqual(self._warnungen({"klein.py": self.ZWEI_GROSSE}), [])

    def test_attrappen_gehoeren_zusammen(self):
        gross = self.ZWEI_GROSSE + "".join("x%d = %d\n" % (i, i) for i in range(320))
        self.assertEqual(self._warnungen({"ding_attrappe.py": gross}), [])

    def test_models_gehoeren_zusammen(self):
        u"""Django FINDET seine Modelle in ``models.py``."""
        gross = self.ZWEI_GROSSE + "".join("x%d = %d\n" % (i, i) for i in range(320))
        self.assertEqual(self._warnungen({"models.py": gross}), [])

    def test_grosse_datei_bleibt_ein_verstoss(self):
        u"""DIE GEGENPROBE: zwei eigenstaendige Klassen, 300+ Code-Zeilen."""
        gross = self.ZWEI_GROSSE + "".join("x%d = %d\n" % (i, i) for i in range(320))
        self.assertEqual(len(self._warnungen({"dienst.py": gross})), 1)

    def test_der_grund_steht_am_hinweis(self):
        u"""Ausgenommenes wird genannt, nicht verschwiegen."""
        satz = _lauf(_Klassen, {"klein.py": self.ZWEI_GROSSE})
        self.assertTrue(any("Aufteilen schadet" in b.warum for b in satz.befunde),
                        [b.warum for b in satz.befunde])
