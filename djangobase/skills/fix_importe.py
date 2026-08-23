# -*- coding: utf-8 -*-
u"""ImportFixer - tote Importe entfernen, auf der skills2-Fixer-Basis.

WARUM AUF ``skills2.fixer.Fixer``
================================
Diese Basis bringt mit, was aggressives Fixen erst verantwortbar macht: eine
SICHERUNG (das Original wandert mit Zeitstempel nach ``werkzeug/sicherung/fixer``)
und ein NETZ (nach dem Schreiben ``pruefen``; faellt es, wird die Datei
zurueckgespielt statt kaputt liegengelassen). skills2 hat keinen Import-Fixer -
dieser ergaenzt die dortigen Fixer (``fix-vermerk``, ``fix-jsschnitt``) um
Kriterium 5, ohne die Basis zu duplizieren.

VIER SICHERUNGEN, DAMIT NUR EINDEUTIG TOTES FAELLT
==================================================
* Seiteneffekt-Module (``signals`` & Co.) bleiben - ihr Import registriert
  Handler, ohne einen Namen zu benutzen.
* ``__init__.py`` bleibt aussen vor (Re-Exporte ohne ``__all__``).
* Nur EINZEILIGE Anweisungen, deren Name(n) ALLE unbenutzt sind - ein
  Teil-Entfernen aus ``import os, sys`` ist zu fehleranfaellig.
* ``__all__``-Eintraege und ``"app.Modell"``-Strings zaehlen als Verwendung.
"""
import ast

from .fixer import Aenderung, Fixer, Vorschau

__all__ = ["ImportFixer"]

#: Verzeichnisse, die nie eigener Projektcode sind (auch Fremd-/Datenordner).
RAUS = ("__pycache__", "migrations", "node_modules", "venv", "pythonVENV",
        ".venv", "site-packages", "staticfiles", ".git", "sicherung", "backup",
        "archiv", "dist", "build", "vendor", "models", "unsloth_compiled_cache")


class ImportFixer(Fixer):
    slug = "tote-importe"
    titel = "Tote Importe entfernen"
    tut = "Entfernt importierte Namen, die in der Datei nirgends vorkommen."
    warum = ("Tote Importe kosten Ladezeit, halten Abhaengigkeiten kuenstlich am "
             "Leben und verwischen, welches Modul wirklich wovon abhaengt.")
    grenzen = ("Seiteneffekt-Importe (signals, admin) und __init__.py bleiben. "
               "Mehrfach-Importe (import os, sys) bleiben, wenn nur einer tot ist.")
    kriterium = 5
    dauer = "3-8 s"

    #: Modul-Endungen, deren blosser Import etwas bewirkt - nie entfernen.
    SEITENEFFEKT = {"signals", "admin", "receivers", "tasks", "checks", "apps"}
    ERLAUBT = {"annotations"}

    def vorschau(self):
        aenderungen = []
        for pfad in self._pyquellen():
            try:
                quelle = pfad.read_text(encoding="utf-8")
                baum = ast.parse(quelle)
            except (OSError, SyntaxError, ValueError):
                continue
            weg = self._tote_zeilen(baum, self._benutzt(baum))
            zeilen = quelle.splitlines(keepends=True)
            # `# noqa` ist die ausdrueckliche Ansage des Autors: unbenutzt,
            # aber gewollt (Weiterleitung, Seiteneffekt, Abwaertskompatibilitaet).
            # Wer sie uebergeht, entfernt Zeilen, die jemand bewusst
            # stehengelassen hat - am 22.08.2026 im assistant passiert
            # (`from .dav_schalter import suppress_dav_push  # noqa: F401`).
            weg = {n for n in weg
                   if 'noqa' not in zeilen[n - 1].lower()}
            if not weg:
                continue
            neu = "".join(z for i, z in enumerate(zeilen, 1) if i not in weg)
            aenderungen.append(Aenderung(
                pfad, "%d tote Importe entfernen" % len(weg), neu))
        return Vorschau(aenderungen,
                        "Nur einzeilige Importe mit durchweg unbenutztem Namen; "
                        "Seiteneffekt-Module und __init__.py bleiben aussen vor.")

    def pruefen(self, aenderung):
        """Netz: kompiliert die Datei nach dem Schnitt noch?"""
        try:
            ast.parse(aenderung.pfad.read_text(encoding="utf-8"))
        except SyntaxError as e:
            return ["kompiliert nicht mehr: %s" % e]
        except OSError as e:
            return ["nicht lesbar: %s" % e]
        return []

    # ------------------------------------------------------------------ intern

    def _pyquellen(self):
        for pfad in self.pfade("*.py"):
            if pfad.name == "__init__.py":
                continue
            if any(t in RAUS for t in pfad.parts):
                continue
            yield pfad

    def _tote_zeilen(self, baum, benutzt):
        weg = set()
        for k in ast.walk(baum):
            if not isinstance(k, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(k, ast.ImportFrom):
                if k.module == "__future__":
                    continue
                if (k.module or "").rsplit(".", 1)[-1] in self.SEITENEFFEKT:
                    continue
                if k.level and not k.module:        # from . import x -> Verdacht
                    continue
            if k.lineno != getattr(k, "end_lineno", k.lineno):
                continue                            # mehrzeilig: nicht anfassen
            namen = [n for n in k.names if n.name != "*"]
            if not namen or any(n.name in self.SEITENEFFEKT for n in namen):
                continue
            if all(self._kurz(n) not in benutzt and self._kurz(n) not in self.ERLAUBT
                   for n in namen):
                weg.add(k.lineno)
        return weg

    @staticmethod
    def _kurz(name):
        return (name.asname or name.name).split(".")[0]

    @staticmethod
    def _benutzt(baum):
        benutzt = set()
        for k in ast.walk(baum):
            if isinstance(k, ast.Name):
                benutzt.add(k.id)
            elif isinstance(k, ast.Attribute):
                w = k
                while isinstance(w, ast.Attribute):
                    w = w.value
                if isinstance(w, ast.Name):
                    benutzt.add(w.id)
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                benutzt.update(k.value.replace(".", " ").replace("[", " ")
                               .replace("]", " ").split())
            elif isinstance(k, ast.Assign):
                for z in k.targets:
                    if isinstance(z, ast.Name) and z.id == "__all__":
                        for e in getattr(k.value, "elts", []):
                            if isinstance(e, ast.Constant):
                                benutzt.add(str(e.value))
        return benutzt
