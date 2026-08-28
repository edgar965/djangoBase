# -*- coding: utf-8 -*-
u"""Umbaugegenprobe - was hat ein Umbau an den Funktionsruempfen wirklich geaendert?

DER ANLASS (28.08.2026, Projekt assistant)
==========================================
Beim Umbau freier Funktionen zu Klassen (Befund ``freie-funktionen``) habe
ich zwei Funktionsruempfe **erfunden statt gelesen**. Ich hatte nur die
``def``-Zeile vor Augen und den Inhalt aus dem Namen geschlossen::

    # was dastand
    Konto(nummer=k.nummer, name=k.name,
          ust_klassifikation=k.ust_klassifikation, ea=k.ea,
          ust_satz=..., ignore_soll=..., sonderbehandlung=...)

    # was ich geschrieben habe
    Konto(nummer=k.nummer, name=k.name, ust_satz=...,
          ist_einnahme=k.ist_einnahme,     # <- gibt es nicht
          ist_ausgabe=k.ist_ausgabe)       # <- gibt es auch nicht

Gefangen hat es ein vorhandener Test (AttributeError, 15 rote Faelle). Bei
einem Modul OHNE Test waere es durchgegangen, und drei Felder haetten in
jeder Steuerauswertung gefehlt - ohne dass irgendwo etwas rot wird.

WAS DIESES WERKZEUG TUT
=======================
Es nimmt die geaenderten Python-Dateien aus git, zerlegt alte und neue
Fassung in Funktions- und Methodenruempfe und vergleicht sie als
Syntaxbaum - ohne Docstrings, ohne Formatierung, ohne Kommentare.

Gemeldet wird jeder Rumpf, der sich geaendert hat, und jeder, der
VERSCHWUNDEN ist. Der zweite Fall ist der gefaehrlichere: Eine Funktion,
die es nach dem Umbau nicht mehr gibt, ist entweder absichtlich
aufgegangen (dann steht sie unter neuem Namen da) oder versehentlich
verlorengegangen.

WAS ES NICHT TUT
================
Es beweist keine Verhaltensgleichheit. Ein Rumpf, der absichtlich anders
ist, erscheint als Unterschied und muss gelesen werden. Das Werkzeug
sorgt dafuer, dass man ihn UEBERHAUPT zu sehen bekommt.

DIE FALLE, DIE ES SELBST HATTE
==============================
Die erste Fassung verglich eine Datei mit sich selbst, wenn die alte
Fassung noch danebenlag - dann ist jeder Rumpf „gleich" und der Vergleich
sagt nichts. Deshalb fuehrt es die Ruempfe nach Herkunftsdatei und meldet
diesen Fall ausdruecklich.
"""
import ast
import difflib
import subprocess

from .werkzeug import Ergebnis, Werkzeug


class Umbaugegenprobe(Werkzeug):
    u"""Vergleicht die Funktionsruempfe geaenderter Dateien gegen HEAD."""

    slug = "umbau-gegenprobe"
    titel = "Umbau-Gegenprobe"
    zweck = ("Zeigt fuer jede geaenderte Datei, welche Funktionsruempfe sich "
             "wirklich geaendert haben - ohne Docstrings und Formatierung.")
    befund = ("Beim Umbau freier Funktionen zu Klassen wurden zwei Ruempfe "
              "ERFUNDEN statt gelesen (Felder, die es am Modell nicht gibt). "
              "Ein vorhandener Test fing es; ohne Test waere es "
              "durchgegangen.")
    abhilfe = ("Jeden gemeldeten Unterschied lesen. Umbenennungen sind "
               "harmlos, aber sie muessen GESEHEN werden. Verschwundene "
               "Ruempfe zuerst pruefen.")
    dauer = "unter 3 s"
    kriterium = 0

    #: Ein git-Werkzeug kann in einem Wegwerf-Verzeichnis nichts finden:
    #: Der Anlassfall braeuchte ein Repo MIT Historie und einem Commit,
    #: gegen den sich vergleichen laesst. Das ist kein Codeschnipsel,
    #: den man in eine Datei schreibt.
    ohne_anlassfall_weil = (
        "Braucht ein git-Repo mit Historie - im Wegwerf-Verzeichnis des "
        "Anlassfall-Checks gibt es keinen Commit zum Vergleichen.")

    #: Gegen was verglichen wird. ``HEAD`` heisst: die Aenderungen im
    #: Arbeitsbaum. ``HEAD~1`` zeigt, was der letzte Commit geaendert hat.
    REVISION = "HEAD"

    #: Mehr Dateien als das deutet auf einen Massenumbau (Formatierung,
    #: Umbenennung ueber das ganze Projekt). Dann ist die Liste kein
    #: Befund mehr, sondern Rauschen.
    MAX_DATEIEN = 40

    SPALTEN = ["Datei", "Rumpf", "Art", "Was"]

    # -- git ---------------------------------------------------------------

    def _git(self, *argumente):
        u"""git im Projektverzeichnis; ``None``, wenn es nicht laeuft."""
        try:
            ergebnis = subprocess.run(("git",) + argumente,
                                      cwd=str(self.wurzel()),
                                      capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        if ergebnis.returncode != 0:
            return None
        return ergebnis.stdout.decode("utf-8", "replace")

    def _geaenderte_dateien(self):
        u"""Geaenderte .py-Dateien - ohne die geloeschten.

        Eine geloeschte Datei hat keinen neuen Stand; sie gehoert in die
        Zusammenfassung, nicht in den Vergleich.
        """
        ausgabe = self._git("diff", "--name-status", self.REVISION)
        if ausgabe is None:
            return None, None
        geaendert, geloescht = [], []
        for zeile in ausgabe.splitlines():
            teile = zeile.split("\t")
            if len(teile) < 2 or not teile[-1].endswith(".py"):
                continue
            if teile[0].startswith("D"):
                geloescht.append(teile[-1])
            else:
                geaendert.append(teile[-1])
        return geaendert, geloescht

    def _alter_stand(self, pfad):
        return self._git("show", f"{self.REVISION}:{pfad}")

    # -- Zerlegen ----------------------------------------------------------

    @staticmethod
    def _ruempfe(quelle):
        u"""``{Name: Zeilen des Rumpfs}``, ohne Docstring.

        Der Docstring fliegt raus, weil er sich bei jedem Umbau aendert -
        stuende er drin, waere jeder Rumpf verschieden und der Vergleich
        wertlos.
        """
        try:
            baum = ast.parse(quelle)
        except SyntaxError:
            return None
        out = {}
        for knoten in ast.walk(baum):
            if not isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            leib = list(knoten.body)
            if (leib and isinstance(leib[0], ast.Expr)
                    and isinstance(leib[0].value, ast.Constant)
                    and isinstance(leib[0].value.value, str)):
                leib = leib[1:]
            if not leib:
                leib = [ast.Pass()]
            modul = ast.Module(body=leib, type_ignores=[])
            out[knoten.name] = ast.unparse(modul).splitlines()
        return out

    # -- Vergleich ---------------------------------------------------------

    @staticmethod
    def _kurzfassung(alt, neu):
        u"""Die erste wirklich abweichende Zeile - mehr passt in keine Spalte."""
        for zeile in difflib.unified_diff(alt, neu, lineterm="", n=0):
            if zeile.startswith("+") and not zeile.startswith("+++"):
                return zeile[1:].strip()[:120]
        for zeile in difflib.unified_diff(alt, neu, lineterm="", n=0):
            if zeile.startswith("-") and not zeile.startswith("---"):
                return "entfaellt: " + zeile[1:].strip()[:110]
        return ""

    def _datei_vergleichen(self, pfad):
        u"""Zeilen fuer EINE Datei."""
        alter_text = self._alter_stand(pfad)
        if alter_text is None:
            # Neu angelegt: Es gibt nichts zu vergleichen. Das ist der
            # Normalfall bei einem Umbau, der eine Klasse in eine neue
            # Datei legt - und kein Befund.
            return []

        alt = self._ruempfe(alter_text)
        try:
            neuer_text = (self.wurzel() / pfad).read_text(encoding="utf-8")
        except OSError:
            return []
        neu = self._ruempfe(neuer_text)

        if alt is None or neu is None:
            return [{"Datei": pfad, "Rumpf": "-", "Art": "unlesbar",
                     "Was": "Syntaxfehler in einer der beiden Fassungen"}]

        zeilen = []
        for name, rumpf in sorted(alt.items()):
            if name not in neu:
                zeilen.append({
                    "Datei": pfad, "Rumpf": name, "Art": "verschwunden",
                    "Was": ("Gibt es nach der Aenderung nicht mehr - "
                            "aufgegangen oder verloren?")})
            elif neu[name] != rumpf:
                zeilen.append({"Datei": pfad, "Rumpf": name, "Art": "geaendert",
                               "Was": self._kurzfassung(rumpf, neu[name])})
        return zeilen

    # -- Lauf --------------------------------------------------------------

    def laufen(self):
        geaendert, geloescht = self._geaenderte_dateien()
        if geaendert is None:
            return Ergebnis(
                self.SPALTEN, [],
                zusammenfassung="git nicht verfuegbar oder kein Repo",
                hinweis=("Dieses Werkzeug vergleicht gegen die git-Historie. "
                         "Ohne Repo hat es nichts, wogegen es pruefen kann."))

        if not geaendert and not geloescht:
            return Ergebnis(
                self.SPALTEN, [],
                zusammenfassung=f"Keine geaenderte .py-Datei gegen "
                                f"{self.REVISION}")

        if len(geaendert) > self.MAX_DATEIEN:
            return Ergebnis(
                self.SPALTEN, [],
                zusammenfassung=f"{len(geaendert)} geaenderte Dateien - "
                                f"zu viele fuer einen sinnvollen Vergleich",
                hinweis=("Bei einem Massenumbau (Formatierung, projektweite "
                         "Umbenennung) ist die Liste kein Befund mehr, "
                         "sondern Rauschen. Erst in kleineren Schritten "
                         "committen, dann erneut pruefen."))

        zeilen = []
        for pfad in geaendert:
            zeilen.extend(self._datei_vergleichen(pfad))
        for pfad in geloescht:
            zeilen.append({
                "Datei": pfad, "Rumpf": "(ganze Datei)", "Art": "geloescht",
                "Was": ("Steht ihr Inhalt jetzt woanders? Sonst ist er weg.")})

        verschwunden = sum(1 for z in zeilen if z["Art"] == "verschwunden")
        hinweis = ""
        if verschwunden:
            hinweis = (
                f"{verschwunden} Ruempfe gibt es nicht mehr. Das ist der "
                "gefaehrliche Fall: Entweder sind sie absichtlich in einer "
                "Klasse aufgegangen - dann stehen sie unter neuem Namen da - "
                "oder sie sind verlorengegangen.")

        return Ergebnis(
            self.SPALTEN, zeilen,
            zusammenfassung=(f"{len(zeilen)} Ruempfe betroffen in "
                             f"{len(geaendert)} Dateien"),
            hinweis=hinweis)
