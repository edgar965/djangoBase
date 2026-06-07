"""Hilfe -> Tests: führt in settings.DJANGOBASE['test_befehle'] konfigurierte
Test-Kommandos aus und zeigt das Ergebnis (rc, stdout, stderr, Dauer)."""
import subprocess
import time

from django.conf import settings
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class TestsView(ZugriffMixin, View):
    def get(self, request):
        befehle = conf()["test_befehle"]
        slug = request.GET.get("run")
        ergebnis = None
        if slug:
            b = next((x for x in befehle if x.get("slug") == slug), None)
            if b:
                ergebnis = self._run(b)
        return render(request, "djangobase/hilfe/tests.html", {
            "aktiv": "tests",
            "befehle": befehle,
            "ergebnis": ergebnis,
            "aktiver_slug": slug,
        })

    def _run(self, b):
        cmd = b["cmd"]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                               encoding="utf-8", errors="replace",
                               cwd=str(settings.BASE_DIR), creationflags=_NO_WINDOW)
            out, err, rc = r.stdout or "", r.stderr or "", r.returncode
        except Exception as exc:  # noqa: BLE001
            out, err, rc = "", str(exc), -1
        return {
            "name": b.get("name", b.get("slug", "")),
            "cmd": " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd),
            "rc": rc, "ok": rc == 0,
            "out": out[-40000:], "err": err[-40000:],
            "dauer": round(time.time() - t0, 1),
        }
