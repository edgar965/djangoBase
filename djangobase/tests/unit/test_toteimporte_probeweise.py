# -*- coding: utf-8 -*-
u"""Ein Import, der eine Frage stellt, ist nicht tot.

DER ANLASS (3DTools, 31.08.2026)
================================
``collision/test_ui.py`` prueft, ob Playwright ueberhaupt installiert
ist::

    try:
        from playwright.sync_api import sync_playwright
        HAS_PLAYWRIGHT = True
    except ImportError:
        HAS_PLAYWRIGHT = False

Der Name ``sync_playwright`` kommt danach nirgends mehr vor — der
Pruefer meldete ihn als tot. Wer dem folgt und ihn streicht, nimmt der
Datei genau das, was sie wissen wollte: ``HAS_PLAYWRIGHT`` waere danach
immer ``True``, und die uebersprungenen Faelle liefen ins Leere.

Das ist die teuerste Sorte Fehlalarm — ein Loeschvorschlag fuer
lebenden Code (siehe ``~/.claude/rules/analysewerkzeuge.md``).

DIE GEGENPROBE STEHT MIT DRIN: Der Pruefer darf nicht blind werden.
``EinToterImport`` und ``EinToterImportImExceptZweig`` halten fest, dass
er weiter meldet, was wirklich tot ist.

BDD - GEGEBEN / DANN
====================
    EinProbeweiserImport          ... wird nicht gemeldet
    EinNacktesExcept              ... auch nicht
    EinAndererFehler              ... wird gemeldet (kein Importtest)
    EinToterImport                ... wird gemeldet
    EinToterImportImExceptZweig   ... wird gemeldet
"""
from djangobase.skills.toteimporte import ToteImporte

from .test_neue_werkzeuge import WerkzeugBasis


class EinProbeweiserImport(WerkzeugBasis):
    u"""Gegeben: Ein Import im ``try``, dessen ``except ImportError`` ein
    Flag setzt."""

    QUELLE = ("try:\n"
              "    from playwright.sync_api import sync_playwright\n"
              "    HAT_PLAYWRIGHT = True\n"
              "except ImportError:\n"
              "    HAT_PLAYWRIGHT = False\n")

    def test_er_wird_nicht_gemeldet(self):
        projekt = self.projekt({'pruefung.py': self.QUELLE})
        self.assertEqual(projekt.fahren(ToteImporte), [])

    def test_auch_modulnotfound_zaehlt(self):
        projekt = self.projekt({
            'pruefung.py': self.QUELLE.replace('ImportError',
                                               'ModuleNotFoundError')})
        self.assertEqual(projekt.fahren(ToteImporte), [])

    def test_auch_als_tupel(self):
        projekt = self.projekt({
            'pruefung.py': self.QUELLE.replace(
                'except ImportError:', 'except (ImportError, OSError):')})
        self.assertEqual(projekt.fahren(ToteImporte), [])


class EinNacktesExcept(WerkzeugBasis):
    u"""Gegeben: ``except:`` ohne Typ — faengt auch den ImportError."""

    def test_er_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'pruefung.py': ("try:\n"
                            "    import kryptografie\n"
                            "    DA = True\n"
                            "except:\n"
                            "    DA = False\n")})
        self.assertEqual(projekt.fahren(ToteImporte), [])


class EinAndererFehler(WerkzeugBasis):
    u"""Gegeben: Ein ``try``, das gar keinen Importfehler erwartet."""

    def test_er_wird_gemeldet(self):
        u"""``except ValueError`` sagt nichts ueber Verfuegbarkeit."""
        projekt = self.projekt({
            'rechnen.py': ("try:\n"
                           "    import json\n"
                           "    x = 1 / 0\n"
                           "except ValueError:\n"
                           "    x = 0\n")})
        zeilen = projekt.fahren(ToteImporte)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('json', zeilen[0]['befund'])


class EinToterImport(WerkzeugBasis):
    u"""Gegeben: Ein gewoehnlicher Import, den niemand benutzt.

    DIE GEGENPROBE zur Schaerfung oben.
    """

    def test_er_wird_weiter_gemeldet(self):
        projekt = self.projekt({
            'laden.py': ("import json\n"
                         "import os\n"
                         "\n"
                         "\n"
                         "def lesen(pfad):\n"
                         "    return json.loads(open(pfad).read())\n")})
        zeilen = projekt.fahren(ToteImporte)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('os', zeilen[0]['befund'])


class EinToterImportImExceptZweig(WerkzeugBasis):
    u"""Gegeben: Der Ersatzweg im ``except`` importiert etwas Unbenutztes.

    Nur der ``try``-Rumpf ist die Frage — der Ersatzweg ist eine Antwort
    und kann sehr wohl tot sein.
    """

    def test_er_wird_gemeldet(self):
        projekt = self.projekt({
            'pruefung.py': ("try:\n"
                            "    import schnell\n"
                            "    NUTZE = schnell\n"
                            "except ImportError:\n"
                            "    import langsam\n"
                            "    NUTZE = None\n")})
        zeilen = projekt.fahren(ToteImporte)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('langsam', zeilen[0]['befund'])
