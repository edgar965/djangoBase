# -*- coding: utf-8 -*-
"""Commits eines Repos aus GitHub holen — die letzten `per_page` oder ALLE, seitenweise.

WARUM (Edgar, 11.10.2026, 3dTools: „mach die Historie mit ALLEN Commits")
------------------------------------------------------------------------
Die GitHub-Schnittstelle gibt je Aufruf höchstens 100 Commits her (`per_page`).
Hilfe → Versionen zeigte deshalb je Repo nur die letzten 100 — in HumanBodyWeb
(590 Commits) fehlten 490, und wer einen Stand von vor drei Wochen suchte,
fand ihn dort nicht. `version_commits_alle` (Konfiguration, Vorgabe aus) holt
die Seiten nacheinander (`page=1, 2, …`), bis eine weniger als `per_page`
liefert. Die Liste geht danach durch denselben Zwischenspeicher wie bisher
(`_GH_CACHE`, 300 s); nur der allererste Abruf braucht entsprechend mehr
Aufrufe (gemessen 11.10.2026, vier Repos mit zusammen 1.177 Commits: 15 s).
"""

import json
import logging

logger = logging.getLogger(__name__)


class Commitseiten:
    #: Obergrenze der Seiten (je `per_page` Commits) — Schutz gegen eine
    #: Schnittstelle, die nie kürzer antwortet.
    SEITEN_MAX = 100

    @classmethod
    def holen(cls, gh, repo, per_page, alle=False):
        """Die rohen Commit-Wörterbücher der Schnittstelle, neueste zuerst.

        `gh(args)` → `(Rückgabecode, Ausgabe, Fehler)` wie `versions._gh`.
        `alle` falsch: ein Aufruf mit `per_page` (wie bisher). Scheitert schon
        die erste Seite, ist die Liste leer; scheitert eine spätere, bleibt das
        bis dahin Geholte (mit Warnung im Log) — die Seite zeigt dann weniger,
        nie nichts."""
        if not alle:
            return cls._seite(gh, repo, per_page, None) or []
        gesamt = []
        for nummer in range(1, cls.SEITEN_MAX + 1):
            seite = cls._seite(gh, repo, per_page, nummer)
            if seite is None:
                if nummer > 1:
                    logger.warning(
                        "Versionen: %s Seite %d nicht lesbar — %d Commits bis hierher",
                        repo, nummer, len(gesamt),
                    )
                break
            gesamt.extend(seite)
            if len(seite) < per_page:
                break
        else:
            logger.warning(
                "Versionen: %s hat mehr als %d Seiten — abgeschnitten bei %d Commits",
                repo, cls.SEITEN_MAX, len(gesamt),
            )
        return gesamt

    @staticmethod
    def _seite(gh, repo, per_page, nummer):
        """Eine Seite (Liste) oder `None`, wenn der Aufruf oder das JSON scheitert."""
        adresse = f"repos/{repo}/commits?per_page={per_page}"
        if nummer is not None:
            adresse += f"&page={nummer}"
        rc, out, _fehler = gh([adresse])
        if rc != 0:
            return None
        try:
            daten = json.loads(out or "[]")
        except json.JSONDecodeError:
            return None
        return daten if isinstance(daten, list) else None
