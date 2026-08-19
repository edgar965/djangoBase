# -*- coding: utf-8 -*-
u"""Klassenkandidat — freie Funktionen, die sich denselben Zustand teilen.

AUFTRAG (Edgar, 19.08.2026, Kriterium 18): „Moeglichst in Klassen unterbringen,
ggf. in Utility-Klassen, statische Funktionen, Klassen verwenden."

DER BEFUND, DEN DIE BEIDEN ANDEREN WERKZEUGE NICHT SEHEN
========================================================
``FreieFunktionen`` zaehlt Funktionen auf Modulebene. ``GlobalerZustand`` zaehlt
Variablen auf Modulebene. Beide melden Mengen — und eine Menge ist noch kein
Umbauauftrag.

Der eigentliche Befund entsteht erst aus BEIDEM zusammen: Greifen mehrere freie
Funktionen auf DIESELBE Modulvariable zu, dann ist das eine Klasse, die noch
niemand geschrieben hat. Die Variable ist ihr Attribut, die Funktionen sind ihre
Methoden. Dieses Werkzeug nennt beides beim Namen und schlaegt den Schnitt vor.

UND DIE UMKEHRUNG: UTILITY STATT ZUSTAND
========================================
Funktionen, die KEINEN gemeinsamen Zustand anfassen, aber denselben
Namensanfang tragen, gehoeren in eine Utility-Klasse mit ``@staticmethod`` —
nicht in eine Klasse mit ``__init__``. Eine Klasse ohne Zustand, die man
instanziieren muss, ist eine Funktionssammlung mit Umweg. Beide Faelle werden
getrennt gemeldet, weil sie zu verschiedenen Umbauten fuehren.
"""

import ast
from collections import defaultdict

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class Kandidat:
    u"""Ein Umbauvorschlag: diese Funktionen, dieser Zustand, diese Klasse."""

    __slots__ = ('pfad', 'zustand', 'funktionen', 'schreibend', 'sorte')

    def __init__(self, pfad, zustand, funktionen, schreibend, sorte='klasse'):
        self.pfad = pfad
        #: ``'klasse'`` = hier fehlt eine Klasse (nackter Container).
        #: ``'kontext'`` = eine Instanz liegt frei herum; sie gehoert in die
        #: Kontext-Klasse des Moduls, nicht in eine neue eigene.
        self.sorte = sorte
        #: Der geteilte Name auf Modulebene.
        self.zustand = zustand
        #: [name] der Funktionen, die ihn lesen oder schreiben.
        self.funktionen = funktionen
        #: [name] der Funktionen, die ihn SCHREIBEN (per ``global``).
        self.schreibend = schreibend

    #: Namen, die als Klassenvorschlag mit etwas Bekanntem kollidieren wuerden.
    #: ``_thread`` ergaebe sonst „Klasse Thread" - und ``threading.Thread`` gibt
    #: es schon (gemessen an ``autotrade_runner.py``, 19.08.2026).
    BESETZT = frozenset({'Thread', 'Lock', 'Queue', 'Event', 'Timer', 'Process',
                         'Pool', 'Session', 'Client', 'Logger', 'Cache', 'Path',
                         'Dict', 'List', 'Set', 'Type', 'Object', 'State'})

    @property
    def vorschlag(self):
        u"""Ein Klassenname aus dem Zustandsnamen - Startpunkt, nicht Vorgabe."""
        rein = self.zustand.strip('_').replace('_', ' ').title().replace(' ', '')
        if not rein:
            return 'Zustand'
        # Kollidiert der Name mit einem bekannten Typ, bekommt er den Modulnamen
        # davor: aus „Thread" wird „AutotradeRunnerThread". Ein Vorschlag, der
        # eine Namenskollision baut, wird nicht uebernommen - und dann bleibt
        # der Befund liegen.
        if rein in self.BESETZT:
            stamm = self.pfad.replace('\\', '/').rsplit('/', 1)[-1]
            stamm = stamm.removesuffix('.py').replace('_', ' ').title().replace(' ', '')
            return stamm + rein
        return rein


class Klassenkandidat(BefundWerkzeug):

    slug = 'klassen-kandidat'
    kriterium = 18
    titel = 'Klassen-Kandidaten aus geteiltem Zustand'
    zweck = ('Findet freie Funktionen, die sich dieselbe Modulvariable teilen — '
             'das ist eine Klasse, die noch niemand geschrieben hat. Und '
             'getrennt davon: Funktionsbuendel ohne Zustand, die in eine '
             'Utility-Klasse mit statischen Methoden gehoeren.')
    abhilfe = ('Geteilter Zustand → Klasse: die Variable wird zum Attribut, die '
               'Funktionen werden zu Methoden, das erste Argument entfaellt. '
               'Kein Zustand → Utility-Klasse mit @staticmethod, damit die '
               'Zusammengehoerigkeit im Namen steht statt im Dateinamen.')
    befund = ('Der Unterschied ist wichtig: Eine Klasse ohne Zustand, die man '
              'erst instanziieren muss, ist eine Funktionssammlung mit Umweg — '
              'sie sieht objektorientiert aus und ist es nicht.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen Funktionen je geteiltem Namen melden?', '2')

    #: Nackte Container und Primitive: Hier FEHLT eine Klasse.
    #:
    #: WARUM DIE UNTERSCHEIDUNG (Edgar, 19.08.2026: „warum logger als
    #: Klassenkandidat, ist das nicht schon eine klasse??"). Der erste Wurf
    #: meldete jede geteilte Modulvariable gleich — und schlug sechsmal eine
    #: Klasse „…Logger" vor. ``logger = logging.getLogger(__name__)`` IST aber
    #: schon ein Objekt. Da fehlt keine Klasse; da liegt eine herum.
    PRIMITIV = (ast.Dict, ast.List, ast.Set, ast.Tuple)

    #: DREI BEFUNDE, DREI UMBAUTEN (Edgar, 19.08.2026: „nutze globale Instanzen,
    #: packe die in eine globale Kontext-Klasse"):
    #:
    #: 1. **Nackter Container + Funktionen drumherum** → eine NEUE Klasse. Die
    #:    Variable wird ihr Attribut, die Funktionen ihre Methoden.
    #: 2. **Instanz auf Modulebene** (``logger``, ``_sitzung``, ``_thread``) →
    #:    keine neue Klasse, sondern in die EINE Kontext-Klasse des PROJEKTS.
    #: 3. **Funktionsbuendel ohne Zustand** → Utility-Klasse mit
    #:    ``@staticmethod``.
    #:
    #: EINE EINZIGE, NICHT EINE JE MODUL (Edgar, 19.08.2026: „Wenn du globale
    #: variablen hast, dann EINE EINZIGE Kontext Klasse die alle globalen
    #: Klasseninstanzen sammelt!"). Der Zwischenstand von heute frueh riet zu
    #: einer Kontext-Klasse *je Modul* - das ist derselbe verstreute Zustand,
    #: nur mit einem Klassennamen davor. Der Sinn entsteht erst durch die
    #: Zentralisierung: An EINER Stelle steht dann, was dieses Programm
    #: ueberhaupt an globalem Zustand hat. Wer wissen will, was ein Neustart
    #: zuruecksetzt oder was sich zwei Anfragen teilen, liest eine Datei.
    KONTEXT_NAME = 'Kontext'

    anlassfall = Anlassfall(
        {"zaehlwerk.py": (
            "_stand = {}\n\n\n"
            "def erhoehen(schluessel):\n"
            "    _stand[schluessel] = _stand.get(schluessel, 0) + 1\n\n\n"
            "def lesen(schluessel):\n"
            "    return _stand.get(schluessel, 0)\n\n\n"
            "def zuruecksetzen():\n"
            "    global _stand\n"
            "    _stand = {}\n")},
        mindestens=1, erwartet_in="zaehlwerk.py",
        warum="Drei Funktionen um EINE Modulvariable: Das ist eine Klasse "
              "'Stand' mit einem Attribut und drei Methoden")

    def pruefen(self, ab='2', **_argumente):
        try:
            grenze = max(2, int(str(ab).strip() or 2))
        except ValueError:
            grenze = 2

        kandidaten, utilities = [], []
        for datei in self.projektdateien('.py'):
            if datei.name in ('settings.py', 'urls.py', 'conf.py'):
                continue
            gefunden, util = self._modul(datei, grenze)
            kandidaten += gefunden
            utilities += util

        befunde = []
        # Zuerst die mit geschriebenem Zustand: dort ist der Umbau am dringendsten.
        for k in sorted(kandidaten, key=lambda k: (-len(k.schreibend),
                                                   -len(k.funktionen))):
            if k.sorte == 'kontext':
                befunde.append(Befund(
                    k.pfad,
                    'Kontext-Klasse: Instanz "%s" liegt frei, %d Funktionen '
                    'benutzen sie (%s)'
                    % (k.zustand, len(k.funktionen), ', '.join(k.funktionen[:5])),
                    'Sie ist bereits ein Objekt — es fehlt keine Klasse, es '
                    'fehlt ein EIGENTUEMER. In die EINE Kontext-Klasse des '
                    'Projekts (%s), nicht in eine je Modul: Erst dadurch steht '
                    'an einer Stelle, was dieses Programm an globalem Zustand '
                    'hat.' % self.KONTEXT_NAME,
                    Befund.WARNUNG if k.schreibend else Befund.HINWEIS))
                continue
            befunde.append(Befund(
                k.pfad,
                'Klasse %s: "%s" + %d Funktionen (%s)'
                % (k.vorschlag, k.zustand, len(k.funktionen),
                   ', '.join(k.funktionen[:5])),
                ('%d davon SCHREIBEN den Zustand (%s) — als Attribut einer '
                 'Instanz gaebe es das Problem nicht'
                 % (len(k.schreibend), ', '.join(k.schreibend[:3])))
                if k.schreibend else
                'Nur lesend — die Variable wird zum Attribut, die Funktionen zu '
                'Methoden.',
                Befund.WARNUNG if k.schreibend else Befund.HINWEIS))

        for pfad, anfang, namen in sorted(utilities, key=lambda u: -len(u[2])):
            befunde.append(Befund(
                pfad,
                'Utility-Klasse %s: %d Funktionen ohne gemeinsamen Zustand (%s)'
                % (anfang.title(), len(namen), ', '.join(namen[:5])),
                'Kein geteilter Zustand → Klasse mit @staticmethod, kein '
                '__init__. Sonst entsteht eine Klasse, die man nur baut, um '
                'ihre Methoden zu rufen.',
                Befund.HINWEIS))

        klassen = [k for k in kandidaten if k.sorte == 'klasse']
        kontexte = [k for k in kandidaten if k.sorte == 'kontext']
        kopf = ['%d Klassen-Kandidaten (nackter Container + Funktionen)' % len(klassen),
                '%d Kontext-Kandidaten (Instanz liegt frei auf Modulebene)' % len(kontexte),
                '%d Utility-Kandidaten ohne Zustand' % len(utilities),
                '%d Funktionen betroffen'
                % (sum(len(k.funktionen) for k in kandidaten)
                   + sum(len(u[2]) for u in utilities))]
        return Befundsatz(self.titel, kopf, befunde)

    # ------------------------------------------------------------------ Baum
    def _modul(self, datei, grenze):
        try:
            quelle = datei.read_text(encoding='utf-8', errors='replace')
            baum = ast.parse(quelle)
        except (SyntaxError, OSError):
            return [], []

        sorte_je_name = {}
        freie = []
        for knoten in baum.body:              # nur Modulebene
            if isinstance(knoten, (ast.Assign, ast.AnnAssign)):
                sorte = self._sorte(knoten)
                if sorte:
                    for n in self._zielnamen(knoten):
                        sorte_je_name[n] = sorte
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not knoten.name.startswith('__'):
                    freie.append(knoten)
        if len(freie) < grenze or not sorte_je_name:
            return [], self._utilities(datei, freie, grenze)

        # Wer fasst welchen Modulnamen an?
        modulnamen = set(sorte_je_name)
        nutzer = defaultdict(list)
        schreiber = defaultdict(list)
        for fn in freie:
            benutzt, schreibt = self._zugriffe(fn, modulnamen)
            for name in benutzt:
                nutzer[name].append(fn.name)
            for name in schreibt:
                schreiber[name].append(fn.name)

        kandidaten = []
        vergeben = set()
        for name, namen in sorted(nutzer.items(), key=lambda p: -len(p[1])):
            if len(namen) < grenze or name.isupper():
                continue                      # Konstanten sind kein Zustand
            kandidaten.append(Kandidat(self.kurz(datei), name, namen,
                                       schreiber.get(name, []),
                                       sorte_je_name.get(name, 'klasse')))
            vergeben |= set(namen)

        # Utility-Kandidaten nur aus den Funktionen, die KEINEN Zustand teilen.
        rest = [fn for fn in freie if fn.name not in vergeben]
        return kandidaten, self._utilities(datei, rest, grenze)

    def _utilities(self, datei, funktionen, grenze):
        u"""Buendel gleichen Namensanfangs OHNE geteilten Zustand."""
        nach_anfang = defaultdict(list)
        for fn in funktionen:
            teile = fn.name.strip('_').split('_')
            if len(teile) > 1:
                nach_anfang[teile[0]].append(fn.name)
        return [(self.kurz(datei), anfang, namen)
                for anfang, namen in nach_anfang.items()
                if len(namen) >= max(grenze, 3)]

    def _sorte(self, knoten):
        u"""Was liegt in diesem Modulnamen? ``'klasse'``, ``'kontext'`` oder None.

        * ``'klasse'`` - nackter Container oder Primitiv: Hier fehlt eine Klasse.
        * ``'kontext'`` - eine Instanz: Sie gehoert in die Kontext-Klasse.
        * ``None`` - ein Alias auf einen bestehenden Namen; kein Zustand.
        """
        wert = getattr(knoten, 'value', None)
        if wert is None:                      # ``x: int`` ohne Wert
            return None
        if isinstance(wert, (self.PRIMITIV, ast.Constant)):
            return 'klasse'
        if isinstance(wert, (ast.Call, ast.Lambda)):
            return 'kontext'                  # haelt bereits ein Objekt
        # ``x = y`` / ``x = Y.z``: ein zweiter Name, kein eigener Zustand.
        return None

    @staticmethod
    def _zielnamen(knoten):
        if isinstance(knoten, ast.AnnAssign):
            return ({knoten.target.id}
                    if isinstance(knoten.target, ast.Name) else set())
        namen = set()
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name):
                namen.add(ziel.id)
        return {n for n in namen if not n.startswith('__')}

    @staticmethod
    def _zugriffe(funktion, modulnamen):
        u"""(gelesen_oder_geschrieben, geschrieben) - beides nur fuer Modulnamen.

        Ein lokaler Name gleichen Namens verdeckt den globalen; deshalb zaehlen
        nur Namen, die die Funktion NICHT selbst bindet - ausser sie erklaert
        ihn ausdruecklich per ``global``."""
        global_erklaert = {name for k in ast.walk(funktion)
                           if isinstance(k, ast.Global) for name in k.names}
        lokal = set()
        for k in ast.walk(funktion):
            if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Store):
                lokal.add(k.id)
            elif isinstance(k, ast.arg):
                lokal.add(k.arg)
        lokal -= global_erklaert

        benutzt, geschrieben = set(), set()
        for k in ast.walk(funktion):
            if not isinstance(k, ast.Name) or k.id not in modulnamen:
                continue
            if k.id in lokal:
                continue
            benutzt.add(k.id)
            if isinstance(k.ctx, ast.Store) and k.id in global_erklaert:
                geschrieben.add(k.id)
        # Auch ein Aufruf wie ``_cache[x] = y`` schreibt, ohne ``global``.
        for k in ast.walk(funktion):
            if isinstance(k, ast.Subscript) and isinstance(k.value, ast.Name):
                if (k.value.id in modulnamen and k.value.id not in lokal
                        and isinstance(k.ctx, ast.Store)):
                    benutzt.add(k.value.id)
                    geschrieben.add(k.value.id)
        return benutzt, geschrieben
