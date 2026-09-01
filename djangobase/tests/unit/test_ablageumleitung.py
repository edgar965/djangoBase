# -*- coding: utf-8 -*-
u"""`Ablageumleitung._verwaiste_raeumen` — was weg darf und was nicht.

DER ANLASS (31.08.2026)
=======================
Die Umleitung legt je Prozess einen Wegwerfordner an (`p60596`). Beim
regulaeren Ende raeumt `atexit` ihn — bei einem harten Abbruch nicht,
und genau der Abbruch ist der Fall, der etwas stehenlaesst. Als
Auffangnetz galt eine Frist von 24 Stunden.

Zu langsam: Zwoelf Ordner aus drei abgebrochenen Laeufen desselben Tages
lagen im Projektbaum. In einem davon steckte eine JS-Attrappe, die
absichtlich auf ein fehlendes Modul zeigt — `GrundtestEsModule` las sie
als echten Projektcode und meldete vier Importe ins Leere. Jeder
Gesamtlauf rot, aus eigenen Resten.

DIE GEFAEHRLICHE RICHTUNG ist die andere: Ein Ordner, der zu einem
LAUFENDEN Prozess gehoert, darf nie geloescht werden — der schreibt
gerade hinein. Deshalb prueft die Haelfte dieser Faelle, was
STEHENBLEIBT.
"""
import os
import time
from pathlib import Path

from djangobase.tests.ablageumleitung import Ablageumleitung

from ..base import BasisTest


class VerwaisteRaeumenTest(BasisTest):

    def setUp(self):
        super().setUp()
        import tempfile

        self.eltern = Path(tempfile.mkdtemp(prefix='verwaist_',
                                            dir=tempfile.gettempdir()))
        self.addCleanup(self._raeumen)
        self.eigener = self.eltern / ('p%d' % os.getpid())
        self.eigener.mkdir()

    def _raeumen(self):
        import shutil
        shutil.rmtree(self.eltern, ignore_errors=True)

    def _anlegen(self, name, alter_s=0):
        ordner = self.eltern / name
        ordner.mkdir()
        (ordner / 'rest.txt').write_text('x', encoding='utf-8')
        if alter_s:
            alt = time.time() - alter_s
            os.utime(ordner, (alt, alt))
        return ordner

    # ----------------------------------------------------------- Was weg darf

    def test_ordner_eines_toten_prozesses_faellt_sofort(self):
        u"""Ohne Frist — der Name sagt, wessen Rest es ist."""
        tot = self._anlegen('p999999999')
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertFalse(tot.exists(),
                         'Der Rest eines toten Prozesses muss sofort fallen')

    def test_ordner_ohne_prozessnummer_faellt_nach_der_frist(self):
        u"""Ueber ihn weiss man nichts — dann entscheidet wieder das Alter."""
        alt = self._anlegen('gb_1f8okk8w', alter_s=Ablageumleitung.VERFALL + 60)
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertFalse(alt.exists())

    # --------------------------------------------------- Was stehenbleiben muss

    def test_ordner_eines_laufenden_prozesses_bleibt(self):
        u"""Die gefaehrliche Richtung: Er schreibt vielleicht gerade hinein."""
        import subprocess
        import sys

        kind = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: kind.poll() is None and kind.kill())
        lebend = self._anlegen('p%d' % kind.pid, alter_s=Ablageumleitung.VERFALL * 3)
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertTrue(lebend.exists(),
                        'Ein laufender Prozess darf seinen Ordner behalten — '
                        'auch einen uralten')

    def test_der_eigene_ordner_bleibt(self):
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertTrue(self.eigener.exists())

    def test_junger_ordner_ohne_prozessnummer_bleibt(self):
        jung = self._anlegen('gb_frisch')
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertTrue(jung.exists())

    def test_dateien_neben_den_ordnern_bleiben_unberuehrt(self):
        datei = self.eltern / 'notiz.txt'
        datei.write_text('kein Ordner', encoding='utf-8')
        Ablageumleitung._verwaiste_raeumen(self.eltern, self.eigener)
        self.assertTrue(datei.exists())

    def test_ein_fehlendes_elternverzeichnis_wirft_nicht(self):
        fehlt = self.eltern / 'gibtsnicht'
        Ablageumleitung._verwaiste_raeumen(fehlt, fehlt / 'p1')
