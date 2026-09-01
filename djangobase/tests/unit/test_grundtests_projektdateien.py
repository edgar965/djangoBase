# -*- coding: utf-8 -*-
u"""`grundtests._projektdateien` — was git ignoriert, ist kein Projektcode.

DER ANLASS (31.08.2026)
=======================
`GrundtestEsModule` und `GrundtestVorlagen` durchsuchten `BASE_DIR` und
uebersprangen dabei eine feste Namensliste: `node_modules`, `venv`,
`pythonVENV`, `.venv`, `site-packages`. Die Liste kennt nur, was jemand
aufgeschrieben hat.

Nicht darin stand `_wegwerf/` — der Ordner, in den `Ablageumleitung` die
Zwischendateien der Testlaeufe umlenkt, damit sie nicht auf C: landen.
Dort liegen Attrappen: winzige `static/app/js/start.js`, die ABSICHTLICH
auf ein fehlendes Nachbarmodul zeigen, weil ein Test genau diesen Fall
prueft. `GrundtestEsModule` las sie als echten Projektcode und meldete
vier JS-Importe ins Leere.

Ein Test, der aus den eigenen Resten rot wird, wird nach der zweiten
Woche ignoriert — und dann prueft er gar nichts mehr.

`.gitignore` wusste es die ganze Zeit. Also wird git gefragt.

WAS HIER GEPRUEFT WIRD
======================
1. Eine ignorierte Datei erscheint nicht (der Fehlalarm ist weg).
2. Eine normale Datei erscheint sehr wohl (der Pruefer ist nicht einfach
   still geworden — die Gegenprobe).
3. Ohne git-Antwort bleibt die Namensliste als Notbremse.
"""
import subprocess
import tempfile
from pathlib import Path

from django.test import override_settings

from djangobase import grundtests

from ..base import BasisTest


class ProjektdateienTest(BasisTest):

    def setUp(self):
        super().setUp()
        self.wurzel = Path(tempfile.mkdtemp(prefix='projektdateien_',
                                            dir=tempfile.gettempdir()))
        self.addCleanup(self._raeumen)
        (self.wurzel / 'app' / 'static' / 'js').mkdir(parents=True)
        (self.wurzel / 'app' / 'static' / 'js' / 'echt.js').write_text(
            "import x from './x.js';\n", encoding='utf-8')
        (self.wurzel / '_wegwerf' / 'static' / 'js').mkdir(parents=True)
        (self.wurzel / '_wegwerf' / 'static' / 'js' / 'attrappe.js').write_text(
            "import y from '../fehlt.js';\n", encoding='utf-8')

    def _raeumen(self):
        import shutil

        # Der GitFilter merkt sich seine Antwort je Wurzel — sonst sieht
        # der naechste Fall die Antwort von diesem.
        from djangobase.skills.gitfilter import GitFilter
        GitFilter._gemerkt.pop(str(self.wurzel.resolve()), None)
        shutil.rmtree(self.wurzel, ignore_errors=True)

    def _repo_anlegen(self, ignoriert='_wegwerf/\n'):
        (self.wurzel / '.gitignore').write_text(ignoriert, encoding='utf-8')
        for befehl in (['git', 'init', '-q'],
                       ['git', 'add', '-A'],
                       ['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-qm', 'erst']):
            subprocess.run(befehl, cwd=str(self.wurzel), capture_output=True,
                           timeout=60)

    def _gefunden(self):
        with override_settings(BASE_DIR=str(self.wurzel)):
            return sorted(p.name for p in
                          grundtests._projektdateien('static/**/*.js'))

    def test_was_git_ignoriert_wird_uebersprungen(self):
        self._repo_anlegen()
        self.assertEqual(self._gefunden(), ['echt.js'],
                         'Die Attrappe aus `_wegwerf/` gehoert nicht dazu')

    def test_normale_dateien_kommen_weiterhin_durch(self):
        u"""Die Gegenprobe: Der Pruefer ist nicht einfach still geworden."""
        self._repo_anlegen()
        self.assertIn('echt.js', self._gefunden())

    def test_ohne_git_bleibt_die_namensliste_die_notbremse(self):
        u"""Kein Repo — dann filtert `GitFilter` nichts, und das ist richtig.

        Ein Projekt ohne git ist kein Grund, gar nichts mehr zu pruefen.
        Die Attrappe erscheint dann wieder; dafuer ist die Namensliste da,
        und `_wegwerf` steht bewusst NICHT darin (sie soll nicht zur
        zweiten Wahrheit werden).
        """
        gefunden = self._gefunden()
        self.assertIn('echt.js', gefunden)
        self.assertIn('attrappe.js', gefunden)

    def test_fremde_ordner_fallen_immer_heraus(self):
        u"""`node_modules` & Co. — auch mit git."""
        (self.wurzel / 'node_modules' / 'static' / 'js').mkdir(parents=True)
        (self.wurzel / 'node_modules' / 'static' / 'js' / 'fremd.js').write_text(
            'export default 1;\n', encoding='utf-8')
        self._repo_anlegen(ignoriert='')
        self.assertNotIn('fremd.js', self._gefunden())
