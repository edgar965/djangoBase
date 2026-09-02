# -*- coding: utf-8 -*-
u"""Der Stapellauf: ein Language Server über das Projekt, Befunde als Liste.

BEIDE WERKZEUGE (Edgar, 02.09.2026: „mache beide, die man umschalten kann")
===========================================================================
``basedpyright`` kommt per pip und bringt Node selbst mit; ``pyright`` gibt es
als pip-Hülle (lädt beim ersten Lauf das npm-Paket nach) und als npm-Paket.
Beide sprechen dieselbe Kommandozeile (``--outputjson``, ``-p <config>``) und
dieselbe JSON-Ausgabe — deshalb EINE Klasse, die nur den Namen wechselt.

WO DIE DATEIEN LIEGEN
=====================
Die ``pyrightconfig.json`` und der Zwischenspeicher der pyright-Hülle liegen
unter dem Ablage-Ordner des Projekts (``BASE_DIR/.cache/umbau/languageserver``),
nie unter ``%TEMP%`` — die 100-GB-Regel des Wirtsprojekts.

WAS DIESE KLASSE NICHT TUT
==========================
Nichts im Request rechnen (das macht ``ls_lauf.LsLauf`` im Thread) und nichts
merken (das macht der ``Speicher`` in der Ansicht). Sie startet einen Prozess,
wartet mit Zeitlimit und liest die Ausgabe.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .ls_javascript import JsPruefer

__all__ = ["LanguageServer", "LsErgebnis"]


class LsErgebnis:
    u"""Was ein Lauf hinterlässt — auch ein gescheiterter."""

    __slots__ = ("werkzeug", "version", "befunde", "dateien", "dauer_s", "fehlt",
                 "abgebrochen", "ausgabe", "wann", "abdruck", "modus",
                 "js_dauer_s", "js_fehlt", "js_befunde")

    def __init__(self, werkzeug="", abdruck="", modus=""):
        self.werkzeug = werkzeug
        self.version = ""
        self.befunde = []
        self.dateien = 0
        self.dauer_s = 0.0
        self.fehlt = ""
        self.abgebrochen = False
        self.ausgabe = ""
        self.wann = time.time()
        self.abdruck = abdruck
        self.modus = modus
        #: Der JavaScript-Teil (tsc): eigene Dauer, eigener Fehlgrund, Zaehler.
        self.js_dauer_s = 0.0
        self.js_fehlt = ""
        self.js_befunde = 0

    def als_dict(self):
        return {f: getattr(self, f) for f in self.__slots__}


class LanguageServer:
    u"""Findet das Programm, schreibt die Konfiguration, fährt den Lauf."""

    NAMEN = ("basedpyright", "pyright")

    def __init__(self, konfig, wurzel, ordner, extra=()):
        self.konfig = konfig
        self.wurzel = Path(wurzel)
        self.ordner = Path(ordner)
        #: Weitere Import-Wurzeln (bei Django: BASE_DIR neben der Repo-Wurzel).
        self.extra = [Path(p) for p in extra]

    # ── finden ───────────────────────────────────────────────────────────
    def finden(self):
        u"""``{name, cli, server, fehlt}`` — welches Programm läuft.

        Reihenfolge bei ``auto``: basedpyright, dann pyright. Gesucht wird
        neben dem Interpreter (``Scripts/`` bzw. ``bin/``), im PATH und im
        npm-Ordner des Nutzers."""
        wunsch = self.konfig.werkzeug
        namen = self.NAMEN if wunsch == "auto" else (wunsch,)
        for name in namen:
            cli = self._programm(name)
            if cli:
                return {"name": name, "cli": cli,
                        "server": self._programm(name + "-langserver"), "fehlt": ""}
        return {"name": wunsch, "cli": None, "server": None,
                "fehlt": (u"%s ist nicht installiert. Abhilfe: "
                          u"pip install %s  (im venv des Projekts)"
                          % (u" und ".join(namen), u" ".join(namen)))}

    def _programm(self, name):
        python = Path(self.konfig.python or sys.executable)
        kandidaten = [python.parent / name, python.parent / (name + ".exe"),
                      python.parent / (name + ".cmd")]
        npm = os.environ.get("APPDATA")
        if npm:
            kandidaten += [Path(npm) / "npm" / (name + ".cmd"),
                           Path(npm) / "npm" / name]
        for k in kandidaten:
            if k.is_file():
                return str(k)
        return shutil.which(name)

    # ── Konfiguration ────────────────────────────────────────────────────
    def konfig_schreiben(self):
        self.ordner.mkdir(parents=True, exist_ok=True)
        pfad = self.ordner / "pyrightconfig.json"
        cfg = self.konfig.als_pyrightconfig(self.wurzel, self.extra, ablage=self.ordner)
        pfad.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return pfad

    def umgebung(self):
        u"""Die pyright-Hülle lädt npm-Pakete in einen Zwischenspeicher —
        hierhin, nicht nach C:."""
        env = dict(os.environ)
        env["PYRIGHT_PYTHON_CACHE_DIR"] = str(self.ordner / "pyright-python")
        env["PYRIGHT_PYTHON_IGNORE_WARNINGS"] = "1"
        return env

    # ── laufen ───────────────────────────────────────────────────────────
    def laufen(self):
        gefunden = self.finden()
        ergebnis = LsErgebnis(gefunden["name"], self.konfig.abdruck(), self.konfig.modus)
        if not gefunden["cli"]:
            ergebnis.fehlt = gefunden["fehlt"]
            return ergebnis
        pfad = self.konfig_schreiben()
        befehl = [gefunden["cli"], "--outputjson", "-p", str(pfad)]
        start = time.monotonic()
        try:
            code, aus, fehler = self._ausfuehren(befehl, self.konfig.zeitlimit)
        except subprocess.TimeoutExpired:
            ergebnis.abgebrochen = True
            ergebnis.dauer_s = round(time.monotonic() - start, 1)
            ergebnis.fehlt = (u"Zeitlimit von %d s überschritten — Lauf abgebrochen"
                              % self.konfig.zeitlimit)
            return ergebnis
        except OSError as e:
            ergebnis.fehlt = u"Programm nicht startbar: %s" % e
            return ergebnis
        ergebnis.dauer_s = round(time.monotonic() - start, 1)
        ergebnis.ausgabe = (fehler or "")[-2000:]
        try:
            befunde, dateien, version = self._parsen(aus, self.wurzel)
        except ValueError:
            ergebnis.fehlt = (u"Ausgabe nicht lesbar (Ende-Code %s): %s"
                              % (code, (aus or fehler or "")[-400:]))
            return ergebnis
        ergebnis.befunde, ergebnis.dateien, ergebnis.version = befunde, dateien, version
        self._javascript(ergebnis)
        return ergebnis

    def _javascript(self, ergebnis):
        u"""JavaScript im selben Lauf, wenn eingeschaltet - Befunde dazu."""
        if not getattr(self.konfig, "javascript", False):
            return
        pruefer = JsPruefer(self.wurzel, self.ordner, self.konfig.pfade,
                            self.konfig.zeitlimit,
                            zusatz=getattr(self.konfig, "zusatz", ()))
        befunde, dauer, fehlt = pruefer.laufen()
        ergebnis.js_dauer_s, ergebnis.js_fehlt, ergebnis.js_befunde = dauer, fehlt, len(befunde)
        ergebnis.befunde.extend(befunde)
        ergebnis.dauer_s = round(ergebnis.dauer_s + dauer, 1)

    def _ausfuehren(self, befehl, zeitlimit):
        u"""``(code, stdout, stderr)`` — beim Zeitlimit stirbt der GANZE Baum.

        DER WINDOWS-KLASSIKER (02.09.2026, erster Lauf auf shortlongx): Mit
        ``subprocess.run(timeout=…)`` lief der Lauf nach 430 s noch. Das
        Zeitlimit hatte nur die pip-Hülle beendet; ihr Node-Kindprozess hielt
        die Pipes offen und rechnete weiter (513 CPU-Sekunden), und
        ``communicate()`` wartete auf ihn. Deshalb ``taskkill /T`` auf die
        Prozess-ID — der Baum, nicht das Blatt."""
        prozess = subprocess.Popen(befehl, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=str(self.wurzel), env=self.umgebung())
        try:
            aus, fehler = prozess.communicate(timeout=zeitlimit)
        except subprocess.TimeoutExpired:
            self._baum_beenden(prozess)
            raise
        return (prozess.returncode, aus.decode("utf-8", "replace"),
                fehler.decode("utf-8", "replace"))

    @staticmethod
    def _baum_beenden(prozess):
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(prozess.pid)],
                           capture_output=True)
        else:
            prozess.kill()
        try:
            prozess.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    @staticmethod
    def _parsen(text, wurzel):
        u"""``(befunde, dateien, version)`` aus der JSON-Ausgabe.

        Ein Befund: ``{datei, zeile, spalte, stufe, regel, text}`` — ``datei``
        relativ zur Wurzel, ``zeile`` 1-basiert (die Ausgabe zählt ab 0)."""
        anfang = (text or "").find("{")
        if anfang < 0:
            raise ValueError("kein JSON")
        daten = json.loads(text[anfang:])
        befunde = []
        wurzel = Path(wurzel)
        for d in daten.get("generalDiagnostics") or []:
            pfad = Path(d.get("file") or "")
            try:
                rel = str(pfad.relative_to(wurzel))
            except ValueError:
                rel = str(pfad)
            start = (d.get("range") or {}).get("start") or {}
            befunde.append({
                "datei": rel.replace("\\", "/"),
                "zeile": int(start.get("line", 0)) + 1,
                "spalte": int(start.get("character", 0)) + 1,
                "stufe": d.get("severity") or "information",
                "regel": d.get("rule") or "",
                "text": (d.get("message") or "").strip(),
            })
        zusammen = daten.get("summary") or {}
        return befunde, int(zusammen.get("filesAnalyzed") or 0), str(daten.get("version") or "")
