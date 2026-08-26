# -*- coding: utf-8 -*-
u"""Kriterium 18 — freie Funktionen und globale Variablen in Klassen.

AUFTRAG (Edgar, 19.08.2026): „Den Code auf freie Funktionen und globale
Variablen ueberpruefen. Moeglichst in Klassen unterbringen, ggf. in
Utility-Klassen, statische Funktionen, Klassen verwenden. Globale Konstanten und
Variablen in Klassen wie Context unterbringen."

Zwei Werkzeuge bedienen das Kriterium — und beide Richtungen werden geprueft:
Sie muessen den Fall FINDEN und duerfen ihn nicht ERFINDEN. Die vier
Fehlalarm-Tests unten sind keine Kuer: Sie stehen fuer Befunde, die beim ersten
Lauf gegen ein echtes Projekt (shortlongx, 646 Module) tatsaechlich kamen und
die echten Treffer verdeckt haetten — 302 gemeldete „Variablen" gingen dadurch
auf 98 zurueck.
"""
import tempfile
from pathlib import Path

from djangobase.skills import kriterien, werkzeug_finden

from ..base import BasisTest


class Kriterium18Test(BasisTest):
    u"""Die beiden Werkzeuge zu Kriterium 18 gegen echte Dateien."""

    def _projekt(self, dateien):
        """Ein Wegwerf-Projekt aus {name: quelltext} - liefert das Werkzeug."""
        ordner = Path(tempfile.mkdtemp(prefix='k18_'))
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        return ordner

    def _lauf(self, slug, dateien, **argumente):
        # ``wurzel`` ist eine METHODE der Basisklasse, kein Attribut - genauso
        # biegt sie ``AnlassfallCheck`` um. Als Attribut gesetzt liefe die
        # Pruefung still gegen das echte Projekt statt gegen die Testdateien.
        ordner = self._projekt(dateien)
        werkzeug = werkzeug_finden(slug)
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    # ------------------------------------------------------------ Kriterium
    def test_kriterium_18_ist_bekannt(self):
        self.assertIn(18, kriterien())
        self.assertIn('Klassen', kriterien()[18])

    def test_beide_werkzeuge_nennen_kriterium_18(self):
        for slug in ('globaler-zustand', 'klassen-kandidat'):
            werkzeug = werkzeug_finden(slug)
            self.assertIsNotNone(werkzeug, '%s ist nicht registriert' % slug)
            self.assertEqual(werkzeug.kriterium, 18)

    # ---------------------------------------------------- findet den Fall
    def test_findet_veraenderlichen_modulzustand(self):
        satz = self._lauf('globaler-zustand', {'speicher.py': (
            '_cache = {}\n'
            '_zaehler = 0\n\n\n'
            'def merken(k, v):\n'
            '    global _zaehler\n'
            '    _zaehler += 1\n'
            '    _cache[k] = v\n')}, ab='1')
        self.assertTrue(satz.befunde, 'geschriebener Modulzustand nicht gemeldet')
        self.assertIn('global', satz.befunde[0].was)

    def test_findet_klassenkandidat_aus_geteiltem_zustand(self):
        satz = self._lauf('klassen-kandidat', {'zaehlwerk.py': (
            '_stand = {}\n\n\n'
            'def erhoehen(k):\n'
            '    _stand[k] = _stand.get(k, 0) + 1\n\n\n'
            'def lesen(k):\n'
            '    return _stand.get(k, 0)\n')})
        self.assertTrue(satz.befunde, 'geteilter Zustand nicht als Klasse erkannt')
        self.assertIn('_stand', satz.befunde[0].was)
        self.assertIn('erhoehen', satz.befunde[0].was)

    def test_utility_kandidat_wird_getrennt_gemeldet(self):
        u"""Ohne Zustand ist es eine Utility-Klasse - ein ANDERER Umbau."""
        satz = self._lauf('klassen-kandidat', {'texte.py': (
            'def text_kuerzen(s):\n    return s[:10]\n\n\n'
            'def text_saeubern(s):\n    return s.strip()\n\n\n'
            'def text_fuellen(s):\n    return s.ljust(10)\n')})
        treffer = [b for b in satz.befunde if 'Utility' in b.was]
        self.assertTrue(treffer, 'Funktionsbündel ohne Zustand nicht gemeldet')
        self.assertIn('staticmethod', treffer[0].warum)

    # --------------------------------------------- erfindet ihn NICHT (4×)
    def test_kein_befund_bei_sauberer_klasse(self):
        satz = self._lauf('globaler-zustand', {'sauber.py': (
            'class Zaehler:\n'
            '    def __init__(self):\n'
            '        self.stand = {}\n\n'
            '    def merken(self, k, v):\n'
            '        self.stand[k] = v\n')}, ab='1')
        self.assertFalse(satz.befunde, 'sauberer Code darf keinen Befund geben')

    def test_alias_auf_methode_ist_kein_zustand(self):
        u"""``_kurz = Klasse.methode`` ist ein zweiter NAME, kein Zustand.

        Gemessen in shortlongx: In ``views/basis.py`` waren die ersten drei
        gemeldeten „Variablen" solche Aliase."""
        satz = self._lauf('globaler-zustand', {'abkuerzung.py': (
            'from collections import OrderedDict\n\n'
            '_neu = OrderedDict.fromkeys\n'
            '_kopie = OrderedDict.copy\n'
            '_leer = OrderedDict.clear\n'
            '_setz = OrderedDict.setdefault\n')}, ab='1')
        self.assertFalse(satz.befunde, 'Alias-Zuweisungen sind kein Zustand')

    def test_wegwerfname_wird_nicht_gemeldet(self):
        u"""``_`` aus einer Tupel-Entpackung ist kein globaler Zustand."""
        satz = self._lauf('globaler-zustand', {'entpacken.py': (
            'def paar():\n    return 1, 2\n\n\n'
            'a, _ = paar()\n'
            'b, _ = paar()\n'
            'c, _ = paar()\n'
            'd, _ = paar()\n')}, ab='1')
        namen = ' '.join(b.was for b in satz.befunde)
        self.assertNotIn('_,', namen)
        self.assertNotIn("'_'", namen)

    def test_ablaufskript_wird_uebersprungen(self):
        u"""In einem Skript IST die Modulebene das Programm.

        Erkannt am CODE (laufende Anweisungen auf Modulebene), nicht am Ordner:
        Eine Ordnerliste raet und liegt beim nächsten Verzeichnis daneben."""
        satz = self._lauf('globaler-zustand', {'auswertung.py': (
            'daten = [1, 2, 3]\n'
            'summe = 0\n'
            'schnitt = 0\n'
            'for wert in daten:\n'
            '    summe += wert\n'
            'schnitt = summe / len(daten)\n'
            'print(schnitt)\n'
            'print(summe)\n')}, ab='1')
        self.assertFalse(satz.befunde, 'Ablaufskript darf nicht gemeldet werden')
        self.assertTrue(any('skript' in z.lower() for z in satz.kopf),
                        'die uebersprungenen Skripte müssen im Kopf stehen')

    def test_framework_funktionen_sind_keine_utility_kandidaten(self):
        u"""Wer vom RAHMENWERK gerufen wird, kann nicht in eine Klasse wandern.

        Gemessen in shortlongx: Von 65 Utility-Kandidaten waren 34 solche Faelle
        — Django-Views (Aufrufer ist die URL-Zuordnung), Pruefungen mit
        Dekorator und ``test_*``. Sie zu verschieben macht funktionierenden Code
        kaputt: ``urls.py`` zeigt ins Leere, die Testsuite findet nichts mehr.
        """
        satz = self._lauf('klassen-kandidat', {'seite.py': (
            'def api_liste(request):\n    return 1\n\n\n'
            'def api_detail(request):\n    return 2\n\n\n'
            'def api_speichern(request):\n    return 3\n\n\n'
            'def api_loeschen(request):\n    return 4\n')})
        self.assertFalse([b for b in satz.befunde if 'Utility' in b.was],
                         'Django-Views duerfen kein Utility-Kandidat sein')

        satz2 = self._lauf('klassen-kandidat', {'pruefungen.py': (
            'def pruefung(*a, **k):\n    return lambda f: f\n\n\n'
            '@pruefung("a")\ndef run_eins():\n    return 1\n\n\n'
            '@pruefung("b")\ndef run_zwei():\n    return 2\n\n\n'
            '@pruefung("c")\ndef run_drei():\n    return 3\n')})
        self.assertFalse([b for b in satz2.befunde if 'Utility' in b.was],
                         'dekorierte Funktionen duerfen kein Kandidat sein')

        satz3 = self._lauf('klassen-kandidat', {'test_dinge.py': (
            'def test_eins():\n    assert 1\n\n\n'
            'def test_zwei():\n    assert 2\n\n\n'
            'def test_drei():\n    assert 3\n')})
        self.assertFalse([b for b in satz3.befunde if 'Utility' in b.was],
                         'test_*-Funktionen sammelt unittest über den Namen')

    def test_echtes_utility_buendel_wird_weiter_gemeldet(self):
        u"""Die Gegenprobe: Ohne Rahmenwerk bleibt der Befund bestehen.

        Sonst hätte die Schaerfung oben das Werkzeug einfach stumm gemacht."""
        satz = self._lauf('klassen-kandidat', {'texte.py': (
            'def text_kuerzen(s):\n    return s[:10]\n\n\n'
            'def text_saeubern(s):\n    return s.strip()\n\n\n'
            'def text_fuellen(s):\n    return s.ljust(10)\n')})
        self.assertTrue([b for b in satz.befunde if 'Utility' in b.was],
                        'ein echtes Bündel muss weiterhin gemeldet werden')

    def test_klassenvorschlag_kollidiert_nicht_mit_bekanntem_typ(self):
        u"""``_thread`` ergaebe „Klasse Thread" - die gibt es schon.

        Ein Vorschlag, der eine Namenskollision baut, wird nicht uebernommen,
        und dann bleibt der Befund liegen."""
        satz = self._lauf('klassen-kandidat', {'laeufer.py': (
            'import threading\n\n'
            '_thread = None\n\n\n'
            'def start():\n'
            '    global _thread\n'
            '    _thread = threading.Thread(target=lambda: None)\n'
            '    _thread.start()\n\n\n'
            'def laeuft():\n'
            '    return _thread is not None and _thread.is_alive()\n')})
        treffer = [b for b in satz.befunde if '_thread' in b.was]
        self.assertTrue(treffer, 'geteilter _thread nicht erkannt')
        self.assertNotIn('Klasse Thread:', treffer[0].was)
        self.assertIn('LaeuferThread', treffer[0].was)

    def test_was_schon_im_kontext_liegt_ist_kein_kandidat(self):
        """Die umgesetzte Abhilfe darf nicht erneut als Befund erscheinen.

        BELEGTER FALL (20.08.2026, shortlongx): ``_anfrage_cache =
        Kontext.anfrage_cache()`` ist genau das, wozu dieses Werkzeug raet - der
        Zustand gehoert der Kontext-Klasse, der Modulname ist nur eine Kurzform
        am Gebrauchsort. Gemeldet wurde er trotzdem, weil die rechte Seite ein
        Aufruf ist. Wer dem Befund folgte, raeumte in die Stelle hinein auf, an
        der schon aufgeraeumt war.

        Geprueft wird beides: dass der aufgeraeumte Fall schweigt UND dass
        echte freie Instanzen weiter gemeldet werden - sonst waere die
        Schaerfung nur eine Blendung."""
        import ast
        from djangobase.skills.klassenkandidat import Klassenkandidat
        werkzeug = Klassenkandidat()
        faelle = (
            ('logger = logging.getLogger(__name__)', 'kontext'),
            ('_sitzung = Sitzung()', 'kontext'),
            ('_x = Anderes.bauen()', 'kontext'),      # fremde Klasse bleibt Kandidat
            ('_stand = {}', 'klasse'),
            ('_cache = Kontext.anfrage_cache()', None),
            ('_t = Kontext.autotrade_sitzung()', None),
            ('_alias = Kontext', None),               # Alias ohne Aufruf
        )
        for quelle, erwartet in faelle:
            knoten = ast.parse(quelle).body[0]
            self.assertEqual(werkzeug._sorte(knoten), erwartet,
                             'falsch eingestuft: %s' % quelle)
