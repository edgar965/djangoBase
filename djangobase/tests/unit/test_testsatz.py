# -*- coding: utf-8 -*-
u"""Testsatz — liest eine Prüf-Kennung als deutschen Satz.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „verbessere meine testcases, so dass es die Gherkin BDD Anforderungen
     erfüllt, z. B. Wer kann es lesen: auch Nicht-Programmierer"
    „mach auch einen testcase dafür im BDD Bereich"

Das war die einzige Eigenschaft, in der Gherkin diesem Weg voraus war.
Eine ``.feature``-Datei liest jeder:

    Szenario: Eine ausgeblendete Person bleibt ausgeblendet

Auf ``/hilfe/tests/`` stand dagegen::

    AliasVerbundTest.test_falte_behaelt_reihenfolge_und_einzelne

Derselbe Satz, nur in Maschinenschrift. ``Testsatz`` liest ihn zurück:

    „Alias Verbund: Falte behaelt reihenfolge und einzelne"

WARUM DAS OHNE ZWEITE DATEI GEHT
================================
Der Satz ist bereits da — er steht in der Schreibweise, die Python für
Bezeichner verlangt. Eine ``.feature``-Datei daneben wäre eine ZWEITE
Fassung desselben Satzes, und zwei Fassungen laufen auseinander, sobald
jemand die eine ändert.

Diese Prüfungen gehören zu Kriterium 19 („Abnahme und Beispiele").
"""
from djangobase.testsatz import Testsatz

from ..base import BasisTest


def _satz(kennung):
    return Testsatz(kennung).satz()


class DerSatzIstLesbarOhneCode(BasisTest):
    u"""Die Zusage, um die es geht: Ein Nicht-Programmierer versteht ihn."""

    def test_unterstriche_werden_zu_leerzeichen(self):
        self.assertEqual(
            _satz('m.PersonTest.test_person_bleibt_erhalten'),
            'Person: Person bleibt erhalten')

    def test_der_vorsatz_test_faellt_weg(self):
        u"""``test_`` sagt nur, DASS es eine Prüfung ist — das sieht man."""
        self.assertNotIn('test_', _satz('m.AbcTest.test_etwas_geht_gut'))

    def test_der_nachsatz_test_faellt_auch_weg(self):
        self.assertTrue(_satz('m.KameraTests.test_bild_kommt_an')
                        .startswith('Kamera:'))

    def test_camelcase_wird_getrennt(self):
        self.assertTrue(
            _satz('m.AliasVerbundTest.test_kette_wird_aufgeloest')
            .startswith('Alias Verbund:'))

    def test_fuellwoerter_bleiben_klein(self):
        u"""``KameraUndPerson`` ist CamelCase, kein englischer Titel."""
        self.assertTrue(_satz('m.KameraUndPerson.test_nur_bekannte')
                        .startswith('Kamera und Person:'))

    def test_das_erste_wort_bleibt_gross(self):
        u"""Auch wenn es ein Füllwort ist: Ein Satz fängt groß an."""
        self.assertTrue(_satz('m.DerZaehlerLaeuftVoll.test_es_faellt_auf')
                        .startswith('Der '))


class DerSatzNenntGegenstandUndErgebnis(BasisTest):
    u"""Zwei Teile, wie bei Gherkin: worum es geht, und was stimmen muss."""

    KENNUNG = 'm.AufbewahrungTraegt.test_person_bleibt_erhalten'

    def test_der_gegenstand_kommt_aus_der_klasse(self):
        self.assertEqual(Testsatz(self.KENNUNG).gegenstand(),
                         'Aufbewahrung traegt')

    def test_das_ergebnis_kommt_aus_der_methode(self):
        self.assertEqual(Testsatz(self.KENNUNG).ergebnis(),
                         'Person bleibt erhalten')

    def test_beides_steht_mit_doppelpunkt_zusammen(self):
        self.assertEqual(_satz(self.KENNUNG),
                         'Aufbewahrung traegt: Person bleibt erhalten')


class EineUnvollstaendigeKennungBRICHTNICHT(BasisTest):
    u"""Die Kennung kommt aus der Test-Erkennung — sie ist nicht immer
    vollständig, und eine Ausnahme in der Anzeige wäre teurer als ein
    kurzer Satz."""

    def test_ohne_klasse_bleibt_das_ergebnis(self):
        self.assertEqual(_satz('test_etwas_geht_gut'), 'Etwas geht gut')

    def test_eine_leere_kennung_wirft_nicht(self):
        self.assertEqual(_satz(''), '')

    def test_ein_none_wirft_auch_nicht(self):
        self.assertEqual(_satz(None), '')

    def test_etwas_voellig_fremdes_bleibt_stehen(self):
        u"""Lieber unverändert anzeigen als etwas erfinden."""
        self.assertEqual(_satz('xyz'), 'Xyz')


class DerTextWIRDNICHTUMGESCHRIEBEN(BasisTest):
    u"""Was im Bezeichner steht, steht auch im Satz.

        „ich brauche keine umlaute in den testcases" (26.08.2026)

    Eine Zwischenfassung ersetzte hier 230 Woerter (``behaelt`` ->
    ``behält``). Das war eine Spur huebscher und kostete Pflege bei jeder
    neuen Pruefung — und ein Wort, das nicht in der Liste stand, blieb
    ohnehin, wie es war.

    Jetzt wird NUR umgebaut, nie umgeschrieben: Unterstriche zu
    Leerzeichen, ``test_`` weg, Klassenname getrennt. Der Wortlaut bleibt.
    """

    def test_ein_wort_bleibt_wie_es_dasteht(self):
        self.assertIn('behaelt',
                      _satz('m.AbcTest.test_falte_behaelt_die_reihenfolge'))

    def test_englische_woerter_bleiben_auch(self):
        satz = _satz('m.AbcTest.test_der_value_bleibt_gleich')
        self.assertIn('value', satz)
        self.assertNotIn('valü', satz)

    def test_es_gibt_keine_wortliste_mehr(self):
        u"""Gegenprobe: Sonst kaeme sie beim naechsten Mal zurueck."""
        import djangobase.testsatz as ts
        self.assertFalse(hasattr(ts, 'UMLAUTE'),
                         'Die Wortliste ist zurueck — sie war Pflegeaufwand '
                         'ohne Gegenwert.')


class DieTestSeiteZeigtSaetze(BasisTest):
    u"""Die Zusage gilt erst, wenn sie auf der Seite ankommt."""

    def test_die_ansicht_benutzt_den_satzleser(self):
        from djangobase.views.tests import _kurz
        self.assertEqual(_kurz('a.b.PersonTest.test_person_bleibt_erhalten'),
                         'Person: Person bleibt erhalten')

    def test_kein_unterstrich_mehr_in_der_anzeige(self):
        from djangobase.views.tests import _kurz
        self.assertNotIn('_', _kurz('a.b.AbcTest.test_etwas_geht_gut'))
