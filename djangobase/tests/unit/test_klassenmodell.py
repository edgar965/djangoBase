# -*- coding: utf-8 -*-
u"""Das Klassenmodell — was aus dem Quelltext gelesen und gezeichnet wird.

WOZU (Edgar, 24.08.2026)
========================
    „erstelle eine Seite in djangoBase hilfe - werkzeug Klassenmodell, das
     soll einen Button enthalten, der so eine Übersicht des Codes erstellt"

`objektwurzeln` misst dasselbe Verhaeltnis als ZAHL. Eine Zahl sagt, wie
gut das Modell ist; sie zeigt nicht, WIE es aussieht.

Der Unterschied, um den es hier geht, ist der zwischen einem Kasten-Eintrag
und einer Linie::

    self.name  = 'Anna'      -> Attribut, steht IM Kasten
    self.zeiger = Zeiger()   -> Beziehung, wird als LINIE gezeichnet
    self.balken = []         -> Sammlung, Vielfachheit 0..*

Wer das verwechselt, bekommt entweder ein Bild ohne Linien oder eines, in
dem jede Zeichenkette ein eigener Kasten ist.
"""
import tempfile
from pathlib import Path

from djangobase.umbau.klassenbild import Klassenbild
from djangobase.umbau.klassenmodell import Beziehung, Klassenmodell

from ..base import BasisTest


def _projekt(dateien):
    ordner = Path(tempfile.mkdtemp(prefix='km_'))
    for name, inhalt in dateien.items():
        (ordner / name).write_text(inhalt, encoding='utf-8')
    return Klassenmodell(ordner).lesen()


class WasAusDemQuelltextGelesenWird(BasisTest):

    def test_eine_klasse_wird_gefunden(self):
        m = _projekt({'a.py': 'class Gast:\n    pass\n'})
        self.assertIn('Gast', m.klassen)

    def test_ein_wert_ist_ein_attribut_keine_beziehung(self):
        m = _projekt({'a.py': (
            'class Gast:\n'
            '    def __init__(self):\n'
            "        self.name = 'Anna'\n")})
        gast = m.klassen['Gast']
        self.assertEqual([f.name for f in gast.felder], ['name'])
        self.assertEqual(gast.haelt, [])

    def test_eine_erzeugte_klasse_ist_eine_beziehung(self):
        m = _projekt({'a.py': (
            'class Zimmer:\n    pass\n\n\n'
            'class Belegung:\n'
            '    def __init__(self):\n'
            '        self.zimmer = Zimmer()\n')})
        self.assertEqual(m.klassen['Belegung'].haelt,
                         [('zimmer', 'Zimmer', '1')])
        self.assertEqual([f.name for f in m.klassen['Belegung'].felder], [])

    def test_eine_sammlung_haelt_viele(self):
        m = _projekt({'a.py': (
            'class Gast:\n    pass\n\n\n'
            'class Belegung:\n'
            '    def __init__(self):\n'
            '        self.gaeste = [Gast()]\n')})
        self.assertEqual(m.klassen['Belegung'].haelt,
                         [('gaeste', 'Gast', '0..*')])

    def test_vererbung_wird_gelesen(self):
        m = _projekt({'a.py': (
            'class Gast:\n    pass\n\n\n'
            'class GastAnmelder(Gast):\n    pass\n')})
        arten = {(b.von, b.nach, b.art) for b in m.beziehungen()}
        self.assertIn(('GastAnmelder', 'Gast', Beziehung.ERBT), arten)

    def test_fremde_oberklassen_zaehlen_nicht(self):
        u"""`Exception` ist keine Klasse dieses Projekts."""
        m = _projekt({'a.py': 'class Fehler(Exception):\n    pass\n'})
        self.assertEqual(m.beziehungen(), [])

    def test_oeffentliche_methoden_stehen_im_kasten(self):
        m = _projekt({'a.py': (
            'class Gast:\n'
            '    def buchen(self):\n        pass\n'
            '    def _intern(self):\n        pass\n')})
        self.assertEqual(m.klassen['Gast'].methoden, ['buchen'])

    def test_der_dickste_ast_ist_der_mit_den_meisten(self):
        m = _projekt({'a.py': (
            'class A:\n    pass\n\n\nclass B:\n    pass\n\n\n'
            'class Klein:\n'
            '    def __init__(self):\n        self.a = A()\n\n\n'
            'class Gross:\n'
            '    def __init__(self):\n'
            '        self.a = A()\n        self.b = B()\n')})
        self.assertEqual(m.dickster_ast(), 'Gross')


class DieNachbarschaftBegrenzt(BasisTest):

    def _kette(self):
        return _projekt({'a.py': (
            'class D:\n    pass\n\n\n'
            'class C:\n'
            '    def __init__(self):\n        self.d = D()\n\n\n'
            'class B:\n'
            '    def __init__(self):\n        self.c = C()\n\n\n'
            'class A:\n'
            '    def __init__(self):\n        self.b = B()\n')})

    def test_ein_schritt_zeigt_die_direkten_nachbarn(self):
        kaesten, _ = self._kette().nachbarschaft('A', tiefe=1)
        self.assertEqual({k.name for k in kaesten}, {'A', 'B'})

    def test_zwei_schritte_gehen_weiter(self):
        kaesten, _ = self._kette().nachbarschaft('A', tiefe=2)
        self.assertEqual({k.name for k in kaesten}, {'A', 'B', 'C'})

    def test_eine_unbekannte_wurzel_liefert_nichts(self):
        # Der Name kommt aus einem Formular — er darf nicht werfen.
        kaesten, linien = self._kette().nachbarschaft('GibtsNicht', tiefe=2)
        self.assertEqual((kaesten, linien), ([], []))


class DasBildWirdGezeichnet(BasisTest):

    def _bild(self):
        m = _projekt({'a.py': (
            'class Zimmer:\n'
            '    def frei(self):\n        pass\n\n\n'
            'class Belegung:\n'
            '    def __init__(self):\n'
            '        self.zimmer = Zimmer()\n'
            "        self.stand = 'offen'\n")})
        kaesten, linien = m.nachbarschaft('Belegung', tiefe=1)
        return Klassenbild(kaesten, linien, 'Belegung').svg()

    def test_es_kommt_svg_heraus(self):
        svg = self._bild()
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.rstrip().endswith('</svg>'))

    def test_beide_kaesten_stehen_drin(self):
        svg = self._bild()
        self.assertIn('>Belegung<', svg)
        self.assertIn('>Zimmer<', svg)

    def test_das_attribut_steht_im_kasten(self):
        u"""`+` statt `-`, und das ist Absicht.

        Das UML-Vorbild schreibt Felder mit `-`. In Python entscheidet aber
        der Name: `self.stand` ist oeffentlich, `self._stand` nicht. Ein
        Bild, das jedes Feld als privat ausgibt, behauptet etwas ueber den
        Quelltext, was nicht stimmt.
        """
        self.assertIn('+ stand : str', self._bild())

    def test_ein_unterstrich_macht_das_feld_privat(self):
        m = _projekt({'a.py': (
            'class A:\n'
            '    def __init__(self):\n'
            "        self._geheim = 1\n")})
        kaesten, linien = m.nachbarschaft('A', tiefe=1)
        self.assertIn('- _geheim : int',
                      Klassenbild(kaesten, linien, 'A').svg())

    def test_die_linie_traegt_feldname_und_vielfachheit(self):
        svg = self._bild()
        self.assertIn('>zimmer<', svg)
        self.assertIn('>1<', svg)

    def test_leeres_projekt_wirft_nicht(self):
        m = _projekt({'a.py': '# nichts\n'})
        kaesten, linien = m.nachbarschaft(tiefe=2)
        svg = Klassenbild(kaesten, linien).svg()
        self.assertIn('<svg', svg)

    def test_spitze_klammern_im_namen_werden_entschaerft(self):
        u"""Der Kasteninhalt kommt aus fremdem Quelltext — er darf das SVG
        nicht aufbrechen."""
        m = _projekt({'a.py': (
            'class A:\n'
            '    def __init__(self):\n'
            "        self.x = '<script>'\n")})
        kaesten, linien = m.nachbarschaft('A', tiefe=1)
        self.assertNotIn('<script>', Klassenbild(kaesten, linien, 'A').svg())
