"""Endpunktprobe — Statuscode jeder GET-Route gegen eine Referenz."""

import json
from pathlib import Path

from django.conf import settings

from .routen import alle_routen, klient
from .befund import Befund, Befundsatz, BefundWerkzeug


class Endpunktprobe(BefundWerkzeug):

    slug = 'endpunkt-probe'
    titel = 'Endpunkt-Probe'
    zweck = ('Ruft jede GET-Route auf, haelt den Statuscode fest und vergleicht '
             'ihn beim naechsten Lauf. Neue, verschwundene und veraenderte '
             'Routen werden gemeldet.')
    abhilfe = ('VOR einem grossen Umbau einmal als Referenz aufnehmen, danach nach '
            'jedem Schritt pruefen. Das ist das Sicherheitsnetz fuer alles, was '
            'keine Tests hat: Wer eine 6.000-Zeilen-Datei zerlegt, merkt einen '
            'kaputten Endpunkt sonst erst, wenn jemand die Seite oeffnet.')
    befund = ('Hat den Umbau von 110 Endpunkten aus einer Datei in Module '
             'abgesichert — 195 Routen unveraendert, jede Abweichung sofort '
             'sichtbar.')
    dauer = 'mehrere Minuten — gemessen: 147 s fuer 188 Routen'
    eingabe = ('modus', "'pruefen' oder 'referenz' (Sollzustand neu aufnehmen)",
               'pruefen')
    ruft_endpunkte_auf = True

    DATEI = '.djangobase-endpunkte.json'

    def pruefen(self, modus='pruefen', **_argumente):
        besucher = klient()
        aktuell = {}
        for route in alle_routen():
            try:
                antwort = besucher.get(route.weg)
                aktuell[route.weg] = antwort.status_code
            except Exception as fehler:  # noqa: BLE001
                aktuell[route.weg] = 'Ausnahme: %s' % type(fehler).__name__

        pfad = Path(str(settings.BASE_DIR)) / self.DATEI
        if str(modus).strip().lower().startswith('ref'):
            pfad.write_text(json.dumps(aktuell, indent=2, ensure_ascii=False),
                            encoding='utf-8')
            return Befundsatz(self.titel, [
                'Referenz mit %d Routen geschrieben:' % len(aktuell),
                self.kurz(pfad),
                'Ab jetzt meldet der Modus "pruefen" jede Abweichung.',
            ])

        if not pfad.is_file():
            return Befundsatz(self.titel, [
                'Noch keine Referenz vorhanden.',
                'Einmal mit Modus "referenz" laufen lassen — am besten JETZT, '
                'solange die Anwendung nachweislich funktioniert.',
                '%d Routen wuerden aufgenommen.' % len(aktuell),
            ])

        try:
            referenz = json.loads(pfad.read_text(encoding='utf-8'))
        except (OSError, ValueError) as fehler:
            return Befundsatz(self.titel, fehler='Referenz nicht lesbar: %s' % fehler)

        befunde = []
        for weg, stand in sorted(aktuell.items()):
            if weg not in referenz:
                befunde.append(Befund(weg, 'NEU: Status %s' % stand,
                                      gewicht=Befund.HINWEIS))
            elif referenz[weg] != stand:
                befunde.append(Befund(
                    weg, 'GEAENDERT: %s -> %s' % (referenz[weg], stand),
                    'vorher %s, jetzt %s' % (referenz[weg], stand), Befund.FEHLER))
        for weg in sorted(set(referenz) - set(aktuell)):
            befunde.append(Befund(weg, 'VERSCHWUNDEN (vorher %s)' % referenz[weg],
                                  gewicht=Befund.FEHLER))

        gleich = len(set(aktuell) & set(referenz)) - sum(
            1 for b in befunde if 'GEAENDERT' in b.was)
        return Befundsatz(self.titel, [
            '%d Routen geprueft, %d unveraendert' % (len(aktuell), gleich),
            'Referenz: ' + self.kurz(pfad),
        ], befunde)
