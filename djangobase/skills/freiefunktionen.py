"""FreieFunktionen — Funktionen auf Modulebene, die in eine Klasse gehoeren."""

import ast
from collections import defaultdict

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
    eingabe = ('ab', 'Ab wie vielen freien Funktionen je Datei melden?', '5')

    anlassfall = Anlassfall(
        {"helfer.py": "".join("def schritt%d(wert):\n    return wert + %d\n\n\n"
                              % (i, i) for i in range(1, 9))},
        mindestens=1, erwartet_in="helfer.py",
        warum="Acht lose Funktionen auf Modulebene: Der Zusammenhang steht "
              "nirgends, und jede traegt ihren Zustand selbst")

    def pruefen(self, ab='5', **_argumente):
        try:
            grenze = max(2, int(str(ab).strip() or 5))
        except ValueError:
            grenze = 5

        sichten, befunde = [], []
        for datei in self.projektdateien('.py'):
            sicht = self._modul(datei)
            if sicht is not None:
                sichten.append(sicht)

        for sicht in sorted(sichten, key=lambda s: -len(s.funktionen)):
            if len(sicht.funktionen) < grenze:
                continue
            gruppen = sicht.gruppen()
            hinweis = ''
            if gruppen:
                schluessel, eintraege = gruppen[0]
                hinweis = ('Buendel "%s": %s'
                           % (schluessel, ', '.join(n for n, _z, _l in eintraege[:6])))
            befunde.append(Befund(
                sicht.pfad,
                '%d freie Funktionen, %d Klassen' % (len(sicht.funktionen),
                                                     sicht.klassen),
                hinweis or 'kein gemeinsamer Namensanfang — einzeln pruefen',
                Befund.WARNUNG if len(sicht.funktionen) >= grenze * 2
                else Befund.HINWEIS))

        gesamt = sum(len(s.funktionen) for s in sichten)
        kopf = ['%d Module, %d Funktionen auf Modulebene' % (len(sichten), gesamt),
                '%d Module mit mindestens %d freien Funktionen'
                % (len(befunde), grenze)]
        return Befundsatz(self.titel, kopf, befunde)

    def _modul(self, datei):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return None
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
