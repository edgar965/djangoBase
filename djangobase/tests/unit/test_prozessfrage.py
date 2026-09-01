# -*- coding: utf-8 -*-
u"""`Prozessfrage` — und was sie vor dem Loeschen verhindert.

DER ANLASS (31.08.2026)
=======================
`Ablageumleitung` legt je Prozess einen Wegwerfordner an, dessen Name
die Prozessnummer traegt. Bei einem harten Abbruch bleibt er liegen;
als Auffangnetz galt eine Frist von 24 Stunden. Zu langsam: Zwoelf
Ordner aus drei abgebrochenen Laeufen desselben Tages lagen im
Projektbaum, und eine JS-Attrappe darin machte jeden Gesamtlauf rot.

Der Ordnername sagt die ganze Zeit, wessen Rest er ist.

WARUM DAS EIGENE TESTS BRAUCHT
==============================
`os.kill(pid, 0)` ist auf POSIX die uebliche Antwort auf „laeufst du
noch?" — **unter Windows BEENDET es den Prozess**. Eine Frage, die
toetet, faellt niemandem auf, solange man sie nur an tote Prozesse
stellt. Deshalb wird hier auch geprueft, dass ein LEBENDER Prozess die
Frage ueberlebt.
"""
import os
import subprocess
import sys
import time

from djangobase.skills.prozessfrage import Prozessfrage

from ..base import BasisTest


class ProzessfrageTest(BasisTest):

    def test_der_eigene_prozess_lebt(self):
        self.assertTrue(Prozessfrage.lebt(os.getpid()))

    def test_eine_unmoegliche_nummer_lebt_nicht(self):
        self.assertFalse(Prozessfrage.lebt(999999999))

    def test_ein_beendeter_prozess_lebt_nicht(self):
        u"""Ein echter Prozess, den wir starten und beenden."""
        kind = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: kind.poll() is None and kind.kill())
        self.assertTrue(Prozessfrage.lebt(kind.pid),
                        'Ein laufender Prozess muss als lebend gelten')
        kind.kill()
        kind.wait(timeout=10)
        # Windows braucht einen Augenblick, bis der Eintrag verschwindet.
        for _ in range(50):
            if not Prozessfrage.lebt(kind.pid):
                break
            time.sleep(0.1)
        self.assertFalse(Prozessfrage.lebt(kind.pid))

    def test_die_frage_toetet_niemanden(self):
        u"""DER Grund für ctypes statt `os.kill`.

        Unter Windows ruft `os.kill(pid, 0)` `TerminateProcess` auf. Wer
        das für die Prüfung „lebt der noch?" benutzt, bringt genau die
        fremden Prozesse um, die er schonen wollte.
        """
        kind = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: kind.poll() is None and kind.kill())
        for _ in range(5):
            Prozessfrage.lebt(kind.pid)
        self.assertIsNone(kind.poll(),
                          'Die Frage hat den Prozess beendet — genau das '
                          'macht `os.kill` unter Windows')

    def test_unsinnige_eingaben_gelten_als_lebend(self):
        u"""Im Zweifel wird nichts geloescht."""
        for eingabe in (None, 'abc', -1, 0, ''):
            self.assertTrue(Prozessfrage.lebt(eingabe),
                            'Bei %r muss die Antwort JA lauten' % (eingabe,))

    def test_nummer_aus_dem_ordnernamen(self):
        self.assertEqual(Prozessfrage.nummer_aus('p60596'), 60596)
        self.assertEqual(Prozessfrage.nummer_aus('p1'), 1)

    def test_ein_name_ohne_nummer_gibt_none(self):
        for name in ('gb_1f8okk8w', 'p', 'pabc', 'irgendwas', ''):
            self.assertIsNone(Prozessfrage.nummer_aus(name),
                              'Bei %r darf keine Nummer herauskommen' % name)
