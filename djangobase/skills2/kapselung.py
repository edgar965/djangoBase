# -*- coding: utf-8 -*-
u"""Kapselung - Modulfunktionen, die zusammen eine Klasse ergeben.

    Kriterium 1 des Auftrags: „Möglichst alle Funktionen kapseln in Klassen"

WAS HIER NICHT GEMELDET WIRD - und warum
========================================
„Moeglichst" ist Teil des Auftrags. Drei Sorten Modulfunktionen bleiben aussen
vor, weil eine Klasse um sie herum den Code SCHLECHTER machen wuerde:

* Django-Views und Management-Commands: Django ruft sie als Funktionen auf; eine
  Klasse daneben waere ein Mantel ohne Inhalt (dafuer gibt es Djangos eigene
  Basisklassen - das ist ein anderer Umbau).
* Einstiegspunkte ``main()``/``handle()``.
* Reine Rechenfunktionen ohne Zustand, die genau einmal gerufen werden. Eine
  Klasse mit einer Methode und ohne Felder ist eine Verkleidung.

GEMELDET WIRD DAS, WORAN MAN ES ERKENNT
=======================================
Mehrere Modulfunktionen, die DASSELBE Argument herumreichen (``cfg``, ``ts``,
``daten``). Dieses Argument ist der Zustand, den die Klasse halten wuerde - und
seine Zahl im Kopf jeder Signatur ist das Mass dafuer, wie viel Kapselung fehlt.
"""
import ast
from collections import Counter

from .werkzeug import Ergebnis, Werkzeug2


class Kapselung(Werkzeug2):
    slug = "kapselung"
    titel = "Funktionen, die eine Klasse ergeben"
    zweck = ("Dateien mit mehreren Modulfunktionen, die dasselbe Argument "
             "herumreichen — das ist der Zustand, den eine Klasse hielte.")
    befund = ("Ein Modul mit zwölf Funktionen, die alle „cfg“ und „quelle“ "
              "durchreichen: Jede Signatur wiederholt, was die Klasse einmal "
              "im Konstruktor hätte.")
    abhilfe = ("Klasse mit dem gemeinsamen Argument als Feld; die Funktionen "
               "werden Methoden. Views, Commands und Einstiegspunkte bleiben "
               "Funktionen — Django ruft sie so auf.")
    dauer = "3–8 s"
    kriterium = 1

    AB_ANZAHL = 3
    EINSTIEGE = {"main", "haupt", "run", "handle"}
    #: Argumentnamen, die nichts ueber Zustand aussagen.
    UNINTERESSANT = {"self", "cls", "request", "args", "kwargs", "x", "n", "i"}

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None or self._django_sonderfall(d):
                continue
            funktionen = [k for k in d.baum.body
                          if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and k.name not in self.EINSTIEGE]
            if len(funktionen) < self.AB_ANZAHL:
                continue
            gemeinsam = self._gemeinsame_argumente(funktionen)
            if not gemeinsam:
                continue
            klassen = [k.name for k in d.baum.body if isinstance(k, ast.ClassDef)]
            zeilen.append({
                "datei": d.name, "zeile": funktionen[0].lineno,
                "funktionen": len(funktionen),
                "gemeinsam": ", ".join("%s (%d×)" % (n, c) for n, c in gemeinsam[:3]),
                "klassen da": len(klassen),
            })
        zeilen.sort(key=lambda z: -z["funktionen"])
        return Ergebnis(
            ["datei", "zeile", "funktionen", "gemeinsam", "klassen da"], zeilen,
            "%d Dateien mit Funktionen um denselben Zustand herum" % len(zeilen),
            "Je öfter dasselbe Argument in den Signaturen steht, desto klarer "
            "ist, was die Klasse halten würde.")

    @staticmethod
    def _django_sonderfall(d):
        name = d.name
        return (name.endswith(("/urls.py", "/admin.py", "/apps.py", "/wsgi.py",
                               "/asgi.py", "/settings.py", "/conftest.py"))
                or "/management/commands/" in name
                or "/migrations/" in name
                or name.endswith("/views.py"))

    def _gemeinsame_argumente(self, funktionen):
        """[(Name, Anzahl)] der Argumente, die in mehreren Funktionen stehen."""
        zaehler = Counter()
        for f in funktionen:
            namen = {a.arg for a in f.args.args} - self.UNINTERESSANT
            zaehler.update(namen)
        return [(n, c) for n, c in zaehler.most_common() if c >= self.AB_ANZAHL]
