# -*- coding: utf-8 -*-
u"""Die Ablauf-Seite: ein Aktivitaetsdiagramm je Einstieg.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „mach mir die grafische Ausgabe von vorher, kein Quelltext, aber
     sowas in der Richtung des Screenshots"
    „belasse diese Ansicht, die ist auch nicht schlecht. mache eine neue
     Seite /hilfe/ablauf mit der neuen anforderung von vorher"

Drei Seiten, drei Fragen — und keine ersetzt die andere:

    /hilfe/klassenmodell/  Wer haelt wen? (Bauplan)
    /hilfe/workflows/      Was ist beteiligt? (Landkarte, Quelltext)
    /hilfe/ablauf/         Was passiert in welcher Reihenfolge? (Prosa)

Diese hier folgt der Vorlage aus dem Screenshot: gefuellter Kreis oben,
Mittelachse, abgerundete Kaesten mit lesbaren Saetzen, Rauten mit
beschrifteten Kanten, Doppelkreis unten.

WOHER DIE SAETZE KOMMEN — UND WOHER NICHT
=========================================
Aus dem Docstring der gerufenen Funktion, sonst aus ihrem Namen als
Woerter gelesen (``beschriftung.py``). NICHT uebersetzt: Ein Woerterbuch
``prepare -> vorbereiten`` waere eine Erfindung, und bei ``handle`` oder
``run`` waere sie fast sicher falsch.

Gemessen an CamTrack tragen nur 16 Prozent der Schritte einen Docstring.
Der Rest liest sich so gut, wie der Entwickler seinen Namen gewaehlt hat
— was zugleich sichtbar macht, wo er ihn schlecht gewaehlt hat.
"""
import logging

from django.conf import settings
from django.shortcuts import render
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau.ablauf import Ablauf
from ..umbau.aktivitaetsbild import Aktivitaetsbild
from ..umbau.beschriftung import Beschriftung
from ..umbau.workflows import Workflowspeicher

logger = logging.getLogger('djangobase.ablauf')


class AblaufView(ZugriffMixin, View):
    u"""Ein Einstieg links, sein Ablauf rechts."""

    vorlage = 'djangobase/hilfe/ablauf.html'

    def get(self, request):
        return self._zeigen(request, request.GET)

    def post(self, request):
        return self._zeigen(request, request.POST)

    def _zeigen(self, request, daten):
        wurzel = settings.BASE_DIR
        liste, alter = Workflowspeicher.holen(wurzel,
                                              neu=bool(daten.get('neu')))
        faecher = liste.reiter()
        reiter = daten.get('reiter') or (faecher[0][0] if faecher else '')
        weg = self._weg(liste, faecher, reiter, daten.get('weg', ''))
        lauf, bild = self._ablauf(liste, weg, daten.get('funktion', ''))
        return render(request, self.vorlage, {
            'aktiv': 'ablauf',
            'reiter': [{'kuerzel': k, 'titel': t, 'anzahl': len(w)}
                       for k, t, w in faecher],
            'offen': reiter,
            'wege': self._wegliste(faecher, reiter, weg),
            'weg': weg,
            'ablauf': lauf,
            'bild': bild,
            'zurueck': bool(daten.get('funktion')),
            'kennzahlen': liste.kennzahlen,
            'alter': alter,
        })

    # ── Das Bild ────────────────────────────────────────────────

    @staticmethod
    def _ablauf(liste, weg, funktion):
        u"""Der Ablauf des Einstiegs — oder der einer angeklickten Stelle."""
        if weg is None:
            return None, ''
        bezug = weg.start
        verzeichnis = liste.verzeichnis
        if funktion and verzeichnis is not None:
            klasse, _punkt, name = funktion.rpartition('.')
            gesucht = (verzeichnis.in_klasse(klasse, name) if klasse
                       else verzeichnis.funktionen.get(name))
            bezug = gesucht or bezug
        if bezug is None:
            return None, ''
        lauf = Ablauf(bezug, verzeichnis).lesen()
        bild = Aktivitaetsbild(
            lauf, lambda k: Beschriftung.fuer(k, verzeichnis))
        return lauf, bild.svg()

    # ── Auswahl (wie bei den Workflows) ─────────────────────────

    @staticmethod
    def _weg(liste, faecher, reiter, gewuenscht):
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
                    'aktiv': gewaehlt is not None
                    and weg.einstieg.titel == gewaehlt.einstieg.titel,
                })
        return aus
