# -*- coding: utf-8 -*-
u"""``languageserver/status/`` — was der Hintergrund-Lauf gerade tut.

Die Seite fragt alle zwei Sekunden; sobald ``status`` nicht mehr ``laeuft``
ist, lädt sie sich neu und zeigt das Ergebnis aus der Ablage. Kein Rechnen
hier, nur Nachsehen.
"""
from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau.ls_lauf import LAUF
from .languageserver import LsSpeicher, konfig_laden, schluessel

__all__ = ["LanguageServerStatusView"]


class LanguageServerStatusView(ZugriffMixin, View):

    def get(self, request):
        zustand = LAUF.zustand()
        ergebnis, alter = LsSpeicher.nachsehen(schluessel(konfig_laden()))
        zustand["ergebnis_da"] = ergebnis is not None
        zustand["alter"] = int(alter) if alter is not None else None
        return JsonResponse(zustand)
