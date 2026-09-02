# -*- coding: utf-8 -*-
u"""Hilfe · Code Review — Abschnitt „Kontextverbrauch".

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „baue die Kontextanalyse auch als werkzeug ein, mach einen extra
     Abschnitt unter Hilfe - Code Review"

Anlass war die Frage davor: „in dieser session wird sehr oft compact
aufgefordert, warum?" Die Antwort liess sich nur messen, nicht schaetzen
— und eine Messung, die man einmal von Hand macht, ist beim naechsten Mal
wieder weg. Deshalb als Werkzeug.

AUF KNOPFDRUCK, NICHT BEIM SEITENAUFRUF
=======================================
Ein Protokoll ist dreistellig MB gross. Am selben Tag hat genau diese
Frage die Seite „Werkzeug Klassenmodell" unbenutzbar gemacht: Sie rechnete
bei jedem Aufruf, wurde nie fertig, legte deshalb nie etwas ab und fing
beim naechsten Mal von vorn an. Hier wird nur gerechnet, wenn jemand den
Knopf drueckt — und das Ergebnis kommt in dieselbe Ablage.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from ..mixins import ZugriffMixin
from ..review.kontext import Kontextanalyse
from ..review.kontext_sitzungen import Sitzungen
from ..umbau.ablage import Speicher

logger = logging.getLogger('djangobase.review')


class Kontextspeicher(Speicher):
    u"""Eine ausgewertete Sitzung — gemerkt und abgelegt.

    Der Schluessel ist der Protokollpfad. Ein Protokoll waechst waehrend
    der Sitzung weiter; wer den frischen Stand will, drueckt „neu
    einlesen". Ein Zeitstempel im Schluessel waere falsch: Dann waere
    jeder Abruf ein neuer Lauf, und die Ablage brachte nichts.
    """

    bereich = 'kontextanalyse'

    @staticmethod
    def bauen(pfad):
        return Kontextanalyse(pfad).lesen()


class ReviewKontextView(ZugriffMixin, View):
    u"""Liefert die Auswertung einer Sitzung als JSON."""

    def get(self, request):
        sitzungen = Sitzungen(settings.BASE_DIR)
        pfad = request.GET.get('sitzung') or sitzungen.neueste()
        if not sitzungen.gueltig(pfad):
            return JsonResponse(
                {'fehler': 'Kein Sitzungsprotokoll zu diesem Projekt '
                           'gefunden.'}, status=404)
        neu = request.GET.get('neu') == '1'
        try:
            analyse, alter = Kontextspeicher.holen(pfad, neu=neu)
        except OSError as exc:
            logger.warning('Kontextanalyse fehlgeschlagen: %s', exc)
            return JsonResponse({'fehler': str(exc)}, status=500)
        return JsonResponse({
            'kennzahlen': analyse.kennzahlen(),
            'arten': analyse.arten(),
            'werkzeuge': analyse.werkzeuge(),
            'groesste': analyse.groesste(),
            'alter': int(alter) if alter is not None else None,
        })


__all__ = ['ReviewKontextView', 'Kontextspeicher']
