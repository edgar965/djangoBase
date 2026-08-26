# -*- coding: utf-8 -*-
"""Hilfe -> Aktuell: das rollierende Fenster mit den Ergebnissen der Claude-CLI.

Die Seite liest nur. Geschrieben wird über ``manage.py aktuell`` (siehe
djangobase/management/commands/aktuell.py) — so gibt es keinen
Schreib-Endpunkt, den eine fremde Webseite bedienen könnte, und die CLI
braucht weder Token noch laufenden Server.

Anders als Hilfe -> Review ist diese Seite NICHT opt-in: Sie erscheint in jedem
Projekt, das djangoBase einbindet (Vorgabe des Nutzers, 13.08.2026). Solange
niemand etwas hineinschreibt, zeigt sie eine Anleitung statt einer leeren
Liste.
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from django.shortcuts import render

from ..aktuell import ARTEN, feed
from ..mixins import ZugriffMixin


class AktuellView(ZugriffMixin, View):
    """Die Seite: neueste Einträge zuerst, nach Art filterbar."""

    #: So viele Eintraege zeigt die Seite auf einmal. Das Fenster selbst haelt
    #: mehr (AktuellFeed.MAX_EINTRAEGE); hier geht es nur um die Lesbarkeit.
    ANZEIGE = 60

    def get(self, request):
        f = feed()
        art = (request.GET.get("art") or "").strip().lower() or None
        eintraege = f.lesen(limit=self.ANZEIGE, art=art)
        # Die Zahlen als LISTE mit dem Namen daneben, nicht als Abbildung:
        # Django-Templates koennen eine Abbildung nicht mit einer Variablen als
        # Schluessel lesen — der erste Versuch (`zaehler|default_if_none`) hat
        # deshalb an jedem Filter-Knopf das ganze Dict ausgegeben.
        zaehler = f.arten_zaehlen()
        return render(request, "djangobase/hilfe/aktuell.html", {
            "aktiv": "aktuell",
            "eintraege": eintraege,
            "arten": [{"slug": a, "anzahl": zaehler.get(a, 0)} for a in ARTEN],
            "aktive_art": art or "",
            "datei": str(f.pfad),
            "max_eintraege": f.MAX_EINTRAEGE,
        })


class AktuellDatenView(ZugriffMixin, View):
    """JSON für die Selbst-Aktualisierung der Seite.

    Die Seite lädt sich nicht komplett neu, sondern fragt hier nach: Wer eine
    lange Ausgabe aufgeklappt hat, soll sie nicht alle 20 Sekunden verlieren."""

    def get(self, request):
        art = (request.GET.get("art") or "").strip().lower() or None
        return JsonResponse({"eintraege": feed().lesen(limit=AktuellView.ANZEIGE, art=art)})


class AktuellLeerenView(ZugriffMixin, View):
    """POST: Fenster leeren."""

    def post(self, request):
        feed().leeren()
        return redirect("djangobase:aktuell")
