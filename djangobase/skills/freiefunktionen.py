"""FreieFunktionen — Funktionen auf Modulebene, die in eine Klasse gehoeren."""

import ast
import re
from collections import Counter, defaultdict

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall


class Modulsicht:
    """Was auf Modulebene steht: freie Funktionen, Klassen, gemeinsame Praefixe."""

    __slots__ = ('pfad', 'funktionen', 'klassen', 'zeilen')

    def __init__(self, pfad, funktionen, klassen, zeilen):
        self.pfad = pfad
        #: [(name, zeile, zeilenzahl, erstes_argument)]
        self.funktionen = funktionen
        self.klassen = klassen
        self.zeilen = zeilen

    def gruppen(self):
        """Funktionen mit gemeinsamem Namensanfang — die deutlichsten Kandidaten.

        `lade_bvh`, `pruefe_bvh`, `schreibe_bvh` sind drei Funktionen mit
        demselben Gegenstand: zusammen eine Klasse. Gruppiert wird ueber den
        ersten Namensteil vor dem Unterstrich, in beide Richtungen (Praefix und
        Suffix), weil beide Schreibweisen ueblich sind.
        """
        nach_anfang = defaultdict(list)
        nach_ende = defaultdict(list)
        for name, zeile, laenge, _erstes in self.funktionen:
            teile = name.strip('_').split('_')
            if len(teile) > 1:
                nach_anfang[teile[0]].append((name, zeile, laenge))
                nach_ende[teile[-1]].append((name, zeile, laenge))
        gefunden = []
        for schluessel, eintraege in list(nach_anfang.items()) + list(nach_ende.items()):
            if len(eintraege) >= 3:
                gefunden.append((schluessel, eintraege))
        # Nach Groesse: die dicksten Buendel zuerst.
        gefunden.sort(key=lambda paar: -len(paar[1]))
        return gefunden


class FreieFunktionen(BefundWerkzeug):

    slug = 'freie-funktionen'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 1
    titel = 'Freie Funktionen'
    zweck = ('Zeigt Module mit vielen Funktionen auf Modulebene und findet '
             'Buendel gleichen Namensanfangs — die naheliegenden Kandidaten '
             'fuer eine Klasse.')
    abhilfe = ('Beim Umstieg auf Objektorientierung. Drei Funktionen mit demselben '
            'Namensanfang und demselben ersten Argument sind fast immer eine '
            'Klasse, die noch niemand geschrieben hat.')
    befund = ('So entstanden im Ursprungsprojekt u. a. Skingewichte, '
             'Bvhbibliothek und Animationsauswahl — vorher lose Funktionen mit '
             'globalen Zwischenspeichern in einer 6.000-Zeilen-Datei.')
    dauer = 'Sekunden'
    #: ALLE melden, nicht erst ab fuenf (24.08.2026, auf Ansage: „der test
    #: soll sie alle melden"). Die Vorgabe 5 versteckte an CamTrack 238 von
    #: 283 Modulen — gemeldet wurden 45. Wer die Zahl kleiner haben will,
    #: dreht sie hier hoch; die Voreinstellung darf nichts verschweigen.
    eingabe = ('ab', 'Ab wie vielen freien Funktionen je Datei melden?', '1')

    anlassfall = Anlassfall(
        {"helfer.py": "".join("def schritt%d(wert):\n    return wert + %d\n\n\n"
                              % (i, i) for i in range(1, 9))},
        mindestens=1, erwartet_in="helfer.py",
        warum="Acht lose Funktionen auf Modulebene: Der Zusammenhang steht "
              "nirgends, und jede traegt ihren Zustand selbst")

    def pruefen(self, ab='1', **_argumente):
        try:
            grenze = max(1, int(str(ab).strip() or 1))
        except ValueError:
            grenze = 1

        sichten, befunde = [], []
        rufer, ansichten = {}, set()
        for datei in self.projektdateien('.py'):
            self._ansichten_sammeln(datei, ansichten)
            sicht = self._modul(datei, rufer)
            if sicht is not None:
                sichten.append(sicht)

        for sicht in sorted(sichten, key=lambda s: -len(s.funktionen)):
            if len(sicht.funktionen) < grenze:
                continue
            gruppen = sicht.gruppen()
            hinweis = ''
            if gruppen:
                schluessel, eintraege = gruppen[0]
                platz = self._wo_hin(eintraege, rufer, ansichten,
                                     sicht.klassen)
                hinweis = ('%d Funktionen als Klasse `%s`: %s. %s'
                           % (len(eintraege), self._klassenname(schluessel),
                              ', '.join(n for n, _z, _l in eintraege[:6]),
                              platz))
            befunde.append(Befund(
                sicht.pfad,
                '%d freie Funktionen, %d Klassen' % (len(sicht.funktionen),
                                                     sicht.klassen),
                hinweis or 'kein gemeinsamer Namensanfang — einzeln pruefen',
                Befund.WARNUNG if len(sicht.funktionen) >= grenze * 2
                else Befund.HINWEIS))

        gesamt = sum(len(s.funktionen) for s in sichten)
        gebuendelt = sum(len(g[1]) for s in sichten for g in s.gruppen())
        kopf = ['%d Module, %d Funktionen auf Modulebene' % (len(sichten), gesamt),
                '%d Module mit mindestens %d freien Funktionen'
                % (len(befunde), grenze),
                '%d davon stehen in einem Buendel gleichen Namensanfangs — '
                'das sind die Klassen, die noch niemand geschrieben hat'
                % gebuendelt]
        return Befundsatz(self.titel, kopf, befunde)

    #: Klassen, an die nichts gehaengt wird. Ein Test RUFT den Code, er
    #: BESITZT ihn nicht — der erste Lauf schlug `ComputeAcceptThresholdTests`
    #: als Halter fuer drei Schwellen-Funktionen vor.
    KEIN_HALTER = ('Test', 'Tests', 'TestCase', 'Mixin')

    def _rufer_sammeln(self, baum, hinein, datei=None):
        u"""Welche KLASSE ruft welche Funktion beim Namen?

        Damit laesst sich die zweite Haelfte der Frage beantworten: nicht
        nur „diese drei gehoeren in eine Klasse", sondern auch „und diese
        Klasse gehoert dorthin".
        """
        if datei is not None and ('test' in datei.name.lower()
                                 or 'tests' in datei.parts):
            return
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            if knoten.name.endswith(self.KEIN_HALTER):
                continue
            for teil in ast.walk(knoten):
                if isinstance(teil, ast.Call) and isinstance(teil.func, ast.Name):
                    hinein.setdefault(teil.func.id, Counter())[knoten.name] += 1

    @staticmethod
    def _klassenname(schluessel):
        u"""Aus dem Buendel-Schluessel ein Klassenname.

        `person` -> `PersonVerwaltung`, `marzahn` -> `MarzahnVerwaltung`.
        Ein Vorschlag, kein Befehl: Wer die Klasse schreibt, findet meist
        einen besseren Namen. Aber ein Vorschlag ist leichter zu
        widersprechen als ein leeres Feld.
        """
        return schluessel.strip('_').replace('_', ' ').title().replace(' ', '')             + 'Verwaltung'

    def _ansichten_sammeln(self, datei, hinein):
        u"""Namen, die in einer `urls.py` als Ansicht eingetragen sind.

        Sie werden vom URL-Router gerufen, nicht von einer Klasse. „Niemand
        ruft sie" waere deshalb die falsche Auskunft — richtig ist: Django
        hat dafuer die klassenbasierte Ansicht, und djangoBase benutzt sie
        durchgehend (`SkillsView(ZugriffMixin, View)`).
        """
        if datei.name != 'urls.py':
            return
        try:
            text = datei.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return
        for treffer in re.finditer(r'views\.(\w+)|path\([^,]+,\s*(\w+)', text):
            name = treffer.group(1) or treffer.group(2)
            if name:
                hinein.add(name)

    def _wo_hin(self, eintraege, rufer, ansichten, eigene_klassen):
        u"""In welchen Baum gehoert die neue Klasse?

        DIE ZWEITE HAELFTE DER FRAGE (Edgar, 24.08.2026)
        ================================================
            „die sollen als Klassen zusammengefasst werden, und dann
             moeglichst in dem Baum der sie braucht"

        Das Werkzeug meldete bisher nur „diese fuenf gehoeren in eine
        Klasse". Wo diese Klasse dann haengt, blieb offen — und genau daran
        scheitert der Umbau: Eine neue Klasse ohne Platz im Baum ist wieder
        eine Wurzel, und davon gab es schon zu viele.

        Gezaehlt wird, welche vorhandene Klasse diese Funktionen am
        haeufigsten ruft. Wer sie braucht, soll sie halten.
        """
        gesamt = Counter()
        for name, _z, _l in eintraege:
            gesamt.update(rufer.get(name) or {})
        if gesamt:
            klasse, zahl = gesamt.most_common(1)[0]
            return ('Haengt an `%s` — die ruft sie %dx, wer sie braucht soll '
                    'sie halten.' % (klasse, zahl))
        treffer = sum(1 for n, _z, _l in eintraege if n in ansichten)
        if treffer:
            return ('%d davon sind Django-Ansichten: gehoeren in eine '
                    'klassenbasierte Ansicht (`View`), nicht in eine eigene '
                    'Klasse daneben.' % treffer)
        if eigene_klassen:
            return ('Im selben Modul steht schon eine Klasse — dort '
                    'anhaengen statt eine zweite Wurzel aufzumachen.')
        return ('Niemand ruft sie aus einer Klasse: eine neue Wurzel, '
                'sparsam einsetzen.')

    def _modul(self, datei, rufer=None):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return None
        if rufer is not None:
            self._rufer_sammeln(baum, rufer, datei)
        funktionen, klassen = [], 0
        for knoten in baum.body:          # nur Modulebene, nicht ast.walk
            if isinstance(knoten, ast.ClassDef):
                klassen += 1
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if knoten.name.startswith('__'):
                    continue
                ende = getattr(knoten, 'end_lineno', knoten.lineno) or knoten.lineno
                erstes = (knoten.args.args[0].arg if knoten.args.args else '')
                funktionen.append((knoten.name, knoten.lineno,
                                   ende - knoten.lineno + 1, erstes))
        if not funktionen:
            return None
        return Modulsicht(self.kurz(datei), funktionen, klassen,
                          getattr(baum, 'end_lineno', 0) or 0)
