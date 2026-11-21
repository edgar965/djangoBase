# -*- coding: utf-8 -*-
"""Tabellen als Karten auf dem Handy — Opt-in je Spalte (21.11.2026, StayNestor-Heizung; Edgar: „Die Tabellen
müssen aber noch angepasst werden, damit sie auf dem Handy bedienbar sind").

``TabellenDaten.spalte(..., handy=…)`` gibt einer Spalte ihre Rolle in der Karte:

- ``titel``: oben in der Karte, groß, ohne Beschriftung (der Name),
- ``kopf``: oben neben dem Titel, klein beschriftet (Ist, Soll),
- ``karte``: darunter als Zeile „Beschriftung: Wert“,
- ``mehr``: erst nach Tippen auf „mehr“ (``js/tabellen_handy.js``).

Spalten ohne Rolle zählen als ``mehr``. Hat keine Spalte eine Rolle, bleibt die Tabelle, wie sie war.

``vorbereiten`` schreibt Beschriftung und Rolle an jede Zelle (``label``/``handy`` → ``data-label``/
``data-handy`` in ``_tabelle.html``) und nennt die Tabellenklasse ``db-handy``;
``css/tabellen_handy.css`` macht daraus bis 768 px Karten, darüber ändert sich nichts. Serverseitig
statt im Browser, damit auch Tabellen stimmen, die eine Seite per ``innerHTML`` nachlädt. Zeilen mit
fertiger Zellenkette (``html``) und Abschnittszeilen (``gruppe``) bleiben unberührt.
"""

from __future__ import annotations

from django.utils.html import strip_tags


class TabellenHandy:
    ROLLEN = ("titel", "kopf", "karte", "mehr")
    KLASSE = "db-handy"

    @classmethod
    def vorbereiten(cls, spalten: list, zeilen: list) -> str:
        """Zellen beschriften; gibt ``KLASSE`` zurück oder "" (keine Spalte hat eine Rolle)."""
        rollen = [s.get("handy", "") for s in spalten]
        if not any(rollen):
            return ""
        unbekannt = set(rollen) - set(cls.ROLLEN) - {""}
        if unbekannt:
            raise ValueError("Unbekannte Handy-Rolle: %s" % ", ".join(sorted(unbekannt)))
        beschriftungen = [strip_tags(str(s.get("label", ""))).strip() for s in spalten]
        for zeile in zeilen:
            if zeile.get("html") or zeile.get("gruppe"):
                continue
            zeile["zellen"] = cls._zellen(zeile.get("zellen", []), beschriftungen, rollen)
        return cls.KLASSE

    @staticmethod
    def _zellen(zellen: list, beschriftungen: list, rollen: list) -> list:
        """Kopien der Zellen mit ``label`` und ``handy`` — Kopien, weil Aufrufer dieselbe Zelle (etwa eine
        leere) in mehreren Spalten verwenden dürfen. ``colspan`` rückt die folgenden Spalten weiter."""
        neu, spalte = [], 0
        for zelle in zellen:
            if spalte < len(rollen):
                zelle = {"label": beschriftungen[spalte], "handy": rollen[spalte] or "mehr", **zelle}
            neu.append(zelle)
            spalte += int(zelle.get("colspan") or 1)
        return neu
