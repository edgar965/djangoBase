# -*- coding: utf-8 -*-
u"""Objektwurzeln — misst die Form des Objektmodells, nicht eine Stelle.

DER MASSSTAB (Edgar, 23.08.2026)
================================
    „ein gutes Objektmodell fängt mit einer Klasse an, und verzweigt immer
     weiter über Instanzen"

    „überprüfe doch die globalen Klassen, davon müsste es ganz wenige geben,
     im Idealfall nur eine"

Das ist ein messbarer Satz — und er misst etwas anderes als die
sechsundvierzig anderen Werkzeuge im Kasten. Die fragen nach EINER Stelle:
zu lang, zu doppelt, zu still. Dieses fragt nach dem GANZEN: Ein
Objektmodell ist ein Baum mit einer Wurzel. Jede Klasse, die auf Modulebene
entsteht, ist eine zweite Wurzel — sie haengt an keinem Ast, gehoert
niemandem und ist von ueberall erreichbar.

WIE ES DAZU KAM
===============
Der Nutzer fragte, warum das Werkzeug ``sammelzustand`` nur zwoelf Befunde
liefert („du hast doch tonnen schlechten code?"). Nachgemessen: Die vier
Ausnahmen kosten zusammen nur sechs Befunde — es lag an der Enge der Regel
selbst. Daraufhin nannte er dieses Muster, und es traf sofort:

    Klassen in CamTrack                548
    auf Modulebene erzeugt              29 eigene, an 31 Stellen
    Idealwert                            1

Darunter ``LaufzeitRegister``, am selben Tag von mir gebaut. Das Muster ist
so bequem, dass es beim Schreiben nicht auffaellt.

WAS ES PRAKTISCH KOSTET
=======================
An genau diesem Tag zweimal bezahlt: Ein ``SilentFailureWatch`` fuer elf
Kameras — weil er niemandem gehoerte, setzte jede funktionierende Kamera den
Zaehler der blind gewordenen zurueck; vier liefen zehn Stunden blind.

WAS HIER GEPRUEFT WIRD
======================
1. Eine Klasse, die auf Modulebene entsteht, wird gefunden.
2. Wird dieselbe Klasse ANDERSWO schon als ``self.x`` gehalten, ist es eine
   Warnung — der Platz im Baum ist da, die globale Instanz ist der Umweg.
3. Fremde Klassen und Rahmenwerk-Vorschriften bleiben draussen. Django
   VERLANGT ``register = Library()`` auf Modulebene.
4. Ein Baum mit einer Wurzel gibt keinen Befund.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.objektwurzeln import Objektwurzeln

from ..base import BasisTest


class ObjektwurzelnTest(BasisTest):

    SLUG = 'objektwurzeln'

    def _lauf(self, dateien, **argumente):
        ordner = Path(tempfile.mkdtemp(prefix='wurzeln_'))
        for name, inhalt in dateien.items():
            pfad = ordner / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug, '%s ist nicht registriert' % self.SLUG)
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    @staticmethod
    def _text(satz):
        return ' '.join(b.was + ' ' + b.warum for b in satz.befunde)

    # ------------------------------------------------------- Registrierung
    def test_werkzeug_ist_registriert(self):
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug)
        self.assertTrue(werkzeug.anlassfall)
        self.assertTrue(werkzeug.anlassfall.warum)

    def test_der_idealwert_steht_im_kopf(self):
        """Ohne ihn ist eine Zahl nur eine Zahl."""
        satz = self._lauf({'a.py': 'class A:\n    pass\n'}, ab='0')
        self.assertTrue(any('Idealwert' in z for z in satz.kopf))

    # ------------------------------------------------------ findet den Fall
    def test_eine_globale_instanz_wird_gefunden(self):
        satz = self._lauf({'wache.py': (
            'class Wache:\n'
            '    def __init__(self):\n'
            '        self.blind = 0\n\n\n'
            'WACHE = Wache()\n')}, ab='0')
        self.assertTrue(satz.befunde, 'die globale Instanz wurde nicht gemeldet')
        self.assertIn('Wache', self._text(satz))

    def test_mehrere_stellen_werden_zusammengefasst(self):
        """Eine Klasse ist EIN Umbau, auch wenn sie dreimal erzeugt wird."""
        satz = self._lauf({
            'a.py': 'class Ding:\n    pass\n\n\nEINS = Ding()\n',
            'b.py': 'from a import Ding\n\n\nZWEI = Ding()\n',
            'c.py': 'from a import Ding\n\n\nDREI = Ding()\n'}, ab='0')
        self.assertEqual(len(satz.befunde), 1,
                         'eine Klasse gehoert einmal in den Bericht')
        self.assertIn('weitere', satz.befunde[0].was)

    def test_wer_schon_einen_platz_im_baum_hat_ist_eine_warnung(self):
        """DER ANLASSFALL.

        Haelt eine andere Klasse dieselbe Klasse bereits als Instanz, dann
        gibt es den Ast — die globale Instanz ist der Umweg.
        """
        satz = self._lauf({
            'wache.py': ('class Wache:\n'
                         '    def __init__(self):\n'
                         '        self.blind = 0\n\n\n'
                         'WACHE = Wache()\n'),
            'kamera.py': ('from wache import Wache\n\n\n'
                          'class Kamera:\n'
                          '    def __init__(self):\n'
                          '        self.wache = Wache()\n')}, ab='0')
        self.assertTrue(satz.befunde)
        self.assertEqual(satz.befunde[0].gewicht, 'warnung')
        self.assertIn('Kamera', satz.befunde[0].warum,
                      'die Meldung muss sagen, WER den Platz schon hat')

    def test_die_zahl_der_wurzeln_steht_im_kopf(self):
        satz = self._lauf({
            'a.py': 'class A:\n    pass\n\n\nEINS = A()\n',
            'b.py': 'class B:\n    pass\n\n\nZWEI = B()\n'}, ab='0')
        self.assertTrue(any('2 eigene Klassen' in z for z in satz.kopf),
                        satz.kopf)

    # ------------------------------------------------- erfindet ihn NICHT
    def test_ein_baum_mit_einer_wurzel_ist_sauber(self):
        """DER WICHTIGSTE NICHT-BEFUND.

        So sieht das Ziel aus: eine Wurzel, alles andere haengt daran.
        """
        satz = self._lauf({'dienst.py': (
            'class Zaehler:\n'
            '    def __init__(self):\n'
            '        self.stand = 0\n\n\n'
            'class Kamera:\n'
            '    def __init__(self):\n'
            '        self.zaehler = Zaehler()\n\n\n'
            'class Dienst:\n'
            '    def __init__(self):\n'
            '        self.kamera = Kamera()\n\n\n'
            'DIENST = Dienst()\n')}, ab='1')
        self.assertFalse(satz.befunde,
                         'ein Baum mit EINER Wurzel darf nichts melden: %s'
                         % [b.was for b in satz.befunde])

    def test_fremde_klassen_bleiben_draussen(self):
        """``Lock`` und ``Path`` sind Wertobjekte, keine Aeste."""
        satz = self._lauf({'a.py': (
            'from threading import Lock\n'
            'from pathlib import Path\n\n\n'
            'SPERRE = Lock()\n'
            'ORT = Path("/tmp")\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_was_das_rahmenwerk_verlangt_bleibt_draussen(self):
        """Django findet die Vorlagen-Filter nur, wenn ``register`` auf
        Modulebene steht. Wer das meldet, meldet eine Vorschrift."""
        satz = self._lauf({'meine_filter.py': (
            'from django import template\n\n\n'
            'register = template.Library()\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_eine_instanz_in_einer_funktion_ist_keine_wurzel(self):
        """Sie entsteht und vergeht — sie haengt an niemandem, aber sie
        ueberlebt auch nichts."""
        satz = self._lauf({'a.py': (
            'class Ding:\n    pass\n\n\n'
            'def mach():\n'
            '    return Ding()\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_eine_klasse_aus_einem_paket_ist_keine_eigene(self):
        """Gezaehlt wird nur, was das Projekt selbst definiert — sonst
        meldet das Werkzeug fremden Code."""
        satz = self._lauf({'a.py': (
            'from woanders import Fremd\n\n\n'
            'DING = Fremd()\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_einstellungsdateien_bleiben_draussen(self):
        """Dort IST die Modulebene die Datenstruktur."""
        satz = self._lauf({'settings.py': (
            'class Conf:\n    pass\n\n\nCONF = Conf()\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_testdateien_bleiben_draussen(self):
        satz = self._lauf({'test_etwas.py': (
            'class Aufbau:\n    pass\n\n\nAUFBAU = Aufbau()\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_leeres_projekt_bleibt_still(self):
        satz = self._lauf({})
        self.assertFalse(satz.befunde)
        self.assertTrue(satz.kopf)


class DieGrenzeIstEinstellbar(BasisTest):
    """Ein Projekt darf entscheiden, wie viele Wurzeln es sich erlaubt —
    aber der Idealwert bleibt eins."""

    def test_unter_der_grenze_kein_befund(self):
        werkzeug = werkzeug_finden('objektwurzeln')
        ordner = Path(tempfile.mkdtemp(prefix='wurzeln_'))
        (ordner / 'a.py').write_text('class A:\n    pass\n\n\nEINS = A()\n',
                                     encoding='utf-8')
        werkzeug.wurzel = lambda: ordner
        self.assertFalse(werkzeug.pruefen(ab='1').befunde)
        self.assertTrue(werkzeug.pruefen(ab='0').befunde)

    def test_die_vorgabe_ist_eins(self):
        self.assertEqual(Objektwurzeln.eingabe[2], '1')
