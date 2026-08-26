# -*- coding: utf-8 -*-
u"""Tests der Gitabfrage — der Cache darf NICHTS am Ergebnis aendern.

Anlass (17.08.2026): `/help/versionen/` brauchte 690 ms warm bei 0 SQL-Abfragen.
650 ms davon waren zwoelf `git`-Prozesse (vier Repos mal drei Befehle), jeder
rund 50 ms — Prozessstart unter Windows. Mit Cache: 28 ms.

Ein Cache ist die gefaehrlichste Art von Beschleunigung: Er wirkt, bis er einen
veralteten Wert ausliefert, den niemand erwartet. Deshalb prueft der erste Test
nicht die Geschwindigkeit, sondern dass **derselbe Wert** herauskommt.
"""
from django.test import override_settings

from djangobase.gitabfrage import Gitabfrage

from ..base import BasisTest


class GitabfrageTest(BasisTest):

    def setUp(self):
        Gitabfrage.leeren()
        self.addCleanup(Gitabfrage.leeren)
        self.laeufe = []
        # `_roh` ist eine staticmethod; ueber die Klasse gelesen ist es eine
        # gewoehnliche Funktion. Fuer die Rueckgabe muss sie wieder als
        # staticmethod gesetzt werden, sonst bekaeme sie die Klasse als
        # erstes Argument.
        echt = Gitabfrage.__dict__["_roh"]

        def spion(repo, args, timeout):
            self.laeufe.append((str(repo), args))
            return "AUSGABE\n"

        Gitabfrage._roh = staticmethod(spion)
        self.addCleanup(setattr, Gitabfrage, "_roh", echt)

    def test_zweiter_aufruf_startet_keinen_prozess(self):
        a = Gitabfrage.lauf("/repo", "status", "--porcelain")
        b = Gitabfrage.lauf("/repo", "status", "--porcelain")
        self.assertEqual(a, b)
        self.assertEqual(len(self.laeufe), 1, self.laeufe)

    def test_andere_argumente_sind_ein_anderer_schluessel(self):
        u"""Sonst liefert `rev-parse` die Antwort von `status`."""
        Gitabfrage.lauf("/repo", "status")
        Gitabfrage.lauf("/repo", "rev-parse", "HEAD")
        Gitabfrage.lauf("/anderes", "status")
        self.assertEqual(len(self.laeufe), 3, self.laeufe)

    def test_leeren_erzwingt_neuen_aufruf(self):
        Gitabfrage.lauf("/repo", "status")
        Gitabfrage.leeren()
        Gitabfrage.lauf("/repo", "status")
        self.assertEqual(len(self.laeufe), 2, self.laeufe)

    @override_settings(DJANGOBASE={"git_cache_sekunden": 0})
    def test_haltbarkeit_null_schaltet_den_cache_ab(self):
        u"""Damit ein Projekt, dem 20 s zu lang sind, ihn ausschalten kann."""
        Gitabfrage.lauf("/repo", "status")
        Gitabfrage.lauf("/repo", "status")
        self.assertEqual(len(self.laeufe), 2, self.laeufe)

    def test_haltbarkeit_vorgabe(self):
        self.assertEqual(Gitabfrage.haltbarkeit(), 20.0)


class GitabfrageEchtTest(BasisTest):
    u"""Gegen das echte `git` — ohne Attrappe."""

    def setUp(self):
        Gitabfrage.leeren()
        self.addCleanup(Gitabfrage.leeren)

    def test_kein_repo_gibt_leerstring(self):
        u"""Die Versionen-Seite muss auch ohne git stehen — das war schon vor
        dem Cache so und darf sich nicht geändert haben."""
        self.assertEqual(Gitabfrage.lauf("/gibt/es/nicht", "status"), "")

    def test_eigenes_repo_liefert_einen_head(self):
        from pathlib import Path

        import djangobase
        wurzel = Path(djangobase.__file__).resolve().parent.parent
        if not (wurzel / ".git").exists():
            self.skipTest("kein Git-Repo — nichts zu vergleichen")
        head = Gitabfrage.lauf(wurzel, "rev-parse", "--short=7", "HEAD").strip()
        self.assertRegex(head, r"^[0-9a-f]{7}$")
        # Zweiter Aufruf aus dem Cache: gleicher Wert, nicht etwa leer.
        self.assertEqual(
            Gitabfrage.lauf(wurzel, "rev-parse", "--short=7", "HEAD").strip(),
            head)
