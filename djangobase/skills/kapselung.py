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

from .anlassfall import Anlassfall
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

    #: Drei freie Funktionen, die denselben Zustand von Hand durchreichen -
    #: genau das ist eine Klasse, die noch keine ist (Kriterium 1).
    anlassfall = Anlassfall(
        {"depot.py": '''def wert(konto, kurse):
    return sum(konto[s] * kurse[s] for s in konto)


def gewichtung(konto, kurse):
    gesamt = wert(konto, kurse)
    return {s: konto[s] * kurse[s] / gesamt for s in konto}


def umschichten(konto, kurse, ziel):
    ist = gewichtung(konto, kurse)
    return {s: ziel.get(s, 0) - ist.get(s, 0) for s in konto}
''',
         "fertig.py": '''class Depot:
    """Schon gekapselt - die drei Huellen darunter sind nur noch Namen."""

    def __init__(self, konto, kurse):
        self.konto = konto
        self.kurse = kurse

    def wert(self):
        return sum(self.konto[s] * self.kurse[s] for s in self.konto)

    def gewichtung(self):
        return {s: self.konto[s] * self.kurse[s] / self.wert()
                for s in self.konto}

    def umschichten(self, ziel):
        ist = self.gewichtung()
        return {s: ziel.get(s, 0) - ist.get(s, 0) for s in self.konto}


def wert(konto, kurse):
    return Depot(konto, kurse).wert()


def gewichtung(konto, kurse):
    return Depot(konto, kurse).gewichtung()


def umschichten(konto, kurse, ziel):
    return Depot(konto, kurse).umschichten(ziel)
'''},
        mindestens=1, hoechstens=1, erwartet_in="depot.py",
        warum="Kriterium 1: Funktionen, die denselben Zustand durchreichen, "
              "sind eine Klasse ohne Konstruktor. `fertig.py` daneben ist die "
              "AUSGEFÜHRTE Abhilfe — sie darf nicht wieder als Befund kommen.")

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None or self._django_sonderfall(d):
                continue
            tabelle = self._tabellen_namen(d)
            klassennamen = {k.name for k in d.baum.body
                            if isinstance(k, ast.ClassDef)}
            funktionen = [k for k in d.baum.body
                          if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and k.name not in self.EINSTIEGE
                          and k.name not in tabelle
                          and not self._huelle(k, klassennamen)]
            if len(funktionen) < self.AB_ANZAHL:
                continue
            gemeinsam = self._gemeinsame_argumente(funktionen)
            # ZWEI verschiedene gemeinsame Argumente, nicht nur eines: Ein
            # einzelnes geteiltes Argument ist oft die Eingabe, zwei sind ein
            # Objekt. Gemessen (shortlongx, 16.08.2026): >= 1 gemeinsames
            # Argument ergab 115 Befunde, >= 2 nur noch 70 - und die
            # verschwundenen 45 waren durchweg Module mit einer gemeinsamen
            # Eingabe, nicht mit gemeinsamem Zustand.
            if len(gemeinsam) < 2:
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
    def _huelle(knoten, klassennamen):
        u"""Ist das nur die Huelle um eine Klasse DERSELBEN Datei?

            def _run_mediapipe_to_csv(job, video_path, output_dir):
                return Erkennung2d(job, video_path, output_dir).mediapipe()

        Genau das ist die Abhilfe, die dieses Werkzeug empfiehlt — die Funktion
        bleibt nur stehen, weil ein Aufrufer sie unter diesem Namen kennt. Sie
        trotzdem zu melden hiess: Nach dem Umbau steht derselbe Befund wieder da
        (3DTools, 17.08.2026; der Aufrufer war `Auftragslauf._csv_erzeugen`).

        Verlangt wird beides — EIN ``return`` als ganzer Rumpf (Docstring zaehlt
        nicht) UND eine Klasse aus dieser Datei darin. Ein Einzeiler, der etwas
        anderes tut, bleibt ein Befund.
        """
        rumpf = [x for x in knoten.body
                 if not (isinstance(x, ast.Expr)
                         and isinstance(getattr(x, "value", None), ast.Constant))]
        if len(rumpf) != 1 or not isinstance(rumpf[0], ast.Return):
            return False
        return any(isinstance(x, ast.Name) and x.id in klassennamen
                   for x in ast.walk(rumpf[0]))

    @staticmethod
    def _tabellen_namen(d):
        """Funktionsnamen, die als WERT in einer Tabelle auf Modulebene stehen.

        DIE FUNKTION IST DANN DIE SCHNITTSTELLE. Eine Registrierungs-Tabelle wie

            def _sig_rsi(closes, period=14): …
            INDIKATOREN = [("rsi", "RSI", _sig_rsi), …]
            INDIKATOR_FN = {key: fn for key, name, fn in INDIKATOREN}

        ruft jede Funktion EINZELN und unabhängig. Das gemeinsame erste Argument
        ist deshalb die Eingabe des Vertrags, kein Feld eines Objekts: Zustand
        wird zwischen Aufrufen geteilt, ein Parameter ist bei jedem Aufruf ein
        anderer.

        Ohne diese Unterscheidung war die Indikator-Bank in shortlongx der
        schwerste Befund des Kriteriums — „14 Funktionen, eines von 13
        getragen". Wer dem folgt, baut eine Klasse um eine Tabelle, die schon
        eine ist (16.08.2026)."""
        namen = set()
        for k in d.baum.body:
            if not isinstance(k, (ast.Assign, ast.AnnAssign)) or k.value is None:
                continue
            for x in ast.walk(k.value):
                if isinstance(x, ast.Name):
                    namen.add(x.id)
                elif isinstance(x, ast.Call):
                    # ``f(...)`` ist ein AUFRUF, keine Registrierung.
                    for arg in list(x.args) + [s.value for s in x.keywords]:
                        for y in ast.walk(arg):
                            if isinstance(y, ast.Name):
                                namen.add(y.id)
        eigene = {f.name for f in d.baum.body
                  if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
        return namen & eigene

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
