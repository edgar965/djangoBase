# -*- coding: utf-8 -*-
u"""Wohin ein erzeugter Testfall geschrieben wird — und ob das erlaubt ist.

DER AUFTRAG (Edgar, 21.08.2026, Punkt 1)
========================================
    „Aus einer Aufzeichnung wird noch kein Testfall per Klick." — „mach 1 und 2"

Bis dahin ging das nur über ``manage.py testfall_aus_aufzeichnung --ziel …``.
Der Kommentar dort begründete das ausdrücklich:

    „Was hier entsteht, ist QUELLTEXT im Projekt … ein Knopf in der Oberfläche
     würde dazu einladen, ihn nebenbei zu drücken und die Datei nie anzusehen."

Das Argument bleibt richtig — deshalb steht es hier nicht auf dem Kopf, sondern
wird umgesetzt: Der Knopf schreibt die Datei, **zeigt danach ihren Pfad und die
Zahl der geprüften Abrufe**, und überschreibt niemals eine vorhandene Datei.
Wer sie nicht ansieht, hat trotzdem einen Test in der Suite, der beim nächsten
Lauf mitfährt — das ist besser als gar keinen, weil der Befehl zu umständlich
war.

DAS ZIELVERZEICHNIS
===================
Jedes Projekt legt seine UI-Tests woanders ab. Reihenfolge:

    1. ``DJANGOBASE_TESTFALL_ZIEL`` aus den Settings — die verlässliche Angabe.
    2. Gesucht wird unterhalb von ``BASE_DIR`` nach einem Verzeichnis, das auf
       ``tests…/ui`` endet (die djangoBase-Konvention ``tests/<bereich>/<art>/``).
    3. Nichts gefunden: eine Meldung, die sagt, welches Setting fehlt — kein
       geratener Ort. Eine Datei, die irgendwo landet, findet niemand wieder.
"""
from pathlib import Path

from django.conf import settings

#: Verzeichnisse, die nie durchsucht werden (schnell und ohne Überraschungen).
_TABU = {"node_modules", "__pycache__", "venv", "pythonVENV", ".git",
         "site-packages", "migrations", "static", "media"}


class TestfallAblage:
    u"""Findet das Zielverzeichnis und legt den Testfall dort ab."""

    def __init__(self, ziel=None):
        self._ziel = Path(ziel) if ziel else None

    # ------------------------------------------------------------- Ziel
    def ziel(self):
        u"""Das Verzeichnis für neue Testfälle — oder ``None``."""
        if self._ziel:
            return self._ziel if self._ziel.is_dir() else None
        aus_settings = getattr(settings, "DJANGOBASE_TESTFALL_ZIEL", "")
        if aus_settings:
            p = Path(aus_settings)
            return p if p.is_dir() else None
        return self._suchen()

    @staticmethod
    def _suchen():
        u"""Ein ``…/tests…/ui``-Verzeichnis unterhalb von BASE_DIR.

        Bewusst flach (höchstens sechs Ebenen) und ohne die Tabu-Ordner: Ein
        vollständiger Durchlauf über ein Projekt mit ``node_modules`` dauert
        Sekunden, und dieser Aufruf hängt an einem Knopfdruck."""
        wurzel = getattr(settings, "BASE_DIR", None)
        if not wurzel:
            return None
        wurzel = Path(wurzel)
        treffer = []
        for pfad in wurzel.rglob("ui"):
            if not pfad.is_dir():
                continue
            teile = pfad.relative_to(wurzel).parts
            if len(teile) > 6 or _TABU & set(teile):
                continue
            if any(t.startswith("test") for t in teile):
                treffer.append(pfad)
        # Der kürzeste Pfad ist der wahrscheinlichste: tiefer liegende sind
        # meist Unterordner eines Bereichs.
        return sorted(treffer, key=lambda p: len(p.parts))[0] if treffer else None

    # ------------------------------------------------------------- Schreiben
    def ablegen(self, fall):
        u"""Den Testfall schreiben. -> (pfad, meldung); ``pfad`` None bei Fehler.

        NICHT ÜBERSCHREIBEN: Eine vorhandene Datei kann von Hand ergänzte
        Zusicherungen tragen — genau die, die eine Aufnahme nicht kennt.
        """
        ordner = self.ziel()
        if ordner is None:
            return None, ("Kein Zielverzeichnis gefunden. Bitte "
                          "DJANGOBASE_TESTFALL_ZIEL in den Settings setzen.")
        pfad = ordner / fall.dateiname()
        if pfad.exists():
            return None, ("Es gibt schon %s — erst umbenennen oder löschen."
                          % pfad.name)
        try:
            pfad.write_text(fall.quelltext(), encoding="utf-8")
        except OSError as fehler:
            return None, "Schreiben fehlgeschlagen: %s" % fehler
        return pfad, "%s geschrieben (%d Abrufe geprüft)" % (pfad.name,
                                                             len(fall.abrufe()))
