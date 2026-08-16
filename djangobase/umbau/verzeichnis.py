# -*- coding: utf-8 -*-
u"""Werkzeugverzeichnis - was im Kasten liegt, in der Reihenfolge des Gebrauchs.

WOZU (17.08.2026): Die Werkzeuge in ``skills2`` haben einen Knopf auf
Hilfe->Skills2 und sind damit sichtbar. Die hier schreiben Quelltext und laufen
deshalb nur auf der Kommandozeile - und waren dadurch praktisch unsichtbar. Wer
sie nicht kennt, baut sie beim naechsten Umbau nach.

Die Liste wird AUS DEM PAKET erhoben, nicht von Hand gepflegt: Zweck aus der
ersten Docstring-Zeile, „schreibt Dateien" daran, ob im Quelltext ein
``write_text``/``rename``/``unlink`` steht. Damit kann die Seite nicht veralten,
und ein neues Modul faellt auf (der Test ``test_jedes_modul_ist_eingeordnet``).
"""
import re
from importlib import import_module
from pathlib import Path

from . import KLASSEN

__all__ = ["Werkzeugverzeichnis"]

#: Merkmale, an denen ein schreibendes Werkzeug erkennbar ist.
SCHREIBT = ("write_text(", ".rename(", ".unlink(", "write_bytes(")


class Werkzeugverzeichnis:
    u"""Die Module von ``djangobase.umbau``, gruppiert nach Arbeitsschritt."""

    #: (Gruppentitel, Was sie leistet, Module) - die Reihenfolge ist die des
    #: Gebrauchs: erst ansehen, dann schneiden, dann aufraeumen, dann gegenpruefen.
    GRUPPEN = (
        ("Umstellen", "Viele Dateien in einem Lauf - Probelauf ist die Vorgabe.",
         ("serverabrufe", "protokoll", "jsimporte", "stilklassen")),
        ("Ansehen", "Was vor dem Schnitt zu klaeren ist: was steht drin, wer "
                    "ruft wen.",
         ("strukturbericht", "aufrufgraph")),
        ("Schneiden", "Definitionen herausheben - ueber den AST, nicht per "
                      "Textsuche.",
         ("modulschneider", "klassenbauer")),
        ("Aufraeumen und gegenpruefen",
         "Die Folgeschaeden eines Schnitts - genau die, die stumm bleiben.",
         ("exportlisten", "unbekanntenamen", "fabrikklasse")),
        ("Grundlagen", "Bausteine, auf denen die anderen aufsetzen.",
         ("codesicht", "kommateilung")),
    )

    def eintraege(self):
        u"""[{gruppe, gruppe_zweck, modul, aufruf, klassen, zweck, schreibt}]"""
        nach_modul = {}
        for klasse, modul in KLASSEN.items():
            nach_modul.setdefault(modul, []).append(klasse)
        raus = []
        for titel, gruppenzweck, module in Werkzeugverzeichnis.GRUPPEN:
            for modul in module:
                raus.append({
                    "gruppe": titel,
                    "gruppe_zweck": gruppenzweck,
                    "modul": modul,
                    "aufruf": "python -m djangobase.umbau.%s" % modul,
                    "klassen": ", ".join(sorted(nach_modul.get(modul, []))),
                    "zweck": self._zweck(modul),
                    "schreibt": self._schreibt(modul),
                })
        return raus

    def gruppen(self):
        u"""[(titel, zweck, [eintrag, ...])] - fuer die Ausgabe auf der Seite."""
        raus = []
        for titel, zweck, _module in Werkzeugverzeichnis.GRUPPEN:
            raus.append((titel, zweck,
                         [e for e in self.eintraege() if e["gruppe"] == titel]))
        return raus

    # ------------------------------------------------------------------ intern
    @staticmethod
    def _zweck(modul):
        u"""Erste Docstring-Zeile, ohne den vorangestellten Klassennamen."""
        text = import_module("." + modul, __package__).__doc__ or ""
        erste = text.strip().split("\n")[0].strip()
        return re.sub(r"^\w+\s+[-—]\s+", "", erste)

    @staticmethod
    def _schreibt(modul):
        pfad = Path(__file__).resolve().parent / (modul + ".py")
        quelle = pfad.read_text(encoding="utf-8", errors="replace")
        return any(marke in quelle for marke in SCHREIBT)
