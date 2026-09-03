# -*- coding: utf-8 -*-
u"""ModulIndex - welcher Punktname gehoert zu welcher Datei, und was steht drin.

Hilfsklasse, kein Werkzeug: :class:`ImportZiele` braucht sie, um ``from x.y
import z`` zu beurteilen, ohne ``x.y`` zu importieren.

WARUM NICHT IMPORTIEREN
=======================
In shortlongx rufen die Werkzeuge ``django.setup()`` auf, und 18 der 25 Dateien
in ``depot/`` rechnen schon beim Import. Ein Pruefwerkzeug, das importiert,
startet Rechenlaeufe auf dem Rechner des Nutzers - und in einem fremden Projekt
weiss es nicht einmal, was es damit anstoesst.

Deshalb rein statisch ueber den Syntaxbaum. Das kostet Genauigkeit an genau drei
Stellen, und die sind benannt statt verschwiegen (:meth:`undurchsichtig`): Wo
der Index nicht sicher urteilen kann, schweigt er und zaehlt den Fall.

WO EIN PUNKTNAME BEGINNT
========================
An der Projektwurzel - und zusaetzlich in jedem Verzeichnis mit ``manage.py``.
Django importiert von dort (``dashboard.views…``), waehrend Nachbarpakete an
der Wurzel haengen (``brain``, ``depot``). Beide Formen kommen in denselben
Projekten vor, deshalb kennt der Index beide.

Reine stdlib.
"""
import ast

__all__ = ["ModulIndex"]


class ModulIndex:
    u"""Punktname -> Quelldatei, und die Namen, die eine Datei auf Modulebene setzt."""

    def __init__(self, dateien, wurzel=None):
        #: ``Quelldatei``-Objekte (``.name`` relativ mit ``/``, ``.baum``).
        self.dateien = list(dateien)
        self.wurzel = wurzel
        self._je_name = None
        self._namen = {}
        self._undurchsichtig = {}

    # ------------------------------------------------------------------ Karte
    @property
    def startpunkte(self):
        u"""Verzeichnisse, unter denen ein Punktname beginnen kann.

        ``""`` ist die Projektwurzel; dazu jedes Verzeichnis mit ``manage.py``
        (``shortlongxWeb``, ``djangoCode``, ``NoiseSpy``, …)."""
        aus = [""]
        for d in self.dateien:
            teile = d.name.split("/")
            if len(teile) == 2 and teile[1] == "manage.py":
                aus.append(teile[0])
        return aus

    @property
    def je_name(self):
        u"""``{"brain.dax_filter": Quelldatei}`` - ein Paket unter seinem Namen."""
        if self._je_name is not None:
            return self._je_name
        starts = self.startpunkte
        karte = {}
        for d in self.dateien:
            if not d.name.endswith(".py"):
                continue
            for start in starts:
                teile = d.name.split("/")
                if start:
                    if teile[0] != start:
                        continue
                    teile = teile[1:]
                elif teile[0] in starts[1:]:
                    # Unter einem Django-Verzeichnis zaehlt nur der kurze Name:
                    # ``dashboard.views``, nicht ``shortlongxWeb.dashboard.views``.
                    continue
                if not teile:
                    continue
                if teile[-1] == "__init__.py":
                    teile = teile[:-1]          # das Paket selbst
                else:
                    teile[-1] = teile[-1][:-3]  # ".py" ab
                if teile:
                    karte.setdefault(".".join(teile), d)
        self._je_name = karte
        return karte

    def datei(self, punktname):
        u"""Die Quelldatei zu einem Punktnamen - oder ``None`` (fremdes Paket)."""
        return self.je_name.get(punktname)

    def ist_paketteil(self, punktname, name):
        u"""Ist ``name`` ein Untermodul von ``punktname``?

        ``from depot.IB import konto`` holt kein Attribut, sondern eine Datei.
        Ohne diese Frage meldet die Pruefung jedes Submodul als fehlend."""
        return ("%s.%s" % (punktname, name)) in self.je_name

    # ------------------------------------------------- Namen einer Modul-Datei
    def namen(self, datei):
        u"""Alle Namen, die diese Datei auf Modulebene setzt.

        Gesucht wird im Modul-Namensraum, nicht nur in ``body``: Ein Name kann
        in ``try/except ImportError`` oder unter ``if TYPE_CHECKING`` entstehen
        und ist dann trotzdem da."""
        if datei.name in self._namen:
            return self._namen[datei.name]
        aus = set()
        if datei.baum is not None:
            for k in self._modulebene(datei.baum):
                aus |= self._gesetzt(k)
        self._namen[datei.name] = aus
        return aus

    @staticmethod
    def _modulebene(baum):
        u"""Knoten im Modul-Namensraum - durch ``if``/``try``/``with`` hindurch,
        aber NICHT in Funktionen und Klassen (deren Namen bleiben drinnen)."""
        eigener_raum = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        offen, aus = list(baum.body), []
        while offen:
            k = offen.pop()
            aus.append(k)
            if isinstance(k, eigener_raum):
                continue
            for feld in ("body", "orelse", "finalbody"):
                offen.extend(getattr(k, feld, None) or [])
            for h in getattr(k, "handlers", None) or []:
                offen.extend(h.body)
        return aus

    def _gesetzt(self, k):
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return {k.name}
        if isinstance(k, ast.Assign):
            aus = set()
            for z in k.targets:
                aus |= self._ziele(z)
            return aus
        if isinstance(k, (ast.AnnAssign, ast.AugAssign)):
            return self._ziele(k.target)
        if isinstance(k, ast.Import):
            # ``import a.b`` bindet ``a``; ``import a.b as c`` bindet ``c``.
            return {(a.asname or a.name.split(".")[0]) for a in k.names}
        if isinstance(k, ast.ImportFrom):
            return {(a.asname or a.name) for a in k.names if a.name != "*"}
        return set()

    def _ziele(self, knoten):
        u"""Die Namen, die ein Zuweisungsziel bindet.

        ``LONG, SHORT = 1, -1`` bindet ZWEI Namen - das Ziel ist ein ``Tuple``,
        kein ``Name``. Die erste Fassung sah nur ``Name`` und meldete deshalb
        neun Importe als „zeigt ins Leere", die alle in Ordnung waren."""
        if isinstance(knoten, ast.Name):
            return {knoten.id}
        if isinstance(knoten, (ast.Tuple, ast.List)):
            aus = set()
            for e in knoten.elts:
                aus |= self._ziele(e)
            return aus
        if isinstance(knoten, ast.Starred):
            return self._ziele(knoten.value)
        return set()                       # x.y = … / x[0] = … binden nichts

    # --------------------------------------------------------- die drei Luecken
    def undurchsichtig(self, datei):
        u"""Warum diese Datei statisch NICHT beurteilbar ist - oder ``None``.

        Wer hier auf ``None`` prueft, meldet nur, was er wirklich weiss:

        * ``from x import *`` - der Name kann von dort stammen.
        * ``__getattr__`` auf Modulebene (PEP 562) - das Modul erfindet Namen.
        * ``globals()``-Schreibzugriff - dasselbe zur Ladezeit.
        """
        if datei.name in self._undurchsichtig:
            return self._undurchsichtig[datei.name]
        grund = self._undurchsichtig[datei.name] = self._luecke(datei)
        return grund

    @staticmethod
    def _luecke(datei):
        if datei.baum is None:
            return u"nicht lesbar"
        for k in ast.walk(datei.baum):
            if isinstance(k, ast.ImportFrom) and any(a.name == "*"
                                                     for a in k.names):
                return u"benutzt from … import *"
            if (isinstance(k, ast.FunctionDef) and k.name == "__getattr__"
                    and k in datei.baum.body):
                return u"hat ein Modul-__getattr__"
            if (isinstance(k, ast.Call) and isinstance(k.func, ast.Name)
                    and k.func.id == "globals"):
                return u"schreibt über globals()"
        return None

    # --------------------------------------------------------------- Aufloesung
    def ziel(self, datei, knoten):
        u"""Der Punktname, den ``from … import`` dieses Knotens meint.

        Loest relative Importe (``from .befund import Befund``) ueber den Pfad
        der importierenden Datei auf. ``None``, wenn er nicht aufloesbar ist."""
        if not knoten.level:
            return knoten.module
        teile = datei.name.split("/")[:-1]      # das Verzeichnis der Datei
        if knoten.level > 1:
            hoch = knoten.level - 1
            if hoch > len(teile):
                return None
            teile = teile[:len(teile) - hoch]
        starts = self.startpunkte[1:]
        if teile and teile[0] in starts:
            teile = teile[1:]
        if not teile:
            return None
        return ".".join(teile + ([knoten.module] if knoten.module else []))
