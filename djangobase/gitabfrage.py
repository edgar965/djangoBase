# -*- coding: utf-8 -*-
u"""Gitabfrage - `git` aufrufen, aber nicht bei jedem Seitenaufruf neu.

DER BEFUND (3DTools, 17.08.2026, im Ablauf gemessen)
===================================================
`/help/versionen/` brauchte **690 ms warm** — bei **0 SQL-Abfragen**. Das
Profil zeigte 650 ms davon in genau einer Funktion: zwoelf `git`-Aufrufen.

    60 ms  HumanBodyWeb      git remote get-url origin
    53 ms  HumanBodyWeb      git rev-parse --short=7 HEAD
    51 ms  HumanBodyWeb      git status --porcelain
    ...                      (dasselbe fuer vier Repos)
   163 ms  HumanBody         git status --porcelain
   ------
   724 ms  zusammen

Nicht `git` ist langsam, sondern **das Starten eines Prozesses unter Windows**:
Jeder der zwoelf Aufrufe kostet rund 50 ms, unabhaengig davon, wie wenig er zu
tun hat. Vier Repos mal drei Befehle — und das bei jedem Aufruf der Seite.

WARUM EIN CACHE UND KEIN NACHBAU
================================
Zwei der drei Angaben liessen sich ohne Prozess lesen (`.git/HEAD`,
`.git/config`). Das waere ein Nachbau von git-Innereien: gepackte Refs,
Symrefs, `worktree`-Dateien, abgetrennter HEAD. Ein falsch gelesener HEAD
zeigt in **sechs Projekten** die falsche Version an — der Gewinn von 100 ms
rechtfertigt dieses Risiko nicht.

Stattdessen dieselbe Antwort wie fuer die `gh api`-Aufrufe daneben: ein Cache
mit Haltbarkeit. Der Arbeitsstand eines Repos aendert sich nicht im
Sekundentakt, und die Seite zeigt eine Versions-HISTORIE.

    erster Aufruf   ~690 ms (wie bisher)
    danach          ~0 ms fuer die Dauer der Haltbarkeit

HALTBARKEIT: `DJANGOBASE["git_cache_sekunden"]`, Vorgabe 20 s. Wer gerade
committet hat, sieht die Anzahl der offenen Aenderungen also bis zu 20 s lang
noch alt. Das ist der Preis, er steht hier.
"""
import subprocess
import threading
import time

from django.conf import settings

__all__ = ["Gitabfrage"]

#: `CREATE_NO_WINDOW` gibt es nur unter Windows - sonst 0.
_KEIN_FENSTER = getattr(subprocess, "CREATE_NO_WINDOW", 0)
#: Vorgabe der Haltbarkeit in Sekunden.
VORGABE_HALTBARKEIT = 20.0


class Gitabfrage:
    u"""Ruft `git` in einem Repo auf und behaelt die Antwort kurz.

    Bewusst KEIN Klassenzustand pro Instanz: Der Cache ist prozessweit, denn
    zwei Anfragen nacheinander sollen sich den Aufruf teilen.
    """

    _werte = {}
    _schloss = threading.Lock()

    @staticmethod
    def haltbarkeit():
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get(
            "git_cache_sekunden")
        return float(eigen) if eigen is not None else VORGABE_HALTBARKEIT

    @classmethod
    def lauf(cls, repo, *args, timeout=5):
        u"""Ausgabe von `git -C <repo> <args>`; Leerstring bei jedem Fehler.

        Ein leerer Rueckgabewert bei Fehlern ist Absicht und aelter als dieser
        Cache: Die Versionen-Seite soll auch dann stehen, wenn `git` fehlt, das
        Verzeichnis kein Repo ist oder der Aufruf in die Zeitgrenze laeuft.
        """
        schluessel = (str(repo), args)
        jetzt = time.time()
        with cls._schloss:
            treffer = cls._werte.get(schluessel)
            if treffer and (jetzt - treffer[0]) < cls.haltbarkeit():
                return treffer[1]
        wert = cls._roh(repo, args, timeout)
        with cls._schloss:
            cls._werte[schluessel] = (time.time(), wert)
        return wert

    @classmethod
    def leeren(cls):
        u"""Cache verwerfen - fuer Tests und nach einem Commit aus der App."""
        with cls._schloss:
            cls._werte.clear()

    @staticmethod
    def _roh(repo, args, timeout):
        try:
            lauf = subprocess.run(["git", "-C", str(repo), *args],
                                  capture_output=True, text=True,
                                  timeout=timeout, encoding="utf-8",
                                  errors="replace",
                                  creationflags=_KEIN_FENSTER)
            return lauf.stdout if lauf.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""
