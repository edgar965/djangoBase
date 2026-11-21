# -*- coding: utf-8 -*-
"""Daten für ``{% include "djangobase/_tabelle.html" with tabelle=… %}`` aus Python bauen.

Die Vorlage erwartet ``{key, spalten, zeilen, leer}``: Spalten ``{label, key, num, sortAus}``, Zeilen
``{zellen: [...], id?, klasse?}``, Zellen ``{html, sort?, klasse?, titel?}`` (``html`` rendert sie
``|safe`` — darum escapt ``zelle`` den Text). ``tabellen_auto.js`` bindet Sortierung und ziehbare
Spalten an jede so gebaute Tabelle.

Vorher lagen ``sp``/``z``/``tab`` in ``search.hilfe_bot_tabellen`` des assistant (09.09.2026) und
wurden von dort auch von Heizung, Mail und Bot geholt. Seit 18.11.2026 stehen sie hier, neben der
Vorlage, die sie füllen (Edgar: „erzeuge mir keinen doppelten code"; die Heizung soll später nach
StayNestor umziehen, das djangoBase auch nutzt). ``search.hilfe_bot_tabellen`` gibt sie weiter.
"""

from __future__ import annotations

from django.utils.html import escape, format_html

from .sortierschluessel import Sortierschluessel
from .tabellen_handy import TabellenHandy


class TabellenDaten:
    """Ohne Zustand — baut nur die Wörterbücher, die die Vorlage liest."""

    @staticmethod
    def spalte(label: str, key: str, num: bool = False, sort_aus: bool = False, handy: str = "") -> dict:
        """Eine Spalte; ``key`` benennt sie für gemerkte Breiten, Reihenfolge und Sortierung. ``handy``:
        Rolle in der Handy-Karte (``titel``/``kopf``/``karte``/``mehr``, ``TabellenHandy``)."""
        spalte = {"label": label, "key": key, "num": num, "sortAus": sort_aus}
        if handy:
            spalte["handy"] = handy
        return spalte

    @staticmethod
    def zelle(text, sort=None, klasse: str = "", fett: bool = False) -> dict:
        """Eine Zelle aus Klartext. ``sort`` ist der Rohwert für die Sortierung."""
        html = format_html("<strong>{}</strong>", text) if fett else escape(text)
        zelle: dict[str, object] = {"html": html}
        if sort is not None:
            zelle["sort"] = Sortierschluessel.aus(sort)
        if klasse:
            zelle["klasse"] = klasse
        return zelle

    @staticmethod
    def tabelle(kennung: str, spalten: list, zeilen: list, leer: str = "keine Einträge") -> dict:
        """Eine Tabelle. ``kennung`` ist ihr Name für die Vorlage (``key`` dort) — nicht zu
        verwechseln mit dem ``key`` einer Spalte. Haben Spalten eine Handy-Rolle, werden die Zellen
        beschriftet und die Tabelle bekommt die Klasse ``db-handy`` (``TabellenHandy``)."""
        tabelle = {"key": kennung, "spalten": spalten, "zeilen": zeilen, "leer": leer}
        klasse = TabellenHandy.vorbereiten(spalten, zeilen)
        if klasse:
            tabelle["klasse"] = klasse
        return tabelle


#: Kurznamen, unter denen die Aufrufer sie seit 09.09.2026 kennen
sp = TabellenDaten.spalte
z = TabellenDaten.zelle
tab = TabellenDaten.tabelle
