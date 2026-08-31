# -*- coding: utf-8 -*-
u"""Die vier Werkzeuge aus dem 3DTools-Durchgang vom 27.08.2026.

Der ``anlassfall-check`` faehrt jedes Werkzeug an seinem eigenen Fall — das ist
die Deckung nach oben. Hier stehen die Faelle DANEBEN: die Formen, an denen
jedes dieser vier im ersten Wurf falsch lag. Beide Male ist es dieselbe
Fehlerklasse, und beide Male haette sie niemand bemerkt:

* ``css-dubletten`` hielt ``padding:8px`` und ``padding: 8px`` fuer
  verschiedene Regeln. Der eigene Anlassfall fiel durch, obwohl dieselbe Regel
  dreimal dastand — Leerraum hinter dem Doppelpunkt.
* ``nur-lesen`` nahm seine Probewurzel nur als RUECKFALL. In jedem Projekt, das
  eigene Wurzeln einstellt (also in jedem eingerichteten), war es damit blind.
"""
from pathlib import Path

from djangobase.skills.cachebusting import Cachebusting
from djangobase.skills.cssdubletten import Cssdubletten
from djangobase.skills.nurlesen import NurLesen
from djangobase.skills.pfadpraefix import Pfadpraefix

from ..base import BasisTest


class Wegwerfprojekt:
    """Ein Miniprojekt im Wegwerfordner, auf das ein Werkzeug losgelassen wird."""

    def __init__(self, ordner, dateien):
        self.ordner = Path(ordner)
        for name, inhalt in dateien.items():
            ziel = self.ordner / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding='utf-8')

    def fahren(self, klasse, **argumente):
        """Das Werkzeug mit DIESEM Ordner als Projektwurzel — Befundzeilen.

        `Wegwerfordner.ansetzen` oeffnet dabei die beiden Siebe
        (Ausschlussliste, `.gitignore`). Ohne das findet ein Werkzeug null
        Dateien, sobald der Ordner INNERHALB des Projekts liegt — und das
        tut er seit der `Ablageumleitung`.
        """
        from ..wegwerfordner import Wegwerfordner

        werkzeug = Wegwerfordner.ansetzen(klasse(), self.ordner)
        return werkzeug.laufen(**argumente).zeilen


class WerkzeugBasis(BasisTest):
    """Legt je Prueffall einen eigenen Wegwerfordner an."""

    def projekt(self, dateien):
        import shutil
        import tempfile
        ordner = tempfile.mkdtemp(prefix='dbwerkzeug_')
        self.addCleanup(shutil.rmtree, ordner, True)
        return Wegwerfprojekt(ordner, dateien)


class CssdublettenTest(WerkzeugBasis):

    def test_leerraum_hinter_dem_doppelpunkt_zaehlt_nicht(self):
        """DER FEHLER DES ERSTEN WURFS.

        `padding:8px` und `padding: 8px` sind dieselbe Regel. Wer das nicht
        vereinheitlicht, findet in einem gewachsenen Projekt fast keine
        Dublette — beide Schreibweisen stehen nebeneinander, sobald zwei Leute
        an denselben Vorlagen gearbeitet haben.
        """
        projekt = self.projekt({
            'templates/a.html': '<style>.karte{padding:8px;color:red}</style>',
            'templates/b.html':
                '<style>.karte { padding: 8px; color: red; }</style>',
            'templates/c.html': '<style>.karte{padding:8px;color:red}</style>',
        })
        zeilen = projekt.fahren(Cssdubletten)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('.karte', zeilen[0]['befund'])
        self.assertIn('3x', zeilen[0]['befund'])

    def test_kommentar_wird_nicht_zum_selektor(self):
        """Ein Vermerk ueber der Regel gehoert nicht in den Vergleich.

        In 3DTools steht ueber jedem erzeugten Stilblock derselbe
        Herkunftsvermerk. Ohne das Entfernen meldete das Werkzeug diesen
        Vermerk als haeufigste Dublette — achtmal, ganz oben.
        """
        vermerk = '/* Erzeugt von css_ausziehen.py */'
        projekt = self.projekt({
            'templates/a.html': '<style>%s .eins{margin:0}</style>' % vermerk,
            'templates/b.html': '<style>%s .zwei{padding:0}</style>' % vermerk,
            'templates/c.html': '<style>%s .drei{border:0}</style>' % vermerk,
        })
        self.assertEqual(projekt.fahren(Cssdubletten), [])

    def test_unter_der_grenze_bleibt_still(self):
        projekt = self.projekt({
            'templates/a.html': '<style>.karte{padding:8px}</style>',
            'templates/b.html': '<style>.karte{padding:8px}</style>',
        })
        self.assertEqual(projekt.fahren(Cssdubletten), [])
        # Mit `ab=2` ist derselbe Bestand ein Befund.
        self.assertEqual(len(projekt.fahren(Cssdubletten, ab='2')), 1)

    def test_zwei_animationen_mit_gleichem_schritt_sind_keine_dublette(self):
        u"""DER FEHLALARM (31.08.2026, assistant).

        ``REGEL`` kennt keine geschachtelten Klammern und fand in
        ``@keyframes spin{from{…}to{…}}`` nicht den Block, sondern seine
        Schritte — ohne den Namen der Animation. Damit galt
        ``to{transform:rotate(360deg)}`` als dieselbe Regel in jeder
        Datei, die irgendetwas dreht: ``@keyframes sync-spin`` wurde als
        Dublette von ``@keyframes spin`` gemeldet.
        """
        dreh = ('@keyframes %s{from{transform:rotate(0deg);}'
                'to{transform:rotate(360deg);}}')
        projekt = self.projekt({
            'templates/a.html': '<style>%s</style>' % (dreh % 'spin'),
            'templates/b.html': '<style>%s</style>' % (dreh % 'sync-spin'),
            'templates/c.html': '<style>%s</style>' % (dreh % 'lade-dreh'),
        })
        self.assertEqual(projekt.fahren(Cssdubletten), [])

    def test_dieselbe_animation_dreimal_ist_sehr_wohl_eine(self):
        u"""DIE GEGENPROBE: gleicher Name, gleicher Rumpf — ein Befund."""
        dreh = ('@keyframes spin{from{transform:rotate(0deg);}'
                'to{transform:rotate(360deg);}}')
        projekt = self.projekt({
            'templates/a.html': '<style>%s</style>' % dreh,
            'templates/b.html': '<style>%s</style>' % dreh,
            'templates/c.html': '<style>%s</style>' % dreh,
        })
        zeilen = projekt.fahren(Cssdubletten)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('@keyframes spin', zeilen[0]['befund'])

    def test_eine_regel_im_media_block_ist_nicht_die_basisregel(self):
        u"""Dieselbe Klasse: eine Ueberschreibung ist keine Dublette.

        ``@media print{.karte{…}}`` und ``.karte{…}`` daneben sagen
        Verschiedenes — die eine gilt beim Drucken, die andere immer.
        """
        projekt = self.projekt({
            'templates/a.html':
                '<style>@media print{.karte{padding:0}}</style>',
            'templates/b.html': '<style>.karte{padding:0}</style>',
            'templates/c.html': '<style>.karte{padding:0}</style>',
        })
        self.assertEqual(projekt.fahren(Cssdubletten), [])

    def test_aber_dieselbe_media_regel_dreimal_zaehlt(self):
        u"""DIE GEGENPROBE: gleiche Bedingung, gleiche Regel."""
        stueck = '<style>@media print{.karte{padding:0}}</style>'
        projekt = self.projekt({
            'templates/a.html': stueck,
            'templates/b.html': stueck,
            'templates/c.html': stueck,
        })
        zeilen = projekt.fahren(Cssdubletten)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('@media print', zeilen[0]['befund'])


class NurLesenTest(WerkzeugBasis):

    def test_probewurzel_gilt_auch_bei_eigener_einstellung(self):
        """DER FEHLER DES ERSTEN WURFS.

        Die Wurzel des eigenen Anlassfalls galt nur, solange das Projekt keine
        eigenen einstellte. In jedem eingerichteten Projekt war das Werkzeug
        damit blind — und `anlassfall-check` meldete es zu Recht.
        """
        werkzeug = NurLesen()
        self.assertIn(NurLesen.PROBEWURZEL, werkzeug.wurzeln())

    def test_schreiben_wird_gemeldet_lesen_nicht(self):
        projekt = self.projekt({
            'schreiber.py': ("import numpy as np\n\n\n"
                             "def x(w):\n"
                             "    np.save('daten/nurlesen/m.npy', w)\n"),
            'leser.py': ("import numpy as np\n\n\n"
                         "def y():\n"
                         "    return np.load('daten/nurlesen/m.npy')\n"),
        })
        zeilen = projekt.fahren(NurLesen)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('schreiber.py', zeilen[0]['ort'])

    def test_offen_bleibt_offen(self):
        """`open(..., 'r')` ist Lesen, `open(..., 'w')` nicht."""
        projekt = self.projekt({
            'a.py': ("def x():\n"
                     "    return open('daten/nurlesen/m.json', 'r').read()\n"),
            'b.py': ("def y(t):\n"
                     "    open('daten/nurlesen/m.json', 'w').write(t)\n"),
        })
        zeilen = projekt.fahren(NurLesen)
        self.assertEqual([z['ort'].split(':')[0] for z in zeilen], ['b.py'])


class PfadpraefixTest(WerkzeugBasis):

    def test_startswith_auf_pfaden_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("import os\n\n\n"
                     "def erlaubt(ziel, wurzel):\n"
                     "    return str(ziel).startswith(os.path.normpath(wurzel))\n"),
        })
        zeilen = projekt.fahren(Pfadpraefix)
        self.assertEqual(len(zeilen), 1, zeilen)

    def test_startswith_auf_nicht_pfaden_bleibt_still(self):
        """`schluessel.startswith('morph_')` ist kein Pfadvergleich."""
        projekt = self.projekt({
            'a.py': ("def regler(schluessel):\n"
                     "    return schluessel.startswith('morph_')\n"),
        })
        self.assertEqual(projekt.fahren(Pfadpraefix), [])

    def test_is_relative_to_bleibt_still(self):
        projekt = self.projekt({
            'a.py': ("from pathlib import Path\n\n\n"
                     "def erlaubt(ziel, wurzel):\n"
                     "    return Path(ziel).is_relative_to(Path(wurzel))\n"),
        })
        self.assertEqual(projekt.fahren(Pfadpraefix), [])


class CachebustingTest(WerkzeugBasis):

    def test_skript_ohne_fassung_wird_gemeldet(self):
        projekt = self.projekt({
            'templates/a.html': '<script src="/static/app/x.js"></script>\n',
        })
        zeilen = projekt.fahren(Cachebusting)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('script src', zeilen[0]['befund'])

    def test_die_drei_ausnahmen(self):
        """Fassung vorhanden, fremde Adresse, Favicon — alle drei still."""
        projekt = self.projekt({
            'templates/a.html': (
                '<script src="/static/app/x.js?v=3"></script>\n'
                '<link rel="stylesheet" href="/static/app/y.css?t=1">\n'
                '<script src="https://cdn.example/lib.js"></script>\n'
                '<link rel="icon" href="/static/img/f.svg">\n'),
        })
        self.assertEqual(projekt.fahren(Cachebusting), [])

    def test_importkarte_ist_keine_ladeadresse(self):
        projekt = self.projekt({
            'templates/a.html': (
                '<script type="importmap" src="/static/karte.json">'
                '</script>\n'),
        })
        self.assertEqual(projekt.fahren(Cachebusting), [])

    def test_nur_vorlagen(self):
        """Eine .html ausserhalb von `templates/` ist keine Vorlage."""
        projekt = self.projekt({
            'doku/bericht.html': '<script src="/static/app/x.js"></script>\n',
        })
        self.assertEqual(projekt.fahren(Cachebusting), [])
