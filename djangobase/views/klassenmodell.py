# -*- coding: utf-8 -*-
u"""Hilfe · Werkzeug Klassenmodell — das Objektmodell des Projekts als Bild.

WOZU (Edgar, 24.08.2026)
========================
    „erstelle eine Seite in djangoBase hilfe - werkzeug Klassenmodell, das
     soll einen Button enthalten, der so eine Übersicht des Codes erstellt"

`objektwurzeln` misst dasselbe Verhaeltnis schon — aber als Zahl („74 von
548 Klassen haengen als self.x an einer anderen"). Eine Zahl sagt, wie gut
das Modell ist; sie zeigt nicht, WIE es aussieht.

Das Bild entsteht auf Knopfdruck, nicht beim Seitenaufruf: Der Durchgang
liest jede ``.py`` des Projekts. Bei CamTrack sind das 1004 Klassen — das
gehoert nicht in den Weg von jemandem, der nur die Seite aufschlaegt.
"""
import time
from pathlib import Path

from django.conf import settings
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau.klassenbild import Klassenbild
from ..umbau.klassenmodell import Klassenmodell

#: Vorgabe fuer die Nachbarschaft. Zwei Schritte zeigen die Wurzel, was sie
#: haelt, und was DIESE halten — bei drei wird es eine Tapete.
TIEFE_VORGABE = 2


class Modellspeicher:
    u"""Haelt das eingelesene Modell, bis jemand ausdruecklich neu liest.

    DIE ANSAGE (Edgar, 24.08.2026)
    ==============================
        „mach auch einen Refresh button, damit der nicht alles neu
         durchgeht?"

    Berechtigt: Der Durchgang liest jede ``.py`` des Projekts — bei
    CamTrack 1023 Klassen. Wer nur eine andere Startklasse ansehen oder
    einen Schritt tiefer gehen will, braucht davon nichts neu.

    Gehalten wird je Bereich, im Arbeitsspeicher des Web-Dienstes. Ein
    Neustart leert ihn, und das ist richtig so: Nach einem Neustart hat
    sich der Quelltext womoeglich geaendert.
    """

    _modelle = {}

    @classmethod
    def holen(cls, wurzel, neu=False):
        u"""``(Modell, Alter in Sekunden oder None)``."""
        schluessel = str(wurzel)
        if not neu and schluessel in cls._modelle:
            modell, wann = cls._modelle[schluessel]
            return modell, time.time() - wann
        modell = Klassenmodell(wurzel).lesen()
        cls._modelle[schluessel] = (modell, time.time())
        return modell, None

    @classmethod
    def leeren(cls):
        cls._modelle.clear()


class KlassenmodellView(ZugriffMixin, View):
    u"""Zeigt die Seite; auf Knopfdruck rechnet sie das Bild."""

    vorlage = 'djangobase/hilfe/klassenmodell.html'

    def get(self, request):
        return self._seite(request)

    def post(self, request):
        wurzel = self._wurzel(request.POST.get('bereich', ''))
        modell, alter = Modellspeicher.holen(
            wurzel, neu=bool(request.POST.get('neu')))
        start = (request.POST.get('start') or '').strip() or None
        try:
            tiefe = max(1, min(4, int(request.POST.get('tiefe')
                                      or TIEFE_VORGABE)))
        except (TypeError, ValueError):
            tiefe = TIEFE_VORGABE
        kaesten, linien = modell.nachbarschaft(start, tiefe)
        gewaehlt = start or modell.dickster_ast()
        return self._seite(
            request,
            bild=Klassenbild(kaesten, linien, gewaehlt).svg() if kaesten else '',
            kennzahlen=modell.kennzahlen(),
            gewaehlt=gewaehlt,
            tiefe=tiefe,
            bereich=request.POST.get('bereich', ''),
            gezeigt=len(kaesten),
            aeste=self._aeste(modell),
            alter=int(alter) if alter is not None else None,
            leer=not kaesten and bool(start),
        )

    # ── intern ──────────────────────────────────────────────────
    @staticmethod
    def _wurzel(bereich):
        u"""Welcher Teil des Projekts wird gelesen?

        Ohne Angabe der ganze Projektbaum. Ein Unterordner macht das Bild
        kleiner und den Durchgang schneller — bei einem Projekt mit ueber
        tausend Klassen ist das der Unterschied zwischen Uebersicht und
        Tapete.
        """
        basis = Path(settings.BASE_DIR)
        teil = (bereich or '').strip().strip('/\\')
        if not teil:
            return basis
        ziel = (basis / teil).resolve()
        # Nicht aus dem Projekt heraus: Der Wert kommt aus einem Formular.
        if basis.resolve() not in ziel.parents and ziel != basis.resolve():
            return basis
        return ziel if ziel.is_dir() else basis

    @staticmethod
    def _aeste(modell, wie_viele=12):
        u"""Die dicksten Aeste als Vorschlagsliste — Wer haelt wie viele?"""
        gezaehlt = []
        for k in modell.klassen.values():
            eigene = {z for _f, z, _v in k.haelt if z in modell.klassen}
            if eigene:
                gezaehlt.append((len(eigene), k.name))
        gezaehlt.sort(reverse=True)
        return [{'name': n, 'zahl': z} for z, n in gezaehlt[:wie_viele]]

    def _seite(self, request, **zusatz):
        from django.shortcuts import render
        daten = {
            'titel': 'Werkzeug Klassenmodell',
            'tiefe': TIEFE_VORGABE,
            'aktiv': 'klassenmodell',
        }
        daten.update(zusatz)
        return render(request, self.vorlage, daten)


__all__ = ['KlassenmodellView']
