"""Hilfe -> Einstellungen: Laufzeit-konfigurierbare DJANGOBASE-Optionen
(Branding, Farben, Theme, Splitter) ueber ein Formular. Persistiert als
JSON-Datei via store.py — keine DB/Migration noetig.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..store import EINSTELLBAR, FARB_KEYS, laden, speichern


class EinstellungenView(ZugriffMixin, View):
    def get(self, request):
        c = conf()
        gespeichert = laden()
        return render(request, "djangobase/hilfe/einstellungen.html", {
            "aktiv": "einstellungen",
            "felder": self._felder(c),
            "theme_modes": c["theme_modes"],
            "hat_overrides": bool(gespeichert),
        })

    def post(self, request):
        if request.POST.get("zuruecksetzen"):
            speichern({})
            messages.success(request, "Einstellungen auf Settings-Werte zurückgesetzt.")
            return redirect(reverse("djangobase:einstellungen"))

        daten = {}
        for key, typ, _label in EINSTELLBAR:
            if typ == "bool":
                daten[key] = request.POST.get(key) == "on"
                continue
            roh = (request.POST.get(key) or "").strip()
            if typ == "int":
                try:
                    daten[key] = int(roh)
                except ValueError:
                    continue  # leer/ungueltig -> Settings-Default behalten
            else:
                daten[key] = roh
        speichern(daten)
        messages.success(request, "Einstellungen gespeichert.")
        return redirect(reverse("djangobase:einstellungen"))

    def _felder(self, c):
        """Aktuelle (effektive) Werte je EINSTELLBAR-Eintrag fuer das Formular."""
        felder = []
        for key, typ, label in EINSTELLBAR:
            wert = c["farben"].get(key, "") if key in FARB_KEYS else c.get(key, "")
            felder.append({"key": key, "typ": typ, "label": label, "wert": wert})
        return felder
