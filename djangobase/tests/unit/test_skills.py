# -*- coding: utf-8 -*-
u"""Tests fuer den Skills2-Werkzeugkasten.

Skills2 liegt in djangoBase und laeuft damit in SECHS Projekten. Ein Werkzeug,
das dort eine Ausnahme wirft, zerlegt eine Hilfe-Seite, die jemand gerade
braucht. Deshalb haelt dieser Test drei Dinge fest:

1. Jedes registrierte Werkzeug laeuft durch und liefert ein ``Ergebnis``, dessen
   Zeilen zu den angekuendigten Spalten passen. Gepruoft wird gegen ein
   ANGELEGTES Mini-Projekt, nicht gegen das Host-Projekt: Sonst haengt das
   Ergebnis davon ab, wo der Test gerade laeuft.
2. Die Werkzeuge FINDEN auch etwas - fuer jede Fehlerart wird eine Datei
   angelegt, die sie enthaelt, und eine Gegenprobe ohne den Fehler.
3. Die Marker (``geteilt gewollt``, ``Dictionary gewollt``,
   ``in der Schleife gewollt``) stufen einen Befund ab. Ohne diesen Test faellt
   ein kaputter Marker erst auf, wenn jemand eine Ausnahmeliste vermisst.
"""
import tempfile
from pathlib import Path

from django.test import override_settings

from djangobase.skills import (KRITERIEN, LEHREN, OHNE_WERKZEUG, WERKZEUGE,
                                gruppen, werkzeug_finden, werkzeuge)
from djangobase.skills.werkzeug import Ergebnis, Werkzeug2

from ..base import BasisTest


class MiniProjekt:
    """Ein winziges Projekt auf der Platte - Grundlage aller Werkzeug-Tests."""

    def anlegen(self, testfall):
        ordner = Path(tempfile.mkdtemp(prefix="skills2_"))
        testfall.addCleanup(self._weg, ordner)
        return ordner

    @staticmethod
    def _weg(ordner):
        import shutil
        shutil.rmtree(ordner, ignore_errors=True)

    @staticmethod
    def schreiben(ordner, name, inhalt):
        pfad = ordner / name
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8")
        return pfad


class WerkzeugGrundlagenTest(BasisTest):
    """Was fuer JEDES Werkzeug gelten muss."""

    def test_registrierung_vollstaendig(self):
        self.assertTrue(WERKZEUGE, "keine Werkzeuge registriert")
        slugs = [k.slug for k in WERKZEUGE]
        self.assertEqual(len(slugs), len(set(slugs)), "doppelte Kennung: %s" % slugs)
        for klasse in WERKZEUGE:
            self.assertTrue(klasse.titel, "%s ohne Titel" % klasse.__name__)
            self.assertTrue(klasse.zweck, "%s ohne Zweck" % klasse.__name__)
            # Der Fall dahinter ist der Grund, warum es das Werkzeug gibt -
            # ohne ihn ist es eine Formalie.
            self.assertTrue(klasse.befund, "%s ohne Fall" % klasse.__name__)
            self.assertIn(klasse.kriterium, KRITERIEN,
                          "%s nennt Kriterium %s, das es nicht gibt"
                          % (klasse.__name__, klasse.kriterium))

    def test_finden(self):
        self.assertIsNone(werkzeug_finden("gibtesnicht"))
        self.assertIsNotNone(werkzeug_finden(WERKZEUGE[0].slug))

    #: Werkzeuge, die den PROJEKTCODE gar nicht ansehen. ``wachstum`` misst, wie
    #: sich Python-Bauformen auf DIESER Maschine verhalten - es liefert seine
    #: sechs Messzeilen auch in einem leeren Ordner, und das ist richtig so.
    #: (16.08.2026: Der Test war rot, ohne dass etwas kaputt war - genau die
    #: Sorte, die man abschaltet statt zu verstehen.)
    #: `seitenzeiten` fragt die URL-Konfiguration des HOSTS, nicht das
    #: Verzeichnis — es findet auch in einem leeren Ordner Seiten, und
    #: das ist richtig so (17.08.2026).
    #: `anlassfall-check` laeuft ueber die WERKZEUGE, nicht ueber das Projekt:
    #: Es baut jedem Werkzeug seinen eigenen Anlassfall nach und berichtet je
    #: Werkzeug eine Zeile — auch im leeren Ordner, und das ist der Zweck.
    #: (Der Test war seit Commit f2e691b rot: Das Werkzeug stand in WERKZEUGE,
    #: aber nicht hier. Nachgetragen am 17.08.2026.)
    #:
    #: Die vier `vorlagen-*`/`endpunkt-*` kamen mit dem Zusammenlegen dazu
    #: (17.08.2026). Sie stammen aus dem aelteren Kasten und fragen bewusst
    #: DJANGO — die Vorlagen-Engine und die URL-Tabelle —, nicht das
    #: Verzeichnis. Ein `override_settings(BASE_DIR=…)` erreicht sie deshalb
    #: nicht: Sie sehen weiter die Vorlagen und Routen des laufenden Projekts.
    #: Das ist ihr Bauprinzip („Django nach seinen eigenen Vorlagen und Routen
    #: fragen, statt Pfade zu raten") und kein Fehler — nur eben nichts, was
    #: dieser Test messen kann.
    OHNE_PROJEKTCODE = {"wachstum", "seitenzeiten", "anlassfall-check",
                        "vorlagen-kontext", "vorlagen-variablen",
                        "endpunkt-zeiten", "endpunkt-profil"}

    def test_alle_laufen_auf_leerem_projekt(self):
        """Ein Projekt ohne Code darf kein Werkzeug zum Absturz bringen."""
        ordner = MiniProjekt().anlegen(self)
        with override_settings(BASE_DIR=str(ordner)):
            for w in werkzeuge():
                ergebnis = w.laufen()
                self.assertIsInstance(ergebnis, Ergebnis,
                                      "%s liefert kein Ergebnis" % w.slug)
                if w.slug in self.OHNE_PROJEKTCODE:
                    self.assertTrue(ergebnis.zeilen,
                                    "%s misst Python selbst und muss auch im "
                                    "leeren Projekt etwas liefern" % w.slug)
                    continue
                self.assertEqual(ergebnis.zeilen, [],
                                 "%s findet etwas in einem leeren Projekt" % w.slug)

    def test_zeilen_passen_zu_spalten(self):
        """Jede Zeile muss die angekündigten Spalten tragen - sonst steht in der
        Tabelle und im Bericht eine leere Zelle, ohne dass jemand es merkt."""
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN)
        MiniProjekt.schreiben(ordner, "static/app.js", BEISPIEL_JS)
        with override_settings(BASE_DIR=str(ordner)):
            for w in werkzeuge():
                ergebnis = w.laufen()
                for zeile in ergebnis.zeilen:
                    fehlend = [s for s in ergebnis.spalten if s not in zeile]
                    self.assertFalse(fehlend, "%s: Spalte(n) %s fehlen in %s"
                                     % (w.slug, fehlend, zeile))


#: Eine Datei, die MEHRERE der gesuchten Muster enthaelt.
BEISPIEL_MIT_FEHLERN = '''# -*- coding: utf-8 -*-
"""Beispielmodul fuer die Tests."""
import json
from pathlib import Path

GETEILT = []                    # veraenderlicher Zustand auf Modulebene


def fuellen(pfad):
    GETEILT.append(pfad)


def datensatz(a, b):
    return {"eins": 1, "zwei": 2, "drei": 3, "vier": 4}


def tupel(a, b):
    return a, b, a + b, a - b, a * b


def lesen(pfade):
    """DIESELBE Datei je Durchlauf - das ist der Befund."""
    aus = []
    for p in pfade:
        kopf = Path("vorlage.txt").read_text()
        aus.append(kopf + p)
    return aus


def lesen_ok(pfade):
    """Je Durchlauf eine ANDERE Datei - das ist der Zweck, kein Befund."""
    aus = []
    for p in pfade:
        aus.append(Path(p).read_text())
    return aus
'''

BEISPIEL_JS = """import { Fehlt } from './gibtesnicht.js';
export class App {}
"""


class ModulZustandTest(BasisTest):
    """Kriterium 9 - und der Marker, der einen Befund abstuft."""

    def test_findet_geteilten_zustand(self):
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN)
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("modulzustand").laufen().zeilen
        namen = [z["name"] for z in zeilen]
        self.assertIn("GETEILT", namen)
        self.assertEqual([z["bewertung"] for z in zeilen if z["name"] == "GETEILT"],
                         ["prüfen"])

    def test_marker_stuft_ab(self):
        """Gegenprobe: mit Vermerk im Code ist derselbe Fund „belegt"."""
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN.replace(
            "GETEILT = []                    # veraenderlicher Zustand auf Modulebene",
            "# geteilt gewollt: ein Vorrat je Server\nGETEILT = []"))
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("modulzustand").laufen().zeilen
        belegt = [z["bewertung"] for z in zeilen if z["name"] == "GETEILT"]
        self.assertEqual(belegt, ["belegt"],
                         "Der Vermerk „geteilt gewollt" + '" wirkt nicht mehr')


class RueckgabeTest(BasisTest):
    """Kriterien 10 und 11."""

    def test_dictionary_und_tupel(self):
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN)
        with override_settings(BASE_DIR=str(ordner)):
            dicts = werkzeug_finden("rueckgabedict").laufen().zeilen
            tupel = werkzeug_finden("rueckgabetupel").laufen().zeilen
        self.assertEqual([z["funktion"] for z in dicts], ["datensatz"])
        self.assertEqual([z["funktion"] for z in tupel], ["tupel"])
        self.assertEqual(tupel[0]["felder"], 5)

    def test_dictionary_marker(self):
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN.replace(
            "def datensatz(a, b):\n    return {",
            "def datensatz(a, b):\n    # Dictionary gewollt: geht als JSON hinaus\n    return {"))
        with override_settings(BASE_DIR=str(ordner)):
            dicts = werkzeug_finden("rueckgabedict").laufen().zeilen
        self.assertEqual([z["bewertung"] for z in dicts], ["belegt"])


class SchleifenTest(BasisTest):
    """Kriterium 12 - inklusive Marker."""

    def test_findet_lesen_in_schleife(self):
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN)
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("schleifenarbeit").laufen().zeilen
        self.assertTrue(any("read_text" in z["was"] for z in zeilen),
                        "read_text in der Schleife nicht gefunden: %s" % zeilen)

    def test_meldet_nicht_was_an_der_schleifenvariablen_haengt(self):
        """DIE UNTERSCHEIDUNG, die das Werkzeug brauchbar macht (16.08.2026).

        ``Path(p).read_text()`` in einer Schleife über ``p`` liest je Durchlauf
        etwas anderes - das ist der Zweck jedes Werkzeugs, das über Dateien
        läuft. Ohne diese Prüfung meldete das Werkzeug im shortlongx-Lauf 199
        Stellen, von denen 190 genau dieses Muster waren; die neun echten Fälle
        gingen darin unter."""
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN)
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("schleifenarbeit").laufen().zeilen
        treffer = [z for z in zeilen if z["zeile"] >= self._zeile_von(
            BEISPIEL_MIT_FEHLERN, "def lesen_ok")]
        self.assertEqual(treffer, [], "lesen_ok() darf keinen Befund liefern")

    @staticmethod
    def _zeile_von(text, marke):
        for nr, z in enumerate(text.splitlines(), 1):
            if z.startswith(marke):
                return nr
        raise AssertionError("Marke %r nicht im Beispiel" % marke)

    def test_marker_stuft_ab(self):
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "modul.py", BEISPIEL_MIT_FEHLERN.replace(
            '        kopf = Path("vorlage.txt").read_text()',
            "        # in der Schleife gewollt: die Vorlage ändert sich je Lauf\n"
            '        kopf = Path("vorlage.txt").read_text()'))
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("schleifenarbeit").laufen().zeilen
        lesen = [z for z in zeilen if "read_text" in z["was"]]
        self.assertEqual([z["bewertung"] for z in lesen], ["belegt"])


class DoppelrumpfTest(BasisTest):
    """Kriterium 6."""

    def test_findet_zwei_gleiche_rumpfe(self):
        ordner = MiniProjekt().anlegen(self)
        rumpf = ('def rechnen(werte):\n'
                 '    summe = 0\n'
                 '    for w in werte:\n'
                 '        summe += w * 2\n'
                 '    return summe / len(werte)\n')
        MiniProjekt.schreiben(ordner, "a.py", rumpf)
        MiniProjekt.schreiben(ordner, "b.py", rumpf.replace("rechnen", "rechnen2"))
        with override_settings(BASE_DIR=str(ordner)):
            zeilen = werkzeug_finden("doppelrumpf").laufen().zeilen
        self.assertEqual(len(zeilen), 1, "Duplikat nicht erkannt: %s" % zeilen)
        self.assertEqual(zeilen[0]["kopien"], 2)

    def test_verschiedene_rumpfe_sind_kein_befund(self):
        """Gegenprobe - sonst meldet das Werkzeug alles."""
        ordner = MiniProjekt().anlegen(self)
        MiniProjekt.schreiben(ordner, "a.py",
                              'def rechnen(w):\n    x = 1\n    y = 2\n    return x + y\n')
        MiniProjekt.schreiben(ordner, "b.py",
                              'def zaehlen(w):\n    x = 5\n    y = 9\n    return x * y\n')
        with override_settings(BASE_DIR=str(ordner)):
            self.assertEqual(werkzeug_finden("doppelrumpf").laufen().zeilen, [])


class LehrenTest(BasisTest):
    """Die Arbeitsliste - Struktur und Vollstaendigkeit."""

    def test_struktur(self):
        """Seit dem Zusammenlegen (17.08.2026) ist eine Lehre ein Dictionary.

        Vorher waren es Tupel ``(slug, gruppe, titel, tun, fall)`` — die zweite
        Sammlung (3DTools) hatte aber ``Lehre``-Objekte mit weiteren Feldern.
        Beide auf EINE Form zu bringen war billiger, als jede Seite und jeden
        Test beide kennen zu lassen."""
        self.assertTrue(LEHREN)
        slugs = [e["slug"] for e in LEHREN]
        self.assertEqual(len(slugs), len(set(slugs)), "doppelter Lehren-Slug")
        for l in LEHREN:
            self.assertTrue(l["gruppe"] and l["titel"] and l["tun"])
            # Ohne den Fall (oder wenigstens die Begruendung) ist eine Lehre
            # eine Meinung.
            self.assertTrue(l["fall"] or l["warum"],
                            "Lehre %s ohne Fall und ohne Begründung" % l["slug"])
            self.assertIn(l["herkunft"], ("review", "kriterien"))

    def test_gruppen_enthalten_alle(self):
        gezaehlt = sum(len(eintraege) for _, eintraege in gruppen())
        self.assertEqual(gezaehlt, len(LEHREN))

    def test_kriterien_ohne_werkzeug_sind_begruendet(self):
        for nr, titel, text in OHNE_WERKZEUG:
            self.assertIn(nr, KRITERIEN)
            self.assertTrue(titel and len(text) > 40,
                            "Kriterium %s ohne brauchbare Begründung" % nr)
        # Und sie dürfen KEIN Werkzeug haben - sonst gehören sie nicht hierher.
        mit_werkzeug = {k.kriterium for k in WERKZEUGE}
        doppelt = [nr for nr, _, _ in OHNE_WERKZEUG if nr in mit_werkzeug]
        self.assertFalse(doppelt, "Kriterien mit Werkzeug in OHNE_WERKZEUG: %s" % doppelt)
