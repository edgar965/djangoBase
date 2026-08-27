# -*- coding: utf-8 -*-
u"""Dokumentation — merkt das Werkzeug, wenn ein Bild nicht mehr stimmt?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „Ich brauche dann auch Testcases die das überprüfen in der CodeReview
     Seite (Mach einen neuen Abschnitt: Dokumentation, wo auch getestet
     wird, ob es ein Klassendiagramm gibt wie in /hilfe/klassenmodell/"

Ein Werkzeug, das Dokumentation prueft, ist nur dann etwas wert, wenn es
in BEIDE Richtungen richtig liegt:

    es meldet    wenn ein Bild fehlt oder ins Leere zeigt
    es schweigt  wenn alles dasteht — sonst schaltet es jemand ab

Der zweite Teil ist der, an dem solche Werkzeuge sterben. Eines, das
immer rot ist, wird nach zwei Wochen ignoriert.

Diese Pruefungen gehoeren zu Kriterium 20 („Dokumentation").
"""
from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund
from djangobase.skills.dokumentation import BILDWERKE, Dokumentation
from djangobase.skills.rangliste import BEREICHE, Rangliste

from ..base import BasisTest


class DasWerkzeugStehtImWerkzeugkasten(BasisTest):
    u"""Ein Werkzeug, das nicht auffindbar ist, laeuft nie."""

    def test_es_laesst_sich_ueber_seinen_namen_finden(self):
        self.assertIsInstance(werkzeug_finden('dokumentation'), Dokumentation)

    def test_es_traegt_kriterium_zwanzig(self):
        self.assertEqual(Dokumentation.kriterium, 20)

    def test_kriterium_zwanzig_hat_einen_eigenen_bereich(self):
        u"""Sonst faellt es in den Auffangkorb und die Ansage nach einem
        eigenen Abschnitt waere nicht erfuellt."""
        stelle = Rangliste.bereich_von(20)
        self.assertEqual(BEREICHE[stelle]['name'], 'Dokumentation')

    def test_es_landet_nicht_bloss_im_auffangkorb(self):
        u"""``bereich_von`` gibt fuer ALLES den letzten Bereich zurueck.
        Ohne diese Gegenprobe waere die Zuordnung oben auch dann gruen,
        wenn Kriterium 20 gar nicht eingetragen waere."""
        self.assertNotEqual(Rangliste.bereich_von(20),
                            Rangliste.bereich_von(999))

    def test_der_bdd_bereich_bleibt_der_letzte(self):
        u"""Der letzte Bereich faengt unbekannte Kriterien auf — das soll
        weiter BDD sein und nicht die Dokumentation."""
        self.assertEqual(BEREICHE[-1]['name'],
                         'Abnahme und Beispiele (BDD)')


class EsSchweigtSolangeDieBilderStehen(BasisTest):
    u"""Am echten Projekt, nicht an einem Abzug: Hier zaehlt, dass das
    Werkzeug im Alltag ruhig bleibt."""

    def setUp(self):
        self.satz = werkzeug_finden('dokumentation').pruefen()

    def test_es_meldet_keinen_fehler(self):
        schwer = [b for b in self.satz.befunde if b.gewicht == Befund.FEHLER]
        self.assertEqual(schwer, [], 'Unerwarteter Fehlbefund: %s'
                         % [b.was for b in schwer])

    def test_es_nennt_die_zahl_der_gezeichneten_wege(self):
        u"""Ohne Kopfzahlen kann niemand nachrechnen, was geprueft wurde."""
        self.assertTrue(any('Wege gezeichnet' in k for k in self.satz.kopf))

    def test_es_nennt_auch_die_ungeloesten_namen(self):
        u"""Die Luecke gehoert genannt, sonst sieht ein unvollstaendiges
        Bild aus wie ein vollstaendiges."""
        self.assertTrue(any('mehrdeutig' in k for k in self.satz.kopf))


class EinFehlendesBildFaelltAuf(BasisTest):
    u"""Der Fall, fuer den es das Werkzeug gibt."""

    def test_ohne_das_klassenmodell_kommt_ein_fehler(self):
        werkzeug = werkzeug_finden('dokumentation')
        werkzeug._bildwurzel = staticmethod(lambda: __import__(
            'pathlib').Path(__import__('tempfile').mkdtemp(prefix='leer_')))
        befunde = werkzeug._bilder_vorhanden()
        self.assertEqual(len(befunde), len(BILDWERKE))
        self.assertTrue(any('Klassenmodell' in b.was for b in befunde))

    def test_der_befund_nennt_die_fehlende_datei(self):
        u"""„Irgendetwas fehlt" hilft niemandem weiter."""
        werkzeug = werkzeug_finden('dokumentation')
        werkzeug._bildwurzel = staticmethod(lambda: __import__(
            'pathlib').Path(__import__('tempfile').mkdtemp(prefix='leer_')))
        befund = werkzeug._bilder_vorhanden()[0]
        self.assertIn('.py', befund.ort)


class DasWerkzeugFuehrtSeinenEigenenBeispielfallMit(BasisTest):
    u"""Kriterium 19 verlangt das von jedem Werkzeug: einen Fall, an dem
    es beweist, dass es seinen Befund noch findet."""

    def test_es_hat_einen_anlassfall(self):
        self.assertIsNotNone(Dokumentation.anlassfall)

    def test_der_anlassfall_sagt_warum_er_so_aussieht(self):
        self.assertTrue(Dokumentation.anlassfall.warum)
