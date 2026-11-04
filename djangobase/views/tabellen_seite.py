"""Einstellungen -> Tabellen (04.11.2026, aus StayNestor — Edgar: „mach in djangoBase eine Tabelle mit den
Einstellungen dafür: Tabellen - Spalten verschieben, Spalten anpassen. Damit kann man das auch
deaktivieren“).

Eine Tabelle mit den Schaltern der Store-Gruppe ``tabellen`` (``store.GRUPPEN``) — sie gelten für alle
Tabellen des Projekts, die ``tabellen_auto.js`` bindet:

* Spalten verschieben: Überschrift greifen und an eine andere Stelle ziehen (``tabellen_reihenfolge.js``);
* Spalten anpassen: Spaltenbreite am Griff ziehen und merken (``tabellen_breiten.js``).

Vorgaben aus ``conf.DEFAULTS`` bzw. ``settings.DJANGOBASE``; ein Klick speichert sofort (Formular schickt sich
beim Umschalten selbst ab). In die Seiten kommen die Werte über ``{% djb_tabellen %}``.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from .. import store
from ..conf import conf
from ..mixins import ZugriffMixin

BESCHREIBUNG = {
    "tabellen_spalten_verschieben": "Spaltenüberschrift mit der Maus greifen und an eine andere Stelle "
    "ziehen. Die Reihenfolge wird je Tabelle gemerkt.",
    "tabellen_spalten_anpassen": "Spaltenbreite am rechten Rand der Überschrift ziehen; Doppelklick setzt "
    "zurück. Die Breiten werden je Tabelle gemerkt.",
}


class TabellenSeite(ZugriffMixin, View):
    def get(self, request):
        c = conf()
        zeilen = [
            {"key": key, "label": label, "beschreibung": BESCHREIBUNG.get(key, ""), "an": bool(c.get(key))}
            for key, _typ, label in store.GRUPPEN["tabellen"]["felder"]
        ]
        return render(
            request,
            "djangobase/hilfe/tabellen.html",
            {
                "aktiv": "einstellungen_tabellen",
                "zeilen": zeilen,
                "je_benutzer": bool(c.get("tabellen_je_benutzer")),
            },
        )

    def post(self, request):
        werte = {
            key: request.POST.get(key) == "1" for key, _typ, _label in store.GRUPPEN["tabellen"]["felder"]
        }
        store.speichern_gruppe("tabellen", werte)
        messages.success(request, "Tabellen-Einstellungen gespeichert.")
        return redirect(request.path)
