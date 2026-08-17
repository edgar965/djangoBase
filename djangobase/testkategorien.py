# -*- coding: utf-8 -*-
u"""Kategorien - was sich aus ``DJANGOBASE["test_befehle"]`` ableiten laesst.

Aus ``views/tests.py`` herausgeloest (17.08.2026): Die Ansicht war auf 399 Zeilen
gewachsen und trug drei Aufgaben — Herleitung, Ausfuehrung, Darstellung. Hier
steht nur die Herleitung:

    Reiter „Alles"        ein Lauf ueber das ganze Projekt
    Unter-Reiter je Art   Sammelknopf + die einzelnen Bereiche dieser Art
    Suiten-Gruppen        nach ``gruppe`` gebuendelt
    Labels je Art         Grundlage der Einzeltest-Discovery

WIRD ABGELEITET, NICHT VORAUSGESETZT
====================================
Die erste Fassung erwartete fertige Sammel-Eintraege aus
:class:`~.testbefehle.Testbefehle`. Damit hatten den Reiter „Alle" genau die
Projekte NICHT, die ihre ``test_befehle`` von Hand pflegen (WalkHop, NoiseSpy,
HumanBodyWeb, shortlongx). Jetzt wird Art und Ziel notfalls aus dem Kommando
gelesen (``manage.py test app.tests.unit`` -> „unit"), und der Reiter steht
ueberall.
"""
import re
import sys

from .testbefehle import Testbefehle

__all__ = ["Kategorien"]

#: Die Test-Arten und ihre Namen stehen an EINER Stelle (Testbefehle) - hier
#: geliehen, statt eine zweite Liste zu fuehren, die auseinanderlaeuft.
ARTEN = Testbefehle.ARTEN
ARTNAMEN = Testbefehle.ARTNAMEN
KURZ = Testbefehle.KURZ


class Kategorien:
    """Leitet aus den Test-Befehlen alles ab, was die Seite gruppiert zeigt."""

    #: Wie lange ein Sammellauf hoechstens dauern darf. Ein Einzellauf begnuegt
    #: sich mit den zehn Minuten aus ``Testlauf.FRIST``; „Alles" kann laenger
    #: brauchen, und ein Abbruch nach Zeitablauf sieht auf der Seite aus wie ein
    #: Fehlschlag.
    SAMMEL_FRIST = 3600
    #: Optionen von ``manage.py test``, auf die ein WERT folgt - deren Wert ist
    #: kein Test-Label (``-v 2`` waere sonst das Label „2").
    WERT_OPTIONEN = {"-v", "--verbosity", "--settings", "--pythonpath", "-t",
                     "--top-level-directory", "--testrunner", "--tag",
                     "--exclude-tag", "--parallel", "-k", "--shuffle",
                     "--durations", "--pdb"}

    def __init__(self, befehle):
        self.befehle = list(befehle or [])
        self.alles, self.arten, self.suiten = self._ableiten()

    # ------------------------------------------------------------- Herleitung

    def _ableiten(self):
        """``(alles, arten, angereicherte_suiten)`` - leer, wenn nichts da ist."""
        if not self.befehle:
            return None, [], self.befehle
        angereichert, nach_art, ohne_art = [], {}, []
        for b in self.befehle:
            # Dictionary gewollt: angereicherte Kopie, das Original bleibt heil.
            e = dict(b)
            e["ziel"] = b.get("ziel") or " ".join(self.ziele(b.get("cmd")))
            e["art"] = b.get("art") or self.art(e["ziel"])
            angereichert.append(e)
            (nach_art.setdefault(e["art"], []) if e["art"] else ohne_art).append(e)
        python = self.python(self.befehle)
        alles = self.sammel(python, "alles", "Alles — jede Art, jede App", [])
        arten = []
        # REIHENFOLGE UND NAMEN aus den Einstellungen (Ansage 17.08.2026: „auch
        # die reihenfolge ist änderbar"). Ohne Angabe bleibt es bei der
        # eingebauten Folge — erst schnell, zuletzt langsam.
        from .testarten import Arten
        einteilung = Arten.aus_einstellungen()
        for art in einteilung.liste():
            dabei = nach_art.get(art) or []
            if not dabei:
                continue
            ziele = [z for e in dabei for z in (e["ziel"] or "").split() if z]
            arten.append({"art": art, "kurz": einteilung.name_von(art),
                          "sammel": self.sammel(
                              python, art,
                              "Alle %s" % einteilung.lang_von(art), ziele),
                          "befehle": dabei})
        if ohne_art:
            arten.append({"art": "apps", "kurz": "Nach App", "sammel": None,
                          "befehle": ohne_art})
        return alles, arten, angereichert

    @classmethod
    def sammel(cls, python, art, name, ziele):
        """Ein Sammelbefehl - alle Ziele einer Art in EINEM Lauf.

        Ein Lauf statt sechs heisst auch: die Testdatenbank wird einmal
        aufgebaut, nicht sechsmal."""
        # Dictionary gewollt: dasselbe Format wie DJANGOBASE["test_befehle"],
        # damit die Ansicht es ohne Sonderweg ausfuehren kann.
        return {"slug": "sammel-" + art, "name": name, "art": art,
                "ziel": " ".join(ziele), "anzahl": len(ziele),
                "frist": cls.SAMMEL_FRIST,
                "cmd": [python, "manage.py", "test"] + list(ziele)
                       + ["--noinput", "-v", "2"]}

    def sammelbefehle(self):
        """Alle abgeleiteten Eintraege - fuer die Ausfuehrung per ``?run=``."""
        aus = [self.alles] if self.alles else []
        return aus + [a["sammel"] for a in self.arten if a.get("sammel")]

    def gruppen(self):
        """Suiten nach ``gruppe`` buendeln - Reihenfolge wie eingetragen.

        Eintraege OHNE ``gruppe`` landen zusammen unter „Test-Suiten (Batch)":
        Projekte, die ihre Liste von Hand pflegen, sehen die Seite damit
        unveraendert. Wer :class:`~.testbefehle.Testbefehle` benutzt, bekommt je
        Bereich eine eigene Karte (Kriterium 17: keine flache Liste aus hundert
        Eintraegen)."""
        aus, nach_name = [], {}
        for b in self.suiten:
            name = b.get("gruppe") or "Test-Suiten (Batch)"
            if name not in nach_name:
                # Dictionary gewollt: geht unveraendert in die Vorlage.
                nach_name[name] = {"name": name, "befehle": []}
                aus.append(nach_name[name])
            nach_name[name]["befehle"].append(b)
        return aus

    def discover(self):
        u"""Labels je Art - Grundlage der Einzeltest-Discovery.

        Wird genommen, wenn das Projekt kein ``test_discover`` pflegt: Die
        Einzeltest-Reiter (und damit die Laufzeit je Testcase) sollen ueberall
        stehen, nicht nur dort, wo jemand die Labels von Hand eingetragen hat.
        Quelle sind dieselben Ziele wie fuer die Sammelknoepfe — eine Liste, kein
        zweiter Ort.
        """
        return [{"typ": a["kurz"], "labels": (a["sammel"]["ziel"] or "").split()}
                for a in self.arten if a.get("sammel")]

    # ---------------------------------------------------------------- Lesehilfen

    @classmethod
    def ziele(cls, cmd):
        """Die Test-Labels eines Kommandos (alles nach ``test``, ohne Optionen)."""
        toks = [str(t) for t in (cmd or [])]
        if "test" not in toks:
            return []
        aus, vorher = [], ""
        for t in toks[toks.index("test") + 1:]:
            if t.startswith("-"):
                vorher = t
                continue
            if vorher in cls.WERT_OPTIONEN:     # der Wert der Option, kein Label
                vorher = ""
                continue
            vorher = ""
            aus.append(t)
        return aus

    @staticmethod
    def art(ziel):
        """„search.tests.chat.unit" -> „unit"; „tracker" -> None."""
        for teil in re.split(r"[.\\/\s]+", ziel or ""):
            if teil in ARTEN:
                return teil
        return None

    @staticmethod
    def python(befehle):
        """Der Interpreter, mit dem das Projekt seine Tests faehrt.

        Aus den vorhandenen Eintraegen genommen, nicht geraten: In mehreren
        Projekten steht dort ein fester venv-Pfad, und ``sys.executable`` ist
        beim Server ein anderer."""
        for b in befehle:
            cmd = b.get("cmd") or []
            if cmd and str(cmd[0]).lower() not in ("python", "python3"):
                return str(cmd[0])
        return sys.executable

    @staticmethod
    def schluessel(name):
        u"""„Search · chat" -> „search-chat" - Speicher-Schluessel einer Tabelle.

        Er landet in ``localStorage`` (Sortierung, Spaltenbreiten), deshalb ohne
        Leerzeichen und Sonderzeichen.
        """
        sauber = "".join(z if z.isalnum() else "-" for z in name.lower())
        return re.sub(r"-+", "-", sauber).strip("-")
