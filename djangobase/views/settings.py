"""Hilfe -> Einstellungen: Laufzeit-konfigurierbare DJANGOBASE-Optionen.

Zwei Seiten/Gruppen (siehe store.GRUPPEN):
  * "website"    -> App-Name, Logo, Untertitel
  * "djangobase" -> Farben, Theme, Splitter, Meldungen

Persistiert als JSON-Datei via store.py — keine DB/Migration. Beim Speichern
wird nur die jeweilige Gruppe aktualisiert (Merge), die andere bleibt erhalten.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..store import (FARB_KEYS, GRUPPEN, laden, leeren_gruppe,
                     speichern_gruppe)


class EinstellungenView(ZugriffMixin, View):
    gruppe = "djangobase"  # via .as_view(gruppe="website") ueberschrieben

    def _aktiv(self):
        return "einstellungen_website" if self.gruppe == "website" else "einstellungen"

    def get(self, request):
        c = conf()
        gespeichert = laden()
        g = GRUPPEN[self.gruppe]
        keys = {k for k, _t, _l in g["felder"]}
        return render(request, "djangobase/hilfe/einstellungen.html", {
            "aktiv": self._aktiv(),
            "gruppe": self.gruppe,
            "gruppe_label": g["label"],
            "gruppe_titel": g["titel"],
            "gruppe_icon": g["icon"],
            "gruppe_beschreibung": g["beschreibung"],
            "felder": self._felder(c, self.gruppe),
            "theme_modes": c["theme_modes"],
            "hat_overrides": any(k in gespeichert for k in keys),
        })

    def post(self, request):
        if request.POST.get("zuruecksetzen"):
            leeren_gruppe(self.gruppe)
            messages.success(request, "Einstellungen auf Settings-Werte zurückgesetzt.")
            return redirect(request.path)

        werte = {}
        for key, typ, _label in GRUPPEN[self.gruppe]["felder"]:
            if typ == "bool":
                werte[key] = request.POST.get(key) == "on"
                continue
            roh = (request.POST.get(key) or "").strip()
            if typ == "int":
                try:
                    werte[key] = int(roh)
                except ValueError:
                    continue  # leer/ungueltig -> Settings-Default behalten
            elif typ == "csv":
                # Komma-getrennt -> Liste; leer -> []; whitespace trimmen.
                werte[key] = [s.strip() for s in roh.split(",") if s.strip()]
            else:
                werte[key] = roh
        speichern_gruppe(self.gruppe, werte)
        messages.success(request, "Einstellungen gespeichert.")
        return redirect(request.path)

    def _felder(self, c, gruppe):
        """Aktuelle (effektive) Werte je Feld der Gruppe fuer das Formular.
        CSV-Typ: Liste wird fuer die Anzeige zu 'a, b, c' zusammengefuegt."""
        felder = []
        for key, typ, label in GRUPPEN[gruppe]["felder"]:
            wert = c["farben"].get(key, "") if key in FARB_KEYS else c.get(key, "")
            if typ == "csv" and isinstance(wert, (list, tuple)):
                wert = ", ".join(str(x) for x in wert)
            felder.append({"key": key, "typ": typ, "label": label, "wert": wert})
        return felder
