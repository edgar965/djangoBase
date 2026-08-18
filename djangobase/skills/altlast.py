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

from .anlassfall import Anlassfall
from .werkzeug import AUSGESCHLOSSEN, Ergebnis, Werkzeug


class Altlast(Werkzeug):
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

    #: Ein Modul, das niemand importiert, und ein Name, der nur an seiner
    #: Definition vorkommt. Daneben ein SKRIPT (``__main__``) - das wird
    #: ausgefuehrt statt importiert und darf nicht als tot gelten; genau diese
    #: Verwechslung hat einmal Loeschvorschlaege fuer lebenden Code erzeugt.
    anlassfall = Anlassfall(
        {"benutzt.py": '''from .helfer import gebraucht


def haupt():
    return gebraucht()
''',
         "helfer.py": '''def gebraucht():
    return 1


def nie_gerufen():
    return 2
''',
         "tot.py": '''def niemand_importiert_mich():
    return 3
''',
         "werkzeug_start.py": '''import sys


def main():
    print("laeuft")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''},
        erwartet_in="tot.py",
        warum="„Modul wird nirgends erwähnt“ hielt fünf lebende Dateien für "
              "tot — die teuerste Sorte Fehlalarm")

    def laufen(self):
        wurzel = self.wurzel()
        zeilen = []
        # 1) Sicherungsordner - die stehen sonst gar nicht in der Suche.
        #
        # HIER ABSICHTLICH OHNE .gitignore-FILTER (18.08.2026): Ein
        # Sicherungsordner IST meistens ignoriert - genau ihn zu finden ist der
        # Zweck dieser Schleife. Wer hier `pfade()` einsetzt, schaltet den
        # Befund ab, statt ihn zu schaerfen. Der Filter greift unten in
        # `_woerter_zaehlen`, wo eine Erwaehnung in ignoriertem Code eine echte
        # Altlast faelschlich am Leben hielte.
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
        for endung in ("*.html", "*.js", "*.mjs", "*.txt", "*.cfg", "*.toml"):
            # Ueber `pfade()`: Eine Erwaehnung in ignoriertem Code ist kein
            # Beleg dafuer, dass ein Modul noch gebraucht wird - sie wuerde eine
            # echte Altlast als lebendig ausweisen.
            for p in self.pfade(endung):
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
        if ("/migrations/" in name or "/management/commands/" in name
                or name.endswith(("/urls.py", "/admin.py", "/apps.py",
                                  "/settings.py", "/views.py"))
                or "/tests" in name or "test_" in name.rsplit("/", 1)[-1]):
            return True
        return Altlast._ist_skript(d)

    @staticmethod
    def _ist_skript(d):
        """Wird diese Datei AUSGEFÜHRT statt importiert?

        Ein Skript darf Namen tragen, die nirgends sonst vorkommen — das ist
        sein Normalfall, kein Verdacht. Erkannt am Code selbst, nicht am Ordner:
        Wer auf Modulebene ``django.setup()`` ruft oder ausgibt, ist ein
        Einstiegspunkt. Eine Ausnahmeliste nach Ordnern rät stattdessen, was der
        Autor gemeint hat, und liegt beim nächsten Verzeichnis daneben.

        Anlass (shortlongx, 16.08.2026): zwei Diagnose-Skripte in ``depot/``
        standen als Löschvorschläge in der Liste — richtig gezählt und trotzdem
        falsch."""
        if "__main__" in d.text:
            return True
        for k in (d.baum.body if d.baum is not None else []):
            if not isinstance(k, ast.Expr) or not isinstance(k.value, ast.Call):
                continue
            ruf = k.value.func
            if (getattr(ruf, "id", None) or getattr(ruf, "attr", None) or "") in (
                    "print", "setup", "main", "exit"):
                return True
        return False
