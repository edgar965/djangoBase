# -*- coding: utf-8 -*-
u"""Wie groß ist dieses Projekt — Dateien, Zeilen, Klassen nach Art.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „ein Button der eine Statistik macht: Anzahl Dateien, Anzahl py
     Code-Dateien, Anzahl html, js, sonstige (mach Vorschlag). Anzahl
     Code-Zeilen gesamt, py, js, htm usw. Anzahl Klassen (py, js)"

WAS DER ERSTE LAUF ZEIGTE
=========================
    Übrige   47 Dateien   4.858.015 Zeilen

Mehr als das ganze übrige Projekt zusammen. Es waren die
`.pkl`-Zwischenspeicher des Kalenders, byteweise als Text gelesen, dazu
`media/` mit 2673 Bildern und Videos — darunter eines mit 1,7 GB. Eine
Statistik über QUELLTEXT darf Laufzeitdaten nicht mitzählen, und sie muss
sagen, was sie ausgelassen hat: Sonst liest sich „1119 Dateien" wie das
ganze Verzeichnis.
"""
import tempfile
from pathlib import Path

from djangobase.umbau.codezahlen import Codezahlen

from ..base import BasisTest


def _zaehlen(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='cz_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
    return Codezahlen(ordner).lesen()


class DieArtStehtAmSuffix(BasisTest):

    def test_die_sieben_arten(self):
        for name, erwartet in (('a.py', u'Python'),
                               ('a.html', u'HTML-Vorlagen'),
                               ('a.js', u'JavaScript'),
                               ('a.css', u'Stilblätter'),
                               ('a.json', u'Einstellungen'),
                               ('a.md', u'Dokumentation'),
                               ('a.png', u'Bilder & Binäres')):
            self.assertEqual(Codezahlen.art(name), erwartet, name)

    def test_was_nirgends_passt_faellt_nicht_weg(self):
        u"""Sonst stimmt die Summe nicht — und man sieht es nicht."""
        self.assertEqual(Codezahlen.art('a.seltsam'), u'Übrige')

    def test_ohne_endung_ist_es_uebrig(self):
        self.assertEqual(Codezahlen.art('Makefile'), u'Übrige')

    def test_die_grossschreibung_zaehlt_nicht(self):
        self.assertEqual(Codezahlen.art('BILD.PNG'), u'Bilder & Binäres')


class DreiZeilenartenStattEiner(BasisTest):
    u"""„Anzahl Code-Zeilen" ist mehrdeutig — hier getrennt gezählt."""

    QUELLE = (u'# ein Kommentar\n'
              u'import os\n'
              u'\n'
              u'\n'
              u'class Ding:\n'
              u'    """Ein Docstring."""\n'
              u'\n'
              u'    def machen(self):\n'
              u'        return "# kein Kommentar"\n')

    def _py(self):
        return _zaehlen({'a.py': self.QUELLE}).arten[u'Python']

    def test_die_drei_arten_ergeben_die_zeilenzahl(self):
        py = self._py()
        self.assertEqual(py.anweisungen + py.kommentar + py.leer, py.zeilen)

    def test_ein_gitter_in_einer_zeichenkette_ist_kein_kommentar(self):
        u"""Wer das mit `startswith('#')` zählt, liegt daneben — aber hier
        steht das Gitter nicht am Zeilenanfang, also greift schon die
        einfache Regel. Der AST entscheidet über Klassen und Funktionen."""
        self.assertEqual(self._py().kommentar, 1)

    def test_klassen_und_funktionen_kommen_aus_dem_ast(self):
        py = self._py()
        self.assertEqual((py.klassen, py.funktionen), (1, 1))

    def test_eine_kaputte_datei_kostet_nur_ihre_klassen(self):
        u"""Die Zeilen zählen weiter — ein Syntaxfehler ist kein Grund,
        die Datei aus der Statistik zu werfen."""
        z = _zaehlen({'kaputt.py': u'def (:\n'})
        self.assertEqual(z.arten[u'Python'].dateien, 1)
        self.assertEqual(z.arten[u'Python'].klassen, 0)


class JavaScriptWirdMitgezaehlt(BasisTest):

    def test_klassen_und_funktionen(self):
        js = _zaehlen({'a.js': (u'export class Kachel {\n'
                                u'    zeichnen() { return 1; }\n'
                                u'}\n'
                                u'function los() { return 2; }\n'
                                u'const auch = (x) => x;\n')}).arten[
            u'JavaScript']
        self.assertEqual(js.klassen, 1)
        self.assertEqual(js.funktionen, 2)

    def test_zwei_schraegstriche_sind_kommentar(self):
        js = _zaehlen({'a.js': u'// hier\nlet x = 1;\n'}).arten[u'JavaScript']
        self.assertEqual((js.kommentar, js.anweisungen), (1, 1))


class LaufzeitdatenZaehlenNicht(BasisTest):
    u"""DER BEFUND (24.08.2026): 47 Dateien mit 4,8 Millionen Zeilen."""

    DATEIEN = {
        'echt.py': u'class Echt:\n    pass\n',
        'media/.cache/kalender.pkl': u'x' * 200,
        'media/bilder/a.png': u'x',
        'logs/out.log': u'zeile\n' * 500,
        'tmp/wegwerf.py': u'class Weg:\n    pass\n',
    }

    def test_nur_der_quelltext_zaehlt(self):
        z = _zaehlen(self.DATEIEN)
        self.assertEqual(z.gesamt()['dateien'], 1)
        self.assertEqual(z.gesamt()['klassen'], 1)

    def test_das_ausgelassene_wird_genannt(self):
        u"""Ohne diese Zahl liest sich „1119 Dateien" wie alles."""
        z = _zaehlen(self.DATEIEN)
        self.assertEqual(z.ausgelassen, 4)
        self.assertEqual(sorted(z.ausgelassen_wo), ['logs', 'media', 'tmp'])

    def test_zu_grosse_dateien_sind_kein_quelltext(self):
        u"""Ein Modell mit 174 MB heißt `.pt`, ein Video `.mp4` — aber
        auch eine `.py` mit 3 MB ist nichts, was jemand geschrieben hat."""
        ordner = Path(tempfile.mkdtemp(prefix='cz_'))
        (ordner / 'riesig.py').write_text(u'# x\n' * 700000,
                                          encoding='utf-8')
        (ordner / 'klein.py').write_text(u'class K:\n    pass\n',
                                         encoding='utf-8')
        z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()['dateien'], 1)
        self.assertEqual(z.ausgelassen_wo.get(u'zu groß'), 1)


class DieSummeStimmt(BasisTest):

    DATEIEN = {'a.py': u'class A:\n    pass\n',
               'b.html': u'<div>\n</div>\n',
               'c.js': u'class C {}\n',
               'd.seltsam': u'was auch immer\n'}

    def test_die_liste_summiert_sich_zum_gesamt(self):
        u"""Ohne diese Eigenschaft ist eine Statistik wertlos: Man sieht
        ihr nicht an, ob etwas fehlt."""
        z = _zaehlen(self.DATEIEN)
        gesamt = z.gesamt()
        for feld in ('dateien', 'zeilen', 'anweisungen', 'kommentar',
                     'leer', 'klassen', 'funktionen'):
            self.assertEqual(sum(a[feld] for a in z.liste()), gesamt[feld],
                             feld)

    def test_auch_leere_arten_stehen_in_der_liste(self):
        u"""Dass ein Projekt KEIN CSS hat, ist eine Auskunft. Eine
        fehlende Zeile liest sich als Versehen."""
        namen = [a['name'] for a in _zaehlen({'a.py': u'x = 1\n'}).liste()]
        self.assertIn(u'Stilblätter', namen)
        self.assertEqual(len(namen), 8)

    def test_die_kennzahlen_trennen_py_und_js(self):
        k = _zaehlen(self.DATEIEN).kennzahlen()
        self.assertEqual((k['py_klassen'], k['js_klassen']), (1, 1))
        self.assertEqual(k['klassen'], 2)

    def test_ein_leeres_verzeichnis_wirft_nicht(self):
        z = _zaehlen({})
        self.assertEqual(z.gesamt()['dateien'], 0)
        self.assertEqual(z.kennzahlen()['kommentar_anteil'], 0.0)
