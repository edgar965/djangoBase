# -*- coding: utf-8 -*-
u"""Aktivitaetsbild — ist die Schrift neben den Bloecken lesbar?

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „mach mir die grafische Ausgabe von vorher, kein Quelltext, aber
     sowas in der Richtung des Screenshots"
    „mach die schriften noch lesbar (neben den Blöcken)"

Der erste Wurf sah aus wie die Vorlage und war trotzdem unbrauchbar:
``[not os.path.isdir(…)]`` lag mitten auf der Raute, ``[sonst]`` auf dem
Pfeil, und die Zeilennummer ``166`` klebte an beiden.

Ein Bild, dessen Beschriftung man nicht lesen kann, beantwortet die
Frage nicht, um die es geht. Diese Pruefungen halten die vier
Korrekturen fest — sie sind alle GEOMETRIE, also nachrechenbar:

    Hof        weisser Rand unter der Schrift, damit Linien sie nicht
               durchschneiden
    Platz      eine Marke wird auf die verfuegbare Breite gekuerzt
    Vollstand  der volle Text bleibt als Tooltip erhalten
    Abstand    Zeilennummern stehen links, nie an der Achse

Sie gehoeren zu Kriterium 20 („Dokumentation").
"""
import ast
import re

from djangobase.umbau.ablauf import Ablauf
from djangobase.umbau.aktivitaetsbild import KASTEN_B, SPUR, Aktivitaetsbild
from djangobase.umbau.beschriftung import Beschriftung

from ..base import BasisTest


class _Bezug:
    def __init__(self, quelle):
        self.knoten = ast.parse(quelle).body[0]
        self.anzeige = 'A.f'
        self.modul = 'probe'
        self.zeile = 1


def _bild(quelle):
    lauf = Ablauf(_Bezug(quelle)).lesen()
    return Aktivitaetsbild(lauf, lambda k: Beschriftung.fuer(k))


VERZWEIGT = ('def f(self):\n'
             '    if not os.path.isdir(self.zwischenlager_pfad_lang):\n'
             '        return 0\n'
             '    self.aufraeumen()\n')


class JedeBeschriftungHatEinenWeissenHof(BasisTest):
    u"""Ohne ihn schneidet jede Linie die Schrift, die ueber ihr liegt."""

    def test_marken_und_nummern_tragen_einen_rand(self):
        svg = _bild(VERZWEIGT).svg()
        self.assertIn('paint-order:stroke', svg)
        self.assertIn('stroke:#fff', svg)


class EineMarkePasstInDenPlatzDenSieHat(BasisTest):
    u"""``[not os.path.isdir(self.zwischenlager_pfad_lang)]`` ist laenger
    als die Spur breit ist. Ungekuerzt lief sie ueber die Raute."""

    def setUp(self):
        self.svg = _bild(VERZWEIGT).svg()
        self.marken = re.findall(
            r'<text class="ak-m"[^>]*>(?:<title>[^<]*</title>)?([^<]*)</text>',
            self.svg)

    def test_es_gibt_ueberhaupt_eine_marke(self):
        self.assertTrue(self.marken, 'Ohne Marke sagt die Raute nicht, '
                                     'wofuer sie sich entscheidet.')

    def test_keine_marke_ist_breiter_als_die_spur(self):
        u"""Grob gerechnet 6 Punkte je Zeichen bei 11er Schrift."""
        for marke in self.marken:
            self.assertLessEqual(len(marke) * 6, SPUR,
                                 'zu lang: %r' % marke)

    def test_der_volle_text_bleibt_als_tooltip(self):
        u"""Kuerzen ist noetig — die Bedingung ganz zu verlieren waere zu
        teuer. Wer genau wissen will, was geprueft wird, faehrt drueber."""
        self.assertIn('<title>', self.svg)
        self.assertIn('isdir', self.svg)


class DieZeilennummerStehtLinks(BasisTest):
    u"""Rechts lag sie genau auf der Achse und der naechsten Raute."""

    def test_die_nummer_sitzt_in_der_linken_haelfte_des_kastens(self):
        bild = _bild(VERZWEIGT).anordnen()
        svg = bild.svg()
        kasten = [t for t in bild.teile if t.art in ('kasten', 'ausgang')][0]
        stelle = re.search(r'<text class="ak-z" x="(\d+)"', svg)
        self.assertIsNotNone(stelle)
        self.assertLess(int(stelle.group(1)), kasten.x,
                        'Die Nummer steht rechts und damit an der Achse.')


class ZwischenNebenspurUndAchseIstPlatz(BasisTest):
    u"""Die Marke steht in dieser Luecke — sie darf nicht null sein."""

    def test_die_luecke_traegt_mehr_als_ein_paar_zeichen(self):
        luecke = SPUR - KASTEN_B / 2.0 - 22
        self.assertGreater(luecke, 100,
                           'Bei 43 Punkten stand „[ja]" als '
                           'Buchstabensalat zwischen Kasten und Raute.')


class DasBildBringtSeinenGrundMit(BasisTest):
    u"""Als STIL, nicht als Attribut: Ein ``fill="…"`` verliert gegen jede
    CSS-Regel des Wirtsprojekts, und die Flaeche blieb dunkel."""

    def test_ein_weisses_rechteck_deckt_das_ganze_bild(self):
        bild = _bild(VERZWEIGT).anordnen()
        svg = bild.svg()
        treffer = re.search(
            r'<rect x="0" y="0" width="(\d+)" height="(\d+)" '
            r'style="fill:#ffffff"', svg)
        self.assertIsNotNone(treffer, 'Kein weisser Grund im Bild.')
        self.assertEqual(int(treffer.group(1)), bild.breite)
        self.assertEqual(int(treffer.group(2)), bild.hoehe)


class DerTextIstProsaUndKeinQuelltext(BasisTest):
    u"""Der eigentliche Unterschied zur Workflow-Seite."""

    def test_aus_einem_methodennamen_werden_woerter(self):
        self.assertEqual(Beschriftung('_install_signal_handlers').satz(),
                         'install signal handlers')

    def test_eine_abkuerzung_bleibt_ein_wort(self):
        u"""Sonst wurde aus ``SUCCESS`` ein „S U C C E S S"."""
        self.assertEqual(Beschriftung('SUCCESS').satz(), 'SUCCESS')

    def test_der_empfaenger_steht_als_gegenstand_davor(self):
        self.assertEqual(Beschriftung('prepare', None, 'service').satz(),
                         'service: prepare')

    def test_self_ist_kein_gegenstand(self):
        u"""``self`` steht in jedem zweiten Kasten und waere Rauschen."""
        self.assertEqual(Beschriftung('tun', None, 'self').satz(), 'tun')

    def test_ein_docstring_schlaegt_den_namen(self):
        quelle = ('def helfen(self):\n'
                  '    """Raeumt die Zwischenablage auf."""\n'
                  '    pass\n')

        class Bezug:
            knoten = ast.parse(quelle).body[0]
        self.assertEqual(Beschriftung('helfen', Bezug()).satz(),
                         'Raeumt die Zwischenablage auf')

    def test_ein_docstring_der_mit_einer_ueberschrift_anfaengt_zaehlt_nicht(self):
        u"""``>>>`` oder ``===`` beschreiben keine Handlung."""
        quelle = ('def helfen(self):\n'
                  '    """>>> helfen()"""\n'
                  '    pass\n')

        class Bezug:
            knoten = ast.parse(quelle).body[0]
        self.assertEqual(Beschriftung('helfen', Bezug()).satz(), 'helfen')


class AusgabeIstKeineHandlung(BasisTest):
    u"""Im ersten Bild stand neunmal „stdout: write"."""

    def test_eine_schreibzeile_erzeugt_keinen_kasten(self):
        lauf = Ablauf(_Bezug(
            'def f(self):\n'
            "    self.stdout.write(self.style.SUCCESS('fertig'))\n"
            '    self.arbeiten()\n')).lesen()
        self.assertEqual([k.aufruf for k in lauf.knoten], ['arbeiten'])


class _EinVerzeichnis:
    """Ein Verzeichnis mit genau einer bekannten Methode."""

    class _Bezug:
        # `anzeige` braucht `Ablauf._ziel`, um das Ziel zu benennen;
        # `schluessel` braucht die Rufer-Abfrage.
        anzeige = 'Dienst.vorbereiten'
        schluessel = 'app.dienst:Dienst.vorbereiten'
        modul = 'app.dienst'
        zeile = 42
        knoten = ast.parse('def vorbereiten(self):\n'
                           '    """Raeumt auf."""\n'
                           '    pass\n').body[0]

    klassen = {}
    funktionen = {}

    def in_klasse(self, _klasse, name):
        return self._Bezug() if name == 'vorbereiten' else None

    def methode(self, name):
        return self._Bezug() if name == 'vorbereiten' else None

    @staticmethod
    def mehrdeutig(_name):
        return False


class _NurEineKlasse:
    """Ein Verzeichnis, das nur eine KLASSE kennt — keine Methode."""

    klassen = {'Dienst': type('B', (), {
        # `anzeige` braucht `Ablauf._ziel`, um das Ziel zu benennen.
        'anzeige': 'Dienst', 'modul': 'app.d', 'zeile': 1,
        'knoten': ast.parse('class Dienst:\n    pass\n').body[0]})()}
    funktionen = {}

    @staticmethod
    def in_klasse(_klasse, _name):
        return None

    @staticmethod
    def methode(_name):
        return None

    @staticmethod
    def mehrdeutig(_name):
        return False


class JederKastenSagtWoherErKommt(BasisTest):
    u"""Klasse, Methode und Fundstelle als Daten am Kasten.

        „kannst du hover und popups machen, die bei Klick auf einen
         Bereich die Klasse und die Methode anzeigt?" (27.08.2026)

    Der Satz im Kasten ist Prosa und sagt darum NICHT, wo das steht.
    Beides zugleich hineinzuschreiben ginge nicht — dann wäre der Kasten
    wieder Quelltext. Also hängen die Angaben als Daten daran, und die
    Seite baut daraus das Fenster.
    """

    QUELLE = ('def f(self):\n'
              '    self.service.vorbereiten()\n')

    def _knoten(self):
        v = _EinVerzeichnis()
        return Ablauf(_Bezug(self.QUELLE), v).lesen().knoten[0], v

    def test_die_methode_steht_am_kasten(self):
        knoten, v = self._knoten()
        self.assertEqual(Beschriftung.herkunft(knoten, v).get('methode'),
                         'vorbereiten')

    def test_die_fundstelle_der_definition_steht_dabei(self):
        u"""Wo der AUFRUF steht und wo die Funktion DEFINIERT ist, sind
        zwei verschiedene Zeilen. Wer springen will, meint die zweite."""
        knoten, v = self._knoten()
        angaben = Beschriftung.herkunft(knoten, v)
        self.assertEqual(angaben.get('modul'), 'app.dienst')
        self.assertEqual(angaben.get('zielzeile'), 42)
        self.assertEqual(angaben.get('zeile'), 2)

    def test_die_quellzeile_bleibt_erhalten(self):
        knoten, v = self._knoten()
        self.assertIn('vorbereiten',
                      Beschriftung.herkunft(knoten, v).get('quelle', ''))

    def test_eine_erzeugte_klasse_heisst_nicht_methode(self):
        u"""``self.x = RecordingService(...)`` stand als „Methode:
        RecordingService" im Fenster. Hier wird eine KLASSE gebaut, und
        wer das verwechselt, sucht im falschen Modul."""
        v = _NurEineKlasse()
        knoten = Ablauf(_Bezug('def f(self):\n    self.x = Dienst()\n'),
                        v).lesen().knoten[0]
        angaben = Beschriftung.herkunft(knoten, v)
        self.assertEqual(angaben.get('klasse'), 'Dienst')
        self.assertEqual(angaben.get('erzeugt'), 'ja')
        self.assertNotIn('methode', angaben)

    def test_im_bild_haengen_die_daten_am_kasten(self):
        v = _EinVerzeichnis()
        lauf = Ablauf(_Bezug(self.QUELLE), v).lesen()
        svg = Aktivitaetsbild(
            lauf,
            beschrifter=lambda k: Beschriftung.fuer(k, v),
            herkunft=lambda k: Beschriftung.herkunft(k, v)).svg()
        self.assertIn('<g class="ak-teil"', svg)
        self.assertIn('data-methode="vorbereiten"', svg)
        self.assertIn('data-modul="app.dienst"', svg)

    def test_ohne_herkunft_erfindet_der_zeichner_nichts(self):
        svg = Aktivitaetsbild(Ablauf(_Bezug(self.QUELLE)).lesen()).svg()
        self.assertNotIn('data-modul', svg)

    def test_jeder_kasten_sagt_wo_er_selbst_steht(self):
        u"""Auch ein Schritt ohne Ziel gehört zu einer Funktion.

        Vorher stand im Fenster nur „Aufruf in Zeile 82", und man wusste
        nicht, in welcher Klasse man überhaupt war.
        """
        v = _EinVerzeichnis()
        lauf = Ablauf(_Bezug(self.QUELLE), v).lesen()
        svg = Aktivitaetsbild(
            lauf, herkunft=lambda k: Beschriftung.herkunft(k, v)).svg()
        self.assertIn('data-gehoertzu="A.f', svg)


class ZweiKaestenDuerfenNichtDasselbeBehaupten(BasisTest):
    u"""Das Stottern, das Edgar am 27.08.2026 gefunden hat.

        „da läuft noch was schief: zweimal signal:signal"

    ``signal.signal(signal.SIGINT, …)`` und ``signal.signal(signal.
    SIGTERM, …)`` standen beide als „signal: signal" untereinander — zwei
    Kästen, die dasselbe behaupteten und den Unterschied verschwiegen.

    Der Code war richtig; die BESCHRIFTUNG war es nicht. Heißt der
    Empfänger wie der Aufruf, sagt die Wiederholung nichts — dann trägt
    das erste Argument die Unterscheidung.
    """

    QUELLE = ('def f(self):\n'
              '    signal.signal(signal.SIGINT, self._an)\n'
              '    signal.signal(signal.SIGTERM, self._an)\n')

    def _saetze(self):
        lauf = Ablauf(_Bezug(self.QUELLE)).lesen()
        return [Beschriftung.fuer(k) for k in lauf.knoten]

    def test_die_beiden_kaesten_sagen_verschiedenes(self):
        erste, zweite = self._saetze()
        self.assertNotEqual(erste, zweite)

    def test_das_unterscheidende_argument_steht_im_kasten(self):
        erste, zweite = self._saetze()
        self.assertIn('SIGINT', erste)
        self.assertIn('SIGTERM', zweite)

    def test_der_name_wird_nicht_verdoppelt(self):
        u"""„signal: signal" ist der Fehler, um den es geht."""
        for satz in self._saetze():
            self.assertNotIn('signal: signal', satz)

    def test_ein_ausdruck_als_argument_kommt_NICHT_in_den_kasten(self):
        u"""Sonst wäre der Kasten wieder Quelltext — genau davon soll das
        Bild ja wegkommen."""
        lauf = Ablauf(_Bezug(
            'def f(self):\n'
            "    warte.warte(options['poll'] or 5)\n")).lesen()
        self.assertEqual(lauf.knoten[0].merkmal, '')


class DasFensterNenntDieRufer(BasisTest):
    u"""„auch von wem die aufgerufen wird" (27.08.2026).

    Ein Bild zeigt EINEN Weg. „Wer ruft das hier eigentlich?" ist die
    Frage, die man vor jeder Änderung stellt — und die das Bild nicht
    beantwortet, weil die anderen Rufer nicht darin stehen.
    """

    class _MitRufern(_EinVerzeichnis):
        @staticmethod
        def rufer(_schluessel):
            return [type('B', (), {'anzeige': 'Erster.tun'})(),
                    type('B', (), {'anzeige': 'Zweiter.tun'})()]

    def test_die_rufer_stehen_in_den_angaben(self):
        v = self._MitRufern()
        knoten = Ablauf(_Bezug('def f(self):\n'
                               '    self.service.vorbereiten()\n'),
                        v).lesen().knoten[0]
        self.assertEqual(Beschriftung.herkunft(knoten, v).get('gerufenvon'),
                         'Erster.tun, Zweiter.tun')

    def test_bei_vielen_rufern_wird_gekuerzt(self):
        u"""Eine Liste mit dreißig Namen beantwortet die Frage nicht mehr,
        sie verdeckt sie."""
        class Viele(_EinVerzeichnis):
            @staticmethod
            def rufer(_schluessel):
                return [type('B', (), {'anzeige': 'K%02d.tun' % i})()
                        for i in range(20)]
        v = Viele()
        knoten = Ablauf(_Bezug('def f(self):\n'
                               '    self.service.vorbereiten()\n'),
                        v).lesen().knoten[0]
        text = Beschriftung.herkunft(knoten, v).get('gerufenvon', '')
        self.assertIn('und 14 weitere', text)

    def test_ohne_rufer_bleibt_das_feld_leer(self):
        u"""Kein „0 Rufer" — ein leeres Feld zeigt die Seite gar nicht an."""
        v = _EinVerzeichnis()
        knoten = Ablauf(_Bezug('def f(self):\n'
                               '    self.service.vorbereiten()\n'),
                        v).lesen().knoten[0]
        self.assertEqual(Beschriftung.herkunft(knoten, v).get('gerufenvon'),
                         '')
