# -*- coding: utf-8 -*-
u"""Endpunkte der Testcase-Aufzeichnung.

Alle antworten JSON und werden von ``aufzeichnung.js`` gerufen:

    GET  ?               Zustand (läuft gerade eine?) + Liste
    POST aktion=start    Aufzeichnung beginnen
    POST aktion=schritte Ereignis-Puffer anhaengen  (haeufigster Aufruf)
    POST aktion=ende     Beenden und die Server-Logs des Zeitraums anhaengen
    POST aktion=name     Umbenennen
    POST aktion=löschen Entfernen

WARUM EIN EINZIGER ENDPUNKT MIT ``aktion``
==========================================
Sechs Pfade für einen Vorgang wären sechs Stellen in ``urls.py``, sechs
Namen und sechs Gelegenheiten, den Zugriffsschutz zu vergessen. Der Schutz
hängt hier an EINER Klasse.

``@csrf_exempt`` bewusst NICHT: Diese Endpunkte schreiben in eine Datei des
Projekts, und der Aufrufer ist die eigene Seite - die hat das Token. Die
IB-Endpunkte in shortlongx sind davon ausgenommen, weil sie aus Skripten
gerufen werden; hier gibt es keinen solchen Fall.
"""
import json
import logging

from django.http import JsonResponse
from django.views import View

from ..aufzeichnung import Aufzeichnungen
from ..aufzeichnung_logs import LogFenster
from ..aufzeichnung_steuerung import Steuerung
from ..aufzeichnung_testfall import Testfall
from ..mixins import ZugriffMixin

log = logging.getLogger("djangobase.tests")

__all__ = ["AufzeichnungView"]


class AufzeichnungView(ZugriffMixin, View):
    u"""Zustand lesen und die Aufzeichnung steuern."""

    def get(self, request):
        u"""Zustand und Liste - mit ``?id=`` die SCHRITTE einer Aufzeichnung.

        Die Schritte kommen nur auf ausdrückliche Anfrage: In der Liste stehen
        Dutzende Aufnahmen, und eine einzelne trägt bis zu tausend Ereignisse.
        Alles mitzuliefern würde die Reiter-Seite bei jedem Takt aufblähen -
        sie fragt im Sekundentakt.

        Gebraucht wird das vom Abspieler (Ansage Edgar, 21.08.2026: ein
        Play-Knopf je Testcase, der die Aktionen im UI nachfährt)."""
        bestand = Aufzeichnungen()
        kennung = (request.GET.get("id") or "").strip()
        if kennung:
            treffer = [a for a in bestand.alle() if a.id == kennung]
            if not treffer:
                return JsonResponse({"ok": False, "fehler": "nicht gefunden"},
                                    status=404)
            a = treffer[0]
            return JsonResponse({"ok": True, "eintrag": a.kurz(),
                                 "schritte": a.schritte})
        laeuft = bestand.laufende()
        return JsonResponse({
            "ok": True,
            "laeuft": laeuft.kurz() if laeuft else None,
            "liste": [a.kurz() for a in bestand.alle()],
        })

    def post(self, request):
        try:
            daten = json.loads(request.body or "{}")
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "fehler": "ungültiges JSON"}, status=400)
        aktion = str(daten.get("aktion") or "")
        methode = getattr(self, "_" + aktion, None) if aktion.isalpha() else None
        if methode is None:
            return JsonResponse({"ok": False, "fehler": "unbekannte Aktion %r" % aktion},
                                status=400)
        return methode(daten)

    # ------------------------------------------------------------- Aktionen
    def _start(self, d):
        a, neu = Steuerung().starten(d.get("name") or "", d.get("seite") or "")
        return JsonResponse({"ok": True, "neu": neu, "laeuft": a.kurz()})

    def _schritte(self, d):
        u"""Der haeufigste Aufruf - er muss billig bleiben und darf nie werfen."""
        n = Steuerung().anhaengen(str(d.get("id") or ""), d.get("schritte") or [])
        return JsonResponse({"ok": True, "uebernommen": n})

    def _ende(self, d):
        bestand = Aufzeichnungen()
        laeuft = bestand.laufende()
        if laeuft is None:
            return JsonResponse({"ok": True, "beendet": None})
        # Die Log-Zeilen des Zeitraums kommen ERST HIER dazu: waehrend der
        # Aufnahme waere jedes Anhaengen ein Dateizugriff mehr, und das Fenster
        # steht ohnehin erst am Ende fest.
        zeilen = LogFenster().zeilen(laeuft.start)
        fertig = Steuerung().beenden(laeuft.id, zeilen)
        return JsonResponse({"ok": True, "beendet": fertig.kurz() if fertig else None})

    def _name(self, d):
        a = Steuerung().umbenennen(str(d.get("id") or ""), d.get("name") or "")
        if a is None:
            return JsonResponse({"ok": False, "fehler": "nicht gefunden oder leerer Name"},
                                status=404)
        return JsonResponse({"ok": True, "eintrag": a.kurz()})

    def _testfall(self, d):
        u"""Aus einer Aufzeichnung eine Testdatei schreiben (Ansage 21.08.2026).

        Bis dahin ging das nur über ``manage.py testfall_aus_aufzeichnung``.
        Die Antwort nennt Pfad und Zahl der geprüften Abrufe - der Knopf soll
        nicht verschleiern, dass hier Quelltext im Projekt entsteht."""
        from ..aufzeichnung_ablage import TestfallAblage
        a = Aufzeichnungen().holen(str(d.get("id") or ""))
        if a is None:
            return JsonResponse({"ok": False, "fehler": "nicht gefunden"},
                                status=404)
        if not a.schritte:
            return JsonResponse({"ok": False,
                                 "fehler": "Diese Aufzeichnung hat keine Schritte"},
                                status=400)
        pfad, meldung = TestfallAblage().ablegen(Testfall(a))
        if pfad is None:
            return JsonResponse({"ok": False, "fehler": meldung}, status=400)
        return JsonResponse({"ok": True, "meldung": meldung, "pfad": str(pfad)})

    def _loeschen(self, d):
        if not Steuerung().loeschen(str(d.get("id") or "")):
            return JsonResponse({"ok": False, "fehler": "nicht gefunden"}, status=404)
        return JsonResponse({"ok": True})
