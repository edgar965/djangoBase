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
from ..umbau.globalbestand import Globalbestand, hauptaeste
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


class Bestandsspeicher:
    u"""Dasselbe fuer den Modulebenen-Bestand: einmal lesen, oft ansehen."""

    _bestaende = {}

    @classmethod
    def holen(cls, wurzel, neu=False):
        schluessel = str(wurzel)
        if not neu and schluessel in cls._bestaende:
            bestand, wann = cls._bestaende[schluessel]
            return bestand, time.time() - wann
        bestand = Globalbestand(wurzel).lesen()
        cls._bestaende[schluessel] = (bestand, time.time())
        return bestand, None

    @classmethod
    def leeren(cls):
        cls._bestaende.clear()


class KlassenmodellView(ZugriffMixin, View):
    u"""Zeigt die Seite; auf Knopfdruck rechnet sie das Bild."""

    vorlage = 'djangobase/hilfe/klassenmodell.html'

    def get(self, request):
        return self._seite(request)

    #: Die Reiter der Seite. Der Schluessel steht im Formular.
    REITER = (
        ('baum', 'Klassenmodell', 'bi-diagram-3'),
        ('funktionen', 'Globale Funktionen', 'bi-code-slash'),
        ('klassen', 'Globale Klassen', 'bi-boxes'),
        ('variablen', 'Globale Variablen', 'bi-hash'),
        ('seiten', 'HTML-Seiten', 'bi-filetype-html'),
    )

    def post(self, request):
        wurzel = self._wurzel(request.POST.get('bereich', ''))
        neu = bool(request.POST.get('neu'))
        reiter = request.POST.get('reiter', 'baum')
        if reiter not in dict((k, 1) for k, _l, _i in self.REITER):
            reiter = 'baum'
        if reiter != 'baum':
            bestand, alter = Bestandsspeicher.holen(wurzel, neu=neu)
            zusatz = {}
            if reiter == 'klassen':
                # Die Einteilung braucht das Klassenmodell (wer haelt wen),
                # nicht den Modulebenen-Bestand.
                modell, _a = Modellspeicher.holen(wurzel, neu=neu)
                zusatz['kategorien'] = modell.kategorien()
                zusatz['klassen_gesamt'] = len(modell.klassen)
            return self._seite(
                request, reiter=reiter, bestand=bestand,
                kennzahlen=bestand.kennzahlen(),
                bereich=request.POST.get('bereich', ''),
                alter=int(alter) if alter is not None else None, **zusatz)
        modell, alter = Modellspeicher.holen(wurzel, neu=neu)
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
            reiter='baum',
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
            'reiter': 'baum',
            'reiter_liste': [{'key': k, 'label': l, 'icon': i}
                             for k, l, i in self.REITER],
            # Je ein Bereich pro Hauptast — ein kleinerer Ausschnitt
            # bedeutet einen schnelleren Durchgang und ein lesbares Bild.
            'bereiche': hauptaeste(settings.BASE_DIR),
        }
        daten.update(zusatz)
        return render(request, self.vorlage, daten)


__all__ = ['KlassenmodellView']
