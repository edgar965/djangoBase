# -*- coding: utf-8 -*-
u"""Statik - eine Kennung, die sich mit den mitgelieferten JS/CSS aendert.

DAS PROBLEM (gemessen am 17.08.2026)
====================================
Die Tests-Seite laedt ihre Module als ES-Import::

    import { TabellenSortierung } from '/static/djangobase/js/tabellen_sortierung.js';

Ohne Query. Der Browser hat die Datei im HTTP-Cache und nimmt sie von dort — der
Service Worker half nicht (sein eigener ``fetch`` geht durch denselben Cache).
Gemessen: ``fetch(datei + '?x=…')`` lieferte die neue Fassung, ``fetch(datei)``
die alte, bei frisch aktiviertem Worker. Sichtbar wurde es daran, dass die
Abschnittszeilen beim Sortieren ans Tabellenende rutschten — der Code, der sie
heraushaelt, kam nie im Browser an.

DIE LOESUNG
===========
Eine Kennung, die niemand pflegen muss: die groesste Aenderungszeit aller
mitgelieferten ``.js``/``.css`` von djangoBase. Sie steht als
``djangobase.statik_v`` im Vorlagen-Kontext::

    <script type="module">
      import { X } from '/static/djangobase/js/x.js?v={{ djangobase.statik_v }}';
    </script>

Aendert jemand eine Datei, aendert sich die Zahl — in JEDEM Konsumenten, ohne
dass dort eine Versionsnummer hochgezaehlt wird (die Projekte pflegen ihre
eigene ``JS_VERSION`` fuer ihre eigenen Dateien; djangoBase kann sie nicht
kennen).

EINMAL JE PROZESS
=================
Der Verzeichnisdurchlauf kostet ein paar Millisekunden; bei jedem Aufruf einer
Seite waere das Verschwendung. Er laeuft deshalb genau einmal und lebt so lange
wie der Prozess — der Entwicklungsserver startet bei jeder Aenderung ohnehin
neu, und in Produktion ist ein Neustart Teil des Deployments.
"""
from pathlib import Path

__all__ = ["Statik"]


class Statik:
    """Cache-Kennung der mitgelieferten statischen Dateien."""

    ENDUNGEN = (".js", ".mjs", ".css")
    _kennung = None

    @classmethod
    def kennung(cls):
        u"""Zahl, die sich mit jeder Aenderung an djangoBase-JS/CSS aendert.

        IM ENTWICKLUNGSBETRIEB jedes Mal frisch (``settings.DEBUG``): Der
        Django-Entwicklungsserver startet bei Aenderungen an ``.py`` neu, NICHT
        bei ``.js``. Eine einmal gemerkte Kennung blieb damit stehen, der
        Browser lieferte die alte Datei aus seinem Cache — und ein Fix schien
        wirkungslos (gemessen 18.08.2026 an ``tests_bereiche.js``: der neue
        Listener kam nie an, die Bereichs-Abschnitte kehrten nach dem Sortieren
        nicht zurueck). Der Verzeichnisdurchlauf kostet wenige Millisekunden;
        in Produktion (DEBUG aus) bleibt es beim einmaligen Rechnen.
        """
        from django.conf import settings
        if getattr(settings, "DEBUG", False):
            return cls._berechnen()
        if cls._kennung is None:
            cls._kennung = cls._berechnen()
        return cls._kennung

    @classmethod
    def _berechnen(cls):
        wurzel = Path(__file__).resolve().parent / "static" / "djangobase"
        neueste = 0
        try:
            for pfad in wurzel.rglob("*"):
                if pfad.suffix.lower() in cls.ENDUNGEN and pfad.is_file():
                    neueste = max(neueste, int(pfad.stat().st_mtime))
        except OSError:
            # Ohne Zugriff lieber eine feste Kennung als ein Fehler beim
            # Rendern JEDER Seite. Der Cache ist dann so gut wie vorher.
            return 1
        return neueste or 1
