# -*- coding: utf-8 -*-
"""Hilfe -> Review: Code-Review im Gespraech mit einem zweiten Modell.

Drei Betriebsarten, drei Knoepfe:

    Einfache Frage    eine Frage, eine Antwort
    Dialog            ein Bereich, beliebig viele Runden (Nachfassen)
    Mehrere Bereiche  mehrere Bereiche gleichzeitig, je ein eigener Verlauf

Die Runden laufen im Hintergrund; die Seite fragt ``status/`` ab. Das ist keine
Bequemlichkeit: Eine Runde dauert je nach Modell und Paketgroesse eine bis fünf
Minuten, und so lange darf keine Anfrage offen stehen.

Sicherheit: Gesendet werden NUR die Dateien der konfigurierten Bereiche, und nur
solche unterhalb von ``review_wurzel`` (Prüfung in ReviewLauf._datei_lesen).
Freitext-Pfade nimmt diese Seite bewusst nicht entgegen — bei einem
Online-Partner verlässt der Inhalt den Rechner.
"""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from ..conf import conf
from ..mixins import ZugriffMixin
from ..review import (NACHFASSEN, REGISTER, ReviewFehler, ReviewLauf,
                      WerkzeugPartner)


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

    @staticmethod
    def _bereiche_anzeigen(bereiche):
        """Bereiche für die Anzeige aufbereiten.

        Ein Datei-Eintrag darf ein Pfad ODER {"pfad", "funktionen"} sein — das
        Template soll das nicht auseinandernehmen müssen, sonst rendert es
        Python-Dicts in ein `title`-Attribut."""
        aufbereitet = []
        for b in bereiche:
            namen = []
            for d in b.get("dateien") or []:
                if isinstance(d, dict):
                    anzahl = len(d.get("funktionen") or [])
                    namen.append("%s%s" % (d.get("pfad", "?"),
                                           " (%d Funktionen)" % anzahl if anzahl else ""))
                else:
                    namen.append(str(d))
            aufbereitet.append({
                "slug": b.get("slug", ""), "name": b.get("name", b.get("slug", "")),
                "anzahl": len(namen), "dateien_text": ", ".join(namen),
            })
        return aufbereitet

    @staticmethod
    def _partner_anzeigen(partner):
        u"""Partner fuers Template — mit Kennzeichen und Auswahlen.

        Ein Werkzeug-Partner bekommt statt der Bereichsliste eine Auswahl,
        WELCHER Git-Stand geprueft wird. Ohne dieses Kennzeichen zeigte die
        Seite ihm die Bereichsauswahl und behauptete damit etwas, das nicht
        stimmt (das Werkzeug liest den Diff, nicht die Bereichsdateien).
        """
        raus = []
        for p in partner:
            ist_werkzeug = p.get("ziel") == WerkzeugPartner.ZIEL
            raus.append(dict(
                p, ist_werkzeug=ist_werkzeug,
                auswahl_liste=(WerkzeugPartner.anzeige_auswahlen(p)
                               if ist_werkzeug else [])))
        return raus

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        u"""Die Seite — und ausdruecklich MIT CSRF-Cookie.

        WARUM DER DEKORATOR (31.08.2026): Diese Seite rendert kein Formular;
        ihre POSTs baut das JavaScript und holt den Token aus dem Cookie
        (``csrf()`` im Template). Django setzt dieses Cookie aber nur, wenn es
        jemand anfordert. Im Browser fiel das nicht auf, weil eine andere Seite
        es vorher gesetzt hatte — ein frischer Client (erste Seite nach dem
        Start, ein Skript, ein anderes Profil) bekam dagegen „CSRF cookie not
        set" und konnte gar nichts starten. Ein Zustand, der von der Reihenfolge
        der besuchten Seiten abhaengt, ist keiner, auf den man bauen kann.
        """
        e = _einstellungen()
        alle = self._partner_anzeigen(e["partner"])
        # WERKZEUGE OBEN, GETRENNT VOM MODELL-WAEHLER (Ansage Edgar,
        # 31.08.2026: „mach einen extra bereich für Coderabbit, ganz oben").
        #
        # Vorher stand das Werkzeug als vierter Eintrag in derselben
        # Partner-Liste wie die drei Modelle - und beim Umschalten wechselte
        # die halbe Bedienung (Bereiche weg, Auswahl da). Zwei Dinge, die sich
        # so verschieden bedienen, gehoeren nicht in dieselbe Auswahlliste.
        werkzeuge = [p for p in alle if p["ist_werkzeug"]]
        return render(request, "djangobase/hilfe/review.html", {
            "aktiv": "review",
            "werkzeuge": werkzeuge,
            "partner": [p for p in alle if not p["ist_werkzeug"]],
            "bereiche": self._bereiche_anzeigen(e["bereiche"]),
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
        frage = (daten.get("frage") or "").strip()
        # WERKZEUG-PARTNER: Es liest den Git-Stand selbst, deshalb braucht es
        # weder Bereich noch Frage. Aus dem Browser kommt nur der SCHLUeSSEL
        # einer in der Konfiguration hinterlegten Auswahl — nie ein Argument
        # der Kommandozeile. Ein unbekannter Schluessel wird abgewiesen statt
        # stillschweigend durch die Vorgabe ersetzt: Sonst prueft der Lauf
        # etwas anderes, als auf der Seite steht.
        auswahl = ""
        if partner.get("ziel") == WerkzeugPartner.ZIEL:
            # DIESELBE Normalisierung wie im Partner — die Konfiguration darf
            # Liste oder Dict sein, und ein `in` auf einer Liste von Dicts
            # haette JEDE Auswahl abgelehnt.
            auswahlen = WerkzeugPartner._auswahlen_lesen(partner.get("auswahlen"))
            # TYP PRUEFEN, BEVOR ``.strip()`` (Befund CodeRabbit, 31.08.2026):
            # ``auswahl`` kommt aus JSON und kann eine Zahl, Liste oder ein
            # Objekt sein. ``.strip()`` haette dann einen AttributeError
            # geworfen - HTTP 500 statt einer verstaendlichen Absage.
            roh_auswahl = daten.get("auswahl") or ""
            if not isinstance(roh_auswahl, str):
                return JsonResponse({"fehler": "Ungueltige Auswahl"}, status=400)
            auswahl = roh_auswahl.strip()
            if auswahl and auswahl not in auswahlen:
                return JsonResponse({"fehler": "Unbekannte Auswahl"}, status=400)
            gewaehlt = []
        else:
            if modus in ("dialog", "bereiche") and not gewaehlt:
                return JsonResponse({"fehler": "Kein Bereich gewaehlt"}, status=400)
            if modus == "dialog":
                gewaehlt = gewaehlt[:1]
            if modus == "frage" and not frage:
                return JsonResponse({"fehler": "Keine Frage eingegeben"}, status=400)

        lauf = ReviewLauf(modus, partner, wurzel=e["wurzel"], ablage=e["ablage"],
                          rolle=e["rolle"], schluessel_datei=e["schluessel_datei"],
                          ollama_url=e["ollama_url"], online_url=e["online_url"],
                          auswahl=auswahl)
        REGISTER.hinzu(lauf)
        # EIN KONFIGURATIONSFEHLER IST KEINE 500 (31.08.2026): Der
        # Werkzeug-Partner weist beim Anlegen zurueck, was er nicht ausfuehren
        # kann (leerer Befehl, unbekannte Auswahl). Ohne diesen Zweig kaeme im
        # Browser ein nackter Serverfehler an, und der Grund staende nur im Log.
        try:
            lauf.starten(bereiche=gewaehlt, frage=frage,
                         titel=daten.get("titel", ""))
        except ReviewFehler as fehler:
            return JsonResponse({"fehler": str(fehler)}, status=400)
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
            return JsonResponse({"fehler": "Es läuft noch eine Runde"}, status=409)
        return JsonResponse({"gestartet": gestartet})


class ReviewStatusView(ZugriffMixin, View):
    """GET: Zustand eines Laufs (die Seite fragt im Takt)."""

    def get(self, request, lauf_id):
        lauf = REGISTER.holen(lauf_id)
        if lauf is None:
            return JsonResponse({"fehler": "Lauf nicht gefunden"}, status=404)
        mit_text = request.GET.get("text", "1") != "0"
        return JsonResponse(lauf.zustand(mit_text=mit_text))
