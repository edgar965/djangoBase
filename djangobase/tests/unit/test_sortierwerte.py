# -*- coding: utf-8 -*-
u"""Die Beurteilung eines ``data-sort``-Werts — ohne laufenden Server.

WARUM DIESE DATEI (05.09.2026)
==============================
``sortierwerte`` war das einzige Werkzeug ohne Anlassfall UND ohne Grund;
drei Prüfungen standen deshalb rot. Ein Anlassfall geht hier nicht: Er ist
ein Mini-Projekt aus DATEIEN, das Werkzeug liest aber die Antwort des
laufenden Servers.

Die Beurteilung selbst hängt jedoch an keinem Server. ``Sortierwert``
entscheidet auf einem Attribut und dem Text daneben — und genau das steht
hier. Ein Werkzeug, dessen Urteil niemand prüft, meldet irgendwann null,
und eine Null sieht aus wie ein sauberes Projekt.

DIE FEHLALARME SIND DIE HÄLFTE DER ARBEIT
=========================================
Der erste Lauf am 01.09.2026 meldete jede Datumsspalte und jeden Betrag
mit nachgestelltem Währungszeichen. Beide stehen hier als Fall, der
NICHT gemeldet werden darf — sonst schärft der nächste Umbau die Regel
nach und der Prüfer wird nach dem dritten Fehlalarm ignoriert.
"""
from django.test import SimpleTestCase

from djangobase.skills.sortierwerte import Sortierwert, Sortierwerte


class DieDeutscheLesart(SimpleTestCase):
    u"""``zahl()`` bildet ``tabellen_sortierung._zahl`` nach — wörtlich.

    Ein „ungefährer" Nachbau meldet entweder Fälle, die im Browser
    stimmen, oder übersieht die echten.
    """

    def test_das_komma_trennt_die_dezimalen(self):
        self.assertEqual(Sortierwert.zahl(u'1.234,5'), 1234.5)

    def test_jeder_punkt_gilt_als_tausenderzeichen(self):
        u"""Der Kern des Befunds: „20.9" wird nicht 20,9 sondern 209."""
        self.assertEqual(Sortierwert.zahl(u'20.9'), 209.0)

    def test_eine_einheit_dahinter_stoert_nicht(self):
        self.assertEqual(Sortierwert.zahl(u'17,4 GB'), 17.4)

    def test_ein_waehrungszeichen_hinten_auch_nicht(self):
        u"""Der erste Fehlalarm: „1.234,5 €" galt als unlesbar."""
        self.assertEqual(Sortierwert.zahl(u'1.234,5 €'), 1234.5)

    def test_text_ist_keine_zahl(self):
        self.assertIsNone(Sortierwert.zahl(u'Gemma 4'))

    def test_leer_ist_keine_zahl(self):
        self.assertIsNone(Sortierwert.zahl(u''))
        self.assertIsNone(Sortierwert.zahl(None))


class DieDreiEchtenBefunde(SimpleTestCase):
    u"""Alle drei sind am 01.09.2026 auf Hilfe → KI-Modelle aufgetreten."""

    def test_eine_einheit_im_schluessel(self):
        u"""``data-sort="137M"`` stellte 137 Millionen über 122 Milliarden."""
        befund = Sortierwert(u'137M', u'137M').befund()
        self.assertIsNotNone(befund)
        self.assertIn(u'Einheit', befund)

    def test_ein_dezimalpunkt_im_schluessel(self):
        u"""Der Anlassfall des Werkzeugs, wörtlich aus ``_WIEDERHOLT``."""
        befund = Sortierwert(u'20.9', u'20,9 B').befund()
        self.assertIsNotNone(befund)
        self.assertIn(u'Dezimalpunkt', befund)

    def test_ein_leerer_schluessel_bei_gefuellter_zelle(self):
        u"""``{{ x|default:'' }}`` mit ``x = 0`` — Django hält 0 für leer,
        und die Spalte sortiert danach gar nicht."""
        befund = Sortierwert(u'', u'12 GB').befund()
        self.assertIsNotNone(befund)
        self.assertIn(u'leerer Sortierschlüssel', befund)

    def test_der_schluessel_des_werkzeugs_wird_wirklich_gemeldet(self):
        u"""Gegenprobe am Werkzeug selbst: ``_WIEDERHOLT`` ist der Fall,
        den es melden MUSS. Wer ihn nur als Kommentar führt, hat nichts."""
        self.assertIn(u'20.9B', Sortierwerte._WIEDERHOLT)
        self.assertIsNotNone(Sortierwert(u'20.9B', u'20.9B').befund())


class WasNichtGEMELDETWerdenDarf(SimpleTestCase):
    u"""Die Fehlalarme des ersten Laufs — jeder einzeln festgehalten.

    Ohne diese Fälle bestünde die Klasse oben auch mit einer Regel, die
    ALLES meldet.
    """

    def test_ein_iso_datum_ist_kein_befund(self):
        u"""ISO sortiert als Text völlig richtig."""
        self.assertIsNone(Sortierwert(u'2026-08-11', u'11.08.2026').befund())

    def test_ein_deutsches_datum_in_der_zelle_auch_nicht(self):
        self.assertIsNone(Sortierwert(u'2026-08-11', u'11.08.2026').befund())

    def test_ein_sauberer_zahlenschluessel_ist_kein_befund(self):
        u"""Ohne Punkt und ohne Einheit ist alles in Ordnung.

        `17.4` steht hier ABSICHTLICH nicht: Der Punkt ist genau der
        Befund — die deutsche Lesart macht daraus 174. Der erste Entwurf
        dieser Prüfung behauptete das Gegenteil und war damit rot; sie
        hat also gefunden, wofür sie da ist.
        """
        self.assertIsNone(Sortierwert(u'17,4', u'17,4 GB').befund())
        self.assertIsNone(Sortierwert(u'1234', u'1.234').befund())
        self.assertIsNone(Sortierwert(u'-3', u'-3').befund())

    def test_ein_prozentzeichen_ist_erlaubt(self):
        u"""``%`` steht in der JS-Regel ausdrücklich drin."""
        self.assertIsNone(Sortierwert(u'42%', u'42 %').befund())

    def test_ein_leerer_schluessel_bei_leerer_zelle_ist_richtig(self):
        u"""„Nichts da" ist ein Zustand, kein Fehler."""
        self.assertIsNone(Sortierwert(u'', u'—').befund())
        self.assertIsNone(Sortierwert(u'', u'').befund())

    def test_ein_textschluessel_bei_textzelle_ist_richtig(self):
        self.assertIsNone(Sortierwert(u'gemma', u'Gemma 4').befund())


class DasWerkzeugSagtWarumEsKeinenAnlassfallHat(SimpleTestCase):
    u"""Ein Werkzeug ohne Beispiel muss einen Grund nennen — und der Grund
    muss einer sein (``test_die_gruende_sind_keine_leerformeln``)."""

    def test_der_grund_steht_da(self):
        self.assertTrue(Sortierwerte.ohne_anlassfall_weil)

    def test_er_ist_keine_leerformel(self):
        self.assertGreater(len(Sortierwerte.ohne_anlassfall_weil), 30)

    def test_er_nennt_diese_pruefdatei(self):
        u"""Sonst liest sich der Grund wie „geht nicht" statt wie
        „geht anders, und zwar dort"."""
        self.assertIn(u'test_sortierwerte', Sortierwerte.ohne_anlassfall_weil)
