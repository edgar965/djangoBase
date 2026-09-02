# -*- coding: utf-8 -*-
u"""JavaScript im selben Lauf — über den TypeScript-Übersetzer mit ``checkJs``.

„mach auch: JavaScript wäre ein zweiter Server (tsserver)" (Edgar, 02.09.2026).
Für den Stapellauf reicht der Übersetzer ``tsc`` mit ``allowJs``/``checkJs``:
Er liest die ES-Module des Projekts, löst Importe auf und meldet, was ein
Language Server auch melden würde — unbekannte Namen (TS2304), falsche
Argumentzahl (TS2554), Eigenschaften, die es nicht gibt (TS2339), Importe ins
Leere (TS2307). Kein Server-Prozess, keine Sitzung: ein Aufruf, Textzeilen als
Antwort. Für Referenzen und Umbenennen in JS bräuchte es den
``typescript-language-server`` — das ist Stufe 3 und noch nicht gebaut.

WAS ER NICHT WEISS
==================
Globale Namen aus eingebundenen Skripten (``Chart`` aus ``chart.umd.min.js``,
``bootstrap``) kennt er nicht und meldet sie als unbekannt. Das ist kein
Fehlalarm des Werkzeugs, sondern eine fehlende Deklaration — die Regel
``TS2304`` lässt sich auf der Seite abschalten, bis eine ``globals.d.ts`` da ist.

Django-frei; ``tsc`` kommt aus ``npm install -g typescript`` (``%APPDATA%\\npm``).
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

__all__ = ["JsPruefer"]

#: ``pfad(zeile,spalte): error TS1234: Meldung`` — die Form mit ``--pretty false``.
ZEILE = re.compile(r"^(?P<datei>.+?)\((?P<zeile>\d+),(?P<spalte>\d+)\): "
                   r"(?P<stufe>error|warning) (?P<regel>TS\d+): (?P<text>.*)$")

#: TS5xxx/TS6xxx sind Fehler AN DER KONFIGURATION, keine Befunde am Code.
#:
#: DER STILLE ABBRUCH (02.09.2026): ``baseUrl`` gibt es in tsc 7 nicht mehr.
#: Der Lauf endete danach nach 0,4 s mit genau EINEM „Befund" — der
#: Fehlermeldung selbst — und die Seite meldete stolz 4.956 Befunde weniger.
#: Ein Abbruch, der wie ein Erfolg aussieht, ist schlimmer als ein Absturz.
KONFIGFEHLER = re.compile(r"error TS(?:5\d{3}|6\d{3}):\s*(?P<text>.+)$", re.M)


class JsPruefer:
    u"""Findet ``tsc``, schreibt die ``jsconfig.json``, liest die Meldungen."""

    AUSSCHLUSS = ("**/node_modules", "**/*.min.js", "**/pythonVENV", "**/venv",
                  "**/.venv", "**/.cache", "**/sicherung", "**/backup_*",
                  "**/*.umd.js", "**/vendor/**")

    def __init__(self, wurzel, ordner, pfade=(), zeitlimit=300, zusatz=()):
        self.wurzel = Path(wurzel)
        self.ordner = Path(ordner)
        self.pfade = list(pfade)
        self.zeitlimit = zeitlimit
        #: Die Liste des Projekts (``pruefausschluss.txt``) — dieselbe, die
        #: der Python-Lauf benutzt; sonst prüfte tsc Dateien mit, die für
        #: pyright längst ausgeschlossen sind.
        self.zusatz = [str(m) for m in zusatz]

    # ── finden ───────────────────────────────────────────────────────────
    def finden(self):
        kandidaten = []
        npm = os.environ.get("APPDATA")
        if npm:
            kandidaten += [Path(npm) / "npm" / "tsc.cmd", Path(npm) / "npm" / "tsc"]
        for k in kandidaten:
            if k.is_file():
                return str(k)
        return shutil.which("tsc")

    # ── Konfiguration ────────────────────────────────────────────────────
    def statikpfade(self):
        u"""``/static/<app>/x.js`` auf den echten Ordner abbilden.

        DER GRÖSSTE EINZELPOSTEN DES ERSTEN LAUFS (02.09.2026)
        =====================================================
        Django-Vorlagen laden ihre Module über die URL::

            import { OptZustand } from '/static/dashboard/opt_zustand.js';

        Das ist zur Laufzeit richtig und für ``tsc`` unauflösbar — er sucht
        einen Ordner ``static`` an der Dateisystem-Wurzel. Gemessen an
        shortlongx: 309 von 311 Importen haben diese Form, daraus 320 ×
        ``TS2307`` und als Folge 1.460 × „Name nicht gefunden" (``OptZustand``
        allein 596 Mal). Zusammen 23 % aller Befunde — und keiner davon ein
        Befund über den Code.

        Die Abbildung entsteht aus dem Dateisystem: jeder ``static``-Ordner in
        den ersten drei Ebenen, und darin jeder Namensraum-Unterordner."""
        pfade, ordner = {}, []
        for muster in ("static", "*/static", "*/*/static"):
            ordner += [p for p in self.wurzel.glob(muster) if p.is_dir()]
        for statisch in ordner:
            fest = str(statisch).replace("\\", "/")
            for unter in sorted(p for p in statisch.iterdir() if p.is_dir()):
                pfade.setdefault("/static/%s/*" % unter.name,
                                 [fest + "/" + unter.name + "/*"])
            pfade.setdefault("/static/*", [fest + "/*"])
        return pfade

    def konfig_schreiben(self):
        u"""``jsconfig.json`` im Ablage-Ordner — Pfade als Muster, Schrägstriche."""
        self.ordner.mkdir(parents=True, exist_ok=True)
        pfad = self.ordner / "jsconfig.json"
        wurzeln = [self.wurzel / p for p in self.pfade] or [self.wurzel]
        cfg = {
            "compilerOptions": {
                "allowJs": True, "checkJs": True, "noEmit": True,
                "target": "es2022", "module": "es2022", "moduleResolution": "bundler",
                "lib": ["es2022", "dom", "dom.iterable"],
                "strict": False, "noImplicitAny": False, "skipLibCheck": True,
                "allowSyntheticDefaultImports": True,
                # KEIN ``baseUrl`` (02.09.2026): tsc 7 kennt die Option nicht
                # mehr („Option 'baseUrl' has been removed") und bricht dann
                # ab, BEVOR eine Datei geprüft ist. Die Ziele in ``paths``
                # stehen deshalb absolut, wie schon ``include``.
                "paths": self.statikpfade(),
            },
            "include": [str(w).replace("\\", "/") + "/**/*.js" for w in wurzeln],
            # Absolut wie ``include``: tsc liest ``exclude`` relativ zur Datei,
            # und die liegt im Ablage-Ordner, nicht ueber dem Projekt.
            "exclude": [str(self.wurzel).replace("\\", "/") + "/" + m
                        for m in list(self.AUSSCHLUSS) + self.zusatz],
        }
        pfad.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return pfad

    # ── laufen ───────────────────────────────────────────────────────────
    def laufen(self):
        u"""``(befunde, dauer_s, fehlt)`` — Befunde wie beim Python-Lauf, ``sprache: js``."""
        tsc = self.finden()
        if not tsc:
            return [], 0.0, (u"tsc ist nicht installiert. Abhilfe: "
                             u"npm install -g typescript")
        pfad = self.konfig_schreiben()
        start = time.monotonic()
        prozess = subprocess.Popen([tsc, "-p", str(pfad), "--pretty", "false"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=str(self.wurzel), shell=str(tsc).endswith(".cmd"))
        try:
            aus, fehler = prozess.communicate(timeout=self.zeitlimit)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(prozess.pid)],
                               capture_output=True)
            else:
                prozess.kill()
            return [], round(time.monotonic() - start, 1), (
                u"tsc: Zeitlimit von %d s überschritten" % self.zeitlimit)
        text = aus.decode("utf-8", "replace") + fehler.decode("utf-8", "replace")
        dauer = round(time.monotonic() - start, 1)
        schaden = KONFIGFEHLER.search(text)
        if schaden:
            return [], dauer, u"tsc-Konfiguration: %s" % schaden.group("text").strip()
        return self._parsen(text, self.wurzel), dauer, ""

    @staticmethod
    def _parsen(text, wurzel):
        befunde = []
        wurzel = Path(wurzel)
        for zeile in (text or "").splitlines():
            m = ZEILE.match(zeile.strip())
            if not m:
                continue
            pfad = Path(m.group("datei"))
            if not pfad.is_absolute():
                pfad = wurzel / pfad
            try:
                rel = str(pfad.resolve().relative_to(wurzel.resolve()))
            except (ValueError, OSError):
                rel = str(pfad)
            befunde.append({
                "datei": rel.replace("\\", "/"),
                "zeile": int(m.group("zeile")), "spalte": int(m.group("spalte")),
                "stufe": m.group("stufe"), "regel": m.group("regel"),
                "text": m.group("text").strip(), "sprache": "js",
            })
        return befunde
