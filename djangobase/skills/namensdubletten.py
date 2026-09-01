"""Namensdubletten — derselbe Name mehrfach, und mehrere Namen für dasselbe."""

import ast
import re
from collections import defaultdict

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall

#: Wortpaare, die im selben Projekt dieselbe Sache meinen — GETRENNT NACH
#: SPRACHE.
#:
#: WARUM GETRENNT (17.08.2026, 3DTools): Die Gruppen standen gemischt
#: (``('path', 'pfad', 'datei', 'file')``). In diesem Projekt heissen die alten
#: API-Ansichten englisch (``character_bvh_file``) und alles Neue deutsch
#: (``pfad_sichern``) — das ist die bewusste Lage, kein Versehen. Gemischte
#: Gruppen melden deshalb JEDEN neuen deutschen Namen gegen seinen englischen
#: Vorgaenger: ein Befund, aus dem nichts folgt, ausser den ganzen Umbau
#: zurueckzudrehen.
#:
#: Innerhalb einer Sprache bleibt der Befund scharf und hat genau an diesem Tag
#: einen echten Fall gefunden: ``get_pose`` neben ``studio_project_load`` — zwei
#: englische Schreibweisen fuer „lesen" in derselben API. Umbenannt zu
#: ``pose_load``.
GLEICHBEDEUTEND = [
    # Englisch
    ('get', 'load', 'fetch', 'read'),
    ('save', 'write', 'store'),
    ('delete', 'remove'),
    ('list', 'all'),
    ('create', 'new', 'build'),
    ('update', 'set'),
    ('check', 'validate'),
    ('name', 'label', 'title'),
    ('count', 'num'),
    ('path', 'file'),
    # Deutsch
    ('hole', 'lade', 'lesen'),
    ('speichern', 'schreiben'),
    ('loeschen', 'entfernen'),
    ('liste', 'alle'),
    ('anlegen', 'neu', 'bauen'),
    ('aendern', 'setzen'),
    ('pruefen', 'testen'),
    ('bezeichnung', 'titel'),
    ('anzahl', 'zahl'),
    ('pfad', 'datei'),
]


class Namensdubletten(BefundWerkzeug):

    slug = 'namens-dubletten'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 7
    titel = 'Namens-Dubletten'
    zweck = ('Findet gleichnamige Klassen und Modulfunktionen an mehreren '
             'Stellen, gleichnamige Moduldateien in verschiedenen Ordnern und '
             'Paare wie get_/hole_, die dasselbe meinen. METHODEN sind '
             'ausgenommen — dass zwei Klassen ein `anzahl()` haben, ist der '
             'Sinn der Sache und keine Dublette.')
    abhilfe = ('Wenn ein Projekt aus mehreren Umbauten gewachsen ist. Zwei Namen '
            'für dieselbe Sache kosten bei jeder Suche Zeit und erzeugen '
            'stille Fehler, sobald jemand den falschen benutzt.')
    befund = ('Genau dieser Fall kostete im Ursprungsprojekt vier Monate: Eine '
             'Vorlage las `unique_videos`, die Ansicht lieferte `upload_files` '
             '— Django rendert dafür kommentarlos nichts, also fiel es keinem '
             'auf.')
    dauer = 'Sekunden'

    #: Namen, die absichtlich ueberall gleich heissen.
    #:
    #: ``Command`` ist Djangos PFLICHTNAME fuer ein Verwaltungskommando —
    #: ``BaseCommand`` wird ueber genau diesen Namen im Modul gesucht. In
    #: assistant stand er mit 56 Vorkommen an der Spitze der Liste
    #: (30.08.2026); wer dem Befund folgt, macht das Projekt kaputt.
    #: Dieselbe Klasse Fehlalarm wie ``Meta`` und ``Migration``, die schon
    #: hier standen (``~/.claude/rules/analysewerkzeuge.md``, Punkt 1).
    ERLAUBT = {
        'main', 'setUp', 'setUpClass', 'tearDown', 'tearDownClass', 'handle',
        'ready', 'get', 'post', 'save', 'clean', '__init__', 'Meta', 'Migration',
        'Command', 'Config', 'apps', 'models', 'views', 'urls', 'admin',
        'tests', 'forms', 'utils', 'conf', 'signals', 'setUpTestData',
        'get_context_data', 'get_queryset', 'form_valid', 'dispatch',
        '__str__', 'pruefen',
    }

    anlassfall = Anlassfall(
        {"laden.py": "def kunde_laden(kennung):\n    return kennung\n",
         "dienst.py": "def kunde_laden(kennung):\n    return {'id': kennung}\n"},
        mindestens=1, erwartet_in="kunde_laden",
        warum="Derselbe Funktionsname in zwei Modulen — man ruft den einen auf "
              "und meint den anderen, und im Zweifel importiert man beide")

    def pruefen(self, **_argumente):
        klassen = defaultdict(list)
        funktionen = defaultdict(list)
        privat = defaultdict(list)
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
                if knoten.name in self.ERLAUBT:
                    continue
                ort = '%s:%d' % (self.kurz(datei), knoten.lineno)
                if knoten.name.startswith('_'):
                    # PRIVATE NAMEN: nicht mehr blind ueberspringen, siehe
                    # `_privat_mit_zwei_gesichtern`. Gesammelt wird hier nur;
                    # gemeldet wird spaeter und nur bei abweichender Signatur.
                    if isinstance(knoten, ast.ClassDef):
                        continue
                    privat[knoten.name].append((self._signatur(knoten), ort))
                    continue
                ziel[knoten.name].append(ort)
                for wort in re.split(r'[_\W]+', knoten.name.lower()):
                    if wort:
                        wortverwendung[wort].add(knoten.name)

        befunde = []
        befunde.extend(self._doppelt(klassen, 'Klasse'))
        befunde.extend(self._doppelt(funktionen, 'Funktion'))
        befunde.extend(self._privat_mit_zwei_gesichtern(privat))
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

        kopf = ['%d Klassennamen, %d Funktionsnamen geprüft'
                % (len(klassen), len(funktionen))]
        return Befundsatz(self.titel, kopf, befunde)

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
    def _signatur(knoten):
        """Die Parameterliste als Zeichenkette — ohne Vorgabewerte."""
        argumente = knoten.args
        namen = [a.arg for a in (list(getattr(argumente, 'posonlyargs', []))
                                 + list(argumente.args))]
        if argumente.vararg:
            namen.append('*' + argumente.vararg.arg)
        namen += [a.arg for a in argumente.kwonlyargs]
        if argumente.kwarg:
            namen.append('**' + argumente.kwarg.arg)
        return ', '.join(namen)

    def _privat_mit_zwei_gesichtern(self, privat):
        """Ein privater Name, der in zwei Dateien VERSCHIEDENES bedeutet.

        WARUM PRIVATE NAMEN NICHT MEHR PAUSCHAL DURCHRUTSCHEN (31.08.2026)
        =================================================================
        Hier stand ``knoten.name.startswith('_')`` als blindes
        ``continue`` — ohne Begruendung daneben. Der Gedanke dahinter ist
        richtig: ``_parse``, ``_key``, ``_norm`` heissen in zwanzig
        Modulen gleich, und das ist keine Dublette, sondern ein kurzer
        Name fuer eine kurze Sache.

        Er traegt aber nicht weit genug. In 3DTools stand
        ``_push_outside_body`` in VIER Dateien::

            collision/warp_sim.py        (cloth_pts, body_pts, body_normals, margin)
            collision/skinning_only.py   (cloth_pts, body_pts, body_normals, margin)
            humanbody_core/cloth.py      (cloth_verts, body_verts, min_dist)
            GarmentFitter/fitter.py      (cloth_verts, ..., min_dist, ...)

        Dreimal derselbe sprechende Name fuer drei verschiedene
        Rechnungen — und Aufrufer in HumanBodyWeb holen ihn mal aus dem
        einen, mal aus dem anderen Modul. Genau das, wovor dieses
        Werkzeug warnen soll; es sah nur weg, weil ein Unterstrich davor
        stand.

        GEMELDET WIRD DESHALB NUR DIE GEFAEHRLICHE HAELFTE: gleiche
        Parameterliste heisst „dieselbe Sache, vielleicht kopiert" — dafuer
        gibt es ``doppelcode`` und ``doppelrumpf``, die den Rumpf
        vergleichen statt den Namen. Verschiedene Parameterlisten heissen
        „verschiedene Sachen unter einem Namen", und dagegen hilft kein
        anderes Werkzeug.
        """
        befunde = []
        for name, treffer in sorted(privat.items()):
            if len(treffer) < 2:
                continue
            signaturen = {}
            for signatur, ort in treffer:
                signaturen.setdefault(signatur, []).append(ort)
            if len(signaturen) < 2:
                continue
            orte = [orte[0] for orte in signaturen.values()]
            beschreibung = '; '.join(
                '(%s)' % signatur if signatur else '()'
                for signatur in list(signaturen)[:3])
            befunde.append(Befund(
                orte[0],
                'Privatname %s bedeutet %dx Verschiedenes'
                % (name, len(signaturen)),
                '%s — auch: %s' % (beschreibung, ', '.join(orte[1:5])),
                Befund.WARNUNG))
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
                '%d Schreibweisen für dieselbe Sache' % len(benutzt),
                '; '.join(beispiele), Befund.HINWEIS))
        return befunde
