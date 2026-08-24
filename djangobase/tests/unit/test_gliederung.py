# -*- coding: utf-8 -*-
u"""Die Gliederung nach Rolle — von Klassen UND Funktionen benutzt.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „mache alle Klassen in allen Tabs und alle Funktionen aus allen Tabs
     auch als Gliederung mit Knöpfen"

Die Einteilung stand im ``Klassenmodell``. Sobald die Funktionen dieselbe
brauchen, gibt es zwei Möglichkeiten: kopieren oder herauslösen. Kopiert
liefen sie beim nächsten Zusatz auseinander — dann stünde `views/` in der
einen Liste unter „Ansichten" und in der anderen unter „Übrige".

DIE EIGENSCHAFT, AUF DIE ES ANKOMMT
===================================
Die Summe aller Gruppen ist die Zahl der Einträge. Ohne sie ist eine
Gliederung wertlos, weil man ihr nicht ansieht, ob etwas fehlt — genau die
Beschwerde, mit der das hier angefangen hat: „1004 klassen, ich erwarte
bereiche und buttons wo ich alle 1004 klassen sehen kann".
"""
from djangobase.umbau.gliederung import nach_rolle, rolle, untergruppe

from ..base import BasisTest


class DieRolleStehtAmPfad(BasisTest):

    def test_verzeichnisse_geben_die_rolle(self):
        self.assertEqual(rolle('views/persons/crud.py'), 'Ansichten')
        self.assertEqual(rolle('services/merge/suggester.py'), 'Dienste')
        self.assertEqual(rolle('tests/unit/test_x.py'), 'Tests')

    def test_auch_der_dateiname_zaehlt(self):
        self.assertEqual(rolle('models.py'), 'Datenmodell')
        self.assertEqual(rolle('forms.py'), 'Oberflaeche')

    def test_test_dateien_ausserhalb_von_tests(self):
        self.assertEqual(rolle('app/test_regression.py'), 'Tests')

    def test_nicht_am_klassennamen(self):
        u"""`VideoCodecProbe` in `views/` ist keine Pruefung."""
        self.assertEqual(rolle('views/recordings/codec_probe.py'), 'Ansichten')

    def test_was_nirgends_passt_faellt_nicht_weg(self):
        self.assertEqual(rolle('kram/beliebig.py'), 'Uebrige')


class DieUntergruppe(BasisTest):

    def test_zwei_pfadteile_bei_unterverzeichnissen(self):
        self.assertEqual(untergruppe('views/persons/crud.py'), 'views/persons')

    def test_ein_pfadteil_genuegt_bei_flacher_ablage(self):
        self.assertEqual(untergruppe('services/x.py'), 'services')

    def test_ohne_verzeichnis_gilt_der_dateiname(self):
        u"""„(Wurzel)" sagte nichts — jetzt steht dort `models.py`."""
        self.assertEqual(untergruppe('models.py'), 'models.py')


class DieSummeStimmt(BasisTest):

    EINTRAEGE = [
        ('Ansicht', 'views/a.py'),
        ('Noch1', 'views/b.py'),
        ('Dienst', 'services/c.py'),
        ('Pruefung', 'tests/unit/d.py'),
        ('Kamera', 'models.py'),
        ('Seltsam', 'kram/e.py'),
    ]

    def test_die_summe_ist_die_zahl_der_eintraege(self):
        gruppen = nach_rolle(self.EINTRAEGE)
        self.assertEqual(sum(r['zahl'] for r in gruppen),
                         len(self.EINTRAEGE))

    def test_kein_name_steht_doppelt(self):
        alle = [n for r in nach_rolle(self.EINTRAEGE)
                for g in r['gruppen'] for n in g['namen']]
        self.assertEqual(sorted(alle), sorted(n for n, _d in self.EINTRAEGE))

    def test_die_groesste_rolle_steht_vorn(self):
        self.assertEqual(nach_rolle(self.EINTRAEGE)[0]['name'], 'Ansichten')

    def test_die_untergruppen_zaehlen_zur_rolle(self):
        for r in nach_rolle(self.EINTRAEGE):
            self.assertEqual(r['zahl'],
                             sum(g['zahl'] for g in r['gruppen']))

    def test_ohne_eintraege_ist_die_liste_leer(self):
        self.assertEqual(nach_rolle([]), [])


class KleineRollenStehenFlach(BasisTest):
    u"""Die Ebene der Verzeichnisse nur, wo sie etwas austrägt.

    DIE FRAGE (Edgar, 24.08.2026)
    =============================
        „was sollen die untertabs bei Globale Funktionen?"

    Sie sagen, WO der Code liegt, und zerlegen eine Rolle, die sonst eine
    Wand wäre. Gemessen an CamTrack/app, Funktionen je Rolle::

        Ansichten 370 (15 Gruppen)   Aufnahme    42 (5)
        Dienste   181 (13)           Übrige      11 (3)
        Tests      96 (5)            Oberfläche  10 (1)  <- ohne Nutzen
        Erkennung  56 (6)            Befehle      3 (1)  <- ebenso

    Bei 370 Einträgen hilft die Ebene, bei 10 ist sie ein Klick ins Leere —
    und bei EINER Untergruppe sagt sie gar nichts.
    """

    def test_eine_grosse_rolle_bleibt_unterteilt(self):
        gross = [('N%d' % i, 'views/teil%d/a.py' % (i % 5)) for i in range(60)]
        rolle = nach_rolle(gross)[0]
        self.assertFalse(rolle['flach'])
        self.assertEqual(len(rolle['gruppen']), 5)

    def test_eine_kleine_rolle_steht_flach(self):
        klein = [('N%d' % i, 'views/teil%d/a.py' % (i % 3)) for i in range(9)]
        self.assertTrue(nach_rolle(klein)[0]['flach'])

    def test_eine_einzige_untergruppe_ist_immer_flach(self):
        u"""Auch bei vielen Einträgen: Die Ebene sagt dann nichts."""
        viele = [('N%d' % i, 'views/nur_hier/a.py') for i in range(200)]
        rolle = nach_rolle(viele)[0]
        self.assertTrue(rolle['flach'])
        self.assertEqual(len(rolle['gruppen']), 1)

    def test_flach_heisst_nicht_weniger(self):
        u"""Die Namen stehen dann direkt an der Rolle — keiner fällt weg."""
        klein = [('Eins', 'kram/a.py'), ('Zwei', 'kram/b.py')]
        rolle = nach_rolle(klein)[0]
        self.assertEqual(rolle['namen'], ['Eins', 'Zwei'])
        self.assertEqual(rolle['zahl'], 2)
