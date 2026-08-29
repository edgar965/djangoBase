# -*- coding: utf-8 -*-
u"""GlobalerZustand — Variablen auf Modulebene, die in eine Klasse gehoeren.

AUFTRAG (Edgar, 19.08.2026, Kriterium 18): „Den Code auf freie Funktionen und
globale Variablen ueberpruefen. Moeglichst in Klassen unterbringen, ggf. in
Utility-Klassen, statische Funktionen, Klassen verwenden. Globale Konstanten und
Variablen in Klassen wie Context unterbringen."

ZWEI SORTEN, ZWEI SCHWEREGRADE
==============================
``FreieFunktionen`` (Kriterium 1) fragt nach dem VERHALTEN auf Modulebene.
Dieses Werkzeug fragt nach dem ZUSTAND — und der ist die gefaehrlichere Haelfte:

* **Veraenderlicher Zustand** (``_cache = {}``, ``_zaehler = 0``, spaeter per
  ``global`` beschrieben) gehoert IMMER in eine Klasse. Er ueberlebt jeden
  Aufruf, gehoert niemandem, und in einem Testlauf traegt ihn die zweite
  Pruefung noch, wenn die erste ihn gefuellt hat. Genau daran sind im
  shortlongx-Projekt mehrfach Pruefungen gegeneinander gelaufen.
* **Konstanten** (``STANDARD_TAGE = 200``) sind harmlos, solange es wenige sind.
  Ab einem Buendel gehoeren sie in eine Konfigurations- oder Kontext-Klasse —
  sonst weiss beim Lesen niemand, welche zusammengehoeren und wer sie liest.

WAS NICHT GEMELDET WIRD
=======================
Der teuerste Fehler eines Pruefwerkzeugs ist der Fehlalarm: Er verdeckt die
echten Befunde (siehe ``~/.claude/rules/analysewerkzeuge.md``). Ausgenommen
sind deshalb:

* ``__all__``, ``__version__`` und andere Dunder — Sprach- bzw. Paketvertrag.
* Django-Pflichtnamen auf Modulebene (``urlpatterns``, ``app_name``,
  ``register``, ``admin``) — sie MUESSEN dort stehen.
* Typ-Aliase und ``Enum``/``NamedTuple``/``dataclass``-Zuweisungen — das sind
  Typdefinitionen, keine Zustaende.
* ``logger = logging.getLogger(__name__)`` — die kanonische Zeile schlechthin.
* Settings-artige Dateien (``settings.py``, ``conf.py``, ``kriterien.py``):
  Dort IST die Modulebene die Datenstruktur.
"""

import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class Modulzustaende:
    u"""Was ein Modul auf oberster Ebene an Zustand hält."""

    __slots__ = ('pfad', 'veraenderlich', 'konstanten', 'global_stellen',
                 'klassen', 'ist_skript')

    def __init__(self, pfad, veraenderlich, konstanten, global_stellen, klassen,
                 ist_skript=False):
        self.pfad = pfad
        #: Ein Ablaufskript laeuft von oben nach unten - dort IST die Modulebene
        #: das Programm, und jede Zwischenvariable dort zu melden waere ein
        #: Fehlalarm. Erkannt AM CODE (laufende Anweisungen auf Modulebene),
        #: nicht am Ordner: Eine Ordnerliste raet und liegt beim naechsten
        #: Verzeichnis daneben. Gemessen am 19.08.2026 in shortlongx:
        #: Ablaufskripte 11-15 solche Anweisungen, echte Module null.
        self.ist_skript = ist_skript
        #: [(name, zeile, art)] — Listen, Dicts, Mengen, Zaehler: alles, was sich
        #: nach dem Import noch aendern kann.
        self.veraenderlich = veraenderlich
        #: [(name, zeile)] — GROSSGESCHRIEBENE Namen mit unveraenderlichem Wert.
        self.konstanten = konstanten
        #: [(name, zeile)] — Stellen mit ``global x``. Der harte Beweis, dass
        #: der Zustand nicht nur da ist, sondern auch beschrieben wird.
        self.global_stellen = global_stellen
        self.klassen = klassen

    @property
    def gewicht(self):
        """Sortierschluessel: geschriebener Zustand zählt am schwersten."""
        return (len(self.global_stellen) * 10 + len(self.veraenderlich) * 3
                + len(self.konstanten))


class GlobalerZustand(BefundWerkzeug):

    slug = 'globaler-zustand'
    kriterium = 18
    titel = 'Globale Variablen und Konstanten'
    zweck = ('Findet veränderlichen Zustand auf Modulebene (Zwischenspeicher, '
             'Zähler, Listen) und Bündel globaler Konstanten — beides '
             'Kandidaten für eine Klasse bzw. eine Kontext-Klasse.')
    abhilfe = ('Veraenderlichen Zustand in die Klasse verschieben, die ihn '
               'benutzt (als Attribut, nicht als Klassenvariable, sonst teilen '
               'sich alle Instanzen denselben). Konstanten-Bündel in eine '
               'Kontext- oder Konfigurationsklasse mit sprechenden Namen.')
    befund = ('Modulweiter Zustand ueberlebt den Aufruf und gehört niemandem: '
              'Im Testlauf trägt die zweite Prüfung noch, was die erste '
              'hineingeschrieben hat, und in einem Server-Prozess teilen sich '
              'alle Anfragen denselben Wert.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen globalen Namen je Datei melden?', '4')

    #: Namen, die auf Modulebene stehen MUESSEN oder dort Vertrag sind.
    ERLAUBT = frozenset({
        'urlpatterns', 'app_name', 'admin', 'register', 'router',
        'logger', 'log', 'application', 'default_app_config',
        'handler400', 'handler403', 'handler404', 'handler500',
        # Channels sucht diesen Namen auf Modulebene von `routing.py` —
        # genau wie Django `urlpatterns`. Ein Pflichtname des Rahmenwerks
        # ist nie ein Befund (29.08.2026, 3DTools).
        'websocket_urlpatterns',
    })

    #: Dateien, deren Modulebene die Datenstruktur IST.
    DATEIEN_AUS = ('settings.py', 'conf.py', 'urls.py', 'kriterien.py',
                   'apps.py', 'wsgi.py', 'asgi.py', 'manage.py', '__init__.py')

    #: Ordner, in denen JEDE Datei die Datenstruktur ist. Wer seine
    #: Einstellungen aufteilt (`ui/settings/pfade.py`, `…/protokoll.py`),
    #: bekommt sonst genau dafuer einen Befund — obwohl er der Regel „eine
    #: Datei, ein Thema" gefolgt ist (29.08.2026, 3DTools).
    ORDNER_AUS = ('settings', 'conf', 'einstellungen')

    #: Aufrufe, deren Ergebnis eine Typdefinition ist, kein Zustand.
    TYP_AUFRUFE = frozenset({'namedtuple', 'NamedTuple', 'TypeVar', 'Enum',
                             'IntEnum', 'StrEnum', 'dataclass', 'NewType'})

    anlassfall = Anlassfall(
        {"speicher.py": (
            "_cache = {}\n"
            "_zaehler = 0\n"
            "_geladen = []\n"
            "GRENZE = 5\n"
            "TITEL = 'x'\n"
            "NAME = 'y'\n\n\n"
            "def merken(schluessel, wert):\n"
            "    global _zaehler\n"
            "    _zaehler += 1\n"
            "    _cache[schlüssel] = wert\n")},
        mindestens=1, erwartet_in="speicher.py",
        warum="Drei veraenderliche Modulvariablen, davon eine per `global` "
              "beschrieben: Der Zwischenspeicher ueberlebt jeden Aufruf und "
              "gehört keiner Klasse")

    def pruefen(self, ab='4', **_argumente):
        try:
            grenze = max(1, int(str(ab).strip() or 4))
        except ValueError:
            grenze = 4

        sichten, skripte = [], 0
        for datei in self.projektdateien('.py'):
            if (datei.name in self.DATEIEN_AUS
                    or datei.parent.name in self.ORDNER_AUS):
                continue
            sicht = self._modul(datei)
            if sicht is None:
                continue
            if sicht.ist_skript:
                skripte += 1
                continue
            sichten.append(sicht)

        befunde = []
        for sicht in sorted(sichten, key=lambda s: -s.gewicht):
            gesamt = len(sicht.veraenderlich) + len(sicht.konstanten)
            # Geschriebener Zustand ist IMMER ein Befund - auch bei einem
            # einzigen Namen. Die Grenze gilt nur fuer die MENGE an
            # Konstanten.
            #
            # SEIT DEM 29.08.2026 GILT DAS AUCH FUER `veraenderlich`: Vorher
            # hiess so jede kleingeschriebene Modulzuweisung, auch eine
            # Django-Ansicht — die Grenze hat den Bericht vor dieser Menge
            # geschuetzt. Jetzt steht dort nur noch, was wirklich ein
            # veraenderlicher Behaelter ist, und EIN `_cache = {}` ist der
            # Fund, um den es geht.
            if (not sicht.global_stellen and not sicht.veraenderlich
                    and gesamt < grenze):
                continue
            befunde.append(Befund(sicht.pfad, self._kopf(sicht),
                                  self._rat(sicht),
                                  Befund.WARNUNG if sicht.global_stellen
                                  else Befund.HINWEIS))

        kopf = [
            '%d Module geprüft, %d mit globalem Zustand' % (len(sichten),
                                                             len(befunde)),
            '%d veraenderliche Modulvariablen, %d davon per "global" beschrieben'
            % (sum(len(s.veraenderlich) for s in sichten),
               sum(len(s.global_stellen) for s in sichten)),
            '%d globale Konstanten' % sum(len(s.konstanten) for s in sichten),
            '%d Ablaufskripte übersprungen (dort IST die Modulebene das Programm)'
            % skripte,
        ]
        return Befundsatz(self.titel, kopf, befunde)

    # ---------------------------------------------------------------- Ausgabe
    @staticmethod
    def _kopf(sicht):
        teile = []
        if sicht.global_stellen:
            teile.append('%d× "global" (%s)'
                         % (len(sicht.global_stellen),
                            ', '.join(n for n, _z in sicht.global_stellen[:4])))
        if sicht.veraenderlich:
            teile.append('%d veränderlich (%s)'
                         % (len(sicht.veraenderlich),
                            ', '.join(n for n, _z, _a in sicht.veraenderlich[:4])))
        if sicht.konstanten:
            teile.append('%d Konstanten' % len(sicht.konstanten))
        return ' · '.join(teile)

    @staticmethod
    def _rat(sicht):
        u"""Der konkrete nächste Schritt - je nachdem, was gefunden wurde."""
        if sicht.global_stellen:
            return ('Wird beschrieben: in eine Klasse als Instanz-Attribut. '
                    'Als Klassenvariable teilen sich alle Instanzen denselben '
                    'Wert - dasselbe Problem, nur weniger sichtbar.')
        if sicht.veraenderlich:
            return ('Veraenderlicher Zustand ohne Eigentuemer: in die Klasse, '
                    'die ihn benutzt. Gibt es sie noch nicht, ist sie der '
                    'eigentliche Befund.')
        return ('Konstanten-Bündel: in eine Kontext- oder Konfigurationsklasse '
                '(%d Namen). Dann steht an einer Stelle, was zusammengehoert.'
                % len(sicht.konstanten))

    # ------------------------------------------------------------------ Baum
    def _modul(self, datei):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return None
        veraenderlich, konstanten, klassen = [], [], 0
        # ``global x`` steht IN Funktionen - dafuer der ganze Baum. Wird
        # frueher gebraucht als frueher: Es entscheidet mit darueber, ob eine
        # kleingeschriebene Zuweisung Zustand ist.
        global_stellen = [(name, knoten.lineno)
                          for knoten in ast.walk(baum)
                          if isinstance(knoten, ast.Global)
                          for name in knoten.names]
        geschrieben = {name for name, _z in global_stellen}
        mehrfach = self._mehrfach_zugewiesen(baum)
        for knoten in baum.body:              # NUR Modulebene, nicht ast.walk
            if isinstance(knoten, ast.ClassDef):
                klassen += 1
                continue
            if not isinstance(knoten, (ast.Assign, ast.AnnAssign)):
                continue
            for name in self._namen(knoten):
                if self._ueberspringen(name, knoten):
                    continue
                if name.isupper():
                    konstanten.append((name, knoten.lineno))
                elif (self._ist_behaelter(knoten) or name in geschrieben
                      or name in mehrfach):
                    veraenderlich.append((name, knoten.lineno,
                                          self._art(knoten)))
                # Sonst: eine DEFINITION, kein Zustand. Siehe
                # `_ist_behaelter`.
        if not (veraenderlich or konstanten or global_stellen):
            return None
        return Modulzustaende(self.kurz(datei), veraenderlich, konstanten,
                              global_stellen, klassen, self._ist_skript(baum))

    #: Aufrufe, die einen veraenderlichen Behaelter liefern.
    BEHAELTERRUFE = frozenset({'dict', 'list', 'set', 'defaultdict',
                               'OrderedDict', 'deque', 'Counter'})

    @classmethod
    def _ist_behaelter(cls, knoten):
        u"""Haelt diese Zuweisung etwas, das man SPAETER aendern kann?

        WARUM DIE UNTERSCHEIDUNG (29.08.2026, 3DTools): Bis hierher galt jede
        kleingeschriebene Zuweisung auf Modulebene als „veraenderlicher
        Zustand". In `core/api/seiten.py` stehen so dreizehn Django-Ansichten:

            character_viewer = Vorlagenseite.ansicht('character_viewer.html', …)

        Das ist eine DEFINITION — dasselbe wie ein `def`, nur aus einer
        Fabrikmethode. Niemand schreibt sie, niemand veraendert sie, `urls.py`
        liest sie einmal. Sie zu melden heisst, dem Leser dreizehn Zeilen
        anzubieten, an denen nichts zu tun ist; der echte Fund daneben
        (`_cache = {}`) geht darin unter.

        `x = 0` bleibt uebrigens draussen: Eine Zahl laesst sich nicht
        veraendern, nur NEU ZUWEISEN — und dafuer braucht es `global` oder eine
        zweite Zuweisung. Beides wird getrennt geprueft.
        """
        wert = knoten.value
        if isinstance(wert, (ast.Dict, ast.List, ast.Set, ast.DictComp,
                             ast.ListComp, ast.SetComp)):
            return True
        if isinstance(wert, ast.Call):
            gerufen = wert.func
            name = (gerufen.attr if isinstance(gerufen, ast.Attribute)
                    else getattr(gerufen, 'id', ''))
            return name in cls.BEHAELTERRUFE
        return False

    @staticmethod
    def _mehrfach_zugewiesen(baum):
        """Namen, die auf Modulebene mehr als einmal zugewiesen werden."""
        gesehen, mehrfach = set(), set()
        for knoten in baum.body:
            if not isinstance(knoten, (ast.Assign, ast.AnnAssign)):
                continue
            ziele = (knoten.targets if isinstance(knoten, ast.Assign)
                     else [knoten.target])
            for ziel in ziele:
                if not isinstance(ziel, ast.Name):
                    continue
                if ziel.id in gesehen:
                    mehrfach.add(ziel.id)
                gesehen.add(ziel.id)
        return mehrfach

    @staticmethod
    def _ist_skript(baum):
        u"""Laeuft die Datei, statt importiert zu werden? Am CODE erkannt.

        Ein Ablaufskript hat ausfuehrbare Anweisungen auf Modulebene: Aufrufe,
        Schleifen, Bedingungen ausserhalb eines ``__main__``-Blocks. Ein Modul,
        das nur definiert und importiert wird, hat davon keine.

        Docstrings zaehlen NICHT (``ast.Expr`` mit Konstante) - sonst waere
        jedes dokumentierte Modul ein Skript.
        """
        laufend = 0
        for knoten in baum.body:
            if isinstance(knoten, (ast.For, ast.While, ast.With, ast.Try)):
                laufend += 1
            elif isinstance(knoten, ast.Expr):
                if not isinstance(knoten.value, ast.Constant):
                    laufend += 1
            elif isinstance(knoten, ast.If):
                # ``if __name__ == "__main__":`` ist die saubere Form und macht
                # die Datei nicht zum Skript im hiesigen Sinn - der Zustand
                # DARUEBER gehoert trotzdem geprueft.
                pruefung = ast.dump(knoten.test)
                if '__name__' not in pruefung:
                    laufend += 1
        return laufend >= 3

    @staticmethod
    def _namen(knoten):
        if isinstance(knoten, ast.AnnAssign):
            return [knoten.target.id] if isinstance(knoten.target, ast.Name) else []
        namen = []
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name):
                namen.append(ziel.id)
            elif isinstance(ziel, (ast.Tuple, ast.List)):
                namen += [e.id for e in ziel.elts if isinstance(e, ast.Name)]
        return namen

    def _ueberspringen(self, name, knoten):
        u"""Fehlalarme aussortieren - die teuerste Sorte Befund.

        AM ECHTEN PROJEKT NACHGESCHAERFT (19.08.2026, shortlongx): Der erste
        Wurf meldete 302 veraenderliche Modulvariablen. Zwei Sorten davon waren
        keine, und beide haetten die echten Befunde verdeckt:

        * ``_`` und ``__`` aus Tupel-Entpackung (``a, _ = f()``) - das ist die
          Wegwerf-Variable, kein Zustand. Sie stand in ``analyze_winners.py``
          unter den ersten vier gemeldeten Namen.
        * **Alias-Zuweisungen** wie ``_de_pct = StrategieRahmen.prozent_de``.
          Das ist ein zweiter Name fuer dieselbe Funktion - der Ersatz fuer
          einen Import, nicht ein Zustand. In ``views/basis.py`` waren die
          ersten drei gemeldeten "Variablen" genau das.
        """
        if name.startswith('__') or name in self.ERLAUBT:
            return True
        if set(name) == {'_'}:                # ``_``, ``__``: Wegwerf-Name
            return True
        wert = getattr(knoten, 'value', None)
        # Alias auf eine Funktion/Klasse (``x = Y.z``, ``x = y``): ein zweiter
        # Name, kein Zustand. Grossgeschriebene Ziele bleiben Konstanten.
        if isinstance(wert, (ast.Attribute, ast.Name)) and not name.isupper():
            return True
        # Alias auf eine Funktion/Klasse (``x = Y.z``, ``x = y``): ein zweiter
        # Name, kein Zustand. Grossgeschriebene Ziele bleiben Konstanten.
        # Typdefinitionen sind kein Zustand.
        if isinstance(wert, ast.Call):
            ruf = wert.func
            gerufen = (ruf.id if isinstance(ruf, ast.Name)
                       else getattr(ruf, 'attr', ''))
            if gerufen in self.TYP_AUFRUFE:
                return True
            # ``logging.getLogger(__name__)`` - die kanonische Zeile.
            if gerufen == 'getLogger':
                return True
        # Reine Typ-Annotation ohne Wert (``x: int``) ist eine Deklaration.
        if isinstance(knoten, ast.AnnAssign) and knoten.value is None:
            return True
        return False

    @staticmethod
    def _art(knoten):
        wert = getattr(knoten, 'value', None)
        if isinstance(wert, ast.Dict):
            return 'dict'
        if isinstance(wert, ast.List):
            return 'list'
        if isinstance(wert, ast.Set):
            return 'set'
        if isinstance(wert, ast.Call):
            return 'Aufruf'
        return 'Wert'
