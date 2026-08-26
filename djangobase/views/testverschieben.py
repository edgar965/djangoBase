# -*- coding: utf-8 -*-
u"""TestVerschiebenView - einen Testfall in eine andere Kategorie umhaengen.

Gegenstueck zur Combo-Box „Verschieben" in jeder Testcase-Tabelle (Ansage
17.08.2026). Die eigentliche Arbeit macht :class:`~.testverschieben.Verschieber`;
hier steht nur, wer darf und was hereinkommen darf.

WARUM POST UND NICHT EIN LINK
=============================
Der Aufruf VERSCHIEBT EINE DATEI. Ein GET-Link wäre von jedem Vorschau-Dienst,
Crawler oder versehentlichen Reload ausloesbar — dieselbe Fehlerklasse, die das
Werkzeug ``schreibrouten`` sucht („Datenverlust auf ein GET hin").
"""
import json
import logging

from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..testverschieben import Verschieber

log = logging.getLogger("djangobase.tests")


class TestVerschiebenView(ZugriffMixin, View):
    u"""POST ``{"id": "mail.tests.unit.test_x.K.test_y", "ziel": "longrunner"}``.

    Mit ``"was": "bereich"`` wechselt stattdessen der BEREICH (Chat, Musik, …) —
    dieselbe Mechanik, nur wandert die Datei quer statt laengs. Ein Endpunkt für
    beides, weil es derselbe Vorgang ist: Datei umhaengen, Historie mitnehmen,
    Discovery-Cache der betroffenen Labels verwerfen.
    """

    def post(self, request):
        try:
            daten = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"ok": False, "error": "kein JSON"}, status=400)
        test_id = str(daten.get("id") or "")[:300]
        ziel = str(daten.get("ziel") or "")[:60]
        was = str(daten.get("was") or "kategorie")[:20]
        if not test_id or not ziel:
            return JsonResponse({"ok": False, "error": "id und ziel nötig"},
                                status=400)
        verschieber = Verschieber()
        # WER was anfasst, gehoert ins Protokoll: Der Aufruf verschiebt eine
        # Datei im Quelltext. Bis 17.08.2026 stand davon nichts in einem Log —
        # weder der Erfolg noch der Grund eines Fehlschlags (Ansage: „beim
        # verschieben, schau auch in den logs, falls es keine gibt dann mach
        # sie"). Die Zeilen landen in `djangobase.log`, sichtbar unter
        # Hilfe → Logs.
        wer = getattr(getattr(request, "user", None), "username", "?")
        log.info("Verschieben angefordert: %s -> %s (%s) durch %s",
                 test_id, ziel, was, wer)
        try:
            if was == "bereich":
                erfolg, meldung, neue_id = verschieber.bereich_verschieben(
                    test_id, ziel)
            else:
                erfolg, meldung, neue_id = verschieber.verschieben(test_id, ziel)
        except Exception:  # noqa: BLE001
            # Eine Ausnahme HIER heisst: Die Datei liegt womoeglich schon am
            # Ziel, und die Seite bekaeme eine nackte Fehlerseite. Genau das ist
            # passiert (`AttributeError` beim Bereichswechsel). Also
            # protokollieren und als Meldung zurueckgeben.
            log.exception("Verschieben fehlgeschlagen: %s -> %s (%s)",
                          test_id, ziel, was)
            return JsonResponse(
                {"ok": False, "error": "Verschieben fehlgeschlagen — Grund "
                                       "steht in djangobase.log (Hilfe → Logs)."},
                status=500)
        if not erfolg:
            log.warning("Verschieben abgelehnt: %s -> %s (%s) — %s",
                        test_id, ziel, was, meldung)
            # 409: Die Anfrage war formal in Ordnung, der Zustand erlaubt sie
            # nicht (falscher Ordner, Ziel belegt, gleiche Kategorie).
            return JsonResponse({"ok": False, "error": meldung}, status=409)
        self._cache_leeren(test_id, neue_id)
        log.info("Verschoben: %s -> %s (%s) durch %s — neue Kennung %s",
                 test_id, ziel, was, wer, neue_id or "unverändert")
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
