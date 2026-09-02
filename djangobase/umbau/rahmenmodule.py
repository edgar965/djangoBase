# -*- coding: utf-8 -*-
u"""Rahmenmodule: Dateien, deren ``__all__`` erst zur Laufzeit entsteht.

DER ANLASS (Edgar, 02.09.2026: „warum sind noch Funde da?")
===========================================================
Nach allen Reparaturen meldete der Language Server über shortlongx immer noch
1.738 Befunde — bei einem Programm, das läuft. Die Aufschlüsselung::

    514  reportUndefinedVariable   30 %
    727  Typmeldungen (12 Regeln)  42 %
    365  reportUnusedImport        21 %

Der grösste Einzelposten war kein Fehler. Ein Projekt kann seine Namen über
ein Sammelmodul weiterreichen::

    # dashboard/views/basis_datensatz.py  — der RAHMEN
    from .basis import *
    ...
    __all__ = [_n for _n in list(globals()) if not _n.startswith("__")]

    # dashboard/views/dax_handel.py       — der KONSUMENT
    from .basis_datensatz import *
    def seite(request):
        return _render(request, ...)      # ← woher kommt _render?

Zur Laufzeit ist das richtig; für einen Typprüfer ist es unauflösbar. Er sieht
ein ``__all__``, das aus ``globals()`` entsteht, kann es nicht auswerten und
meldet danach **jeden** durchgereichten Namen im Konsumenten als „nicht
definiert". Gemessen: von 119 verschiedenen so gemeldeten Namen existierten
**115 im Projekt** (486 der 514 Meldungen). Die vier übrigen waren
Alias-Importe (``import x as _zb``) — auch sie kein Fehler.

WAS DIESES MODUL TUT
====================
Es beantwortet zwei Fragen am Quelltext, nicht an einer Namensliste:

* Ist diese Datei ein **Rahmen**? (``__all__`` entsteht aus einem Ausdruck
  statt aus einer Liste von Zeichenketten.)
* Ist diese Datei ein **Konsument**? (Sie holt sich per ``import *`` etwas aus
  einem Rahmen.)

Daraus folgt, welche Meldung nichts über den Code aussagt:

===============================  ==========================================
in einem Rahmen                  ``reportUnsupportedDunderAll`` — genau die
                                 Konstruktion, um die es geht
in einem Rahmen                  ``reportUnusedImport`` — der Import IST die
                                 Weitergabe; „unbenutzt" ist hier der Zweck
in einem Konsumenten             ``reportUndefinedVariable`` — der Name kommt
                                 aus dem Stern-Import
===============================  ==========================================

Alles andere bleibt sichtbar, auch in diesen Dateien. Ein Tippfehler in einem
Konsumenten fällt damit nicht mehr auf — das ist der Preis, und er steht so
auf der Seite: die Kennzahl ``stumm`` nennt die Zahl, das Häkchen schaltet es
ab. Ohne den Filter verdecken 500 Fehlalarme die echten Befunde; das ist der
teurere Preis (dieselbe Abwägung wie bei ``TS2339`` in ``ls_konfig``).

WARUM AM QUELLTEXT UND NICHT IM LAUF
====================================
Die Erkennung könnte im Lauf passieren und im Ergebnis liegen. Dann wirkte
das Häkchen aber erst nach einer Neurechnung (70 s auf shortlongx), und jedes
gespeicherte Ergebnis wäre blind. Stattdessen wird hier gelesen — und nur die
Dateien, die überhaupt einen Befund haben. Auf shortlongx sind das rund 300
von 1.271, mit Regex-Vorfilter unter einer Zehntelsekunde.

Django-frei; ohne diese Datei ändert sich nichts (der Filter ist abschaltbar).
"""
import ast
import re
from pathlib import Path

__all__ = ["Rahmenmodule", "RAHMEN_REGELN", "KONSUMENT_REGELN"]

#: Meldungen, die IN einem Rahmenmodul nichts über den Code sagen.
RAHMEN_REGELN = ("reportUnsupportedDunderAll", "reportUnusedImport")

#: Meldungen, die in einem Stern-Importeur nichts über den Code sagen.
KONSUMENT_REGELN = ("reportUndefinedVariable",)

#: Vorfilter: nur Dateien mit einem dieser Wörter werden überhaupt geparst.
VORFILTER = re.compile(r"__all__|import\s+\*")


class Rahmenmodule:
    u"""Erkennt Rahmen und ihre Stern-Importeure — je Projektwurzel gemerkt."""

    #: ``pfad -> (mtime, groesse, (dynamisch, ziele))``. Ein Lauf fragt jede
    #: Datei mehrfach (``roh()`` steckt in vier Sichten), und zwischen zwei
    #: Seitenaufrufen ändert sich am Quelltext meist nichts.
    _gelesen = {}

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        self._rahmen = set()
        self._konsumenten = set()
        self._geprueft = set()

    # ── Abfrage ──────────────────────────────────────────────────────────
    def einlesen(self, dateien):
        u"""Die Dateien mit Befund ansehen — und die Ziele ihrer Stern-Importe.

        Zwei Runden, weil ein Rahmen selbst keinen Befund haben muss: Erst die
        gemeldeten Dateien, dann die Module, aus denen sie per ``*`` holen."""
        offen = []
        for rel in dateien:
            if rel in self._geprueft or not rel.endswith(".py"):
                continue
            self._geprueft.add(rel)
            dynamisch, ziele = self._ansehen(self.wurzel / rel)
            if dynamisch:
                self._rahmen.add(rel)
            offen.append((rel, ziele))
        # Runde zwei: die Ziele auflösen und fragen, ob sie Rahmen sind.
        for rel, ziele in offen:
            for ziel in ziele:
                if self._ist_rahmen(ziel):
                    self._konsumenten.add(rel)
                    break
        return self

    def rahmen(self):
        return self._rahmen

    def konsumenten(self):
        return self._konsumenten

    def stumm(self, befund):
        u"""Sagt dieser Befund etwas über den Code — oder über die Konstruktion?"""
        datei, regel = befund.get("datei", ""), befund.get("regel", "")
        if regel in RAHMEN_REGELN and datei in self._rahmen:
            return True
        return regel in KONSUMENT_REGELN and datei in self._konsumenten

    # ── Quelltext ────────────────────────────────────────────────────────
    def _ist_rahmen(self, pfad):
        u"""Ein Ziel eines Stern-Imports — hat es ein Laufzeit-``__all__``?"""
        if pfad is None:
            return False
        rel = self._relativ(pfad)
        if rel is not None and rel in self._geprueft:
            return rel in self._rahmen
        dynamisch, _ziele = self._ansehen(pfad)
        if rel is not None:
            self._geprueft.add(rel)
            if dynamisch:
                self._rahmen.add(rel)
        return dynamisch

    def _ansehen(self, pfad):
        u"""``(dynamisches __all__, [Ziele der Stern-Importe])`` — mit Merker."""
        try:
            stat = pfad.stat()
        except OSError:
            return False, []
        merker = self._gelesen.get(str(pfad))
        if merker and merker[0] == stat.st_mtime and merker[1] == stat.st_size:
            return merker[2]
        try:
            baum = ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            antwort = (False, [])
        else:
            antwort = (self._dynamisch(baum), self._sternziele(baum, pfad))
        self._gelesen[str(pfad)] = (stat.st_mtime, stat.st_size, antwort)
        return antwort

    @staticmethod
    def _dynamisch(baum):
        u"""``__all__`` aus einem Ausdruck statt aus Zeichenketten-Literalen.

        ``__all__ = ["a", "b"]`` ist statisch — pyright liest es und meldet
        danach zu Recht. ``__all__ = [_n for _n in globals()]``, ``__all__ =
        sorted(...)`` oder ``__all__ += basis.__all__`` sind es nicht."""
        for knoten in baum.body:
            ziele, wert = [], None
            if isinstance(knoten, ast.Assign):
                ziele, wert = knoten.targets, knoten.value
            elif isinstance(knoten, ast.AugAssign):
                ziele, wert = [knoten.target], knoten.value
            if not any(isinstance(z, ast.Name) and z.id == "__all__" for z in ziele):
                continue
            if not isinstance(wert, (ast.List, ast.Tuple)):
                return True
            if not all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                       for e in wert.elts):
                return True
        return False

    def _sternziele(self, baum, pfad):
        u"""Die Dateien, aus denen diese Datei per ``from … import *`` holt."""
        raus = []
        for knoten in baum.body:
            if not isinstance(knoten, ast.ImportFrom):
                continue
            if not any(a.name == "*" for a in knoten.names):
                continue
            ziel = self._aufloesen(knoten, pfad)
            if ziel is not None:
                raus.append(ziel)
        return raus

    def _aufloesen(self, knoten, pfad):
        u"""``from .x import *`` → Datei. Relativ sicher, absolut nach Versuch.

        Ein absoluter Import (``from dashboard.views.basis import *``) hängt an
        ``sys.path``, den dieses Modul nicht kennt. Probiert werden die Wurzel
        und ihre Hauptäste; findet sich nichts, gilt das Ziel als unbekannt und
        es wird NICHTS stummgeschaltet — lieber ein Fehlalarm zuviel als eine
        verschluckte Meldung."""
        modul = knoten.module or ""
        if knoten.level:
            basis = pfad.parent
            for _ in range(knoten.level - 1):
                basis = basis.parent
            kandidaten = [basis]
        else:
            kandidaten = [self.wurzel] + self._hauptaeste()
        if not modul:
            return None
        teil = modul.replace(".", "/")
        for basis in kandidaten:
            for ziel in (basis / (teil + ".py"), basis / teil / "__init__.py"):
                if ziel.is_file():
                    return ziel
        return None

    def _hauptaeste(self):
        u"""Die Verzeichnisse direkt unter der Wurzel — mögliche Import-Wurzeln."""
        if not hasattr(self, "_aeste"):
            try:
                self._aeste = [p for p in self.wurzel.iterdir()
                               if p.is_dir() and not p.name.startswith(".")]
            except OSError:
                self._aeste = []
        return self._aeste

    def _relativ(self, pfad):
        try:
            return str(pfad.relative_to(self.wurzel)).replace("\\", "/")
        except ValueError:
            return None
