# -*- coding: utf-8 -*-
u"""TestVerschiebenView - einen Testfall in eine andere Kategorie umhaengen.

Gegenstueck zur Combo-Box „Verschieben" in jeder Testcase-Tabelle (Ansage
17.08.2026). Die eigentliche Arbeit macht :class:`~.testverschieben.Verschieber`;
hier steht nur, wer darf und was hereinkommen darf.

WARUM POST UND NICHT EIN LINK
=============================
Der Aufruf VERSCHIEBT EINE DATEI. Ein GET-Link waere von jedem Vorschau-Dienst,
Crawler oder versehentlichen Reload ausloesbar — dieselbe Fehlerklasse, die das
Werkzeug ``schreibrouten`` sucht („Datenverlust auf ein GET hin").
"""
import json
import logging

from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..testverschieben import Verschieber

log = logging.getLogger("django")


class TestVerschiebenView(ZugriffMixin, View):
    """POST ``{"id": "mail.tests.unit.test_x.K.test_y", "ziel": "longrunner"}``."""

    def post(self, request):
        try:
            daten = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"ok": False, "error": "kein JSON"}, status=400)
        test_id = str(daten.get("id") or "")[:300]
        ziel = str(daten.get("ziel") or "")[:40]
        if not test_id or not ziel:
            return JsonResponse({"ok": False, "error": "id und ziel nötig"},
                                status=400)
        verschieber = Verschieber()
        erfolg, meldung, neue_id = verschieber.verschieben(test_id, ziel)
        if not erfolg:
            # 409: Die Anfrage war formal in Ordnung, der Zustand erlaubt sie
            # nicht (falscher Ordner, Ziel belegt, gleiche Kategorie).
            return JsonResponse({"ok": False, "error": meldung}, status=409)
        self._cache_leeren(test_id, neue_id)
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return JsonResponse({"ok": True, "meldung": meldung, "id": neue_id})

    @staticmethod
    def _cache_leeren(alte_id, neue_id):
        u"""Die betroffenen Discovery-Einträge verwerfen - nicht den ganzen Cache.

        Die Testliste je Label ist zehn Minuten gecacht (``TestsView``). Nach
        einem Umzug sind GENAU ZWEI Labels falsch: das alte und das neue. Ein
        ``cache.clear()`` waere bequemer und wuerde alles andere mitnehmen, was
        im selben Speicher liegt.
        """
        from django.core.cache import cache
        from ..testverschieben import Verschieber
        for kennung in (alte_id, neue_id):
            teile = str(kennung or "").split(".")
            art = Verschieber.art_von(kennung)
            if not art or art not in teile:
                continue
            label = ".".join(teile[:teile.index(art) + 1])
            cache.delete("djangobase:testids:%s" % label)
