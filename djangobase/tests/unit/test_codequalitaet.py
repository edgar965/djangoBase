# -*- coding: utf-8 -*-
u"""Code-Qualität mit vier etablierten Werkzeugen.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „Dann brauche ich ein Tool zur Evaluierung der Code-Qualität, davon
     sollte es schon einige geben. Mach einen Button dazu der Code-Qualität
     mit 2-3 Methoden überprüft"

„Davon sollte es schon einige geben" — deshalb ist hier nichts selbst
gebaut: `radon` misst zweimal (Komplexität je Funktion, Wartbarkeit je
Datei), `pyflakes` findet echte Fehler, `pycodestyle` Formsachen.

DIE ZWEI FEHLER AUS DEM ERSTEN LAUF
===================================
1. `pycodestyle` meldete **„0 Abweichungen in 0 Regeln"** für einen
   Quelltext mit 2839 zu langen Zeilen. Grund: `Checker(pfad, quiet=True,
   options=...)` hat ein `assert not kwargs`, sobald `options` gesetzt ist
   — jede Datei flog in meinen eigenen `except Exception: continue`. Ein
   Verfahren, das bei jedem Fehlschlag „alles gut" sagt, ist schlimmer als
   keines.
2. Die Vorlage lief in ein `TypeError: 'int' object is not iterable`:
   `zahlen['arten']` war bei „Echte Fehler" eine Liste von Paaren, bei
   „Stil" eine Zahl. Gleicher Name, andere Bauart.
"""
import unittest
import tempfile
from pathlib import Path

from djangobase.umbau.codequalitaet import Codequalitaet, Verfahren

from ..base import BasisTest


def _messen(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='cq_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return Codequalitaet(ordner).messen()


#: Eine Funktion mit vielen Verzweigungen — radon soll sie finden.
VERWICKELT = u'def viel(a):\n' + u''.join(
    u'    if a == %d:\n        return %d\n' % (i, i) for i in range(14))

#: Ein unbenutzter Import und eine unbenutzte Variable — pyflakes-Futter.
FEHLERHAFT = u'import os\nimport sys\n\n\ndef machen():\n    x = 1\n    return 2\n'

#: Eine zu lange Zeile — pycodestyle-Futter (E501).
ZU_LANG = u'x = "%s"\n' % ('y' * 120)


#: DREI ZUSTAENDE STATT ZWEI (27.08.2026)
#: ======================================
#: Diese Faelle brauchen ``radon``, ``pyflakes`` und ``pycodestyle``. Fehlen
#: sie, lieferte der Lauf bisher 29 rote Faelle mit Meldungen wie
#: ``KeyError: 'arten'`` - also 29 Meldungen, die aussehen wie ein kaputtes
#: Projekt und in Wahrheit „pip install fehlt" heissen. Genau so ist es am
#: 27.08.2026 in shortlongx passiert.
#:
#: Die PRODUKTIVSEITE macht es schon richtig: ``umbau/codequalitaet.py``
#: setzt ``v.fehlt = 'radon'`` und zeigt „nicht gelaufen" statt einer leeren
#: Liste. Nur die Pruefungen kannten diesen dritten Zustand nicht.
#:
#: djangoBase haengt in rund sechs Projekten; keines davon muss die
#: Werkzeuge haben (sie sind ein optionales Extra, siehe pyproject.toml).
#: Ein uebersprungener Fall sagt die Wahrheit, ein roter luegt.
def _fehlendes_werkzeug(*module):
    u"""Name des ersten fehlenden Moduls - oder '' wenn alle da sind."""
    import importlib.util
    for m in module:
        if importlib.util.find_spec(m) is None:
            return m
    return ''


FEHLT = _fehlendes_werkzeug('radon', 'pyflakes', 'pycodestyle')
BRAUCHT_WERKZEUGE = unittest.skipIf(
    FEHLT, u'%s ist nicht installiert - siehe Extra „codequalitaet"' % FEHLT)


@BRAUCHT_WERKZEUGE
class AlleVierLaufen(BasisTest):

    def _namen(self, messung):
        return [v['name'] for v in messung.als_liste()]

    def test_vier_verfahren_stehen_da(self):
        namen = self._namen(_messen({'a.py': u'x = 1\n'}))
        self.assertEqual(len(namen), 4)
        for teil in (u'Komplexität', u'Wartbarkeitsindex', u'Echte Fehler',
                     u'Stil'):
            self.assertTrue(any(teil in n for n in namen), teil)

    def test_jedes_nennt_sein_werkzeug(self):
        u"""Damit nachlesbar ist, WER das behauptet."""
        werkzeuge = set(v['werkzeug'] for v in
                        _messen({'a.py': u'x = 1\n'}).als_liste())
        self.assertEqual(werkzeuge, {'radon', 'pyflakes', 'pycodestyle'})


@BRAUCHT_WERKZEUGE
class JedesVerfahrenFindetSeinen(BasisTest):

    def _eines(self, messung, teil):
        for v in messung.als_liste():
            if teil in v['name']:
                return v
        raise AssertionError('%r ist kein Verfahren' % teil)

    def test_radon_findet_die_verwickelte_funktion(self):
        v = self._eines(_messen({'a.py': VERWICKELT}), u'Komplexität')
        self.assertTrue(v['treffer'])
        self.assertEqual(v['treffer'][0]['name'], 'viel')

    def test_eine_geradlinige_funktion_faellt_nicht_auf(self):
        v = self._eines(_messen({'a.py': u'def wenig():\n    return 1\n'}),
                        u'Komplexität')
        self.assertFalse(v['treffer'])

    def test_die_verteilung_steht_dabei(self):
        u"""„216 auffällig" allein sagt nicht, ob der Rest gut ist."""
        v = self._eines(_messen({'a.py': VERWICKELT}), u'Komplexität')
        raenge = dict(v['zahlen']['raenge'])
        self.assertEqual(sorted(raenge), list('ABCDEF'))

    def test_pyflakes_findet_die_unbenutzte_variable(self):
        v = self._eines(_messen({'a.py': FEHLERHAFT}), u'Echte Fehler')
        arten = dict(v['zahlen']['arten'])
        self.assertEqual(arten.get('UnusedVariable'), 1)

    def test_tote_einfuhren_fuehrt_ein_anderes_werkzeug(self):
        u"""KEINE DUPLIKATE (Edgar, 25.08.2026)

        `pyflakes` meldet auch unbenutzte Einfuhren — und genau die meldet
        `tote-importe` seit Kriterium 5, mit Wissen, das `pyflakes` nicht
        hat (Seiteneffekt-Module, `__all__`, Namen in Zeichenketten). Zwei
        Werkzeuge fuer denselben Befund heisst zwei Listen, die
        auseinanderlaufen.
        """
        v = self._eines(_messen({'a.py': FEHLERHAFT}), u'Echte Fehler')
        self.assertIsNone(dict(v['zahlen']['arten']).get('UnusedImport'))
        self.assertEqual(dict(v['zahlen']['anderswo'])['tote-importe'], 2)

    def test_der_befund_verschwindet_aber_nicht(self):
        u"""Weglassen wäre schlimmer als doppelt melden."""
        v = self._eines(_messen({'a.py': FEHLERHAFT}), u'Echte Fehler')
        self.assertIn('tote-importe', v['satz'])

    def test_pycodestyle_findet_die_lange_zeile(self):
        u"""DER ERSTE LAUF MELDETE HIER NULL — weil mein eigener
        `except Exception` den `assert not kwargs` verschluckte."""
        v = self._eines(_messen({'a.py': ZU_LANG}), u'Stil')
        self.assertTrue(v['treffer'], u'pycodestyle meldet wieder nichts')
        self.assertEqual(v['treffer'][0]['name'], 'E501')

    def test_die_wartbarkeit_misst_jede_datei(self):
        v = self._eines(_messen({'a.py': u'x = 1\n', 'b.py': u'y = 2\n'}),
                        u'Wartbarkeitsindex')
        self.assertEqual(v['zahlen']['gemessen'], 2)


@BRAUCHT_WERKZEUGE
class DieZahlenHabenUeberallDieselbeBauart(BasisTest):
    u"""DER FEHLER (24.08.2026): `TypeError: 'int' object is not iterable`.

    `zahlen['arten']` war bei „Echte Fehler" eine Liste von Paaren, bei
    „Stil" eine Zahl — und die Vorlage lief mit einem `{% for %}` darüber.
    """

    def test_arten_ist_ueberall_eine_liste_von_paaren(self):
        for v in _messen({'a.py': FEHLERHAFT + ZU_LANG}).als_liste():
            arten = v['zahlen'].get('arten')
            if arten is None:
                continue
            for eintrag in arten:
                self.assertEqual(len(eintrag), 2,
                                 u'%s: %r' % (v['name'], eintrag))

    def test_raenge_ist_ueberall_eine_liste_von_paaren(self):
        for v in _messen({'a.py': VERWICKELT}).als_liste():
            for eintrag in v['zahlen'].get('raenge') or ():
                self.assertEqual(len(eintrag), 2)


@BRAUCHT_WERKZEUGE
class DasProjektSagtWieLangEineZeileSeinDarf(BasisTest):
    u"""``setup.cfg`` schlägt pycodestyles Vorgabe von 79 Zeichen.

    GEMESSEN AN CamTrack (26.08.2026)
    =================================
    3320 Stil-Abweichungen — davon **3009 ein und dieselbe Regel**: E501,
    Zeilen über 79 Zeichen. Das Projekt schreibt aber auf 100; nur 438
    Zeilen sind länger.

    Ein Bericht, der zu 91 % aus einer Regel besteht, die niemand
    angenommen hat, verdeckt die 311 echten Befunde daneben. Nach dem
    Anlegen einer ``setup.cfg`` mit ``max_line_length = 100`` blieben 775.

    Das ist dieselbe Sorte Fehler wie ein Prüfer, der Kommentare anmahnt:
    Er misst etwas, wonach niemand gefragt hat — und wird deshalb
    ignoriert, samt allem Richtigen darin.
    """

    #: 90 Zeichen: über pycodestyles Vorgabe (79), unter unserer (100).
    MITTELLANG = u'x = "%s"\n' % ('y' * 84)

    def test_ohne_konfiguration_gilt_die_vorgabe(self):
        werte = _messen({'m.py': self.MITTELLANG})
        stil = [v for v in werte.als_liste() if 'PEP 8' in v['name']][0]
        self.assertGreaterEqual(stil['zahlen']['gesamt'], 1,
                                'Ohne setup.cfg muss die 90-Zeichen-Zeile '
                                'als E501 auffallen.')

    def test_setup_cfg_hebt_die_grenze(self):
        werte = _messen({
            'm.py': self.MITTELLANG,
            'setup.cfg': u'[pycodestyle]\nmax_line_length = 100\n'})
        stil = [v for v in werte.als_liste() if 'PEP 8' in v['name']][0]
        self.assertEqual(stil['zahlen']['gesamt'], 0,
                         'Mit max_line_length = 100 darf die 90-Zeichen-Zeile '
                         'nicht mehr gemeldet werden — sonst misst das '
                         'Werkzeug gegen eine Regel, die das Projekt nicht '
                         'hat.')

    def test_tox_ini_geht_auch(self):
        werte = _messen({
            'm.py': self.MITTELLANG,
            'tox.ini': u'[pycodestyle]\nmax_line_length = 100\n'})
        stil = [v for v in werte.als_liste() if 'PEP 8' in v['name']][0]
        self.assertEqual(stil['zahlen']['gesamt'], 0)

    def test_eine_wirklich_zu_lange_zeile_faellt_weiter_auf(self):
        u"""Die Gegenprobe: Die Grenze heben heißt nicht abschalten."""
        werte = _messen({
            'm.py': ZU_LANG,
            'setup.cfg': u'[pycodestyle]\nmax_line_length = 100\n'})
        stil = [v for v in werte.als_liste() if 'PEP 8' in v['name']][0]
        self.assertGreaterEqual(stil['zahlen']['gesamt'], 1)


@BRAUCHT_WERKZEUGE
class WasNichtGemessenWird(BasisTest):

    def test_laufzeitdaten_bleiben_draussen(self):
        m = _messen({'echt.py': u'x = 1\n',
                     'media/weg.py': FEHLERHAFT,
                     'logs/auch_weg.py': FEHLERHAFT})
        self.assertEqual(len(m.dateien), 1)

    def test_ein_fehlendes_werkzeug_meldet_sich(self):
        u"""Eine leere Trefferliste sähe aus wie „nichts gefunden"."""
        v = Verfahren(u'Test', 'gibtsnicht', u'nichts')
        v.fehlt = 'gibtsnicht'
        self.assertEqual(v.als_dict()['fehlt'], 'gibtsnicht')
        self.assertEqual(v.als_dict()['treffer'], [])

    def test_ein_leeres_projekt_wirft_nicht(self):
        m = _messen({})
        self.assertEqual(len(m.dateien), 0)
        self.assertEqual(len(m.als_liste()), 4)

    def test_eine_kaputte_datei_stoppt_den_lauf_nicht(self):
        m = _messen({'kaputt.py': u'def (:\n', 'gut.py': VERWICKELT})
        namen = [t['name'] for v in m.als_liste() for t in v['treffer']]
        self.assertIn('viel', namen)
