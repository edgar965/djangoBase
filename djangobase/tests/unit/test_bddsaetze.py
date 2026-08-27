# -*- coding: utf-8 -*-
u"""Prüft das Werkzeug, das prüft, ob sich Prüfungen als Satz lesen.

DER ANLASS (Edgar, 27.08.2026)
==============================
    „es kann doch nicht sein, dass die testcases grün sind! das sind völlig
     neue Anforderungen!!"

Der Einwand traf. ``test_testsatz.py`` belegt den Umwandler an achtzehn
handverlesenen Beispielen — sieben eingebaute Beschädigungen machen alle
achtzehn rot, die Prüfungen sind echt. Sie prüfen nur die falsche Sache:
Die Zusage ist nicht „der Umwandler funktioniert", sondern „jede Kennung des
Projekts liest sich als Satz". Dafür gab es nichts.

WAS HIER BESONDERS ZÄHLT: DIE FEHLALARME
========================================
Der erste Entwurf des Werkzeugs meldete an djangoBase **49 Treffer, davon 34
falsch** — jede ``Js*Test``-Klasse, weil die Regel verbliebenes CamelCase
anmeckerte (``JsWaisen`` ist ein Eigenname), und ``Kriterium 18 ist bekannt``
wegen der Zahl. Nach dem Entschärfen: 16 Treffer, alle echt.

Deshalb prüfen die Fälle unten beide Richtungen: dass die zwei echten Mängel
gemeldet werden UND dass die vier gesunden Formen es nicht werden. Ein
Prüfwerkzeug ohne Gegenprobe auf Fehlalarme verdeckt genau die Befunde, die
es finden soll.
"""
from djangobase.skills.bddsaetze import BddSaetze

from ..base import BasisTest


def _maengel(klasse, methode):
    return BddSaetze.maengel(klasse, methode)


class EinNameOhneAussageWirdGemeldet(BasisTest):
    u"""Ein Gegenstand ist keine Zusage — er sagt nicht, was gelten soll."""

    def test_ein_einzelnes_wort_ist_keine_aussage(self):
        u"""„Hilfe Views: Versionen" — was soll an ihnen stimmen?"""
        self.assertIn(u"ohne Aussage",
                      _maengel("HilfeViewsTest", "test_versionen"))

    def test_zwei_woerter_tragen_schon_eine(self):
        self.assertEqual(
            _maengel("HilfeViewsTest", "test_versionen_kommen_aus_github"), [])

    def test_ohne_klasse_fehlt_der_gegenstand(self):
        self.assertIn(u"ohne Gegenstand", _maengel("", "test_laedt_die_liste"))


class GesundeNamenWerdenNICHTGemeldet(BasisTest):
    u"""Die Gegenprobe zu den 34 Fehlalarmen des ersten Entwurfs."""

    def test_ein_eigenname_in_camelcase_ist_kein_mangel(self):
        u"""``JsWaisen`` heisst so — testsatz.ZUSAMMEN klebt das Js absichtlich."""
        self.assertEqual(
            _maengel("JsWaisenTest", "test_findet_waise_mit_anmeldung"), [])

    def test_eine_zahl_im_satz_ist_kein_mangel(self):
        u"""„Kriterium 18 ist bekannt" ist ein tadelloser deutscher Satz."""
        self.assertEqual(
            _maengel("Kriterium18Test", "test_kriterium_18_ist_bekannt"), [])

    def test_ein_englisches_fachwort_ist_kein_mangel(self):
        self.assertEqual(_maengel("CacheTest", "test_der_cache_bleibt_warm"), [])

    def test_eine_klasse_als_ganzer_satz_geht_auch(self):
        u"""Der BDD-Stil selbst: Die Klasse trägt die Zusage."""
        self.assertEqual(
            _maengel("DerSatzIstLesbarOhneCode", "test_umlaute_kommen_zurueck"),
            [])


class DieDritteRegelKonnteGarNichtAusloesen(BasisTest):
    u"""Warum es bei ZWEI Regeln bleibt — damit sie niemand neu erfindet.

    Der erste Entwurf meldete Maschinenschrift im fertigen Satz. Nach dem
    Entfernen der Fehlalarme (CamelCase, Zahlen) blieb der Unterstrich —
    und der überlebt die Umwandlung nie: ``_trennen`` wirft ihn beim
    Zerlegen weg, ``ergebnis`` ersetzt ihn durch ein Leerzeichen. Eine
    Regel, die nicht auslösen kann, behauptet eine Deckung, die es nicht
    gibt.
    """

    def test_ein_unterstrich_ueberlebt_die_umwandlung_nicht(self):
        from djangobase.testsatz import Testsatz
        self.assertNotIn("_", Testsatz("A_B_Test.test_der_wert_stimmt").satz())

    def test_deshalb_meldet_ein_solcher_name_nichts(self):
        u"""Genau diese Gegenprobe hat die tote Regel aufgedeckt."""
        self.assertEqual(_maengel("A_B_Test", "test_der_wert_stimmt"), [])


class DasWerkzeugLiestDasGanzeProjekt(BasisTest):
    u"""Nicht achtzehn Beispiele, sondern jede Kennung — das war der Auftrag."""

    def test_es_findet_die_kennungen_einer_testdatei(self):
        w = BddSaetze()
        kennungen = w.kennungen()
        # In diesem Projekt gibt es Prüfungen; die Liste darf nicht leer sein,
        # sonst sucht das Werkzeug am falschen Ort und meldet fröhlich null.
        self.assertTrue(kennungen, u"keine Kennung gefunden — sucht es überhaupt?")

    def test_jede_kennung_traegt_datei_zeile_klasse_methode(self):
        erste = BddSaetze().kennungen()[0]
        self.assertEqual(len(erste), 4)
        self.assertTrue(str(erste[0]).endswith('.py'))
        self.assertGreater(erste[1], 0)

    def test_der_bericht_nennt_die_grundgesamtheit(self):
        u"""„3 von 1.017" — ohne den Nenner ist die Zahl nicht einzuordnen."""
        e = BddSaetze().laufen()
        self.assertIn(u"von", e.zusammenfassung)
        self.assertIn(u"Kennungen", e.zusammenfassung)
