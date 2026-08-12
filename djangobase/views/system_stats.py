"""Auslastungs-Leiste: der Endpunkt, den ``static/djangobase/js/system_stats.js`` abfragt.

WOZU (uebernommen aus shortlongx am 12.08.2026)
-----------------------------------------------
Ein laengerer Rechenlauf sieht von aussen aus wie ein haengender Server. Die
Leiste beantwortet in einem Blick, WO die Arbeit gerade steckt: GPU, CPU,
Arbeitsspeicher, Netz. In shortlongx hat genau diese Unterscheidung einmal den
Unterschied zwischen „Batch zu klein" (GPU bei 0,6 %) und „Zeilenbau" (CPU auf
einem Kern) ausgemacht.

Das Modul ist bewusst anspruchslos: Es antwortet IMMER, auch ohne ``nvidia-smi``
und ohne ``psutil`` - dann eben mit weniger Feldern. Eine Anzeige, die den Server
zum Stolpern bringt, waere schlimmer als keine Anzeige.

DIE MESSUNG DAHINTER (shortlongx, 28.07.2026)
---------------------------------------------
Eine Aktualisierung kostet 0,22 s (``nvidia-smi`` rund 0,07 s +
``psutil.cpu_percent(interval=0.15)``). Die Leiste fragt waehrend eines Laufs
jede Sekunde, und wer mehrere Tabs offen hat, fragt mehrfach. Auf dem
Entwicklungs-Server - der Anfragen NACHEINANDER abarbeitet - ging damit rund ein
Fuenftel der einzigen Bahn fuers ANZEIGEN der Auslastung drauf statt fuers
Rechnen.

Deshalb rechnet diese View NICHT: Sie liest nur ab, was ein Hintergrund-Faden
ohnehin bereitgestellt hat (``SystemStats.lesen`` ueber ``HintergrundCache``).
Wer das aendert, macht die Anzeige wieder zum Bremsklotz.
"""
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ..system_stats import SystemStats

__all__ = ["api_system_stats"]

logger = logging.getLogger(__name__)


@csrf_exempt
def api_system_stats(request):
    """GPU-/CPU-Auslastung als JSON. Antwortet auch im Fehlerfall mit 200.

    ``{"ok": false}`` statt eines 500ers ist Absicht: Die Leiste ist Beiwerk.
    Faellt die Messung aus - keine Grafikkarte, ``psutil`` fehlt, ``nvidia-smi``
    haengt -, soll die Seite darueber nicht rot werden, sondern die Leiste
    stillschweigend leer bleiben."""
    try:
        return JsonResponse(dict(SystemStats.lesen(), ok=True))
    except Exception:                                        # noqa: BLE001
        logger.exception("System-Stats fehlgeschlagen")
        return JsonResponse({"ok": False})
