# -*- coding: utf-8 -*-
"""Hilfe -> Review: Code-Review im Gespraech mit einem zweiten Modell.

Drei Betriebsarten, drei Knoepfe:

    Einfache Frage    eine Frage, eine Antwort
    Dialog            ein Bereich, beliebig viele Runden (Nachfassen)
    Mehrere Bereiche  mehrere Bereiche gleichzeitig, je ein eigener Verlauf

Die Runden laufen im Hintergrund; die Seite fragt ``status/`` ab. Das ist keine
Bequemlichkeit: Eine Runde dauert je nach Modell und Paketgroesse eine bis fuenf
Minuten, und so lange darf keine Anfrage offen stehen.

Sicherheit: Gesendet werden NUR die Dateien der konfigurierten Bereiche, und nur
solche unterhalb von ``review_wurzel`` (Pruefung in ReviewLauf._datei_lesen).
Freitext-Pfade nimmt diese Seite bewusst nicht entgegen — bei einem
Online-Partner verlaesst der Inhalt den Rechner.
"""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from ..conf import conf
from ..mixins import ZugriffMixin
from ..review import NACHFASSEN, REGISTER, ReviewLauf


def _einstellungen():
    """Review-Teil der Konfiguration mit aufgeloesten Vorgaben."""
    from django.conf import settings
    c = conf()
    wurzel = c.get("review_wurzel") or settings.BASE_DIR
    ablage = c.get("review_ablage") or (c["log_verzeichnis"] / "review")
    return {
        "partner": c.get("review_partner") or [],
        "bereiche": c.get("review_bereiche") or [],
        "wurzel": wurzel,
        "ablage": ablage,
        "rolle": c.get("review_rolle") or None,
        "schluessel_datei": c.get("review_schluessel_datei") or None,
        "ollama_url": c.get("review_ollama_url") or None,
        "online_url": c.get("review_online_url") or None,
    }


class ReviewView(ZugriffMixin, View):
    """Die Seite selbst."""

    def get(self, request):
        e = _einstellungen()
        return render(request, "djangobase/hilfe/review.html", {
            "aktiv": "review",
            "partner": e["partner"],
            "bereiche": e["bereiche"],
            "nachfassen": [{"slug": k, "text": v} for k, v in NACHFASSEN.items()],
            "wurzel": str(e["wurzel"]),
            "laeufe": [{"id": l.id, "titel": l.titel, "modus": l.modus}
                       for l in REGISTER.liste()],
        })


class ReviewStartView(ZugriffMixin, View):
    """POST: neuen Lauf anlegen und die erste Runde anstossen."""

    def post(self, request):
        try:
            daten = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"fehler": "Ungueltiges JSON"}, status=400)

        e = _einstellungen()
        modus = daten.get("modus", "frage")
        if modus not in ("frage", "dialog", "bereiche"):
            return JsonResponse({"fehler": "Unbekannte Betriebsart"}, status=400)

        partner = next((p for p in e["partner"]
                        if p.get("slug") == daten.get("partner")), None)
        if partner is None:
            return JsonResponse({"fehler": "Unbekannter Partner"}, status=400)

        # Nur konfigurierte Bereiche — keine Pfade aus dem Request.
        gewaehlt = [b for b in e["bereiche"] if b.get("slug") in (daten.get("bereiche") or [])]
        if modus in ("dialog", "bereiche") and not gewaehlt:
            return JsonResponse({"fehler": "Kein Bereich gewaehlt"}, status=400)
        if modus == "dialog":
            gewaehlt = gewaehlt[:1]
        frage = (daten.get("frage") or "").strip()
        if modus == "frage" and not frage:
            return JsonResponse({"fehler": "Keine Frage eingegeben"}, status=400)

        lauf = ReviewLauf(modus, partner, wurzel=e["wurzel"], ablage=e["ablage"],
                          rolle=e["rolle"], schluessel_datei=e["schluessel_datei"],
                          ollama_url=e["ollama_url"], online_url=e["online_url"])
        REGISTER.hinzu(lauf)
        lauf.starten(bereiche=gewaehlt, frage=frage,
                     titel=daten.get("titel", ""))
        return JsonResponse({"id": lauf.id, "zustand": lauf.zustand(mit_text=False)})


class ReviewNachfassenView(ZugriffMixin, View):
    """POST: weitere Runde in einem Lauf (ein Faden oder alle)."""

    def post(self, request, lauf_id):
        lauf = REGISTER.holen(lauf_id)
        if lauf is None:
            return JsonResponse({"fehler": "Lauf nicht gefunden (Server neu gestartet?)"},
                                status=404)
        try:
            daten = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"fehler": "Ungueltiges JSON"}, status=400)

        text = (daten.get("text") or "").strip()
        vorlage = daten.get("vorlage")
        if vorlage:
            if vorlage not in NACHFASSEN:
                return JsonResponse({"fehler": "Unbekannte Vorlage"}, status=400)
            text = NACHFASSEN[vorlage]
        if not text:
            return JsonResponse({"fehler": "Keine Nachfrage"}, status=400)

        gestartet = lauf.nachfassen(text, slug=daten.get("faden") or None)
        if not gestartet:
            return JsonResponse({"fehler": "Es laeuft noch eine Runde"}, status=409)
        return JsonResponse({"gestartet": gestartet})


class ReviewStatusView(ZugriffMixin, View):
    """GET: Zustand eines Laufs (die Seite fragt im Takt)."""

    def get(self, request, lauf_id):
        lauf = REGISTER.holen(lauf_id)
        if lauf is None:
            return JsonResponse({"fehler": "Lauf nicht gefunden"}, status=404)
        mit_text = request.GET.get("text", "1") != "0"
        return JsonResponse(lauf.zustand(mit_text=mit_text))
