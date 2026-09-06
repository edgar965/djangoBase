# -*- coding: utf-8 -*-
u"""Hilfe -> Cache: das Konzept, sein Zustand im Projekt und die Befunde.

DIE ANSAGE (Edgar, 06.09.2026)
==============================
    „dokumentiere das Caching-Konzept (auch fuer ES-Module usw.) in djangoBase
     Hilfe - Cache, schreib da alles rein an Erkenntnissen und Problemen, die
     du hattest, und wie du das machst, damit neue Projekte das genau so machen"

Die Seite hat drei Teile: der Zustand des Projekts (Middleware, Fassungspfad,
ASGI-Huelle, aktuelle Fassung), die Befunde des Werkzeugs `cachekonzept`
(dieselben wie in der Konformitaetspruefung), und die Regeln mit ihrer
Vorgeschichte als Text. Gerechnet wird beim Seitenaufruf: ein Durchlauf ueber
die Vorlagen und Skripte kostet wenige hundert Millisekunden.
"""
from django.conf import settings
from django.shortcuts import render
from django.views import View

from ..cachekonzept import Cachekonzept
from ..mixins import ZugriffMixin

__all__ = ["CacheView"]


class CacheView(ZugriffMixin, View):
    u"""Zustand, Befunde und Regeln auf einer Seite."""

    vorlage = "djangobase/hilfe/cache.html"

    def get(self, request):
        from ..skills.cachekonzept import Cachekonzept as Werkzeug
        try:
            satz = Werkzeug().pruefen()
            befunde, kopf, fehler = satz.befunde, satz.kopf, ""
        except Exception as ausnahme:                      # die Seite muss stehen, auch wenn der Lauf hinfaellt
            befunde, kopf, fehler = [], "", u"%s: %s" % (type(ausnahme).__name__, ausnahme)
        return render(request, self.vorlage, {
            "aktiv": "cache",
            "zustand": self._zustand(),
            "regeln": Cachekonzept.REGELN,
            "befunde": befunde,
            "kopf": kopf,
            "fehler": fehler,
        })

    @staticmethod
    def _zustand():
        u"""Was im laufenden Projekt gesetzt ist — jede Zeile mit Ja/Nein."""
        kette = list(getattr(settings, "MIDDLEWARE", []) or [])
        fremde_nocache = [m for m in kette if Cachekonzept.NOCACHE.search(m) and not m.startswith("djangobase.")]
        asgi = Cachekonzept.asgi_quelle()
        fassung = None
        try:
            from ..fassungsstatik import Fassungsstatik
            fassung = Fassungsstatik.fassung()
        except Exception:                                  # ohne Statik-Ordner gibt es keine Fassung
            fassung = None
        return [
            (u"CacheHeaderMiddleware in MIDDLEWARE",
             "djangobase.cache_middleware.CacheHeaderMiddleware" in kette,
             u"HTML no-store, Statik mit ?v= ein Jahr, Statik ohne Kennung no-cache"),
            (u"Keine pauschale NoCache-Middleware", not fremde_nocache,
             ", ".join(fremde_nocache) if fremde_nocache else u"—"),
            (u"Fassungspfad eingehaengt (/statik/v-…/)", Cachekonzept.fassungspfad_eingehaengt(),
             u"include('djangobase.fassungsstatik') in urls.py"),
            (u"StatikKopfzeilen um die ASGI-Anwendung",
             asgi is not None and "StatikKopfzeilen" in asgi,
             Cachekonzept.asgi_pfad() or u"kein ASGI_APPLICATION"),
            (u"Aktuelle Fassung der Statik", bool(fassung),
             u"v-%s" % fassung if fassung else u"keine Statik gefunden"),
        ]
