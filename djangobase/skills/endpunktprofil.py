"""Endpunktprofil — cProfile fuer EINE Route, eigene Zeit und Aufrufbaum."""

import cProfile
import io
import pstats

from .routen import klient
from .befund import Befund, Befundsatz, BefundWerkzeug


class Endpunktprofil(BefundWerkzeug):

    slug = 'endpunkt-profil'
    titel = 'Endpunkt-Profil'
    zweck = ('Profiliert eine einzelne Route mit cProfile und zeigt beide '
             'Sichten: tottime (wo gerechnet wird) und cumulative (wer es '
             'veranlasst).')
    abhilfe = ('Sobald die Endpunkt-Zeiten einen Ausreisser zeigen. Beide Listen '
            'sind noetig — die eigene Zeit allein verraet nicht, warum eine '
            'Funktion 40.000-mal laeuft.')
    befund = ('So kamen die groessten Funde zustande: eine Doppelschleife mit '
             '248.354 abs()-Aufrufen, 7.067 einzelne stat()-Aufrufe statt eines '
             'Verzeichnisscans, und 144 ms reines JSON-Kodieren fuer ein '
             'Ergebnis, das schon im Zwischenspeicher lag.')
    dauer = 'Sekunden'
    eingabe = ('weg', 'Welche Route? (z. B. /hilfe/logs/)', '/')
    ruft_endpunkte_auf = True

    #: So viele Zeilen je Sicht.
    ZEILEN = 15

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = ("fragt den LAUFENDEN Server und misst dabei Abfragen und Zeit")

    def pruefen(self, weg='/', **_argumente):
        ziel = (str(weg).strip() or '/')
        if not ziel.startswith('/'):
            ziel = '/' + ziel
        besucher = klient()
        # Einmal warmlaufen: Der erste Aufruf enthaelt Importe und das Fuellen
        # aller Zwischenspeicher und verzerrt das Bild sonst vollstaendig.
        besucher.get(ziel)

        profil = cProfile.Profile()
        profil.enable()
        antwort = besucher.get(ziel)
        profil.disable()

        kopf = ['%s -> Status %s, %d Byte'
                % (ziel, antwort.status_code, len(antwort.content))]
        befunde = []
        for sortierung, erklaerung in (
                ('tottime', 'eigene Zeit — hier wird gerechnet'),
                ('cumulative', 'inklusive Aufgerufener — hier wird veranlasst')):
            befunde.append(Befund('— %s —' % sortierung, erklaerung,
                                  gewicht=Befund.HINWEIS))
            befunde.extend(self._zeilen(profil, sortierung))
        return Befundsatz(self.titel, kopf, befunde)

    def _zeilen(self, profil, sortierung):
        puffer = io.StringIO()
        pstats.Stats(profil, stream=puffer).sort_stats(sortierung).print_stats(
            self.ZEILEN)
        befunde = []
        for zeile in puffer.getvalue().split('\n'):
            teile = zeile.split(None, 5)
            if len(teile) < 6 or not teile[0][0].isdigit():
                continue
            aufrufe, eigen, _pa, gesamt, _pg, ort = teile
            befunde.append(Befund(
                self._kurzort(ort),
                '%8s Aufrufe   eigen %ss   gesamt %ss' % (aufrufe, eigen, gesamt),
                gewicht=Befund.HINWEIS))
        return befunde

    @staticmethod
    def _kurzort(ort):
        """`…/site-packages/django/db/models/base.py:482(__init__)` kuerzen."""
        for marke in ('site-packages\\', 'site-packages/', '\\lib\\', '/lib/'):
            stelle = ort.lower().find(marke)
            if stelle >= 0:
                return '…' + ort[stelle + len(marke):]
        return ort[-70:] if len(ort) > 70 else ort
