# -*- coding: utf-8 -*-
u"""``languageserver/referenzen/`` — Referenzen, Definition, Umbenennen.

Stufe 2 des Plans. Alles läuft über EINE offene Sitzung je (Server, Wurzel)
(``umbau/ls_sitzung.py``); die erste Anfrage startet sie und dauert deshalb
ein paar Sekunden länger.

UMBENENNEN IN ZWEI SCHRITTEN
============================
``vorschau`` liefert jede Stelle (Datei, Zeile, alt, neu); erst ``umbenennen``
mit ``bestaetigt: true`` schreibt — mit Sicherung und Kompilier-Netz
(``umbau/ls_umbenennen.py``). Ein Klick allein ändert keine Datei.
"""
import json
import logging

from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau import ls_sitzung
from ..umbau.languageserver import LanguageServer
from ..umbau.ls_umbenennen import Umbenennung
from .languageserver import extra_pfade, konfig_laden, ordner, wurzel

logger = logging.getLogger("djangobase.languageserver")

__all__ = ["LanguageServerReferenzenView"]


class LanguageServerReferenzenView(ZugriffMixin, View):

    AKTIONEN = ("referenzen", "definition", "vorschau", "umbenennen")

    def post(self, request):
        try:
            daten = json.loads(request.body or b"{}")
        except ValueError:
            return JsonResponse({"fehler": u"kein JSON"}, status=400)
        aktion = daten.get("aktion")
        if aktion not in self.AKTIONEN:
            return JsonResponse({"fehler": u"unbekannte Aktion"}, status=400)
        try:
            pfad = (wurzel() / str(daten.get("datei") or "")).resolve()
            if wurzel().resolve() not in pfad.parents:
                return JsonResponse({"fehler": u"Datei liegt nicht im Projekt"}, status=400)
            zeile, spalte = int(daten.get("zeile") or 1), int(daten.get("spalte") or 1)
            sitzung = self._sitzung()
            if aktion == "referenzen":
                return JsonResponse({"stellen": sitzung.referenzen(pfad, zeile, spalte)})
            if aktion == "definition":
                return JsonResponse({"stellen": sitzung.definition(pfad, zeile, spalte)})
            name = (daten.get("name") or "").strip()
            if not name.isidentifier():
                return JsonResponse({"fehler": u"kein gültiger Name: %r" % name}, status=400)
            edit = sitzung.umbenennen(pfad, zeile, spalte, name)
            umbau = Umbenennung(edit, wurzel(), ordner() / "sicherung")
            if aktion == "vorschau" or not daten.get("bestaetigt"):
                return JsonResponse({"vorschau": umbau.vorschau()})
            bericht = umbau.anwenden()
            logger.info("Language Server: umbenannt nach %s — %d Stellen in %d Dateien, "
                        "Sicherung %s", name, bericht["stellen"], bericht["dateien"],
                        bericht["sicherung"])
            # Die Sitzung kennt die alten Texte — nach dem Schreiben neu aufbauen.
            ls_sitzung.alle_beenden()
            return JsonResponse({"bericht": bericht})
        except (TimeoutError, RuntimeError, OSError) as e:
            logger.warning("Language Server: %s", e)
            return JsonResponse({"fehler": str(e)}, status=502)

    @staticmethod
    def _sitzung():
        konfig = konfig_laden()
        server = LanguageServer(konfig, wurzel(), ordner(), extra_pfade()).finden()
        if not server.get("server"):
            raise RuntimeError(server.get("fehlt") or
                               u"%s-langserver nicht gefunden" % server.get("name"))
        return ls_sitzung.holen(server["server"], wurzel(),
                                konfig.als_lsp_einstellungen(wurzel(), extra_pfade()))
