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




class DiesesWerkzeugHatKeinenAnlassfall(BasisTest):
    u"""Gegeben: Der Anlassfall ist entfallen — mit angegebenem Grund.

    WAS PASSIERT IST (27.08.2026)
    =============================
    Er verlangte ``mindestens=1`` und ``erwartet_in='abgeschnitten'``:
    Eine Kette über sieben Klassen wird bis Tiefe fünf gezeichnet, das
    Bild zeigt also weniger als den ganzen Weg — und DAS war der Befund.

    Seit ``Workflowbild._abschluss`` den Fußvermerk setzt, verschweigt
    das Bild seine Grenze nicht mehr. Der Hinweis ist erledigt, und der
    Anlassfall fiel um.

    Nachbauen lässt er sich nicht: Der verbliebene Befund („Bild
    verschweigt seine Grenze") hängt am ZEICHNER, nicht am geprüften
    Projekt. Der Anlassfall-Mechanismus stellt Dateien.

    Ein Anlassfall auf ``mindestens=0`` war der erste Versuch und war
    falsch: Er verlangt nur noch Schweigen und beweist gerade NICHT,
    dass das Werkzeug etwas sehen kann — stünde aber als „sieht seinen
    Fall" in der Tabelle. Jetzt trägt das Werkzeug den vorgesehenen
    ``ohne_anlassfall_weil``-Vermerk, wie neun andere auch.
    """

    def test_es_traegt_keinen_anlassfall_mehr(self):
        self.assertIsNone(getattr(Dokumentation, 'anlassfall', None))

    def test_aber_einen_grund(self):
        u"""Ohne Grund stünde es als UNGEPRÜFT da — und das wäre es."""
        self.assertTrue(Dokumentation.ohne_anlassfall_weil)

    def test_der_grund_nennt_wo_die_gegenprobe_steht(self):
        self.assertIn('EinBildDasSeineGrenzeVERSCHWEIGT',
                      Dokumentation.ohne_anlassfall_weil)

    def test_der_pruefer_fuehrt_es_als_erklaert(self):
        from djangobase.skills.anlassfall_check import Pruefergebnis
        ergebnis = Pruefergebnis(Dokumentation)
        self.assertEqual(ergebnis.stand, Pruefergebnis.ERKLAERT)
        self.assertIn('kein Anlassfall nötig', ergebnis.urteil)

    def test_und_nicht_als_ungeprueft(self):
        from djangobase.skills.anlassfall_check import Pruefergebnis
        self.assertNotEqual(Pruefergebnis(Dokumentation).stand,
                            Pruefergebnis.UNGEPRUEFT)


class _Bezug:
    u"""So viel Bezug, wie das Bild zum Zeichnen braucht."""

    def __init__(self, name):
        self.name = self.anzeige = name
        self.klasse = name
        self.art = 'klasse'
        self.modul = 'attrappe'
        self.datei = None
        self.zeile = 1


class _Schritt:
    def __init__(self, name, tiefe=0):
        self.bezug = _Bezug(name)
        self.tiefe = tiefe
        self.grund = 'aufruf'


class _Einstieg:
    titel = 'Ein Weg, der weitergeht'
    datei = 'attrappe.py'


class _Weg:
    u"""Ein abgeschnittener Weg — mehr braucht die Pruefung nicht."""

    def __init__(self, abgeschnitten=True):
        self.einstieg = _Einstieg()
        self.schritte = [_Schritt('Erste'), _Schritt('Zweite', 1)]
        self.kanten = []
        self.offen = []
        self.abgeschnitten = abgeschnitten

    @property
    def klassen(self):
        return ['Erste', 'Zweite']


class _Liste:
    def __init__(self, wege):
        self.wege = wege
        self.verworfen = 0
        self.kennzahlen = {}


class EinBildDasSeineGrenzeZeigt(BasisTest):
    u"""Gegeben: Der Weg geht weiter, und das Bild sagt es.

    DIE VORGESCHICHTE (27.08.2026)
    ==============================
    Bis heute meldete dieses Werkzeug JEDES gekuerzte Bild — an assistant
    waren das 33 von 34, und die Begruendung stand im eigenen Docstring:
    „ein Bild, das seine eigene Grenze verschweigt, wird fuer das Ganze
    gehalten." Seit ``Workflowbild._abschluss`` einen Fussvermerk setzt,
    verschweigt keines mehr etwas — der Hinweis ist damit erledigt, nicht
    unterdrueckt.

    Der erste Versuch pruefte auf ``'wf-mehr' in svg`` und war IMMER wahr:
    Der Name steht auch im Stilblock, den jedes Bild mitbringt. Die
    Pruefung haette nie wieder etwas gemeldet. Aufgefallen ist es nur,
    weil die Gegenprobe unten verlangt wurde.
    """

    def test_wird_nicht_mehr_gemeldet(self):
        self.assertEqual(Dokumentation._abgeschnittene(_Liste([_Weg()])), [])

    def test_der_vermerk_steht_wirklich_im_bild(self):
        from djangobase.umbau.workflowbild import Workflowbild
        svg = Workflowbild(_Weg()).svg()
        self.assertIn('<text class="wf-mehr"', svg)
        self.assertIn('hier geht der Weg weiter', svg)

    def test_ein_vollstaendiges_bild_traegt_keinen_vermerk(self):
        from djangobase.umbau.workflowbild import Workflowbild
        svg = Workflowbild(_Weg(abgeschnitten=False)).svg()
        self.assertNotIn('<text class="wf-mehr"', svg)


class EinBildDasSeineGrenzeVERSCHWEIGT(BasisTest):
    u"""Gegeben: Der Weg geht weiter, und das Bild sagt es NICHT.

    Die Gegenprobe. Faellt sie um, meldet das Werkzeug nichts mehr —
    dann waere der Hinweis nicht behoben, sondern abgeschaltet.
    """

    def setUp(self):
        from djangobase.umbau import workflowbild
        self.echt = workflowbild.Workflowbild._abschluss
        workflowbild.Workflowbild._abschluss = lambda self: []

    def tearDown(self):
        from djangobase.umbau import workflowbild
        workflowbild.Workflowbild._abschluss = self.echt

    def test_wird_gemeldet(self):
        befunde = Dokumentation._abgeschnittene(_Liste([_Weg()]))
        self.assertEqual(len(befunde), 1)

    def test_der_befund_nennt_den_weg(self):
        befund = Dokumentation._abgeschnittene(_Liste([_Weg()]))[0]
        self.assertIn('Ein Weg, der weitergeht', befund.was)

    def test_ein_vollstaendiger_weg_bleibt_still(self):
        u"""Auch ohne Vermerk: Was nicht gekuerzt ist, ist kein Befund."""
        self.assertEqual(
            Dokumentation._abgeschnittene(_Liste([_Weg(False)])), [])
