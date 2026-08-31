# -*- coding: utf-8 -*-
u"""Hilfe -> Review: die gespeicherten Befunde eines Prüfwerkzeugs ausliefern.

WARUM EIN EIGENER ENDPUNKT (31.08.2026)
---------------------------------------
``review_status`` liefert den Zustand eines LAUFENDEN Laufs — also das, was
diese Sitzung gerade angestoßen hat. Nach einem Serverneustart ist das Register
leer, und mit ihm die Seite: Die Befunde von heute Vormittag waren nur noch als
Textblock in der Mitschrift zu finden.

Dieser Endpunkt liest stattdessen die Ablage der CLI. Er kostet keinen Lauf,
überlebt jeden Neustart und liefert die Befunde strukturiert statt als Block.

WELCHES VERZEICHNIS GELESEN WIRD, ENTSCHEIDET DIE KONFIGURATION
---------------------------------------------------------------
Aus dem Browser kommt der **Slug eines konfigurierten Partners**, nie ein Pfad.
Ein Freitext-Verzeichnis wäre hier dasselbe Loch wie ein Freitext-Argument in
der Kommandozeile — und die Review-Seite steht in sechs Projekten.
"""
from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..review import BefundLager, WerkzeugPartner
from .review import _einstellungen

__all__ = ["ReviewBefundeView"]


class ReviewBefundeView(ZugriffMixin, View):
    u"""GET: die gespeicherten Befunde eines Werkzeug-Partners."""

    def get(self, request, slug):
        partner = self._partner(slug)
        if partner is None:
            return JsonResponse({"fehler": u"Unbekanntes Werkzeug"}, status=404)

        wurzel = partner.get("wurzel") or _einstellungen()["wurzel"]
        lager = BefundLager(wurzel, ablage=partner.get("befund_ablage"))
        if not lager.vorhanden():
            # KEIN LEERES ERGEBNIS, SONDERN EIN GRUND: „0 Befunde" und „ich
            # finde die Ablage nicht" sehen auf einer Seite gleich aus und
            # bedeuten das Gegenteil.
            return JsonResponse({
                "wurzel": str(wurzel), "laeufe": [], "belegt": False,
                "hinweis": (u"Keine Ablage unter %s. Entweder lief hier noch nie "
                            u"ein Review, oder der Serverprozess sieht ein anderes "
                            u"Benutzerprofil als die Konsole (LOCALAPPDATA)."
                            % lager.ablage),
            })

        ordner, belegt = lager.repo_ordner()
        laeufe = lager.laeufe()
        return JsonResponse({
            "wurzel": str(wurzel),
            "ablage": str(lager.ablage),
            "ordner": ordner.name if ordner else "",
            # Ob die Zuordnung Ablage->Repository bewiesen ist oder nur über
            # den Ordnernamen geraten. Die Seite schreibt das hin.
            "belegt": belegt,
            "laeufe": laeufe,
            "hinweis": "" if laeufe else (
                u"Für %s liegen keine gespeicherten Befunde. Ein Lauf über "
                u"„Prüfen lassen“ legt sie an." % wurzel),
        })

    @staticmethod
    def _partner(slug):
        u"""Der konfigurierte Werkzeug-Partner zu diesem Slug — oder ``None``.

        Ein Modell-Partner wird ausdrücklich NICHT zurückgegeben: Er legt keine
        Befunddateien an, und eine leere Liste dafür wäre eine Antwort auf eine
        Frage, die niemand gestellt hat."""
        for p in _einstellungen()["partner"]:
            if p.get("slug") == slug and p.get("ziel") == WerkzeugPartner.ZIEL:
                return p
        return None
