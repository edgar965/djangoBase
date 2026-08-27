# -*- coding: utf-8 -*-
u"""Die Workflow-Seite: was das Projekt tut, aus dem Code gelesen.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „in hilfe, neues Menü mit Seite: workflows, ähnlich aufgebaut wie
     /hilfe/klassenmodell/. Ich möchte die wichtigsten Workflows darin
     grafisch dokumentieren, in 3-4 Tabs"
    „die workflows sollst du aber ermitteln, schau dir jede Seite durch
     und ermittle 20-50 Workflows"
    „ordne sie an nach Komplexität (Anzahl der beteiligten Klassen)"

Aufbau wie beim Klassenmodell: Der Durchgang kostet Zeit, also wird er
gespeichert und ueberlebt den Neustart; die Seite zeigt beim Aufschlagen
den letzten Stand statt leer dazustehen.

WAS DIESE SEITE VON DER HILFE UNTERSCHEIDET
===========================================
Eine Hilfeseite beschreibt, was passieren SOLL. Diese Seite zeigt, was
tatsaechlich im Code steht — und wird darum nicht falsch, wenn jemand den
Code aendert, sondern zeigt den geaenderten Weg.

Gegenprobe am selben Tag: ``app/templates/app/help/workflow.html`` zeichnet
denselben Ablauf als ASCII und spricht von „10-Minuten-Segmenten". Seit
v0.83 schreibt der Segment-Muxer Stundendateien, seit v0.88 liegt der
Hauptstrom in 10-SEKUNDEN-Bloecken. Genau dieser Verfall soll hier nicht
mehr moeglich sein.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from ..umbau.ablage import Speicher
from ..umbau.workflowbild import Workflowbild
from ..umbau.workflows import Workflowliste
from ..mixins import ZugriffMixin

logger = logging.getLogger('djangobase.workflows')


class Workflowspeicher(Speicher):
    u"""Die ermittelten Wege — einmal gelesen, dann gemerkt.

    Gemessen an CamTrack: 688 Dateien, 284 Einstiege, rund zwei Sekunden.
    Das gehoert nicht in jeden Reiterwechsel.
    """

    bereich = 'workflows'

    @staticmethod
    def bauen(wurzel):
        return Workflowliste(wurzel).lesen()


class WorkflowsView(ZugriffMixin, View):
    u"""Zeigt die Wege; auf Knopfdruck liest sie den Code neu."""

    vorlage = 'djangobase/hilfe/workflows.html'

    def get(self, request):
        return self._zeigen(request, request.GET)

    def post(self, request):
        return self._zeigen(request, request.POST)

    def _zeigen(self, request, daten):
        wurzel = self._wurzel()
        neu = bool(daten.get('neu'))
        liste, alter = Workflowspeicher.holen(wurzel, neu=neu)
        faecher = liste.reiter()
        reiter = daten.get('reiter') or (faecher[0][0] if faecher else '')
        gewaehlt = self._weg(liste, faecher, reiter, daten.get('weg', ''))
        return render(request, self.vorlage, {
            'aktiv': 'workflows',
            'reiter': [{'kuerzel': k, 'titel': t, 'anzahl': len(w)}
                       for k, t, w in faecher],
            'offen': reiter,
            'wege': self._wegliste(faecher, reiter, gewaehlt),
            'weg': gewaehlt,
            'bild': Workflowbild(gewaehlt).svg() if gewaehlt else '',
            'kennzahlen': liste.kennzahlen,
            'verworfen': liste.verworfen,
            'alter': alter,
            'wurzel': str(wurzel),
        })

    # ── Auswahl ─────────────────────────────────────────────────

    @staticmethod
    def _wurzel():
        u"""Der Projektbaum. Ein Unterordner waere hier falsch: Ein Weg
        laeuft quer durch das Projekt, und ein Ausschnitt schnitte ihn
        genau dort ab, wo es interessant wird."""
        return settings.BASE_DIR

    @staticmethod
    def _weg(liste, faecher, reiter, gewuenscht):
        u"""Der angezeigte Weg — der gewaehlte, sonst der erste des Reiters."""
        for kuerzel, _titel, wege in faecher:
            if kuerzel != reiter:
                continue
            for weg in wege:
                if weg.einstieg.titel == gewuenscht:
                    return weg
            return wege[0] if wege else None
        return liste.wege[0] if liste.wege else None

    @staticmethod
    def _wegliste(faecher, reiter, gewaehlt):
        aus = []
        for kuerzel, _titel, wege in faecher:
            if kuerzel != reiter:
                continue
            for weg in wege:
                aus.append({
                    'titel': weg.einstieg.titel,
                    'art': weg.einstieg.art,
                    'klassen': len(weg.klassen),
                    'schritte': len(weg.schritte),
                    'offen': len(set(weg.offen)),
                    'aktiv': gewaehlt is not None
                    and weg.einstieg.titel == gewaehlt.einstieg.titel,
                })
        return aus


class WorkflowsDatenView(ZugriffMixin, View):
    u"""Dieselbe Ermittlung als JSON — fuer die Pruefung im Werkzeugkasten.

    Damit misst der Test dasselbe, was die Seite zeigt. Zwei Wege zur
    selben Zahl laufen auseinander; das ist die Lehre aus der Live-Kachel.
    """

    def get(self, request):
        liste, _alter = Workflowspeicher.holen(self._wurzel(),
                                               neu=bool(request.GET.get('neu')))
        return JsonResponse(liste.als_dict())

    @staticmethod
    def _wurzel():
        return settings.BASE_DIR
