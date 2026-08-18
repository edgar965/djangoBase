# -*- coding: utf-8 -*-
u"""Tests fuer den Anlassfall-Check (Hilfe -> Skills2).

WARUM ES DIESE TESTS GIBT (17.08.2026)
======================================
Ein Pruefwerkzeug, das nach einem Umbau nichts mehr findet, meldet null - und
null sieht aus wie ein sauberes Projekt. Zweimal an einem Abend war es
stattdessen Blindheit:

* ``getattr-namen`` liess jede Zeichenkette als Beleg gelten und haette seinen
  eigenen Anlassfall (``orb_nacht``) nicht mehr gefunden.
* ``js-vererbung`` haette einen absichtlich globalen Namen als Absturz gemeldet.

Der Check stellt jedem Werkzeug seinen Fall hin. Diese Tests stellen sicher, dass
der Check selbst funktioniert - denn ein blinder Blindheits-Pruefer waere die
teuerste Variante des Fehlers.

DER LAUF DAUERT ~30 SEKUNDEN. Er faehrt jedes Werkzeug zweimal (Anlassfall +
leeres Verzeichnis) und ist damit der langsamste Unit-Test hier. Das ist
gewollt: Er ersetzt die Frage „stimmen die Zahlen noch?", die sonst niemand
stellt.
"""
from djangobase.skills import WERKZEUGE
from djangobase.skills.anlassfall import Anlassfall
from djangobase.skills.anlassfall_check import (ORDNER, AnlassfallCheck,
                                                 Probelauf)

from ..base import BasisTest


class AnlassfallGrundlagenTest(BasisTest):
    """Der Datentyp selbst - schnell, ohne Dateien."""

    def test_zu_wenige_befunde_sind_blind(self):
        fall = Anlassfall({"a.py": "x = 1\n"}, mindestens=1)
        self.assertIn("blind", fall.urteil([]))
        self.assertEqual("", fall.urteil([{"datei": "a.py"}]))

    def test_zu_viele_befunde_heissen_die_ausnahme_greift_nicht(self):
        fall = Anlassfall({"a.py": "x = 1\n"}, mindestens=1, hoechstens=1)
        self.assertIn("zu grob", fall.urteil([{"a": 1}, {"a": 2}]))

    def test_erwartet_in_prueft_die_richtige_stelle(self):
        fall = Anlassfall({"a.py": "x = 1\n"}, erwartet_in="orb_nacht")
        self.assertIn("etwas anderes", fall.urteil([{"feld": "position"}]))
        self.assertEqual("", fall.urteil([{"feld": "orb_nacht"}]))


class AnlassfallCheckTest(BasisTest):
    """Der Sammellauf ueber alle Werkzeuge."""

    def setUp(self):
        super().setUp()
        self.ergebnis = AnlassfallCheck().laufen()

    def test_kein_werkzeug_ist_blind(self):
        u"""Geprüft und trotzdem nichts gefunden — das ist der schlimme Fall.

        Gelesen wird das Feld ``stand``, nicht der Urteilstext: Die Liste
        erlaubter Formulierungen war vorher der Grund, warum dieser Test bei
        einer neuen Formulierung rot wurde, ohne dass sich etwas geändert hatte.
        """
        blind = [z for z in self.ergebnis.zeilen if z["stand"] == "blind"]
        self.assertFalse(
            blind,
            "Diese Werkzeuge finden ihren eigenen Anlassfall nicht mehr: %s"
            % "; ".join("%s (%s)" % (z["werkzeug"], z["urteil"])
                        for z in blind))

    def test_keines_meldet_auf_leerem_verzeichnis(self):
        """Wer im Leeren etwas findet, sucht nicht in der übergebenen Wurzel.

        Dann sagt auch ein grüner Anlassfall-Lauf nichts aus — das Werkzeug
        durchsucht in Wahrheit das ganze Projekt. ``esmodulimporte`` war genau
        so gebaut (``settings.BASE_DIR`` statt ``self.wurzel()``)."""
        laut = [z for z in self.ergebnis.zeilen
                if isinstance(z["im Leeren"], int) and z["im Leeren"] > 0]
        self.assertFalse(laut, "meldet ohne Code: %s"
                         % ", ".join(z["werkzeug"] for z in laut))

    def test_jedes_werkzeug_ist_geprueft_oder_erklaert(self):
        u"""Anlassfall — oder ein Satz, warum es keinen geben kann.

        Ein Prüfer, der nach einem Umbau seinen eigenen Fall nicht mehr sieht,
        meldet null und sieht dabei aus wie ein sauberes Projekt. Deshalb
        bringt jedes Werkzeug seinen Anlassfall mit.

        Manche können keinen haben: Sie messen nur (Zeilen, Zeiten) oder
        brauchen den laufenden Server bzw. den Django-Renderer. Die sagen das
        selbst — ``ohne_anlassfall_weil`` steht AM WERKZEUG. Hier stand bis zum
        18.08.2026 eine Namensliste; zwei Orte für dieselbe Angabe laufen
        auseinander, und der zweite ist immer der, den man beim Umbau vergisst.
        """
        stumm = [z["werkzeug"] for z in self.ergebnis.zeilen
                 if z["stand"] == "ungeprueft"]
        self.assertFalse(
            stumm,
            "ohne Anlassfall und ohne Begründung: %s — entweder einen "
            "Anlassfall bauen oder `ohne_anlassfall_weil` setzen"
            % ", ".join(stumm))

    def test_raeumt_hinter_sich_auf(self):
        self.assertFalse((AnlassfallCheck().wurzel() / ORDNER).exists(),
                         "der Wegwerf-Ordner ist liegengeblieben")


class SabotageTest(BasisTest):
    """Die Gegenprobe: Wird der Check rot, wenn ein Werkzeug blind ist?

    Ohne diesen Test wäre er ein Prüfer, der nur grün kann — genau das, was er
    verhindern soll. Gebaut wird ein Werkzeug, das absichtlich nichts findet.
    """

    def test_ein_blindes_werkzeug_faellt_auf(self):
        from djangobase.skills.werkzeug import Ergebnis, Werkzeug

        class BlindesWerkzeug(Werkzeug):
            slug = "blind-zum-test"
            titel = "findet nie etwas"
            anlassfall = Anlassfall({"a.py": "x = 1\n"}, mindestens=1)

            def laufen(self):
                return Ergebnis(["datei"], [])

        pruefung = AnlassfallCheck()
        basis = pruefung.wurzel() / ORDNER / "sabotage"
        try:
            BlindesWerkzeug.anlassfall.schreiben(basis)
            lauf = Probelauf(BlindesWerkzeug, basis).fahren()
            self.assertIn("blind",
                          BlindesWerkzeug.anlassfall.urteil(lauf.zeilen))
        finally:
            pruefung._aufraeumen(pruefung.wurzel() / ORDNER)

    def test_jedes_werkzeug_das_einen_fall_hat_nennt_auch_den_grund(self):
        """``warum`` ist Pflicht: Ein Anlassfall ohne den Vorfall dahinter ist
        in einem Jahr nicht mehr zu beurteilen."""
        for klasse in WERKZEUGE:
            fall = getattr(klasse, "anlassfall", None)
            if fall is None:
                continue
            with self.subTest(werkzeug=klasse.slug):
                self.assertTrue(fall.warum,
                                "%s: Anlassfall ohne Begründung" % klasse.slug)
                self.assertTrue(fall.dateien, "%s: leerer Fall" % klasse.slug)
