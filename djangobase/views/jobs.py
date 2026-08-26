"""Hilfe -> Jobs: listet die in ``djangobase.jobs`` registrierten Hintergrund-
Jobs und zeigt deren Live-Zustand. Optional je Job: „Jetzt ausfuehren" und
Aktivieren/Deaktivieren. Ein JSON-Endpoint (``?format=json``) liefert denselben
Snapshot für das Auto-Refresh der Seite."""
from __future__ import annotations

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from .. import jobs as jobs_registry
from ..mixins import ZugriffMixin


class JobsView(ZugriffMixin, View):
    """Hilfe -> Jobs: Uebersicht + Steuerung registrierter Jobs."""

    def get(self, request):
        snap = jobs_registry.snapshot()
        if request.GET.get("format") == "json":
            return JsonResponse({"jobs": snap})
        return render(request, "djangobase/hilfe/jobs.html", {
            "aktiv": "jobs",
            "jobs": snap,
        })

    def post(self, request):
        slug = (request.POST.get("job") or "").strip()
        aktion = (request.POST.get("aktion") or "").strip()
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
