# -*- coding: utf-8 -*-
u"""Zwischendateien ohne ``dir=`` — und die Ausnahmen, die bleiben muessen.

Der ``anlassfall-check`` faehrt das Werkzeug an seinem eigenen Fall.
Hier stehen die Formen daneben, an denen ein solcher Pruefer zu viel
meldet: Fehlalarme sind teurer als fehlende Befunde, weil sie die
echten verdecken.

DIE VORGESCHICHTE
=================
Aus ``tempfile`` ohne ``dir=`` sind in einem Projekt rund 100 GB
Datenmuell auf C: entstanden. In assistant fanden sich sechs solche
Stellen — jede legt eine VOLLSTAENDIGE Kopie an (Mail-Anhang, PDF beim
Verkleinern, WAV beim Entrauschen).

BDD - GEGEBEN / DANN
====================
    EineZwischendateiOhneOrt ... wird gemeldet
    EineMitOrt               ... nicht
    EinTest                  ... nicht
    JedeAnlegerfunktion      ... wird erkannt
"""
from djangobase.skills.systemablage import Systemablage

from .test_neue_werkzeuge import WerkzeugBasis


class EineZwischendateiOhneOrt(WerkzeugBasis):
    u"""Gegeben: Der Ort bleibt offen — dann waehlt ihn das System."""

    def test_mkstemp_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': "import tempfile\n\nx = tempfile.mkstemp(suffix='.pdf')\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])

    def test_die_meldung_nennt_den_aufruf(self):
        projekt = self.projekt({'a.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        self.assertIn('mkstemp', projekt.fahren(Systemablage)[0]['befund'])

    def test_auch_direkt_importiert(self):
        u"""``from tempfile import mkstemp`` ist derselbe Aufruf."""
        projekt = self.projekt({
            'a.py': "from tempfile import mkstemp\nx = mkstemp()\n"})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)

    def test_mehrere_in_einer_datei_zaehlen_einzeln(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp()\n"
                     "y = tempfile.mkstemp()\n")})
        self.assertEqual(len(projekt.fahren(Systemablage)), 2)


class JedeAnlegerfunktion(WerkzeugBasis):
    u"""Gegeben: ``tempfile`` bietet mehrere Wege zum selben Ergebnis."""

    def test_alle_werden_erkannt(self):
        zeilen = ['import tempfile']
        for name in Systemablage.ANLEGER:
            zeilen.append(f'x = tempfile.{name}()')
        projekt = self.projekt({'a.py': '\n'.join(zeilen) + '\n'})
        self.assertEqual(len(projekt.fahren(Systemablage)),
                         len(Systemablage.ANLEGER))

    def test_ein_verzeichnis_zaehlt_mit(self):
        u"""``TemporaryDirectory`` ist der teuerste Fall — dort landet
        nicht eine Datei, sondern ein ganzer Ablauf."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "with tempfile.TemporaryDirectory() as d:\n"
                     "    pass\n")})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)


class EineMitOrt(WerkzeugBasis):
    u"""Gegeben: ``dir=`` ist angegeben."""

    def test_sie_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp(dir='/projekt/tmp')\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_egal_was_darin_steht(self):
        u"""Wohin genau, entscheidet das Projekt — nicht dieses
        Werkzeug."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "from django.conf import settings\n"
                     "x = tempfile.mkstemp(dir=settings.BASE_DIR)\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_auch_neben_anderen_angaben(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp(suffix='.pdf', prefix='a_',\n"
                     "                     dir='/projekt/tmp')\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_aber_die_daneben_schon(self):
        u"""Die Gegenprobe: Eine richtige Stelle darf die falsche
        daneben nicht verdecken."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "gut = tempfile.mkstemp(dir='/projekt/tmp')\n"
                     "schlecht = tempfile.mkstemp()\n")})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])


class EinTest(WerkzeugBasis):
    u"""Gegeben: Eine Pruefung legt ein Wegwerf-Verzeichnis an.

    Es verschwindet mit ihr, und es geht um Beispieldaten, nicht um
    Nutzdaten.
    """

    def test_am_dateinamen_erkannt(self):
        projekt = self.projekt({
            'app/test_x.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_am_ordner_erkannt(self):
        projekt = self.projekt({
            'app/tests/hilfe.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_produktivcode_daneben_schon(self):
        projekt = self.projekt({
            'app/tests/hilfe.py': "import tempfile\nx = tempfile.mkstemp()\n",
            'app/dienst.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('dienst.py', zeilen[0]['ort'])


class EineKaputteDatei(WerkzeugBasis):
    u"""Gegeben: Eine Datei, die sich nicht zerlegen laesst."""

    def test_sie_wirft_nicht(self):
        projekt = self.projekt({
            'kaputt.py': "def (:\n",
            'gut.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)


class DerEigeneAnlassfall(WerkzeugBasis):
    u"""Gegeben: Der Fall, den das Werkzeug bei sich traegt."""

    def test_er_wird_gefunden(self):
        fall = Systemablage.anlassfall
        projekt = self.projekt(fall.dateien)
        zeilen = fall.dateibezogen(projekt.fahren(Systemablage))
        self.assertGreaterEqual(len(zeilen), fall.mindestens, zeilen)
        self.assertLessEqual(len(zeilen), fall.hoechstens, zeilen)
        self.assertIn(fall.erwartet_in, zeilen[0]['ort'])

    def test_und_im_leeren_findet_es_nichts(self):
        self.assertEqual(self.projekt({}).fahren(Systemablage), [])
