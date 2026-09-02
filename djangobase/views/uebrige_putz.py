# -*- coding: utf-8 -*-
u"""Hilfe → Klassenmodell → Statistik: die „Übrigen" einer Endung löschen.

    „mach mir in der Tabelle bei Statistik, in der Tabelle bei „Übrige"
     einen Button Löschen mit dem ich die die Dinger lösche" (Edgar,
     02.09.2026)

ZWEI SCHRITTE, NICHT EINER
==========================
``GET`` liefert die Vorschau: wie viele Dateien, wie viel Platz, die
ersten Pfade. ``POST`` löscht. Der Browser zeigt die Vorschau in einer
Rückfrage, und erst deren Bestätigung schickt den POST.

Das ist kein Zierrat: In der Liste stehen neben Chrome-Cache und
Testdumps auch `.docx`, `.xlsx` und `.log` — Dateien, die man sehen will,
bevor sie weg sind. Die Rückfrage nennt sie beim Namen.

Aus dem Browser kommt ausschliesslich eine **Endung**, nie ein Pfad. Alles
Weitere macht ``UebrigeSuche`` unterhalb von ``BASE_DIR``.
"""
import json

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau.uebrigesuche import UebrigeSuche, geschuetzt


class UebrigePutzView(ZugriffMixin, View):
    u"""GET = Vorschau, POST = löschen."""

    #: Der Wert, den die Tabelle für Dateien ohne Endung schickt. Ein
    #: leerer Parameter ist im Formular nicht von „fehlt" zu unterscheiden.
    OHNE = '(ohne)'

    def _endung(self, roh):
        u"""Die Endung aus der Anfrage — geprüft, nie ein Pfad.

        Erlaubt ist der Sammelwert für „ohne Endung" oder ein Punkt mit
        Buchstaben, Ziffern, Bindestrich. Damit kann kein Pfadtrenner,
        kein `..` und kein Doppelpunkt durchkommen.
        """
        roh = (roh or '').strip()
        if roh == self.OHNE:
            return ''
        # GESCHÜTZTE ARTEN WERDEN ABGEWIESEN (02.09.2026, nach dem Verlust
        # von 10 `.xlsm`, 6 `.xlsx` und 2 `.otf`). Die Tabelle zeigt für
        # sie schon keinen Knopf; hier steht die Prüfung ein zweites Mal,
        # weil eine Absage aus dem Browser keine Absage ist.
        if geschuetzt(roh):
            return None
        if (len(roh) > 1 and len(roh) <= 12 and roh[0] == '.'
                and all(z.isalnum() or z == '-' for z in roh[1:])):
            return roh.lower()
        return None

    #: Mehr Endungen nimmt niemand von Hand aus — und die Tabelle zeigt
    #: ohnehin höchstens 25 Zeilen.
    HOECHSTENS = 25

    def _endungen(self, rohliste):
        u"""Mehrere Endungen prüfen — alle oder keine.

        Eine unzulässige Endung wird NICHT stillschweigend übergangen:
        Sonst löschte ein Klick auf fünf Zeilen am Ende vier, und der
        Bericht sähe aus, als sei alles erledigt.
        """
        if not isinstance(rohliste, list) or not rohliste:
            return None
        if len(rohliste) > self.HOECHSTENS:
            return None
        raus = []
        for roh in rohliste:
            if not isinstance(roh, str):
                return None
            endung = self._endung(roh)
            if endung is None:
                return None
            raus.append(endung)
        return sorted(set(raus))

    def get(self, request):
        u"""Vorschau — für eine Endung (``endung=``) oder mehrere
        (``endungen=.log,.dump``)."""
        viele = request.GET.get('endungen')
        suche = UebrigeSuche(settings.BASE_DIR)
        if viele:
            endungen = self._endungen([e for e in viele.split(',') if e])
            if endungen is None:
                return JsonResponse({'fehler': u'Unzulässige Auswahl'},
                                    status=400)
            return JsonResponse(suche.vorschau_mehrere(endungen))
        endung = self._endung(request.GET.get('endung'))
        if endung is None:
            return JsonResponse({'fehler': u'Unzulässige Endung'}, status=400)
        return JsonResponse(suche.vorschau(endung))

    def post(self, request):
        try:
            daten = json.loads(request.body or b'{}')
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'fehler': u'Ungültiges JSON'}, status=400)
        # MEHRERE ENDUNGEN (02.09.2026, auf Ansage). Der Mengenabgleich
        # gilt hier für die SUMME: Der Browser hat eine Gesamtzahl gezeigt,
        # und genau die muss noch stimmen.
        if 'endungen' in daten:
            endungen = self._endungen(daten.get('endungen'))
            if endungen is None:
                return JsonResponse({'fehler': u'Unzulässige Auswahl'},
                                    status=400)
            suche = UebrigeSuche(settings.BASE_DIR)
            erwartet = daten.get('anzahl')
            gefunden = sum(len(p) for p in suche.sammeln(endungen).values())
            if isinstance(erwartet, int) and erwartet != gefunden:
                return JsonResponse({
                    'fehler': (u'Der Bestand hat sich geändert: erwartet %d, '
                               u'gefunden %d. Bitte neu ansehen.'
                               % (erwartet, gefunden)),
                    'anzahl': gefunden}, status=409)
            return JsonResponse(suche.loeschen_mehrere(endungen))
        endung = self._endung(daten.get('endung'))
        if endung is None:
            return JsonResponse({'fehler': u'Unzulässige Endung'}, status=400)
        # NOCHMALS BESTÄTIGT: Der Browser muss die Anzahl mitschicken, die
        # er dem Nutzer gezeigt hat. Weicht sie von der jetzt gefundenen ab,
        # hat sich zwischen Vorschau und Klick etwas geändert — dann wird
        # nicht gelöscht, sondern neu gefragt. Sonst löscht ein Klick auf
        # „3 Dateien" am Ende dreitausend.
        erwartet = daten.get('anzahl')
        suche = UebrigeSuche(settings.BASE_DIR)
        # EINMAL erheben, zweimal benutzen: Der Durchgang über den Baum
        # kostet auf `assistant` rund 20 Sekunden. Geprüft wird trotzdem
        # jede Datei einzeln unmittelbar vor dem Löschen — das ist der
        # Schutz, nicht die Frische dieser Liste.
        treffer = suche.finden(endung)
        if isinstance(erwartet, int) and erwartet != len(treffer):
            return JsonResponse({
                'fehler': (u'Der Bestand hat sich geändert: erwartet %d, '
                           u'gefunden %d. Bitte neu ansehen.'
                           % (erwartet, len(treffer))),
                'anzahl': len(treffer)}, status=409)
        return JsonResponse(suche.loeschen(endung, treffer=treffer))
