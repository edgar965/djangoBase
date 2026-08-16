"""Namensdubletten — derselbe Name mehrfach, und mehrere Namen fuer dasselbe."""

import ast
import re
from collections import defaultdict

from .werkzeug import Befund, Ergebnis, Werkzeug

#: Wortpaare, die im selben Projekt dieselbe Sache meinen. Links das, was in
#: gemischtsprachigen Projekten haeufig nebeneinander steht.
GLEICHBEDEUTEND = [
    ('get', 'hole', 'lade', 'load', 'fetch'),
    ('save', 'speichern', 'schreiben', 'write', 'store'),
    ('delete', 'loeschen', 'remove', 'entfernen'),
    ('list', 'liste', 'alle', 'all'),
    ('create', 'anlegen', 'neu', 'new', 'build', 'bauen'),
    ('update', 'aendern', 'setzen', 'set'),
    ('check', 'pruefen', 'validate', 'testen'),
    ('name', 'bezeichnung', 'label', 'titel', 'title'),
    ('count', 'anzahl', 'zahl', 'num'),
    ('path', 'pfad', 'datei', 'file'),
]


class Namensdubletten(Werkzeug):

    slug = 'namens-dubletten'
    name = 'Namens-Dubletten'
    zweck = ('Findet gleichnamige Klassen und Modulfunktionen an mehreren '
             'Stellen, gleichnamige Moduldateien in verschiedenen Ordnern und '
             'Paare wie get_/hole_, die dasselbe meinen. METHODEN sind '
             'ausgenommen — dass zwei Klassen ein `anzahl()` haben, ist der '
             'Sinn der Sache und keine Dublette.')
    wann = ('Wenn ein Projekt aus mehreren Umbauten gewachsen ist. Zwei Namen '
            'fuer dieselbe Sache kosten bei jeder Suche Zeit und erzeugen '
            'stille Fehler, sobald jemand den falschen benutzt.')
    beleg = ('Genau dieser Fall kostete im Ursprungsprojekt vier Monate: Eine '
             'Vorlage las `unique_videos`, die Ansicht lieferte `upload_files` '
             '— Django rendert dafuer kommentarlos nichts, also fiel es keinem '
             'auf.')
    dauer = 'Sekunden'

    #: Namen, die absichtlich ueberall gleich heissen.
    ERLAUBT = {
        'main', 'setUp', 'setUpClass', 'tearDown', 'tearDownClass', 'handle',
        'ready', 'get', 'post', 'save', 'clean', '__init__', 'Meta', 'Migration',
        'Config', 'apps', 'models', 'views', 'urls', 'admin', 'tests', 'forms',
        'utils', 'conf', 'signals', 'setUpTestData', 'get_context_data',
        'get_queryset', 'form_valid', 'dispatch', '__str__', 'pruefen',
    }

    def pruefen(self, **_argumente):
        klassen = defaultdict(list)
        funktionen = defaultdict(list)
        moduldateien = defaultdict(list)
        wortverwendung = defaultdict(set)

        for datei in self.projektdateien('.py'):
            moduldateien[datei.name].append(self.kurz(datei))
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
            except (SyntaxError, OSError):
                continue
            # NUR Modulebene (`baum.body`), nicht `ast.walk`: Methoden zaehlen
            # nicht als Dublette. Zwei Klassen mit je einem `anzahl()` sind
            # normale Objektorientierung — mit ast.walk waren 29 von 29 Befunden
            # genau solche Fehlalarme.
            for knoten in baum.body:
                if isinstance(knoten, ast.ClassDef):
                    ziel = klassen
                elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ziel = funktionen
                else:
                    continue
                if knoten.name in self.ERLAUBT or knoten.name.startswith('_'):
                    continue
                ziel[knoten.name].append('%s:%d' % (self.kurz(datei), knoten.lineno))
                for wort in re.split(r'[_\W]+', knoten.name.lower()):
                    if wort:
                        wortverwendung[wort].add(knoten.name)

        befunde = []
        befunde.extend(self._doppelt(klassen, 'Klasse'))
        befunde.extend(self._doppelt(funktionen, 'Funktion'))
        for dateiname, orte in sorted(moduldateien.items()):
            if len(orte) > 1 and dateiname not in ('__init__.py', 'apps.py',
                                                   'models.py', 'views.py',
                                                   'urls.py', 'admin.py',
                                                   'tests.py', 'forms.py'):
                befunde.append(Befund(
                    orte[0], 'Dateiname %s liegt %dx im Projekt'
                             % (dateiname, len(orte)),
                    'auch: ' + ', '.join(orte[1:5]), Befund.HINWEIS))
        befunde.extend(self._synonyme(wortverwendung))

        kopf = ['%d Klassennamen, %d Funktionsnamen geprueft'
                % (len(klassen), len(funktionen))]
        return Ergebnis(self.name, kopf, befunde)

    def _doppelt(self, namen, art):
        befunde = []
        for name, orte in sorted(namen.items()):
            if len(orte) < 2:
                continue
            befunde.append(Befund(
                orte[0], '%s %s existiert %dx' % (art, name, len(orte)),
                'auch: ' + ', '.join(orte[1:6]),
                Befund.WARNUNG if len(orte) > 2 else Befund.HINWEIS))
        return befunde

    @staticmethod
    def _synonyme(wortverwendung):
        """Wortpaare, die beide im Projekt vorkommen und dasselbe meinen."""
        befunde = []
        for gruppe in GLEICHBEDEUTEND:
            benutzt = [wort for wort in gruppe if wort in wortverwendung]
            if len(benutzt) < 2:
                continue
            beispiele = []
            for wort in benutzt:
                erste = sorted(wortverwendung[wort])[:2]
                beispiele.append('%s (%s)' % (wort, ', '.join(erste)))
            befunde.append(Befund(
                ' / '.join(benutzt),
                '%d Schreibweisen fuer dieselbe Sache' % len(benutzt),
                '; '.join(beispiele), Befund.HINWEIS))
        return befunde
