# -*- coding: utf-8 -*-
u"""TestNummerView - den Platz eines Testfalls in der Tabelle ändern.

    „Die enthält zahlen, aufsteigend, die man ändern kann, dann verschieben sich
    die tests in der Tabelle." (Edgar, 17.08.2026)

POST ``{"id": "<test-id>", "nummer": 7, "gruppe": ["<id>", …]}``

``gruppe`` ist die Liste der Kennungen IN DER GERADE ANGEZEIGTEN Reihenfolge —
die Seite weiß, was sie zeigt, und schickt es mit. Der Server ordnet daraus neu
und speichert die Plaetze; zurück kommt die neue Reihenfolge, damit die Seite
die Zeilen ohne Neuladen umhaengen kann.

WARUM POST
==========
Der Aufruf SCHREIBT (``logs/testreihenfolge.json``). Ein GET-Link wäre von
jedem Vorschau-Dienst oder Reload ausloesbar — dieselbe Ueberlegung wie beim
Verschieben.

WAS GEPRUEFT WIRD
=================
Nur bekannte Test-IDs (Discovery) kommen in die Ablage. Sonst könnte eine
Anfrage die Datei mit beliebigen Schlüsseln füllen; harmlos in der Wirkung,
aber es wäre Muell, den niemand mehr los wird.
"""
import json
import logging

from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..testreihenfolge import Reihenfolge

log = logging.getLogger("djangobase.tests")


class TestNummerView(ZugriffMixin, View):
    """Speichert den neuen Platz und liefert die neue Reihenfolge."""

    #: So viele Kennungen nimmt eine Gruppe hoechstens (eine Kategorie im
    #: assistant hat rund 350) - ein Deckel gegen aufgeblaehte Anfragen.
    MAX_GRUPPE = 5000

    def post(self, request):
        try:
            daten = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"ok": False, "error": "kein JSON"}, status=400)
        test_id = str(daten.get("id") or "")[:300]
        gruppe = daten.get("gruppe") or []
        if not test_id or not isinstance(gruppe, list):
            return JsonResponse({"ok": False, "error": "id und gruppe nötig"},
                                status=400)
        gruppe = [str(g)[:300] for g in gruppe[:self.MAX_GRUPPE]]

        bekannte = self._bekannte()
        if bekannte and test_id not in bekannte:
            return JsonResponse({"ok": False, "error": "unbekannter Testfall"},
                                status=409)
        gefiltert = [g for g in gruppe if not bekannte or g in bekannte]
        reihe = Reihenfolge().setzen(test_id, daten.get("nummer"), gefiltert)
        if not reihe:
            return JsonResponse(
                {"ok": False, "error": "Nummer nicht anwendbar — der Fall steht "
                                       "nicht in der übergebenen Gruppe."},
                status=409)
        log.info("Test-Reihenfolge: %s auf Platz %s durch %s (%d in der Gruppe)",
                 test_id, daten.get("nummer"),
                 getattr(getattr(request, "user", None), "username", "?"),
                 len(reihe))
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return JsonResponse({"ok": True, "reihe": reihe})

    @staticmethod
    def _bekannte():
        u"""Alle entdeckten Test-IDs - leer, wenn die Discovery nichts liefert.

        Leer heißt „nicht prüfbar", nicht „nichts erlaubt": In einem Projekt
        ohne Discovery wäre die Spalte sonst tot.
        """
        from ..conf import conf
        from ..testkategorien import Kategorien
        from .tests import TestsView
        try:
            c = conf()
            befehle = c.get("test_befehle") or TestsView._befehle_abgeleitet()
            discover = c.get("test_discover") or Kategorien(befehle).discover()
            _kategorien, bekannte = TestsView._einzeltests(discover,
                                                           mit_djangobase=True)
            return bekannte
        except Exception:  # noqa: BLE001
            log.exception("Test-IDs für die Nummern-Prüfung nicht ermittelbar")
            return set()
