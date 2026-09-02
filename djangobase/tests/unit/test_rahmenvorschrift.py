# -*- coding: utf-8 -*-
u"""Erkennt `freie-funktionen` die Funktionen, die Django VORSCHREIBT?

DER FEHLALARM (27.08.2026, 3DTools)
===================================
Gemeldet wurde `ui/context_processors.py` als **Warnung**: zwei Funktionen auf
Modulebene, Vorschlag „Klasse `ContextProcessors`". Wer dem folgt, macht die
Seite kaputt — `import_string` macht genau einen `rsplit(".", 1)` und suchte
danach ein Modul namens `ui.context_processors.ContextProcessors`.

Das ist dieselbe Fehlerklasse wie „`Command` 23x vergeben" (`~/.claude/rules/
analysewerkzeuge.md`): ein Befund, der zum Kaputtmachen auffordert — die
teuerste Sorte Fehlalarm.

WAS HIER GEPRUEFT WIRD
======================
Beide Richtungen. Der Fehlalarm muss weg sein UND der echte Befund muss
bleiben: Acht lose Funktionen in einer Hilfsdatei sind weiterhin ein Fall.
"""

import ast

from django.test import SimpleTestCase, override_settings

from djangobase.skills.rahmenvorschrift import Rahmenvorschrift

#: Wie eine Django-Einstellung die Kontextprozessoren fuehrt.
VORLAGEN = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'ui.context_processors.version',
        'ui.context_processors.active_theme',
    ]},
}]


class SelbstGerufeneNamenTest(SimpleTestCase):
    u"""Was der `__main__`-Block ruft, muss auf Modulebene bleiben.

    ANLASS (01.09.2026, 3DTools): `convert/dazknochennamen.py` ist ein
    Kommandozeilen-Werkzeug. Der Vorschlag, sein `main()` in eine Klasse
    zu heben, haette es nicht mehr startbar gemacht.
    """

    #: Eine Datei, wie ein Kommandozeilen-Werkzeug sie hat.
    WERKZEUG = ('def main():\n    pass\n\n\n'
               'if __name__ == \"__main__\":\n    main()\n')

    def test_main_unter_dunder_main_zaehlt(self):
        baum = ast.parse(self.WERKZEUG)
        self.assertIn('main', Rahmenvorschrift.selbst_gerufen(baum))

    def test_ohne_den_block_zaehlt_nichts(self):
        u"""Sonst waere jede Funktion, die irgendwo gerufen wird,
        ausgenommen."""
        baum = ast.parse('def main():\n    pass\n\n\nmain()\n')
        self.assertEqual(Rahmenvorschrift.selbst_gerufen(baum), set())

    def test_eine_andere_bedingung_zaehlt_nicht(self):
        quelle = ('import sys\n\n\ndef main():\n    pass\n\n\n'
                  'if sys.argv:\n    main()\n')
        baum = ast.parse(quelle)
        self.assertEqual(Rahmenvorschrift.selbst_gerufen(baum), set())


class EigeneRahmennamenTest(SimpleTestCase):
    u"""Ein fremder Rahmen darf seine Namen selbst nennen.

    ANLASS (01.09.2026, 3DTools): Das Blender-Addon traegt in zehn Modulen
    `register`/`unregister` auf Modulebene. Blender ruft genau diese beiden
    Namen am Modul — in einer Klasse ruft sie niemand mehr.
    """

    @override_settings(DJANGOBASE={'rahmenfunktionen': ['register',
                                                       'unregister']})
    def test_angegebene_namen_zaehlen(self):
        namen = Rahmenvorschrift.namen()
        self.assertIn('register', namen)
        self.assertIn('unregister', namen)

    @override_settings(DJANGOBASE={})
    def test_ohne_angabe_zaehlt_nichts(self):
        u"""Die Ausnahme entsteht nur durch den Eintrag, nicht von selbst."""
        self.assertNotIn('register', Rahmenvorschrift.namen())

    @override_settings(DJANGOBASE={'rahmenfunktionen': ['Register']})
    def test_grossgeschriebenes_zaehlt_nicht(self):
        u"""Eine Klasse darf eine Klasse sein — und ein Tippfehler wirkt nicht."""
        self.assertNotIn('Register', Rahmenvorschrift.namen())

    @override_settings(DJANGOBASE={'rahmenfunktionen': 'register'})
    def test_ein_einzelner_name_als_zeichenkette(self):
        u"""Wer nur einen Namen hat, schreibt ihn ohne Liste."""
        self.assertIn('register', Rahmenvorschrift.namen())


class NamenAusDenEinstellungenTest(SimpleTestCase):
    u"""Nur was WIRKLICH eingetragen ist, gilt als vorgeschrieben."""

    @override_settings(TEMPLATES=VORLAGEN)
    def test_kontextprozessoren_zaehlen(self):
        namen = Rahmenvorschrift.namen()
        self.assertIn('version', namen)
        self.assertIn('active_theme', namen)
        self.assertIn('request', namen)

    @override_settings(TEMPLATES=VORLAGEN)
    def test_ein_erfundener_name_zaehlt_nicht(self):
        u"""Sonst waere die Ausnahme ein Freibrief fuer jeden Namen."""
        self.assertNotIn('lade_bvh', Rahmenvorschrift.namen())

    @override_settings(MIDDLEWARE=['django.middleware.common.CommonMiddleware'])
    def test_klassen_in_der_middleware_zaehlen_nicht(self):
        u"""`CommonMiddleware` DARF eine Klasse sein — die Frage meint sie nicht."""
        self.assertNotIn('CommonMiddleware', Rahmenvorschrift.namen())

    def test_rahmendateien(self):
        for name in ('manage.py', 'wsgi.py', 'asgi.py'):
            with self.subTest(datei=name):
                self.assertTrue(
                    Rahmenvorschrift.eigene_datei('A:/projekt/' + name))
        self.assertFalse(Rahmenvorschrift.eigene_datei('A:/projekt/dienste.py'))


class WerkzeugVerhaltenTest(SimpleTestCase):
    u"""Das Werkzeug selbst — an einem nachgebauten Projekt."""

    def _sicht(self, quelle, name='context_processors.py', vorgeschrieben=()):
        import tempfile
        from pathlib import Path
        from djangobase.skills.freiefunktionen import FreieFunktionen
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / name
            datei.write_text(quelle, encoding='utf-8')
            return FreieFunktionen()._modul(datei, None, vorgeschrieben)

    KONTEXT = ("def version(request):\n    return {}\n\n\n"
               "def active_theme(request):\n    return {}\n")

    def test_vorgeschriebene_funktionen_zaehlen_nicht(self):
        self.assertIsNone(self._sicht(
            self.KONTEXT, vorgeschrieben={'version', 'active_theme'}),
            'ein Kontextprozessor ist kein Befund')

    def test_ohne_die_ausnahme_waere_es_ein_befund(self):
        u"""DIE GEGENPROBE: Der Waechter muss ohne die Liste anschlagen."""
        sicht = self._sicht(self.KONTEXT, vorgeschrieben=())
        self.assertIsNotNone(sicht)
        self.assertEqual(len(sicht.funktionen), 2)

    def test_echter_befund_bleibt(self):
        u"""Acht lose Funktionen sind weiterhin ein Fall."""
        quelle = ''.join('def schritt%d(wert):\n    return wert + %d\n\n\n'
                         % (i, i) for i in range(1, 9))
        sicht = self._sicht(quelle, name='helfer.py',
                            vorgeschrieben={'version', 'active_theme'})
        self.assertIsNotNone(sicht)
        self.assertEqual(len(sicht.funktionen), 8)

    def test_manage_py_wird_uebergangen(self):
        quelle = "def main():\n    pass\n"
        self.assertIsNone(self._sicht(quelle, name='manage.py'))
