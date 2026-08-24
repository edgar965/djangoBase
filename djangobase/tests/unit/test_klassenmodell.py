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
        ziel = ordner / name
        # Unterordner anlegen: Seit den Test-Faellen liegen Dateien auch in
        # `tests/…`, und `write_text` legt kein Verzeichnis an.
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding='utf-8')
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


class JedeKlasseInGenauEinenTopf(BasisTest):
    u"""Die Einteilung aller Klassen.

    DIE FRAGE (Edgar, 24.08.2026)
    =============================
        „bei Klassenmodell steht 1004 Klassen, wenn ich aber die Bereiche
         aufzähle die gelistet sind, komme ich auf unter 50. Wo ist der
         Rest? Kategorisiere sie alle"

    Das Bild zeigt eine Nachbarschaft — am groessten Ast von CamTrack
    siebzehn Kaesten, und tiefer wird es nicht. Der Rest fehlt nicht im
    Bild, er haengt an nichts::

        Klassen gesamt   1004      Test              465
        gehalten           71      Freistehend       274
        Oberklasse         26      Datenklasse        79

    Die Einteilung trennt, was SYSTEMBEDINGT frei steht (Model, Ansicht,
    Ausnahme, Test), von dem, was frei steht, weil es niemand eingehaengt
    hat. Ohne diese Trennung liest sich „908 haengen an nichts" wie ein
    Vorwurf — die Haelfte davon sind Tests.
    """

    def _toepfe(self, quelle):
        m = _projekt({'a.py': quelle})
        return {k['key']: k['namen'] for k in m.kategorien()}

    def test_die_summe_stimmt(self):
        u"""Kein Doppel, keine Luecke — sonst taugt die Zahl nichts."""
        m = _projekt({'a.py': (
            'from django.db import models\n\n\n'
            'class Kamera(models.Model):\n    pass\n\n\n'
            'class Fehler(Exception):\n    pass\n\n\n'
            'class Wert:\n    pass\n\n\n'
            'class Dienst:\n'
            '    def __init__(self):\n        self.w = Wert()\n'
            '    def tu(self):\n        pass\n')})
        toepfe = m.kategorien()
        self.assertEqual(sum(k['zahl'] for k in toepfe), len(m.klassen))
        alle = [n for k in toepfe for n in k['namen']]
        self.assertEqual(len(alle), len(set(alle)), 'eine Klasse doppelt')

    def test_ein_model_ist_ein_model(self):
        toepfe = self._toepfe('from django.db import models\n\n\n'
                              'class Kamera(models.Model):\n    pass\n')
        self.assertEqual(toepfe['model'], ['Kamera'])

    def test_eine_ansicht_ist_eine_ansicht(self):
        toepfe = self._toepfe('from django.views import View\n\n\n'
                              'class SeiteView(View):\n'
                              '    def get(self, r):\n        pass\n')
        self.assertEqual(toepfe['ansicht'], ['SeiteView'])

    def test_eine_ausnahme_auch_am_namen(self):
        u"""`class JsonBodyError(ValueError)` erbt nicht von Exception."""
        toepfe = self._toepfe('class JsonBodyError(ValueError):\n    pass\n')
        self.assertEqual(toepfe['ausnahme'], ['JsonBodyError'])

    def test_eine_klasse_ohne_methoden_ist_ein_wert(self):
        toepfe = self._toepfe('class Punkt:\n    x = 0\n    y = 0\n')
        self.assertEqual(toepfe['daten'], ['Punkt'])

    def test_nur_statische_methoden_sind_ein_werkzeug(self):
        toepfe = self._toepfe(
            'class Rechner:\n'
            '    @staticmethod\n    def plus(a, b):\n        return a + b\n'
            '    @classmethod\n    def mal(cls, a, b):\n        return a * b\n')
        self.assertEqual(toepfe['werkzeug'], ['Rechner'])

    def test_wer_gehalten_wird_haengt_im_baum(self):
        toepfe = self._toepfe(
            'class Teil:\n'
            '    def __init__(self):\n        self.n = 1\n'
            '    def tu(self):\n        pass\n\n\n'
            'class Halter:\n'
            '    def __init__(self):\n        self.t = Teil()\n'
            '    def lauf(self):\n        pass\n')
        self.assertEqual(toepfe['im_baum'], ['Teil'])
        self.assertEqual(toepfe['frei'], ['Halter'])

    def test_wer_beerbt_wird_ist_oberklasse(self):
        toepfe = self._toepfe(
            'class Basis:\n'
            '    def __init__(self):\n        self.n = 1\n'
            '    def tu(self):\n        pass\n\n\n'
            'class Kind(Basis):\n'
            '    def __init__(self):\n        self.m = 2\n'
            '    def auch(self):\n        pass\n')
        self.assertEqual(toepfe['oberklasse'], ['Basis'])

    def test_der_eigentliche_befund_heisst_freistehend(self):
        toepfe = self._toepfe(
            'class Einsam:\n'
            '    def __init__(self):\n        self.n = 1\n'
            '    def tu(self):\n        pass\n')
        self.assertEqual(toepfe['frei'], ['Einsam'])

    def test_jede_kategorie_erklaert_sich(self):
        u"""Eine Zahl ohne Erklaerung ist eine Behauptung."""
        for k in _projekt({'a.py': 'class A:\n    pass\n'}).kategorien():
            self.assertTrue(k['label'] and k['erklaerung'], k)


class AlleKlassenSindErreichbar(BasisTest):
    u"""Zu jeder genannten Zahl muss es einen Weg geben.

    DIE BESCHWERDE (Edgar, 24.08.2026)
    ==================================
        „ich verstehe die Übersicht immer noch nicht. 1004 klassen, ich
         erwarte bereiche und buttons wo ich alle 1004 klassen sehen kann!"

    Die Seite nannte 1004, zeigte 17 im Bild und bot zwölf Ast-Knöpfe. Die
    übrigen 987 waren genannt, aber nicht erreichbar — eine Zahl ohne Weg
    ist eine Behauptung.
    """

    def test_die_bereiche_enthalten_jede_klasse(self):
        m = _projekt({'a.py': 'class Eins:\n    pass\n\n\nclass Zwei:\n    pass\n'})
        bereiche = m.nach_bereich()
        alle = [n for b in bereiche for n in b['namen']]
        self.assertEqual(sorted(alle), sorted(m.klassen))

    def test_keine_klasse_steht_doppelt(self):
        m = _projekt({'a.py': 'class A:\n    pass\n\n\nclass B:\n    pass\n'})
        alle = [n for b in m.nach_bereich() for n in b['namen']]
        self.assertEqual(len(alle), len(set(alle)))

    def test_die_zahl_stimmt_mit_der_liste(self):
        m = _projekt({'a.py': 'class A:\n    pass\n\n\nclass B:\n    pass\n'})
        for b in m.nach_bereich():
            self.assertEqual(b['zahl'], len(b['namen']))


class EinTestIstKeinAst(BasisTest):
    u"""Der Einstieg ins Klassenbild darf keine Prüfung sein.

    DER FALL (Edgar, 24.08.2026)
    ============================
        „was soll die Unterteilung Mit Chrome oder Vollbild zeigt den
         Hauptstrom?? das ist komplett gaga!"

    Unter „Dickste Äste" standen `_MitChrome`, `VollbildZeigtDenHauptstrom`,
    `WacheUnterscheidetKaputtVonLeer` — Testklassen, die je EIN Objekt
    halten. Sie füllten die Liste auf zwölf auf, obwohl es nur sechs echte
    Äste gibt. Ein Test RUFT das Programm, er ist nicht Teil seines Modells.
    """

    def _mit_test(self):
        return _projekt({
            'echt.py': (
                'class Teil:\n    pass\n\n\n'
                'class Dienst:\n'
                '    def __init__(self):\n'
                '        self.t = Teil()\n'
                '    def lauf(self):\n        pass\n'),
        })

    def test_eine_klasse_im_testordner_ist_ein_test(self):
        m = _projekt({'tests/test_x.py': 'class MitChrome:\n    pass\n'})
        self.assertTrue(m.klassen['MitChrome'].ist_test)

    def test_eine_datei_mit_test_praefix_zaehlt_auch(self):
        m = _projekt({'test_lauf.py': 'class VollbildZeigt:\n    pass\n'})
        self.assertTrue(m.klassen['VollbildZeigt'].ist_test)

    def test_produktionscode_ist_kein_test(self):
        u"""`VideoCodecProbe` in `views/` heisst nur so."""
        m = _projekt({'codec_probe.py': 'class VideoCodecProbe:\n    pass\n'})
        self.assertFalse(m.klassen['VideoCodecProbe'].ist_test)

    def test_der_dickste_ast_ist_nie_ein_test(self):
        m = _projekt({
            'echt.py': ('class A:\n    pass\n\n\n'
                        'class Dienst:\n'
                        '    def __init__(self):\n        self.a = A()\n'
                        '    def lauf(self):\n        pass\n'),
            'tests/test_viel.py': (
                'class VielHalter:\n'
                '    def __init__(self):\n'
                '        self.a = A()\n'
                '        self.b = A()\n'
                '    def pruefe(self):\n        pass\n'),
        })
        self.assertEqual(m.dickster_ast(), 'Dienst')
