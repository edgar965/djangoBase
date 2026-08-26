"""Hilfe -> Jobs: listet die in ``djangobase.jobs`` registrierten Hintergrund-
Jobs und zeigt deren Live-Zustand. Optional je Job: „Jetzt ausfuehren" und
Aktivieren/Deaktivieren. Ein JSON-Endpoint (``?format=json``) liefert denselben
Snapshot für das Auto-Refresh der Seite."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from .. import jobs as jobs_registry
from ..mixins import ZugriffMixin

logger = logging.getLogger(__name__)


class JobsView(ZugriffMixin, View):
    """Hilfe -> Jobs: Uebersicht + Steuerung registrierter Jobs."""

    def get(self, request):
        snap = jobs_registry.snapshot()
        if request.GET.get("format") == "json":
            return JsonResponse({"jobs": snap})
        return render(request, "djangobase/hilfe/jobs.html", dict({
            "aktiv": "jobs",
            "jobs": snap,
        }, **self._uebersicht(neu=False)))

    @staticmethod
    def _uebersicht(neu):
        """Bestand und Verlauf für die Tabelle darunter.

        WARUM ZWEI TEILE AUF EINER SEITE (26.08.2026)
        =============================================
        Oben stehen die REGISTRIERTEN Daemons mit ihrem Live-Zustand -
        das ist die alte Seite und bleibt, wie sie war. Darunter steht,
        was das Projekt an Abläufen HAT und was davon zuletzt gelaufen
        ist: "welcher Job wann zuletzt lief, wie lange er brauchte und
        ob er Fehler warf" (Ansage Edgar).

        Beides gehört zusammen, misst aber Verschiedenes: Der Zustand
        ist der Augenblick, der Verlauf die Vergangenheit. Ein Daemon
        ohne Lauf-Historie ist normal, ein Befehl ohne Live-Zustand
        auch.

        Ein Fehler hier darf die Seite nicht kosten - die registrierten
        Jobs oben sollen auch dann stehen, wenn der Verlauf klemmt.
        """
        from ..jobuebersicht import Jobuebersicht

        try:
            uebersicht = Jobuebersicht()
            return {
                "zeilen": uebersicht.zeilen(neu=neu),
                "zahlen": uebersicht.zahlen(),
                "stand": uebersicht.stand(),
                "stand_veraltet": uebersicht.veraltet(),
            }
        except Exception:
            logger.exception("JobsView._uebersicht: Exception gefangen")
            return {"zeilen": [], "zahlen": {}, "stand": None,
                    "stand_veraltet": True, "uebersicht_fehler": True}

    def post(self, request):
        slug = (request.POST.get("job") or "").strip()
        aktion = (request.POST.get("aktion") or "").strip()

        # „Jetzt aktualisieren" gehört zu keinem einzelnen Job — es
        # ermittelt den Bestand des ganzen Projekts neu (26.08.2026).
        # Deshalb vor der Job-Suche: `slug` ist hier leer.
        if aktion == "ermitteln":
            return self._neu_ermitteln(request)

        job = jobs_registry.get(slug)
        ist_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ok, msg = False, "Unbekannter Job."
        if job:
            if aktion == "trigger" and job["trigger"]:
                job["trigger"]()
                ok, msg = True, f"{job['name']}: Lauf ausgeloest."
            elif aktion == "enable" and job["set_enabled"]:
                job["set_enabled"](True)
                ok, msg = True, f"{job['name']}: aktiviert."
            elif aktion == "disable" and job["set_enabled"]:
                job["set_enabled"](False)
                ok, msg = True, f"{job['name']}: deaktiviert."
            else:
                msg = "Aktion für diesen Job nicht verfuegbar."
        if ist_ajax:
            return JsonResponse({"ok": ok, "msg": msg, "jobs": jobs_registry.snapshot()})
        (messages.success if ok else messages.error)(request, msg)
        return redirect("djangobase:jobs")

    @staticmethod
    def _neu_ermitteln(request):
        """Den Bestand sofort neu ermitteln — Knopf „Jetzt aktualisieren".

        Das kann dauern: Für die Beschreibung wird jede Befehlsklasse
        importiert (in assistant 93). Genau deshalb gibt es den Knopf
        überhaupt — sonst liefe das bei jedem Seitenaufruf.
        """
        from ..jobkatalog import Jobkatalog

        try:
            gefunden = Jobkatalog().aktualisieren()
            messages.success(request, "%d Jobs ermittelt." % len(gefunden))
        except Exception:
            logger.exception("JobsView._neu_ermitteln: Exception gefangen")
            messages.error(request,
                           "Die Jobs konnten nicht ermittelt werden — "
                           "Einzelheiten stehen unter Hilfe → Logs.")
        return redirect("djangobase:jobs")
