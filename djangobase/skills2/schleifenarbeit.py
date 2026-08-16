# -*- coding: utf-8 -*-
u"""Schleifenarbeit - Datei- und Datenbankzugriff, der in der Schleife steht.

WAS EINE STATISCHE PRUEFUNG HIER LEISTEN KANN - und was nicht
=============================================================
Sie kann nicht messen. Was sie kann, ist die Handvoll Muster finden, die schon
mehrfach Minuten gekostet haben: Arbeit in einer Schleife, die vor die Schleife
gehoert. Gesucht wird nur, was auch ohne Messung eindeutig ist - Datei- oder
Datenbankzugriff in einer Schleife und Sammlungen, die per ``+=`` wachsen
(quadratisch).

Jeder Befund nennt die Schleifentiefe. Ob er sich lohnt, entscheidet eine
Messung; der Befund sagt nur, WO zu messen ist.

WENN ES IN DER SCHLEIFE STEHEN MUSS
===================================
Manchmal IST der Zugriff je Durchlauf der Zweck - eine Datei je Handelstag lässt
sich nicht vor die Schleife ziehen. Solche Stellen tragen den Vermerk

    # in der Schleife gewollt: eine Datei je Handelstag

und werden abgestuft. Ein Vermerk IM CODE statt einer Ausnahmeliste im Werkzeug:
Eine Liste hier raet, was der Autor gemeint hat, und liegt irgendwann daneben.
"""
import ast

from .werkzeug import Ergebnis, Werkzeug2


class Schleifenarbeit(Werkzeug2):
    slug = "schleifenarbeit"
    titel = "Arbeit in Schleifen"
    zweck = ("Datei-/DB-Zugriffe innerhalb von Schleifen und Sammlungen, die per "
             "+= wachsen — mit Schleifentiefe als Maß.")
    befund = ("Drei Prüffunktionen lasen dasselbe Verzeichnis je einmal komplett "
              "durch. Einzeln harmlos; die Suite besteht aus hundert solcher "
              "Prüfungen.")
    abhilfe = ("Vor die Schleife ziehen und das Ergebnis merken — als Instanz je "
               "Lauf, nicht als Klassen-Zwischenspeicher (sonst entsteht genau "
               "der Modul-Zustand aus dem ersten Werkzeug).")
    dauer = "3–8 s"
    kriterium = 12

    MARKER = "in der Schleife gewollt"
    TEUER = {"read_text": "liest eine Datei", "write_text": "schreibt eine Datei",
             "open": "öffnet eine Datei", "loads": "parst JSON",
             "dumps": "serialisiert JSON", "glob": "durchsucht das Dateisystem",
             "rglob": "durchsucht rekursiv", "all": "holt einen Datenbank-Satz",
             "filter": "stellt eine DB-Abfrage", "get": "stellt eine DB-Abfrage",
             "count": "zählt in der Datenbank"}
    #: Nur bei diesen Empfaengern ist get/filter/all eine DB-Abfrage.
    DB_EMPFAENGER = ("objects", "queryset", "qs")

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None:
                continue
            for schleife in d.knoten(ast.For, ast.While):
                zeilen.extend(self._in_schleife(d, schleife))
        zeilen.sort(key=lambda z: (z["bewertung"] != "prüfen", -z["tiefe"]))
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        return Ergebnis(
            ["datei", "zeile", "was", "tiefe", "bewertung"], zeilen,
            "%d Stellen, davon %d ohne Vermerk" % (len(zeilen), len(offen)),
            "Tiefe 2 heißt: zwei ineinander liegende Schleifen — dort kostet ein "
            "Dateizugriff n×m mal.")

    def _in_schleife(self, d, schleife):
        aus, tiefe = [], self._tiefe(schleife)
        for k in ast.walk(schleife):
            if k is schleife:
                continue
            if isinstance(k, ast.Call):
                name = getattr(k.func, "attr", None) or getattr(k.func, "id", None)
                if name not in self.TEUER:
                    continue
                if name in ("get", "filter", "all", "count"):
                    empf = getattr(getattr(k.func, "value", None), "attr", "")
                    if empf not in self.DB_EMPFAENGER:
                        continue
                aus.append({"datei": d.name, "zeile": k.lineno,
                            "was": "%s() %s" % (name, self.TEUER[name]),
                            "tiefe": tiefe,
                            "bewertung": "belegt" if self._begruendet(d, k.lineno)
                                         else "prüfen"})
            elif isinstance(k, ast.AugAssign) and isinstance(k.op, ast.Add):
                if isinstance(k.value, (ast.List, ast.JoinedStr)) or (
                        isinstance(k.value, ast.Constant)
                        and isinstance(k.value.value, str)):
                    aus.append({"datei": d.name, "zeile": k.lineno,
                                "was": "+= kopiert die ganze Sammlung",
                                "tiefe": tiefe,
                                "bewertung": "belegt" if self._begruendet(d, k.lineno)
                                             else "prüfen"})
        return aus

    def _begruendet(self, d, zeile):
        zeilen = d.text.splitlines()
        von = max(0, zeile - 6)
        return any(self.MARKER in z for z in zeilen[von:zeile])

    @staticmethod
    def _tiefe(schleife):
        return 1 + max((1 for k in ast.walk(schleife)
                        if isinstance(k, (ast.For, ast.While)) and k is not schleife),
                       default=0)
