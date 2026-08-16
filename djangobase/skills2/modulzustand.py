# -*- coding: utf-8 -*-
u"""ModulZustand - veraenderliche Sammlungen auf Modulebene finden.

DER BEFUND, DER DAS WERKZEUG AUSGELOEST HAT (shortlongx, 16.08.2026)
====================================================================
Eine Liste ``_GEKAPPT`` sammelte Vermerke „dieses Optimierungs-Raster war zu
fein und wurde abgeschnitten". Geschrieben wurde sie in einer Datei, geleert in
zwei anderen, gelesen in einer vierten. Zwei Folgen:

* Geleert wurde nur in EINEM der beiden Rechenpfade. Der andere meldete die
  Kappung eines fremden, laengst beendeten Laufs.
* Der Entwicklungsserver ist multithreaded. Zwei gleichzeitige Anfragen
  schrieben in dieselbe Liste.

Bemerkenswert war, was neun Zeilen darueber stand: ein Kommentar, der den Server
ausdruecklich als multithreaded bezeichnet - und direkt darunter einer, der
behauptete, er bearbeite „eine Anfrage nach der anderen". Beide Annahmen
nebeneinander, und der Code beruhte auf der falschen.

Die Suche fand 31 solcher Sammlungen im Projekt; genau zwei waren echte Fehler.

WARUM EIN VERMERK IM CODE STATT EINER LISTE IM WERKZEUG
=======================================================
Die uebrigen 29 sind absichtlich geteilt (Zwischenspeicher je Datenstand, ein
Prozess-Pool je Server). Damit das Werkzeug sie nicht jedes Mal meldet, tragen
sie den Vermerk ``geteilt gewollt: <Grund>`` in ihrer Naehe. Eine Ausnahmeliste
IM WERKZEUG waere die schlechtere Loesung: Sie raet, was der Autor gemeint hat.
"""
import ast

from .werkzeug import Ergebnis, Werkzeug2


class ModulZustand(Werkzeug2):
    slug = "modulzustand"
    titel = "Zustand auf Modulebene"
    zweck = ("Veränderliche Sammlungen (list/dict/set) auf Modulebene, die "
             "irgendwo mutiert werden — auch dateiübergreifend.")
    befund = ("Eine Liste, in einer Datei gefüllt und in einer anderen geleert, "
              "meldete Warnungen des falschen Laufs — und zwei gleichzeitige "
              "Anfragen schrieben hinein. Django ist multithreaded.")
    abhilfe = ("Zustand, der genau eine Anfrage lang gilt, gehört in ein Objekt "
               "(oder threading.local). Absichtlich Geteiltes bekommt den "
               "Vermerk „geteilt gewollt: <Grund>“ in den Code.")
    dauer = "3–8 s"
    kriterium = 9

    MARKER = "geteilt gewollt"
    #: Methoden, die eine Sammlung veraendern.
    MUTATION = {"append", "extend", "insert", "remove", "pop", "clear", "update",
                "add", "discard", "setdefault", "popitem"}

    def laufen(self):
        dateien = [d for d in self.dateien() if d.baum is not None]
        index, eigen = {}, {}
        for d in dateien:
            eigen[d.name] = self._eigene_namen(d)
            for name, zeile, art in self._mutationen(d):
                index.setdefault(name, []).append((d.name, zeile, art))
        zeilen = []
        for d in dateien:
            for name, knoten in self._kandidaten(d).items():
                treffer = index.get(name)
                if not treffer:
                    continue
                stellen = [(z, a) for f, z, a in treffer if f == d.name]
                fremd = [(f, z, a) for f, z, a in treffer
                         if f != d.name and name not in eigen.get(f, ())]
                zeilen.append(self._zeile(d, name, knoten, stellen, fremd))
        zeilen.sort(key=lambda z: (z["bewertung"] != "prüfen", z["datei"]))
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        return Ergebnis(
            ["datei", "zeile", "name", "art", "mutationen", "bewertung"],
            zeilen,
            "%d Sammlungen auf Modulebene, davon %d ohne Beleg"
            % (len(zeilen), len(offen)),
            "Ein Eintrag ist erst ein Fehler, wenn der Zustand ANFRAGE-bezogen "
            "ist. Zwischenspeicher, die für alle gelten sollen, sind in Ordnung "
            "— sie brauchen nur den Vermerk im Code.")

    # ----------------------------------------------------------------- Suche
    @staticmethod
    def _kandidaten(d):
        """{Name: Knoten} der Modulebenen-Zuweisungen auf list/dict/set."""
        aus = {}
        for k in d.baum.body:
            if not isinstance(k, (ast.Assign, ast.AnnAssign)):
                continue
            ziele = k.targets if isinstance(k, ast.Assign) else [k.target]
            wert = k.value
            if wert is None:
                continue
            veraenderlich = isinstance(wert, (ast.List, ast.Dict, ast.Set)) or (
                isinstance(wert, ast.Call)
                and getattr(wert.func, "id", "") in ("list", "dict", "set",
                                                     "defaultdict", "OrderedDict"))
            if not veraenderlich:
                continue
            for z in ziele:
                if isinstance(z, ast.Name):
                    aus[z.id] = k
        return aus

    def _mutationen(self, d):
        """(Name, Zeile, Art) jeder Stelle, die eine Sammlung verändert."""
        aus = []
        for k in ast.walk(d.baum):
            if isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute):
                if k.func.attr in self.MUTATION and isinstance(k.func.value, ast.Name):
                    aus.append((k.func.value.id, k.lineno, k.func.attr))
            elif isinstance(k, ast.Subscript) and isinstance(k.ctx, (ast.Store, ast.Del)):
                if isinstance(k.value, ast.Name):
                    aus.append((k.value.id, k.lineno, "[…] ="))
        return aus

    @staticmethod
    def _eigene_namen(d):
        """Namen, die eine Datei SELBST bindet - gegen Namensgleichheit.

        Ohne das meldete die erste Fassung jede lokale Variable, die zufällig so
        hieß wie ein Modulname anderswo."""
        aus = set()
        for k in ast.walk(d.baum):
            if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Store):
                aus.add(k.id)
            elif isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                aus.add(k.name)
                for a in getattr(getattr(k, "args", None), "args", []) or []:
                    aus.add(a.arg)
            elif isinstance(k, (ast.Import, ast.ImportFrom)):
                for n in k.names:
                    aus.add(n.asname or n.name.split(".")[0])
            elif isinstance(k, ast.Global):
                aus.difference_update(k.names)
        return aus

    def _zeile(self, d, name, knoten, stellen, fremd):
        belegt = self._begruendet(d, knoten.lineno)
        if belegt:
            bewertung = "belegt"
        elif fremd:
            bewertung = "prüfen"
        else:
            bewertung = "prüfen"
        art = type(knoten.value).__name__.lower()
        mut = ", ".join(sorted({a for _, a in stellen})[:4]) or "—"
        if fremd:
            mut += " · fremd: " + ", ".join(sorted({f for f, _, _ in fremd})[:2])
        return {"datei": d.name, "zeile": knoten.lineno, "name": name,
                "art": art, "mutationen": mut, "bewertung": bewertung}

    def _begruendet(self, d, zeile):
        zeilen = d.text.splitlines()
        von = max(0, zeile - 9)
        return any(self.MARKER in z for z in zeilen[von:zeile])
