# -*- coding: utf-8 -*-
u"""Altlast - ungenutzter Code und aufgehobene Alt-Staende.

    Kriterium 5 des Auftrags: „Entferne ungenutzten Code, kein alter Code
    (Legacy), der als Sicherung noch behalten wurde"

DREI SORTEN
===========
* Ordner, die ausdruecklich Altstaende halten (``sicherung``, ``backup``,
  ``alt``). Git IST die Sicherung - ein Ordner daneben ist eine zweite Wahrheit.
* Module, die nirgends importiert werden und kein Einstiegspunkt sind.
* Funktionen und Klassen, deren Name im ganzen Projekt genau EINMAL vorkommt:
  an ihrer eigenen Definition.

DIE GRENZE DER METHODE - und warum sie hier trotzdem taugt
==========================================================
Ein Namensvergleich findet keinen Aufruf ueber ``getattr(obj, name)``, keinen
aus einem Template und keinen aus JavaScript. Deshalb werden Vorlagen und
JS-Dateien MITDURCHSUCHT, und Django-Sonderfaelle (Views, Commands,
Migrationen, Tests) bleiben aussen vor.

Was danach uebrig bleibt, ist ein begruendeter VERDACHT - keine Freigabe zum
Loeschen. Ein Pruefwerk dieser Art hat in shortlongx einmal 122 lebende Namen
fuer tot erklaert; seither steht der Satz in jedem Befund.
"""
import ast
import re
from collections import Counter

from .werkzeug import AUSGESCHLOSSEN, Ergebnis, Werkzeug2


class Altlast(Werkzeug2):
    slug = "altlast"
    titel = "Alter und ungenutzter Code"
    zweck = ("Sicherungs-Ordner, nie importierte Module und Namen, die im ganzen "
             "Projekt nur an ihrer Definition vorkommen.")
    befund = ("Ein Sicherungsordner mit 405 Dateien neben dem Code — und "
              "Funktionen, die seit einem Umbau niemand mehr ruft.")
    abhilfe = ("Sicherungsordner löschen (Git hält den Stand). Bei einzelnen "
               "Namen erst nachsehen: Ein Verdacht ist keine Freigabe.")
    dauer = "5–15 s"
    kriterium = 5

    #: Verdaechtige Ordnernamen - dieselben, die auch die Suche ausschliesst.
    SICHERUNGSNAMEN = {"sicherung", "backup", "archiv", "alt", "_alt", "old"}
    EINSTIEGE = {"main", "haupt", "handle", "run", "ready", "setUp", "tearDown"}

    def laufen(self):
        wurzel = self.wurzel()
        zeilen = []
        # 1) Sicherungsordner - die stehen sonst gar nicht in der Suche.
        for p in sorted(wurzel.rglob("*")):
            if not p.is_dir() or p.name not in self.SICHERUNGSNAMEN:
                continue
            if any(t in AUSGESCHLOSSEN - self.SICHERUNGSNAMEN for t in p.parts):
                continue
            anzahl = len(list(p.rglob("*.py")))
            if anzahl:
                zeilen.append({"art": "Sicherungsordner",
                               "datei": p.relative_to(wurzel).as_posix(),
                               "zeile": 0, "name": p.name,
                               "hinweis": "%d Python-Dateien" % anzahl})
        # 2) Namen, die nur an ihrer Definition vorkommen.
        #
        # EINMAL ZÄHLEN, DANN NACHSCHLAGEN (Korrektur beim ersten Lauf): Die
        # erste Fassung suchte je Namen einmal durch den gesamten Quelltext -
        # bei 1.400 Namen und 15 MB Text lief sie in die Zeitüberschreitung.
        # Genau der Fehler, den das Nachbarwerkzeug „Arbeit in Schleifen"
        # meldet; hier stand er im Prüfer selbst.
        dateien = self.dateien()
        haeufigkeit = self._woerter_zaehlen(dateien)
        for d in dateien:
            if d.baum is None or self._sonderfall(d):
                continue
            for k in d.baum.body:
                if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if k.name in self.EINSTIEGE or k.name.startswith("__"):
                    continue
                if haeufigkeit.get(k.name, 0) <= 1:
                    zeilen.append({
                        "art": "Klasse" if isinstance(k, ast.ClassDef) else "Funktion",
                        "datei": d.name, "zeile": k.lineno, "name": k.name,
                        "hinweis": "Name kommt nur an der Definition vor — nachsehen, "
                                   "nicht blind löschen"})
        return Ergebnis(
            ["art", "datei", "zeile", "name", "hinweis"], zeilen,
            "%d Verdachtsfälle" % len(zeilen),
            "Ein Namensvergleich sieht keine dynamischen Aufrufe. Vorlagen und "
            "JS sind mitdurchsucht; alles Übrige ist ein Verdacht, kein Urteil.")

    def _woerter_zaehlen(self, dateien):
        """{Wort: Anzahl} über den gesamten Quelltext - Python, Vorlagen, JS.

        Ein Durchlauf, ein Zähler. Danach kostet jede Frage „kommt der Name
        anderswo vor?" einen Nachschlag statt einer Volltextsuche."""
        zaehler = Counter()
        muster = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        for d in dateien:
            zaehler.update(muster.findall(d.text))
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for endung in ("*.html", "*.js", "*.mjs", "*.txt", "*.cfg", "*.toml"):
            for p in wurzel.rglob(endung):
                if any(t in raus for t in p.parts):
                    continue
                try:
                    if p.stat().st_size > 2_000_000:      # Datendateien überspringen
                        continue
                    zaehler.update(muster.findall(
                        p.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    continue
        return zaehler

    @staticmethod
    def _sonderfall(d):
        name = d.name
        return ("/migrations/" in name or "/management/commands/" in name
                or name.endswith(("/urls.py", "/admin.py", "/apps.py",
                                  "/settings.py", "/views.py"))
                or "/tests" in name or "test_" in name.rsplit("/", 1)[-1])
