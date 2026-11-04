"""POST ``<hilfe>/tabellen/einstellung/`` mit ``{"schluessel": "tblBreiten:…", "wert": "…"}`` — merkt eine
Tabellen-Einstellung des angemeldeten Benutzers (``TabellenEinstellung``); ``"wert": null`` vergisst sie
(04.11.2026, aus StayNestor). Aufgerufen von ``tabellen_speicher.js``, nur mit
``DJANGOBASE["tabellen_je_benutzer"] = True``.

Jeder angemeldete Benutzer (keine Staff-Pflicht — es sind seine eigenen Einstellungen). Nur die Schlüssel der
djangoBase-Tabellen (``VORSAETZE``), höchstens ``GRENZE`` Zeichen je Wert.
"""

import json

from django.http import JsonResponse
from django.views import View

from ..conf import conf
from ..tabellen_einstellung import TabellenEinstellung


class TabellenEinstellungSpeichern(View):
    VORSAETZE = ("tblBreiten:", "dbTabSort:", "db-spalten:", "tblReihe:")
    GRENZE = 20000

    def post(self, request):
        if not conf().get("tabellen_je_benutzer"):
            return JsonResponse({"ok": False, "fehler": "Nicht eingeschaltet."}, status=404)
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "fehler": "Nicht angemeldet."}, status=403)
        try:
            daten = json.loads(request.body or b"{}")
        except ValueError:
            return JsonResponse({"ok": False, "fehler": "Kein JSON."}, status=400)
        schluessel, wert = str(daten.get("schluessel") or ""), daten.get("wert")
        laenge = TabellenEinstellung._meta.get_field("schluessel").max_length
        if not schluessel.startswith(self.VORSAETZE) or len(schluessel) > laenge:
            return JsonResponse({"ok": False, "fehler": "Unbekannter Schlüssel."}, status=400)
        if wert is None:
            TabellenEinstellung.objects.filter(benutzer=request.user, schluessel=schluessel).delete()
            return JsonResponse({"ok": True})
        if not isinstance(wert, str) or len(wert) > self.GRENZE:
            return JsonResponse({"ok": False, "fehler": "Wert zu lang oder kein Text."}, status=400)
        TabellenEinstellung.objects.update_or_create(
            benutzer=request.user, schluessel=schluessel, defaults={"wert": wert}
        )
        return JsonResponse({"ok": True})
