# -*- coding: utf-8 -*-
"""RuffBefunde — Linter und Formatierer in einem Werkzeug, ein Knopf.

DIE ANSAGE (Edgar, 18.09.2026)
==============================
Aus gunSlinger kam die Frage, ob dessen Prüflauf (ruff, mypy, Testsuite,
Strukturregeln) auch für die Django-Projekte taugt. Drei davon gab es
hier schon: `strukturtests` für die Strukturregeln, der Language Server
(basedpyright) für die Typen, Hilfe → Tests für die Suite. Was fehlte,
war ruff — „mach das in djangoBase".

WAS RUFF KANN, WAS `code-qualitaet` NICHT KANN
==============================================
`code-qualitaet` fährt pyflakes und pycodestyle — ruff enthält beide
(als F- und E/W-Regeln), dazu isort (I), flake8-bugbear (B) und pyupgrade
(UP), und es ist in Rust geschrieben: ein Projekt mit 700 Dateien in
unter einer Sekunde statt zwanzig. Vor allem aber hat ruff einen
FORMATIERER. Ob eine Zeile so oder so umbrochen wird, entscheidet dann
niemand mehr — das ist die Frage, die in jeder Review Zeit kostet und
nie etwas findet.

Dieses Werkzeug meldet, was `ruff check` und `ruff format --check`
sagen; geschrieben wird nichts (Skills melden, Fixer schreiben). Die
Abhilfe steht auf der Kommandozeile: `ruff check --fix` und
`ruff format` — beides als EIGENER Commit „nur Formatierung", nie
vermischt mit einer fachlichen Änderung. Sonst ist im Diff nicht mehr
zu sehen, was sich geändert hat.

WELCHE REGELN GELTEN
====================
Hat das Projekt eine eigene Konfiguration (`ruff.toml`, `.ruff.toml`
oder `[tool.ruff]` in `pyproject.toml`), gilt die — ruff findet sie
selbst. Sonst gilt `djangobase/ruff_vorgabe.toml`, die Vorgabe für alle
Konsumenten. Welche von beiden gegriffen hat, steht in der Kopfzeile.

KEINE DUPLIKATE (dieselbe Regel wie in `code-qualitaet`)
========================================================
Unbenutzte Einfuhren (F401) führt `tote-importe` — mit Wissen, das ruff
nicht hat (Seiteneffekt-Module, Namen in Zeichenketten). Leere
f-Zeichenketten (F541) führt `fix-fzeichenkette`. Beides wird GEZÄHLT
und in der Kopfzeile mit dem Namen des zuständigen Werkzeugs genannt,
aber nicht noch einmal aufgelistet.
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["RuffBefunde"]


class RuffBefunde(BefundWerkzeug):
    """`ruff check` und `ruff format --check` — Befunde in einer Tabelle."""

    slug = "ruff"
    kriterium = 0
    titel = "ruff (Linter und Formatierer)"
    zweck = (
        "Fährt `ruff check` (pyflakes, pycodestyle, isort, bugbear, "
        "pyupgrade) und `ruff format --check` über den Quelltext — mit "
        "den Regeln des Projekts oder der djangoBase-Vorgabe."
    )
    befund = (
        "In gunSlinger hat ruff vor jedem Commit ungenutzte Einfuhren, "
        "einen `tuple[str, str]`-Typfehler und Importreihenfolgen "
        "gefunden, bevor ein Mensch die Datei sah; der Formatierer "
        "beendet jede Stilfrage mechanisch."
    )
    abhilfe = (
        "`ruff check --fix .` und `ruff format .` im Projekt — als "
        "eigener Commit „nur Formatierung“. Ohne eigene Konfiguration "
        "`--config A:/shared/djangoBase/djangobase/ruff_vorgabe.toml "
        "--target-version py3XX` (Version des Projekt-Interpreters) "
        "anhängen."
    )
    dauer = "unter 2 s auch bei 700 Dateien (ruff ist in Rust geschrieben)"

    anlassfall = Anlassfall(
        {
            "kaputt.py": ("import os\n\n\ndef lesen(pfad):\n    return offen(pfad).read()\n"),
            "krumm.py": ("x = {'a':1,'b':2}\n"),
        },
        mindestens=2,
        hoechstens=2,
        erwartet_in="kaputt.py",
        warum="`offen` gibt es nicht (F821, ein Fehler, der erst beim Aufruf "
        "knallt); `krumm.py` ist ungeformt; und `os` wird nicht "
        "gebraucht — das zählt für `tote-importe` und darf hier NICHT "
        "als dritte Zeile auftauchen (hoechstens=2 wacht darüber)",
    )

    #: Die Konfigurationsdateien, die ruff selbst findet. Liegt eine davon
    #: in der Projektwurzel, wird KEINE Vorgabe übergeben.
    EIGENE = ("ruff.toml", ".ruff.toml")
    #: Die Vorgabe für Projekte ohne eigene Regeln — im Paket, damit sie mit
    #: `pip install -e` überall dieselbe ist.
    VORGABE = Path(__file__).resolve().parent.parent / "ruff_vorgabe.toml"

    #: Befunde, die ein anderes Werkzeug führt: Code → Kennung des Werkzeugs.
    ANDERSWO = {"F401": "tote-importe", "F541": "fix-fzeichenkette"}

    #: Regeln, deren Verstoß zur Laufzeit knallt — schwerste Stufe.
    #: F821/F822/F823 undefinierte Namen, F811 doppelt definiert (die ältere
    #: Fassung läuft nie), F5xx/F6xx kaputte Formatierung und Vergleiche,
    #: F7xx `return`/`yield` an unmöglicher Stelle.
    FEHLER_AB = ("F5", "F6", "F7", "F811", "F82")
    #: Formsachen — Zeilenlänge, Leerraum, Importreihenfolge.
    HINWEIS_AB = ("E", "W", "I")
    #: So kennzeichnet ruff einen Syntaxfehler: ohne Code (alte Fassungen),
    #: `E999` (bis 0.4) oder `invalid-syntax` (seit 0.5).
    SYNTAX = ("", "E999", "invalid-syntax")

    #: So viele Zeichen Dateiliste je Aufruf. Windows kappt die Befehlszeile
    #: bei rund 32 000; 700 Dateien wären mehr. Lieber drei Aufrufe als ein
    #: Lauf über das ganze Verzeichnis: So sieht ruff DIESELBE Menge wie jedes
    #: andere Werkzeug (Ausschlussliste, `.gitignore`) — sonst wären die
    #: Zahlen nebeneinander nicht vergleichbar.
    JE_AUFRUF = 20_000

    def pruefen(self, **_argumente):
        if importlib.util.find_spec("ruff") is None:
            return Befundsatz(
                self.titel,
                [],
                [],
                fehler=(
                    "ruff ist nicht installiert — `pip install ruff` in der "
                    "Umgebung des Projekts (Extra „codequalitaet“ von djangoBase)"
                ),
            )
        wurzel = self.wurzel()
        dateien = sorted(self._relativ(p, wurzel) for p in self.projektdateien(".py"))
        kopf = ["%d Python-Dateien" % len(dateien), self._regelquelle(wurzel)]
        if not dateien:
            return Befundsatz(self.titel, kopf, [])
        befunde, anderswo = [], {}
        for meldung in self._check(wurzel, dateien):
            code = meldung.get("code") or ""
            if code in self.ANDERSWO:
                anderswo[code] = anderswo.get(code, 0) + 1
                continue
            befunde.append(self._befund(meldung, code))
        ungeformt = self._format(wurzel, dateien)
        for datei in ungeformt:
            befunde.append(
                Befund(
                    datei,
                    "ruff format — würde neu formatiert",
                    "Der Formatierer entscheidet Umbrüche und Leerraum "
                    "mechanisch; `ruff format` schreibt die Datei so, wie er "
                    "sie sehen will.",
                    Befund.HINWEIS,
                )
            )
        kopf.append("%d Meldungen von `ruff check`" % (len(befunde) - len(ungeformt)))
        kopf.append("%d Dateien ungeformt" % len(ungeformt))
        for code, zahl in sorted(anderswo.items()):
            kopf.append("%d× %s → %s" % (zahl, code, self.ANDERSWO[code]))
        rang = {Befund.FEHLER: 0, Befund.WARNUNG: 1, Befund.HINWEIS: 2}
        befunde.sort(key=lambda b: (rang.get(b.gewicht, 3), b.ort))
        return Befundsatz(self.titel, kopf, befunde)

    # ------------------------------------------------------------ ruff rufen

    def _check(self, wurzel, dateien):
        """Alle Meldungen von `ruff check` als Liste von Dictionaries."""
        meldungen = []
        for stapel in self._stapel(dateien):
            lauf = self._ruff(wurzel, ["check", "--output-format", "json", "--exit-zero"] + stapel)
            if lauf.returncode != 0:
                raise RuntimeError("ruff check: %s" % (lauf.stderr or lauf.stdout).strip()[:300])
            meldungen += json.loads(lauf.stdout or "[]")
        return meldungen

    #: Zwei Ausgabeformen von `ruff format --check`: bis 0.15 eine Zeile
    #: „Would reformat: pfad", seit 0.16 ein Block „unformatted: File would
    #: be reformatted" mit „ --> pfad:zeile:spalte" darunter. Beide gelesen,
    #: sonst meldet das Werkzeug nach dem naechsten ruff-Update still null.
    UNGEFORMT = (re.compile(r"^Would reformat: (.+?)\s*$"), re.compile(r"^\s*--> (.+?):\d+:\d+\s*$"))

    def _format(self, wurzel, dateien):
        """Die Dateien, die `ruff format` ändern würde — relative Pfade."""
        ungeformt = set()
        for stapel in self._stapel(dateien):
            lauf = self._ruff(wurzel, ["format", "--check"] + stapel)
            # 0 = alles geformt, 1 = es gäbe etwas zu tun; alles andere ist
            # ein Abbruch (Syntaxfehler stehen dann in stderr, der Rest
            # der Dateien wurde trotzdem geprüft).
            for zeile in lauf.stdout.splitlines():
                for muster in self.UNGEFORMT:
                    treffer = muster.match(zeile)
                    if treffer:
                        ungeformt.add(self._relativ(Path(treffer.group(1)), wurzel))
        return sorted(ungeformt)

    def _ruff(self, wurzel, argumente):
        befehl = [sys.executable, "-m", "ruff"] + argumente
        vorgabe = self._vorgabe(wurzel)
        if vorgabe:
            # DIE VERSION DES PROJEKTS, NICHT DIE DER VORGABE (18.09.2026):
            # Mit festem `py310` meldete ruff im assistant (Python 3.14) 58
            # „Syntaxfehler" — Zeilenumbrueche in f-Strings, seit 3.12
            # erlaubt. Das Werkzeug laeuft im Interpreter des Projekts, also
            # ist dessen Version die richtige. Bei EIGENER Konfiguration
            # bleibt es bei der: Ein Projekt darf bewusst aelter zielen.
            befehl[3:3] = ["--config", str(vorgabe), "--target-version", self._zielversion()]
        lauf = subprocess.run(
            befehl, cwd=str(wurzel), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if lauf.returncode not in (0, 1) and vorgabe and "target-version" in (lauf.stderr or ""):
            # Ein ruff, das diese Python-Version noch nicht kennt: lieber
            # ohne Zielversion als gar nicht.
            befehl = [a for a in befehl if a not in ("--target-version", self._zielversion())]
            lauf = subprocess.run(
                befehl, cwd=str(wurzel), capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        return lauf

    @staticmethod
    def _zielversion():
        return "py%d%d" % sys.version_info[:2]

    def _stapel(self, dateien):
        """Die Dateiliste in Stücke, die auf eine Befehlszeile passen."""
        stapel, laenge = [], 0
        for datei in dateien:
            if stapel and laenge + len(datei) + 3 > self.JE_AUFRUF:
                yield stapel
                stapel, laenge = [], 0
            stapel.append(datei)
            laenge += len(datei) + 3
        if stapel:
            yield stapel

    # ---------------------------------------------------------- Regelquelle

    def _vorgabe(self, wurzel):
        """Die djangoBase-Vorgabe — oder None, wenn das Projekt eigene hat."""
        return None if self._eigene(wurzel) else self.VORGABE

    def _eigene(self, wurzel):
        """Der Name der projekteigenen Konfiguration, sonst ``""``."""
        for name in self.EIGENE:
            if (wurzel / name).is_file():
                return name
        pyproject = wurzel / "pyproject.toml"
        if pyproject.is_file():
            try:
                text = pyproject.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
            if "[tool.ruff" in text:
                return "pyproject.toml"
        return ""

    def _regelquelle(self, wurzel):
        eigene = self._eigene(wurzel)
        if eigene:
            return "Regeln: %s des Projekts" % eigene
        return "Regeln: djangoBase-Vorgabe (djangobase/ruff_vorgabe.toml)"

    # ---------------------------------------------------------------- Befund

    def _befund(self, meldung, code):
        ort = self._relativ(Path(meldung.get("filename", "")), self.wurzel())
        stelle = meldung.get("location") or {}
        if stelle.get("row"):
            ort = "%s:%d" % (ort, stelle["row"])
        text = meldung.get("message", "")
        if code in self.SYNTAX:
            # Syntaxfehler: die Datei läuft gar nicht — schwerste Stufe.
            return Befund(ort, "Syntaxfehler", text, Befund.FEHLER)
        was = "%s — %s" % (code, text)
        adresse = meldung.get("url") or ""
        return Befund(ort, was, adresse, self._gewicht(code))

    def _gewicht(self, code):
        if code.startswith(self.FEHLER_AB):
            return Befund.FEHLER
        if code.startswith(self.HINWEIS_AB):
            return Befund.HINWEIS
        return Befund.WARNUNG

    @staticmethod
    def _relativ(pfad, wurzel):
        try:
            return str(Path(pfad).relative_to(wurzel)).replace("\\", "/")
        except ValueError:
            return str(pfad).replace("\\", "/")
