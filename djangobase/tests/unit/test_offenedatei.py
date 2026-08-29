# -*- coding: utf-8 -*-
u"""``open()`` ohne ``with`` und ohne ``close()`` — und die Ausnahmen.

DAS MUSTER
==========
Logdatei auf, an ``Popen`` weitergegeben, nie zu. Der Subprozess erbt
den Deskriptor und schreibt weiter — die Ausgabe stimmt also. Der
aufrufende Prozess behält seinen aber auch. Genau deshalb fällt es nicht
auf: Es gibt nichts zu sehen, bis keine Handles mehr da sind.

In assistant fünfmal gefunden (28./29.08.2026), viermal als Abschrift
voneinander. Die fünfte Stelle macht es richtig und war die Vorlage.

BDD - GEGEBEN / DANN
====================
    EineOffeneDatei    ... wird gemeldet
    EinTryFinally      ... nicht
    EinWithBlock       ... nicht
    EinRueckgabewert   ... nicht (gehört dem Aufrufer)
"""
from djangobase.skills.offenedatei import OffeneDatei

from .test_neue_werkzeuge import WerkzeugBasis


class EineOffeneDatei(WerkzeugBasis):
    u"""Gegeben: Die Datei wird geöffnet und liegen gelassen."""

    def test_sie_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("def f(pfad):\n"
                     "    datei = open(pfad, 'w')\n"
                     "    datei.write('x')\n")})
        zeilen = projekt.fahren(OffeneDatei)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:2', zeilen[0]['ort'])

    def test_die_meldung_nennt_den_namen(self):
        projekt = self.projekt({
            'a.py': "def f(p):\n    protokoll = open(p, 'w')\n"})
        self.assertIn('protokoll', projekt.fahren(OffeneDatei)[0]['befund'])

    def test_zwei_in_einer_funktion_zaehlen_einzeln(self):
        projekt = self.projekt({
            'a.py': ("def f(p, q):\n"
                     "    eins = open(p, 'w')\n"
                     "    zwei = open(q, 'w')\n")})
        self.assertEqual(len(projekt.fahren(OffeneDatei)), 2)

    def test_der_haeufige_fall_mit_popen(self):
        projekt = self.projekt({
            'a.py': ("import subprocess\n"
                     "\n"
                     "\n"
                     "def starten(befehl, pfad):\n"
                     "    lf = open(pfad, 'w')\n"
                     "    subprocess.Popen(befehl, stdout=lf)\n")})
        self.assertEqual(len(projekt.fahren(OffeneDatei)), 1)


class EinTryFinally(WerkzeugBasis):
    u"""Gegeben: Die Datei wird im ``finally`` geschlossen."""

    def test_sie_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("import subprocess\n"
                     "\n"
                     "\n"
                     "def starten(befehl, pfad):\n"
                     "    protokoll = open(pfad, 'w')\n"
                     "    try:\n"
                     "        subprocess.Popen(befehl, stdout=protokoll)\n"
                     "    finally:\n"
                     "        protokoll.close()\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])

    def test_auch_ein_close_ohne_finally_zaehlt(self):
        projekt = self.projekt({
            'a.py': ("def f(p):\n"
                     "    datei = open(p, 'w')\n"
                     "    datei.write('x')\n"
                     "    datei.close()\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])

    def test_und_die_uebergabe_an_einen_schliesser(self):
        u"""``self._schliessen(datei)`` — so macht es der Indexer."""
        projekt = self.projekt({
            'a.py': ("class X:\n"
                     "    def f(self, p):\n"
                     "        datei = open(p, 'w')\n"
                     "        self._schliessen(datei)\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])


class EinWithBlock(WerkzeugBasis):
    u"""Gegeben: ``with open(...) as f``."""

    def test_er_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("def f(p):\n"
                     "    with open(p, 'w') as datei:\n"
                     "        datei.write('x')\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])

    def test_auch_mit_popen_darin(self):
        projekt = self.projekt({
            'a.py': ("import subprocess\n"
                     "\n"
                     "\n"
                     "def f(befehl, p):\n"
                     "    with open(p, 'w') as datei:\n"
                     "        subprocess.Popen(befehl, stdout=datei)\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])


class EinRueckgabewert(WerkzeugBasis):
    u"""Gegeben: Die Funktion gibt die Datei zurück.

    Dann gehört sie dem Aufrufer — ob DER sie schließt, kann diese
    Prüfung nicht wissen. Ohne diese Ausnahme meldete das Werkzeug jede
    Fabrikmethode.
    """

    def test_sie_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("def oeffnen(p):\n"
                     "    datei = open(p, 'w')\n"
                     "    return datei\n")})
        self.assertEqual(projekt.fahren(OffeneDatei), [])

    def test_aber_die_andere_daneben_schon(self):
        projekt = self.projekt({
            'a.py': ("def oeffnen(p):\n"
                     "    datei = open(p, 'w')\n"
                     "    return datei\n"
                     "\n"
                     "\n"
                     "def liegenlassen(p):\n"
                     "    andere = open(p, 'w')\n"
                     "    andere.write('x')\n")})
        zeilen = projekt.fahren(OffeneDatei)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('andere', zeilen[0]['befund'])


class ZweiFunktionen(WerkzeugBasis):
    u"""Gegeben: Geschlossen wird in einer ANDEREN Funktion."""

    def test_das_zaehlt_nicht(self):
        u"""Absichtlich streng: Wer die Datei woanders schließt, gibt
        sie normalerweise zurück — und das ist die Ausnahme oben. Sonst
        wäre jeder Name irgendwo im Modul ein Freibrief."""
        projekt = self.projekt({
            'a.py': ("def auf(p):\n"
                     "    datei = open(p, 'w')\n"
                     "    merken(datei)\n"
                     "\n"
                     "\n"
                     "def zu(datei):\n"
                     "    datei.close()\n")})
        self.assertEqual(len(projekt.fahren(OffeneDatei)), 1)


class EineKaputteDatei(WerkzeugBasis):
    u"""Gegeben: Eine Datei, die sich nicht zerlegen lässt."""

    def test_sie_wirft_nicht(self):
        projekt = self.projekt({
            'kaputt.py': "def (:\n",
            'gut.py': "def f(p):\n    d = open(p, 'w')\n"})
        self.assertEqual(len(projekt.fahren(OffeneDatei)), 1)


class DerEigeneAnlassfall(WerkzeugBasis):
    u"""Gegeben: Der Fall, den das Werkzeug bei sich trägt."""

    def test_er_wird_gefunden(self):
        fall = OffeneDatei.anlassfall
        projekt = self.projekt(fall.dateien)
        zeilen = fall.dateibezogen(projekt.fahren(OffeneDatei))
        self.assertGreaterEqual(len(zeilen), fall.mindestens, zeilen)
        self.assertLessEqual(len(zeilen), fall.hoechstens, zeilen)
        self.assertIn(fall.erwartet_in, zeilen[0]['ort'])

    def test_und_im_leeren_findet_es_nichts(self):
        self.assertEqual(self.projekt({}).fahren(OffeneDatei), [])
