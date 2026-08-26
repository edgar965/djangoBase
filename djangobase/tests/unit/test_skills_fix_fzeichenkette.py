# -*- coding: utf-8 -*-
u"""Leere f-Zeichenketten entschärfen — und warum es nur DIESEN Fixer gab.

DIE FRAGE (Edgar, 25.08.2026)
=============================
    „Hast du auch alle Werkzeuge in djangoBase für die Code-Qualität und
     für die Fixes der Code-Qualität usw?"  …  „merge, keine Duplikate!"

Beim Nachsehen kam ein Fund gegen mich heraus: djangoBase hatte längst
``ImportFixer`` (Kriterium 5) — mit Sicherung, Netz und sogar
``# noqa``-Erkennung. Ich hatte daneben in CamTrack ein eigenes Skript
``tools/wartung/pyflakes_fixen.py`` gebaut, das dieselben toten Einfuhren
entfernt: im falschen Projekt, ohne Sicherung, ohne Netz.

Übrig blieb genau EINE Fähigkeit, die es hier noch nicht gab — die leeren
f-Zeichenketten. Sie ist jetzt ein Fixer wie die anderen; das Skript ist
gelöscht.

DIE VIER FÄLLE, DIE ES ZU UNTERSCHEIDEN GILT
============================================
    f'fertig'        ->  'fertig'      leer, wird entschärft
    f'{n} Stück'     ->  unverändert   hat einen Platzhalter
    f'x'  # noqa     ->  unverändert   ausdrückliche Ansage des Autors
    f'a' 'b'         ->  'a' 'b'       Verkettung: die Spalte muss stimmen
"""
import io
import tempfile
from pathlib import Path

from djangobase.skills.fix_fzeichenkette import FixFZeichenkette

from ..base import BasisTest


def _fixer(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='fixf_'))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        io.open(ziel, 'w', encoding='utf-8').write(inhalt)
    werkzeug = FixFZeichenkette()
    werkzeug.wurzel = lambda: ordner
    return werkzeug, ordner


class WasEntschaerftWird(BasisTest):

    QUELLE = (u"def melden(n):\n"
              u"    a = f'fertig'\n"
              u"    b = f'{n} Stück'\n"
              u"    c = f'auch leer'  # noqa\n"
              u"    d = f'a' 'b'\n"
              u"    return a, b, c, d\n")

    def _neu(self):
        werkzeug, _o = _fixer({'melden.py': self.QUELLE})
        aenderungen = werkzeug.vorschau().aenderungen
        self.assertEqual(len(aenderungen), 1)
        return aenderungen[0].neuer_text

    def test_ein_leeres_f_faellt(self):
        self.assertIn(u"a = 'fertig'", self._neu())

    def test_ein_platzhalter_bleibt(self):
        self.assertIn(u"b = f'{n} Stück'", self._neu())

    def test_noqa_bleibt(self):
        u"""Dieselbe Regel wie bei ``ImportFixer``: Die Marke ist die
        ausdrückliche Ansage des Autors."""
        self.assertIn(u"c = f'auch leer'  # noqa", self._neu())

    def test_eine_verkettung_wird_an_der_richtigen_stelle_geschnitten(self):
        u"""Der AST nennt bei ``f'a' 'b'`` den Anfang der GANZEN Verkettung.
        Ohne die Prüfung „steht dort wirklich ein f?" schneidet ein Fixer
        hier mitten in den Quelltext."""
        self.assertIn(u"d = 'a' 'b'", self._neu())

    def test_die_zahl_steht_im_was(self):
        werkzeug, _o = _fixer({'melden.py': self.QUELLE})
        self.assertEqual(werkzeug.vorschau().aenderungen[0].was,
                         '2 leere f-Zeichenketten')


class WasUnberuehrtBleibt(BasisTest):

    def test_eine_datei_ohne_f_erzeugt_keine_aenderung(self):
        werkzeug, _o = _fixer({'ruhig.py': u"x = 'nichts'\n"})
        self.assertEqual(werkzeug.vorschau().aenderungen, [])

    def test_eine_kaputte_datei_wird_uebersprungen(self):
        u"""Ein Syntaxfehler ist ein Fall für `code-qualität`, nicht für
        einen Fixer, der schreiben will."""
        werkzeug, _o = _fixer({'kaputt.py': u"def (:\n"})
        self.assertEqual(werkzeug.vorschau().aenderungen, [])

    def test_ein_leeres_projekt_wirft_nicht(self):
        werkzeug, _o = _fixer({})
        self.assertEqual(werkzeug.vorschau().aenderungen, [])


class DasNetzHaeltStand(BasisTest):

    def test_nach_dem_schreiben_ist_nichts_uebrig(self):
        werkzeug, ordner = _fixer({'a.py': u"x = f'leer'\n"})
        aenderung = werkzeug.vorschau().aenderungen[0]
        io.open(aenderung.pfad, 'w', encoding='utf-8').write(
            aenderung.neuer_text)
        self.assertEqual(werkzeug.pruefen(aenderung), [])

    def test_eine_kaputte_datei_wird_gemeldet(self):
        u"""Das Netz muss anschlagen, sonst bleibt Kaputtes liegen."""
        werkzeug, _o = _fixer({'a.py': u"x = f'leer'\n"})
        aenderung = werkzeug.vorschau().aenderungen[0]
        io.open(aenderung.pfad, 'w', encoding='utf-8').write(u"def (:\n")
        self.assertTrue(werkzeug.pruefen(aenderung))

    def test_uebriggebliebene_werden_gemeldet(self):
        u"""Nicht nur „parst noch" — auch „ist wirklich erledigt"."""
        werkzeug, _o = _fixer({'a.py': u"x = f'leer'\n"})
        aenderung = werkzeug.vorschau().aenderungen[0]
        io.open(aenderung.pfad, 'w', encoding='utf-8').write(u"y = f'immer noch'\n")
        self.assertTrue(werkzeug.pruefen(aenderung))


class KeineDuplikate(BasisTest):
    u"""Ein Befund gehört genau EINEM Werkzeug.

    „merge, keine Duplikate!" (Edgar, 25.08.2026)
    """

    def test_der_fixer_ist_angemeldet(self):
        from djangobase.skills import FIXER
        self.assertIn('fix-fzeichenkette', [k.slug for k in FIXER])

    def test_code_qualitaet_listet_fremde_befunde_nicht_selbst(self):
        u"""`pyflakes` meldet auch tote Einfuhren — die führt
        `tote-importe`, mit Wissen, das `pyflakes` nicht hat."""
        from djangobase.umbau.codequalitaet import ANDERSWO
        self.assertEqual(ANDERSWO['UnusedImport'], 'tote-importe')
        self.assertEqual(ANDERSWO['FStringMissingPlaceholders'],
                         'fix-fzeichenkette')

    def test_sie_verschwinden_aber_nicht(self):
        u"""Weglassen wäre schlimmer als doppelt melden: Die Zahl bleibt,
        mit dem Namen des Werkzeugs, das den Befund führt."""
        from djangobase.umbau.codequalitaet import Codequalitaet
        werkzeug, ordner = _fixer({'a.py': u"import os\n"})
        messung = Codequalitaet(ordner).messen()
        fehler = [v for v in messung.verfahren if 'Fehler' in v.name][0]
        self.assertEqual(fehler.treffer, [])
        self.assertIn('tote-importe', fehler.satz)
