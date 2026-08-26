# -*- coding: utf-8 -*-
u"""TestDauerView - Laufzeit eines im BROWSER gefahrenen Tests entgegennehmen.

WARUM ES DIESEN EINEN SCHREIB-ENDPUNKT GIBT
===========================================
Die UI-/Browser-Tests laufen nicht im Serverprozess, sondern im Iframe der
Tests-Seite. Ihre Laufzeit kennt nur der Browser. Ohne diesen Endpunkt hätten
sie als einzige Liste keine Historie - und „bei jedem Testcase soll auch die
Performance aufnotiert werden" (Ansage 17.08.2026) gilt für alle.

Er schreibt in dieselbe Datei wie die serverseitigen Laeufe
(``logs/testhistorie.json``), damit es EINE Historie gibt und nicht zwei.

WAS ER NICHT ANNIMMT
====================
* Nur angemeldete Nutzer mit Zugriff auf die Hilfe-Seiten (``ZugriffMixin``).
* Nur Kennungen mit dem Praefix ``ui:`` - so kann ein Browser-Aufruf keine
  Laufzeit eines Python-Tests ueberschreiben.
* Kennung hoechstens 200 Zeichen, Dauer 0 bis 3600 s, und hoechstens
  ``HOECHSTENS`` verschiedene UI-Kennungen in der Datei. Ohne diese Grenzen
  könnte ein Aufruf in einer Schleife die Datei beliebig groß machen.
"""
import json
import logging
import time

from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..testhistorie import Testhistorie

log = logging.getLogger("djangobase.tests")


class TestDauerView(ZugriffMixin, View):
    """POST ``{"id": "ui:gruppe.fall", "dauer": 2.31, "ok": true}``."""

    #: So viele verschiedene UI-Kennungen werden gefuehrt.
    HOECHSTENS = 500
    PRAEFIX = "ui:"

    def post(self, request):
        try:
            daten = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"ok": False, "error": "kein JSON"}, status=400)
        kennung = str(daten.get("id") or "")[:200]
        if not kennung.startswith(self.PRAEFIX):
            return JsonResponse(
                {"ok": False, "error": "nur Kennungen mit Präfix '%s'"
                                       % self.PRAEFIX}, status=400)
        try:
            dauer = float(daten.get("dauer"))
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "dauer fehlt"}, status=400)
        if not 0 <= dauer <= 3600:
            return JsonResponse({"ok": False, "error": "dauer unplausibel"},
                                status=400)

        historie = Testhistorie()
        vorhanden = [k for k in historie.daten["tests"]
                     if k.startswith(self.PRAEFIX)]
        if kennung not in vorhanden and len(vorhanden) >= self.HOECHSTENS:
            log.warning("Testhistorie: %d UI-Kennungen erreicht, %r nicht "
                        "aufgenommen", self.HOECHSTENS, kennung)
            return JsonResponse({"ok": False, "error": "zu viele Kennungen"},
                                status=429)
        historie.merken(time.strftime("%d.%m.%Y %H:%M:%S"), {kennung: dauer})
        # Dictionary gewollt: geht unveraendert als JSON zurueck an die Seite.
        return JsonResponse({"ok": True, "laeufe": historie.laeufe(kennung)})
