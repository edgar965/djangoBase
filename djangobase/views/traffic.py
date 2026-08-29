"""Benutzer → Traffic: Besucher-Statistik wie man sie von Analytics kennt.

Datenquelle ist das Seitenaufruf-Modell (gefüllt von
djangobase.traffic.TrafficMiddleware). Granularität wählbar:
Tag (30 Tage) / Woche (12 Wochen) / Monat (12 Monate); alle Blöcke
(Kennzahlen, Länder, Seiten, Referrer, Geräte, MB) beziehen sich auf
dasselbe Zeitfenster. Bots werden überall ausgeblendet.
"""
import json
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..mixins import ZugriffMixin
from ..models import Seitenaufruf, Verbrauch
from ..traffic import verbrauch_buchen

GRANULARITAETEN = {
    # key: (Anzahl Perioden, Trunc-Funktion, Schritt-Tage, Label)
    "tag": (30, TruncDate, 1, "30 Tage"),
    "woche": (12, TruncWeek, 7, "12 Wochen"),
    "monat": (12, TruncMonth, 31, "12 Monate"),
}

LAENDER_NAMEN = {
    "DE": "Deutschland", "AT": "Österreich", "CH": "Schweiz", "US": "USA",
    "GB": "Großbritannien", "FR": "Frankreich", "NL": "Niederlande",
    "PL": "Polen", "IT": "Italien", "ES": "Spanien", "DK": "Dänemark",
    "SE": "Schweden", "CZ": "Tschechien", "BE": "Belgien", "TR": "Türkei",
    "RU": "Russland", "UA": "Ukraine", "CN": "China", "JP": "Japan",
    "IN": "Indien", "BR": "Brasilien", "CA": "Kanada", "AU": "Australien",
}


def _flagge(iso):
    """ISO-Code → Flaggen-Emoji (Regional-Indicator-Paar)."""
    if len(iso) != 2 or not iso.isalpha():
        return "🌐"
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in iso.upper())


def _mb(byte_anzahl):
    return round((byte_anzahl or 0) / (1024 * 1024), 1)


# Geschätzte Bytes pro Kachel, falls der Browser keine Resource-Timing-Größe
# liefert (z. B. Cross-Origin ohne Timing-Allow-Origin → transferSize 0).
KACHEL_BYTES = 22 * 1024

ROUTING_MODI = {"auto": ("🚗", "Auto"), "bicycle": ("🚲", "Fahrrad"),
                "pedestrian": ("🥾", "Zu Fuß")}


@method_decorator(csrf_exempt, name="dispatch")
class VerbrauchBeaconView(View):
    """Öffentlicher Beacon-Endpoint: der Karten-Client meldet geladene Kacheln
    (navigator.sendBeacon, static/djangobase/js/verbrauch.js). CSRF-frei, weil
    sendBeacon keine Header setzen kann; Werte werden serverseitig geklemmt."""

    def post(self, request):
        try:
            d = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return HttpResponse(status=204)
        if d.get("typ") == "tile":
            verbrauch_buchen("tile", anzahl=d.get("anzahl", 0),
                             bytes=d.get("bytes", 0), detail="karte")
        return HttpResponse(status=204)


class TrafficView(ZugriffMixin, View):
    """Benutzer → Traffic: Kennzahlen + Diagramme + Tabellen."""

    def get(self, request):
        """Die Seite — sechs Auswertungen, jede in ihrer eigenen Methode.

        BIS ZUM 29.08.2026 STAND ALLES HIER (Rang C, Befund
        `code-qualitaet`). Jeder Teil ist fuer sich einfach; sie standen nur
        alle untereinander. Geschnitten ist an den Kommentaren, die ohnehin
        schon da waren.
        """
        g = request.GET.get("g")
        if g not in GRANULARITAETEN:
            g = "tag"
        perioden, trunc, schritt_tage, fenster_label = GRANULARITAETEN[g]

        jetzt = timezone.localtime()
        heute = jetzt.date()
        start = jetzt - timedelta(days=perioden * schritt_tage)

        qs = Seitenaufruf.objects.filter(zeit__gte=start, bot=False)
        seiten_qs = qs.filter(typ="html")

        labels, aufrufe, besucher, mbs = self._zeitreihe(
            qs, trunc, g, heute, perioden)
        kpi = self._kennzahlen(jetzt, start, mbs)
        laender, laender_roh = self._laender(seiten_qs)
        gesamt = sum(r["n"] for r in laender_roh) or 1
        kpi["laender_anzahl"] = len([r for r in laender_roh if r["land"]])

        return render(request, "djangobase/hilfe/traffic.html", {
            "aktiv": "traffic",
            "verbrauch": self._dienste(start),
            "g": g,
            "fenster_label": fenster_label,
            "granularitaeten": [("tag", "Tag"), ("woche", "Woche"),
                                ("monat", "Monat")],
            "kpi": kpi,
            "chart_daten": {
                "labels": labels, "aufrufe": aufrufe,
                "besucher": besucher, "mb": mbs,
                "geraete": self._geraete(seiten_qs),
            },
            "laender": laender,
            "seiten": self._seiten(seiten_qs, gesamt),
            "referrer": self._referrer(seiten_qs),
            "erfasst_seit": Seitenaufruf.objects.order_by("zeit")
                            .values_list("zeit", flat=True).first(),
        })

    # ------------------------------------------------------------ Zeitreihe

    @staticmethod
    def _zeitreihe(qs, trunc, g, heute, perioden):
        """Aufrufe, Besucher und MB je Periode — rueckwaerts bis `perioden`.

        LUECKEN MUESSEN NULL SEIN, nicht fehlen: Die Datenbank liefert nur
        Perioden, in denen etwas passiert ist. Wer die Liste daraus baut,
        bekommt ein Diagramm, das stille Tage einfach ueberspringt — und
        damit eine Kurve, die steiler aussieht, als sie ist.

        `TruncDate` liefert ein `date`, `TruncWeek`/`-Month` ein `datetime`;
        beides wird auf `date` gebracht, sonst findet der Nachschlag nichts.
        """
        reihe = {}
        for r in (qs.annotate(p=trunc("zeit")).values("p")
                    .annotate(aufrufe=Count("id", filter=Q(typ="html")),
                              besucher=Count("besucher", distinct=True,
                                             filter=Q(typ="html")),
                              bytes=Sum("groesse"))
                    .order_by("p")):
            p = r["p"]
            reihe[p.date() if hasattr(p, "date") else p] = r

        labels, aufrufe, besucher, mbs = [], [], [], []
        for i in range(perioden - 1, -1, -1):
            p, label = TrafficView._periode(g, heute, i)
            labels.append(label)
            r = reihe.get(p) or {}
            aufrufe.append(r.get("aufrufe") or 0)
            besucher.append(r.get("besucher") or 0)
            mbs.append(_mb(r.get("bytes")))
        return labels, aufrufe, besucher, mbs

    @staticmethod
    def _periode(g, heute, i):
        """Der Anfang der `i`-ten Periode rueckwaerts, plus ihre Beschriftung.

        Monate rechnet `timedelta` nicht — es kennt nur feste Laengen.
        Deshalb hier von Hand, mit Jahresuebertrag.
        """
        if g == "monat":
            jahr, monat = heute.year, heute.month - i
            while monat < 1:
                monat += 12
                jahr -= 1
            p = heute.replace(year=jahr, month=monat, day=1)
            return p, p.strftime("%b %y")
        if g == "woche":
            p = heute - timedelta(days=heute.weekday()) - timedelta(weeks=i)
            return p, "KW " + p.strftime("%V")
        p = heute - timedelta(days=i)
        return p, p.strftime("%d.%m.")

    # ----------------------------------------------------------- Kennzahlen

    @staticmethod
    def _kennzahlen(jetzt, start, mbs):
        """Heute, sieben Tage, dreissig Tage — Aufrufe und Besucher."""
        def zahlen(von):
            s = Seitenaufruf.objects.filter(zeit__gte=von, bot=False,
                                            typ="html")
            return (s.count(), s.values("besucher").distinct().count())

        heute_aufrufe, heute_besucher = zahlen(
            jetzt.replace(hour=0, minute=0, second=0, microsecond=0))
        w7_aufrufe, w7_besucher = zahlen(jetzt - timedelta(days=7))
        w30_aufrufe, w30_besucher = zahlen(jetzt - timedelta(days=30))
        return {
            "heute_aufrufe": heute_aufrufe, "heute_besucher": heute_besucher,
            "w7_aufrufe": w7_aufrufe, "w7_besucher": w7_besucher,
            "w30_aufrufe": w30_aufrufe, "w30_besucher": w30_besucher,
            "mb_fenster": round(sum(mbs), 1),
            "bot_anzahl": Seitenaufruf.objects.filter(zeit__gte=start,
                                                      bot=True).count(),
        }

    # --------------------------------------------------------------- Tabellen

    @staticmethod
    def _laender(seiten_qs):
        """Die zwoelf haeufigsten Laender — und die Rohliste fuer die Summe.

        Die Rohliste geht mit zurueck, weil zwei Kennzahlen daran haengen:
        die Gesamtzahl (Nenner der Prozente) und „wie viele Laender ueberhaupt".
        Sie zweimal abzufragen waere eine zweite Abfrage fuer dieselbe Zeile.
        """
        roh = list(seiten_qs.values("land")
                   .annotate(n=Count("id"),
                             besucher=Count("besucher", distinct=True))
                   .order_by("-n"))
        gesamt = sum(r["n"] for r in roh) or 1
        laender = [{
            "iso": r["land"] or "?",
            "flagge": _flagge(r["land"] or ""),
            "name": LAENDER_NAMEN.get(r["land"], r["land"] or "Unbekannt"),
            "n": r["n"], "besucher": r["besucher"],
            "prozent": round(100 * r["n"] / gesamt, 1),
        } for r in roh[:12]]
        return laender, roh

    @staticmethod
    def _seiten(seiten_qs, gesamt):
        """Die 25 meistbesuchten Seiten, mit Balkenlaenge."""
        roh = (seiten_qs.values("pfad")
               .annotate(n=Count("id"),
                         besucher=Count("besucher", distinct=True),
                         bytes=Sum("groesse"))
               .order_by("-n")[:25])
        groesste = max((r["n"] for r in roh), default=1)
        return [{
            "pfad": r["pfad"], "n": r["n"], "besucher": r["besucher"],
            "mb": _mb(r["bytes"]),
            "balken": round(100 * r["n"] / groesste),
            "prozent": round(100 * r["n"] / gesamt, 1),
        } for r in roh]

    @staticmethod
    def _referrer(seiten_qs):
        """Die fuenfzehn haeufigsten Verweise von aussen."""
        return list(seiten_qs.exclude(referrer="")
                    .values("referrer")
                    .annotate(n=Count("id"),
                              besucher=Count("besucher", distinct=True))
                    .order_by("-n")[:15])

    @staticmethod
    def _geraete(seiten_qs):
        """Aufrufe je Geraeteart — JEDE Art, auch die mit null.

        Die Reihenfolge kommt aus `Seitenaufruf.GERAETE` und nicht aus der
        Datenbank: Ein Diagramm, dessen Balken die Plaetze tauschen, sobald
        eine Art einmal fehlt, ist nicht lesbar.
        """
        roh = dict(seiten_qs.values_list("geraet")
                   .annotate(n=Count("id")).order_by())
        paare = [(label, roh.get(key, 0))
                 for key, label in Seitenaufruf.GERAETE]
        return {"labels": [l for l, _ in paare],
                "werte": [n for _, n in paare]}

    # ------------------------------------------------------ Externe Dienste

    @staticmethod
    def _dienste(start):
        """Kartenkacheln und Navigation — Anzahl und geschaetzte Menge."""
        vb = Verbrauch.objects.filter(zeit__gte=start)
        kacheln = vb.filter(typ="tile").aggregate(n=Sum("anzahl"),
                                                  b=Sum("bytes"))
        kachel_n = kacheln["n"] or 0
        kachel_b = kacheln["b"] or 0
        # Cache-Treffer liefern transferSize 0 → für die nicht gemessenen
        # Kacheln den Schätzwert ergänzen, damit die MB realistisch bleiben.
        gemessen = vb.filter(typ="tile", bytes__gt=0).aggregate(
            n=Sum("anzahl"))["n"] or 0
        kachel_mb = _mb(kachel_b + max(0, kachel_n - gemessen) * KACHEL_BYTES)

        roh = (vb.filter(typ="route").values("detail")
               .annotate(n=Sum("anzahl"), b=Sum("bytes")).order_by("-n"))
        route_n = sum(r["n"] or 0 for r in roh)
        route_b = sum(r["b"] or 0 for r in roh)
        return {
            "kachel_n": kachel_n, "kachel_mb": kachel_mb,
            "route_n": route_n, "route_mb": _mb(route_b),
            "routing": [{
                "modus": ROUTING_MODI.get(r["detail"],
                                          ("🧭", r["detail"] or "—"))[1],
                "icon": ROUTING_MODI.get(r["detail"], ("🧭", ""))[0],
                "n": r["n"] or 0,
            } for r in roh],
            "hat_daten": bool(kachel_n or route_n),
        }
