"""Benutzer → Traffic: Besucher-Statistik wie man sie von Analytics kennt.

Datenquelle ist das Seitenaufruf-Modell (gefüllt von
djangobase.traffic.TrafficMiddleware). Granularität wählbar:
Tag (30 Tage) / Woche (12 Wochen) / Monat (12 Monate); alle Blöcke
(Kennzahlen, Länder, Seiten, Referrer, Geräte, MB) beziehen sich auf
dasselbe Zeitfenster. Bots werden überall ausgeblendet.
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from ..mixins import ZugriffMixin
from ..models import Seitenaufruf

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


class TrafficView(ZugriffMixin, View):
    """Benutzer → Traffic: Kennzahlen + Diagramme + Tabellen."""

    def get(self, request):
        g = request.GET.get("g")
        if g not in GRANULARITAETEN:
            g = "tag"
        perioden, trunc, schritt_tage, fenster_label = GRANULARITAETEN[g]

        jetzt = timezone.localtime()
        heute = jetzt.date()
        start = jetzt - timedelta(days=perioden * schritt_tage)

        qs = Seitenaufruf.objects.filter(zeit__gte=start, bot=False)
        seiten_qs = qs.filter(typ="html")

        # ---- Zeitreihe: Aufrufe + Besucher (nur Seiten) und MB (alles) ----
        # TruncDate liefert date, TruncWeek/-Month datetime → auf date normieren
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
            if g == "monat":
                # Monatsanfänge rückwärts (timedelta kennt keine Monate)
                jahr, monat = heute.year, heute.month - i
                while monat < 1:
                    monat += 12
                    jahr -= 1
                p = heute.replace(year=jahr, month=monat, day=1)
                labels.append(p.strftime("%b %y"))
            elif g == "woche":
                p = heute - timedelta(days=heute.weekday()) - timedelta(weeks=i)
                labels.append("KW " + p.strftime("%V"))
            else:
                p = heute - timedelta(days=i)
                labels.append(p.strftime("%d.%m."))
            r = reihe.get(p) or {}
            aufrufe.append(r.get("aufrufe") or 0)
            besucher.append(r.get("besucher") or 0)
            mbs.append(_mb(r.get("bytes")))

        # ---- Kennzahlen ---------------------------------------------------
        def _zahlen(von):
            s = Seitenaufruf.objects.filter(zeit__gte=von, bot=False, typ="html")
            return (s.count(), s.values("besucher").distinct().count())

        heute_aufrufe, heute_besucher = _zahlen(
            jetzt.replace(hour=0, minute=0, second=0, microsecond=0))
        w7_aufrufe, w7_besucher = _zahlen(jetzt - timedelta(days=7))
        w30_aufrufe, w30_besucher = _zahlen(jetzt - timedelta(days=30))
        bot_anzahl = Seitenaufruf.objects.filter(zeit__gte=start, bot=True).count()

        # ---- Länder -------------------------------------------------------
        laender_roh = (seiten_qs.values("land")
                       .annotate(n=Count("id"),
                                 besucher=Count("besucher", distinct=True))
                       .order_by("-n"))
        gesamt = sum(r["n"] for r in laender_roh) or 1
        laender = [{
            "iso": r["land"] or "?",
            "flagge": _flagge(r["land"] or ""),
            "name": LAENDER_NAMEN.get(r["land"], r["land"] or "Unbekannt"),
            "n": r["n"], "besucher": r["besucher"],
            "prozent": round(100 * r["n"] / gesamt, 1),
        } for r in laender_roh[:12]]

        # ---- Meistbesuchte Seiten ----------------------------------------
        seiten_roh = (seiten_qs.values("pfad")
                      .annotate(n=Count("id"),
                                besucher=Count("besucher", distinct=True),
                                bytes=Sum("groesse"))
                      .order_by("-n")[:25])
        seiten_max = max((r["n"] for r in seiten_roh), default=1)
        seiten = [{
            "pfad": r["pfad"], "n": r["n"], "besucher": r["besucher"],
            "mb": _mb(r["bytes"]),
            "balken": round(100 * r["n"] / seiten_max),
            "prozent": round(100 * r["n"] / gesamt, 1),
        } for r in seiten_roh]

        # ---- Referrer + Geräte -------------------------------------------
        referrer = list(seiten_qs.exclude(referrer="")
                        .values("referrer")
                        .annotate(n=Count("id"),
                                  besucher=Count("besucher", distinct=True))
                        .order_by("-n")[:15])
        geraete_roh = dict(seiten_qs.values_list("geraet")
                           .annotate(n=Count("id")).order_by())
        geraete = [(label, geraete_roh.get(key, 0))
                   for key, label in Seitenaufruf.GERAETE]

        return render(request, "djangobase/hilfe/traffic.html", {
            "aktiv": "traffic",
            "g": g,
            "fenster_label": fenster_label,
            "granularitaeten": [("tag", "Tag"), ("woche", "Woche"), ("monat", "Monat")],
            "kpi": {
                "heute_aufrufe": heute_aufrufe, "heute_besucher": heute_besucher,
                "w7_aufrufe": w7_aufrufe, "w7_besucher": w7_besucher,
                "w30_aufrufe": w30_aufrufe, "w30_besucher": w30_besucher,
                "mb_fenster": round(sum(mbs), 1),
                "laender_anzahl": len([r for r in laender_roh if r["land"]]),
                "bot_anzahl": bot_anzahl,
            },
            "chart_daten": {
                "labels": labels, "aufrufe": aufrufe,
                "besucher": besucher, "mb": mbs,
                "geraete": {"labels": [l for l, _ in geraete],
                            "werte": [n for _, n in geraete]},
            },
            "laender": laender,
            "seiten": seiten,
            "referrer": referrer,
            "erfasst_seit": Seitenaufruf.objects.order_by("zeit")
                            .values_list("zeit", flat=True).first(),
        })
