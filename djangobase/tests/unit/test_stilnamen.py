# -*- coding: utf-8 -*-
u"""`Stilnamen` — erkennt es den Fall, und schweigt es beim Rest?

Der Prüfer sucht Klassennamen, die mit VERSCHIEDENEN Regeln belegt sind. Zwei
Sorten Fehlalarm sind dabei teurer als ein übersehener Fund, und beide sind
schon eingetreten:

* **Gruppen** (`.a, .b { … }`): Dort steht derselbe Name absichtlich an
  mehreren Regeln, die sich ergänzen. Der erste Anlauf hat sie für einen
  Streit gehalten, `hb-padding-3px` in `theatre.html` gespalten und den
  Eingabefeldern die Hälfte ihres Stils genommen — gemeldet von der eigenen
  Gegenprobe, nicht von einem Test.

* **Handgeschriebene Namen**: Dass `.panel-tab` auf drei Seiten anders
  aussieht, ist der Sinn einer seitenlokalen Komponente. Der zweite Anlauf
  meldete 13 solcher Namen; nach dem dritten Fehlalarm liest niemand mehr hin.
"""
from djangobase.skills.befund import Befund
from djangobase.skills.stilnamen import Stilnamen

from ..base import BasisTest


def _finden(text):
    """Die Befunde des Prüfers zu EINER Vorlage, ohne Dateisystem."""
    werkzeug = Stilnamen()
    return werkzeug._regeln(text)


class RegelnLesenTest(BasisTest):
    """Was der Prüfer überhaupt als Regel gelten lässt."""

    def test_einfacher_name_zaehlt(self):
        self.assertEqual(
            [('', 'a', 'color: red')],
            _finden('<style>.a { color: red }</style>'))

    def test_vervielfachter_name_ist_derselbe(self):
        u"""`.x.x.x` ist die Schreibweise der Umsteller für Spezifität."""
        self.assertEqual(
            [('', 'x', 'color: red')],
            _finden('<style>.x.x.x { color: red }</style>'))

    def test_gruppen_bleiben_draussen(self):
        u"""DER Fehlalarm, der beim ersten Anlauf Schaden angerichtet hat."""
        text = ('<style>\n'
                '.a, .b { background: #111 }\n'
                '.a, .c { padding: 4px }\n'
                '</style>')
        self.assertEqual([], _finden(text))

    def test_ein_name_faellt_auch_dann_raus_wenn_er_daneben_allein_steht(self):
        u"""Steht `.a` einmal in einer Gruppe, ist jede Aussage über `.a`
        unvollständig — dann lieber schweigen."""
        text = ('<style>\n'
                '.a, .b { background: #111 }\n'
                '.a { padding: 4px }\n'
                '.d { margin: 0 }\n'
                '</style>')
        self.assertEqual([('', 'd', 'margin: 0')], _finden(text))

    def test_verschachtelter_ausdruck_zaehlt_nicht(self):
        self.assertEqual([], _finden('<style>.a .b { color: red }</style>'))
        self.assertEqual([], _finden('<style>div.a { color: red }</style>'))


class ErzeugtErkennenTest(BasisTest):
    """Trägt der Name seine eigene erste Angabe?"""

    def test_erzeugte_namen(self):
        for name, rumpf in (('hb-margin-top-20px', 'margin-top: 20px; color: #fff'),
                            ('hb-color-4fc1ff', 'color: #4fc1ff'),
                            ('hb-width-100', 'width: 100%; padding: 4px'),
                            ('hb-display-flex', 'display:flex; gap:6px')):
            with self.subTest(name=name):
                self.assertTrue(Stilnamen._ist_erzeugt(name, rumpf))

    def test_handgeschriebene_namen(self):
        for name, rumpf in (('panel-tab', 'flex: 1; text-align: center'),
                            ('viewer-panel', 'display: flex'),
                            ('main-content', 'max-width: none')):
            with self.subTest(name=name):
                self.assertFalse(Stilnamen._ist_erzeugt(name, rumpf))

    def test_leerer_rumpf_ist_nicht_erzeugt(self):
        self.assertFalse(Stilnamen._ist_erzeugt('hb-x', ''))
        self.assertFalse(Stilnamen._ist_erzeugt('hb-x', 'kein doppelpunkt'))


class BefundeTest(BasisTest):
    """Der Lauf über ein Wegwerf-Verzeichnis — Schwere und Wortlaut."""

    def _lauf(self, dateien):
        import shutil
        import tempfile
        from pathlib import Path
        ordner = Path(tempfile.mkdtemp(prefix='stilnamen_'))
        self.addCleanup(shutil.rmtree, str(ordner), True)
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = Stilnamen()
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen().befunde

    def test_zwei_regeln_in_einer_datei_sind_ein_fehler(self):
        befunde = self._lauf({'a.html': (
            '<style>\n'
            '.hb-margin-top-20px { margin-top: 20px; color: #4fc1ff }\n'
            '.hb-margin-top-20px { margin-top: 20px; color: #ff9940 }\n'
            '</style>')})
        self.assertEqual(1, len(befunde))
        self.assertEqual(Befund.FEHLER, befunde[0].gewicht)
        self.assertIn('hb-margin-top-20px', befunde[0].was)

    def test_ueber_dateien_hinweg_nur_ein_hinweis(self):
        befunde = self._lauf({
            'a.html': '<style>.hb-width-100 { width: 100%; padding: 4px }</style>',
            'b.html': '<style>.hb-width-100 { width: 100%; margin-top: 8px }</style>',
        })
        self.assertEqual(1, len(befunde))
        self.assertEqual(Befund.HINWEIS, befunde[0].gewicht)

    def test_handgeschriebener_name_bleibt_still(self):
        befunde = self._lauf({
            'a.html': '<style>.panel-tab { flex: 1; padding: 8px }</style>',
            'b.html': '<style>.panel-tab { flex: 0 0 auto; padding: 6px }</style>',
        })
        self.assertEqual([], befunde)

    def test_derselbe_rumpf_ist_kein_befund(self):
        befunde = self._lauf({
            'a.html': '<style>.hb-width-100 { width: 100% }</style>',
            'b.html': '<style>.hb-width-100 { width: 100% }</style>',
        })
        self.assertEqual([], befunde)


class AtBloeckeTest(BasisTest):
    u"""Eine Ueberschreibung fuer Druck oder schmale Fenster ist kein Streit.

    DER FALL (30.08.2026, assistant): Alle 30 Fehler-Befunde des Projekts
    hatten dieselbe Form — eine Basisregel und daneben ihre Fassung in
    @media print oder @media (max-width: …). Der Ausdruck REGEL
    kennt keine geschachtelten Klammern und las die zweite als Regel auf
    derselben Ebene. Wer dem folgt, nimmt jeder Seite ihre Druckansicht.
    """

    #: Die Druckansicht, wie sie in jeder zweiten Vorlage steht.
    DRUCKSEITE = ('<style>\n'
                  '.noprint { margin-bottom: 1rem }\n'
                  '@media print { .noprint { display: none }'
                  ' body { margin: 0 } }\n'
                  '</style>')

    def _lauf(self, dateien):
        import shutil
        import tempfile
        from pathlib import Path
        ordner = Path(tempfile.mkdtemp(prefix='stilnamen_at_'))
        self.addCleanup(shutil.rmtree, str(ordner), True)
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = Stilnamen()
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen().befunde

    def test_die_beiden_ebenen_werden_getrennt_gelesen(self):
        gefunden = Stilnamen()._regeln(self.DRUCKSEITE)
        self.assertEqual(['', '@media print'],
                         sorted(b for b, _n, _r in gefunden))

    def test_die_druckfassung_ist_kein_befund(self):
        self.assertEqual([], self._lauf({'a.html': self.DRUCKSEITE}))

    def test_auch_ein_umbruch_ist_keiner(self):
        self.assertEqual([], self._lauf({'a.html': (
            '<style>\n'
            '.hb-width-100 { width: 100%; padding: 4px }\n'
            '@media (max-width: 900px) {'
            ' .hb-width-100 { width: 100%; padding: 2px } }\n'
            '</style>')}))

    def test_zweimal_im_selben_media_block_bleibt_ein_fehler(self):
        u"""Die Gegenprobe: Der Pruefer ist nicht einfach still geworden."""
        befunde = self._lauf({'a.html': (
            '<style>@media print {\n'
            '.hb-margin-top-20px { margin-top: 20px; color: #4fc1ff }\n'
            '.hb-margin-top-20px { margin-top: 20px; color: #ff9940 } }\n'
            '</style>')})
        self.assertEqual(1, len(befunde))
        self.assertEqual(Befund.FEHLER, befunde[0].gewicht)
        self.assertIn('@media print', befunde[0].was)
