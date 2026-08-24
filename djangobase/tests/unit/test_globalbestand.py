# -*- coding: utf-8 -*-
u"""Was auf Modulebene steht — und welche Seite welches Skript zieht.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „neuer Tab: Globale Funktionen, neuer Tab: Globale Klasse, neuer Tab
     Globale Variablen, neuer Tab HTML Seiten, darin je eine HTML Seite und
     deren JS code, auch als Abhängigkeiten falls verfügbar"

Das Klassenbild beantwortet „wer haelt wen". Diese Listen beantworten die
Frage davor: **Was haengt an gar keiner Klasse?** Beides sieht man im Bild
NICHT — dort ist nur, was schon eine Klasse ist.

DER UNTERSCHIED, AUF DEN ES ANKOMMT
===================================
Nicht jede Modulvariable ist ein Fund::

    MAX = 5          Vorgabe — gehoert auf Modulebene
    _cache = {}      Zustand — ueberlebt jeden Aufruf, gehoert niemandem
    __all__ = [...]  Ausfuhrliste — eine Liste, aber kein Zustand

Ohne die dritte Unterscheidung stellte `__all__` ein Viertel aller
„veraenderlichen" Variablen (gemessen an CamTrack: 172 statt 49) und machte
die Zahl wertlos.
"""
import tempfile
from pathlib import Path

from djangobase.umbau.globalbestand import Globalbestand, hauptaeste

from ..base import BasisTest


def _bestand(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='gb_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return Globalbestand(ordner).lesen()


class WasAufModulebeneSteht(BasisTest):

    def test_eine_freie_funktion_wird_gefunden(self):
        b = _bestand({'a.py': 'def rechne(x, y):\n    return x + y\n'})
        self.assertEqual([e.name for e in b.funktionen], ['rechne'])
        self.assertEqual(b.funktionen[0].zusatz, 'x, y')

    def test_eine_methode_ist_keine_freie_funktion(self):
        u"""Nur die OBERSTE Ebene zaehlt — sonst waere jede Methode ein Fund."""
        b = _bestand({'a.py': (
            'class Gast:\n'
            '    def buchen(self):\n        pass\n')})
        self.assertEqual(b.funktionen, [])
        self.assertEqual([e.name for e in b.klassen], ['Gast'])

    def test_die_oberklasse_steht_daneben(self):
        b = _bestand({'a.py': (
            'class Basis:\n    pass\n\n\n'
            'class Kind(Basis):\n    pass\n')})
        kind = [e for e in b.klassen if e.name == 'Kind'][0]
        self.assertEqual(kind.zusatz, 'Basis')

    # ── der Unterschied, auf den es ankommt ──────────────────────
    def test_eine_zahl_ist_eine_konstante(self):
        b = _bestand({'a.py': 'MAX = 5\n'})
        self.assertEqual(b.variablen[0].zusatz, 'Konstante')

    def test_ein_leeres_woerterbuch_ist_zustand(self):
        b = _bestand({'a.py': '_cache = {}\n'})
        self.assertEqual(b.variablen[0].zusatz, 'veränderlich')

    def test_auch_ueber_einen_aufruf_erzeugt(self):
        b = _bestand({'a.py': 'from collections import defaultdict\n'
                              '_je_kamera = defaultdict(list)\n'})
        werte = {e.name: e.zusatz for e in b.variablen}
        self.assertEqual(werte['_je_kamera'], 'veränderlich')

    def test_die_ausfuhrliste_ist_kein_zustand(self):
        u"""DER FALL: `__all__` stellte ein Viertel aller Funde."""
        b = _bestand({'a.py': "__all__ = ['A', 'B']\n"})
        self.assertEqual(b.variablen[0].zusatz, 'Ausfuhrliste')
        self.assertEqual(b.kennzahlen()['veraenderlich'], 0)


class WelcheSeiteWelchesSkript(BasisTest):

    def _seiten(self):
        return _bestand({
            'templates/seite.html': (
                '{% extends "grund.html" %}\n'
                '<script type="module" '
                'src="{% static \'app/js/start.js\' %}"></script>\n'),
            'static/app/js/start.js': (
                "import { a } from './teil_a.js';\n"
                "import { b } from '../gemeinsam/teil_b.js';\n"),
            'static/app/js/teil_a.js': 'export const a = 1;\n',
        })

    def test_die_seite_wird_gefunden(self):
        b = self._seiten()
        self.assertEqual(len(b.seiten), 1)
        self.assertIn('seite.html', b.seiten[0].pfad)

    def test_das_skript_haengt_an_der_seite(self):
        skripte = [js for js, _a in self._seiten().seiten[0].skripte]
        self.assertEqual(skripte, ['app/js/start.js'])

    def test_die_abhaengigkeiten_stehen_daneben(self):
        u"""Ein Skript zieht weitere — das gehoert zur Seite."""
        _js, abh = self._seiten().seiten[0].skripte[0]
        self.assertEqual(abh, ['teil_a.js', 'teil_b.js'])

    def test_was_die_seite_einbindet_steht_dabei(self):
        self.assertEqual(self._seiten().seiten[0].eingebunden, ['grund.html'])

    def test_eine_vorlage_ohne_skript_und_einbindung_faellt_weg(self):
        b = _bestand({'templates/nur_text.html': '<h1>Hallo</h1>\n'})
        self.assertEqual(b.seiten, [])

    def test_ein_fehlendes_skript_wirft_nicht(self):
        # Der Pfad in der Vorlage muss nicht auf der Platte liegen.
        b = _bestand({'templates/s.html':
                      '<script src="{% static \'gibts/nicht.js\' %}"></script>'})
        self.assertEqual(b.seiten[0].skripte, [('gibts/nicht.js', [])])


class DieHauptaeste(BasisTest):

    def test_verzeichnisse_mit_klassen_werden_gefunden(self):
        u"""Mit KLASSEN, nicht mit Python (geaendert 24.08.2026).

        Vorher genuegte eine `.py`-Datei. `tools` und `config` standen
        damit zur Wahl, enthalten aber null Klassen — wer sie waehlte,
        bekam ein leeres Bild ohne Erklaerung.
        """
        ordner = Path(tempfile.mkdtemp(prefix='ha_'))
        (ordner / 'app').mkdir()
        (ordner / 'app' / 'x.py').write_text('class Da:\n    pass\n',
                                             encoding='utf-8')
        (ordner / 'ohne').mkdir()
        (ordner / 'ohne' / 'y.py').write_text('def tu():\n    pass\n',
                                              encoding='utf-8')
        namen = [e['name'] for e in hauptaeste(ordner)]
        self.assertEqual(namen, ['app'])

    def test_die_zahl_der_klassen_steht_dabei(self):
        u"""Die Zahl im Auswahlfeld sind KLASSEN, nicht Dateien.

        Vorher stand dort die Dateizahl (`werkzeug (233)`) und las sich
        wie eine Klassenzahl. Das Ergebnis darunter nannte eine andere.
        """
        ordner = Path(tempfile.mkdtemp(prefix='ha_'))
        (ordner / 'app').mkdir()
        for i in range(3):
            (ordner / 'app' / ('x%d.py' % i)).write_text(
                'class K%d:\n    pass\n' % i, encoding='utf-8')
        self.assertEqual(hauptaeste(ordner)[0]['klassen'], 3)

    def test_ohne_unterordner_ist_die_liste_leer(self):
        self.assertEqual(hauptaeste(tempfile.mkdtemp(prefix='ha_')), [])


class DieZahlenSagenDasselbe(BasisTest):
    u"""Auswahlfeld und Ergebnis müssen übereinstimmen.

    DIE BESCHWERDE (Edgar, 24.08.2026)
    ==================================
        „ich verstehe deine Navigation nicht. was soll der ‚Bereich‘?? ich
         möchte eine klare Navigation haben wo ich alle Unterteilungen habe
         die die Summe 1004 ergibt"

    Es waren drei verschiedene Zahlen für dieselbe Sache im Umlauf:

        Auswahlfeld      233   `.py`-DATEIEN, gelesen wie Klassen
        Auswahlfeld      615   Klassen ohne `tests/`
        Auswahlfeld     1086   Klassen-DEFINITIONEN
        Ergebnis        1004   verschiedene Klassen-NAMEN

    `tools (14)` und `config (6)` sahen nach Inhalt aus und enthielten null
    Klassen. Wer zwei Zahlen für dieselbe Sache sieht, glaubt keiner von
    beiden.
    """

    def _projekt(self):
        import tempfile
        from pathlib import Path
        ordner = Path(tempfile.mkdtemp(prefix='hz_'))
        (ordner / 'echt').mkdir()
        (ordner / 'echt' / 'a.py').write_text(
            'class Eins:\n    pass\n\n\nclass Zwei:\n    pass\n',
            encoding='utf-8')
        (ordner / 'echt' / 'tests').mkdir()
        (ordner / 'echt' / 'tests' / 'test_x.py').write_text(
            'class DreiTest:\n    pass\n', encoding='utf-8')
        # Gleicher Name zweimal — zaehlt einmal, wie im Klassenmodell.
        (ordner / 'echt' / 'b.py').write_text(
            'class Eins:\n    pass\n', encoding='utf-8')
        (ordner / 'leer').mkdir()
        (ordner / 'leer' / 'nur_funktionen.py').write_text(
            'def tu():\n    pass\n', encoding='utf-8')
        return ordner

    def test_die_quelle_nennt_dieselbe_zahl_wie_das_modell(self):
        from djangobase.umbau.klassenmodell import Klassenmodell
        ordner = self._projekt()
        quellen = {q['name']: q['klassen'] for q in hauptaeste(ordner)}
        echt = len(Klassenmodell(ordner / 'echt').lesen().klassen)
        self.assertEqual(quellen['echt'], echt,
                         'Auswahlfeld und Ergebnis nennen verschiedene '
                         'Zahlen — dann glaubt man keiner von beiden.')

    def test_gleichnamige_klassen_zaehlen_einmal(self):
        u"""In CamTrack heissen 82 Klassen doppelt: 1086 gegen 1004."""
        quellen = {q['name']: q['klassen'] for q in hauptaeste(self._projekt())}
        self.assertEqual(quellen['echt'], 3, 'Eins, Zwei, DreiTest')

    def test_tests_zaehlen_mit(self):
        u"""Das Klassenmodell schliesst `tests/` nicht aus — die Quelle
        darf es dann auch nicht."""
        quellen = {q['name']: q['klassen'] for q in hauptaeste(self._projekt())}
        self.assertEqual(quellen['echt'], 3)

    def test_ein_verzeichnis_ohne_klassen_steht_nicht_zur_wahl(self):
        u"""`tools (14)` sah nach Inhalt aus und hatte null Klassen."""
        namen = [q['name'] for q in hauptaeste(self._projekt())]
        self.assertNotIn('leer', namen)
