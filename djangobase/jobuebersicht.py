# -*- coding: utf-8 -*-
u"""Die Zeilen der Jobs-Seite: Bestand und Verlauf zusammengefuehrt.

Angelegt am 26.08.2026. Der Auftrag lautete: "eine Seite unter Hilfe, die
zeigt, welcher Job wann zuletzt lief, wie lange er brauchte und ob er
Fehler warf."

Drei Bausteine, drei Zustaendigkeiten - hier laufen sie zusammen:

    Joberkennung   WELCHE Jobs gibt es?      (findet Befehle + Daemons)
    Jobkatalog     gemerkt, taeglich neu     (spart 93 Importe je Aufruf)
    Jobverlauf     WAS ist passiert?         (Zeit, Dauer, Ausgang)

Die Trennung hat einen Grund: Ein Job kann im Bestand stehen und nie
gelaufen sein (dann ist die Verlaufsspalte leer), und er kann im Verlauf
stehen, aber aus dem Bestand verschwunden sein - weil jemand die Datei
geloescht hat. Der zweite Fall waere sonst unsichtbar; genau dann will
man aber wissen, dass da noch etwas laeuft oder lief.
"""
import logging

logger = logging.getLogger(__name__)

__all__ = ['Jobuebersicht']


class Jobuebersicht(object):
    u"""Baut die Tabelle der Jobs-Seite.

        uebersicht = Jobuebersicht()
        zeilen = uebersicht.zeilen()
        stand = uebersicht.stand()       # wann zuletzt ermittelt
    """

    def __init__(self, katalog=None, verlauf=None):
        self._katalog = katalog
        self._verlauf = verlauf

    @property
    def katalog(self):
        if self._katalog is None:
            from .jobkatalog import Jobkatalog

            self._katalog = Jobkatalog()
        return self._katalog

    @property
    def verlauf(self):
        if self._verlauf is None:
            from .jobverlauf import Jobverlauf

            self._verlauf = Jobverlauf()
        return self._verlauf

    # ------------------------------------------------------------- lesen
    def zeilen(self, neu=False):
        u"""Je Job eine Zeile, Jobs mit Fehlern zuerst.

        ``neu=True`` ermittelt den Bestand neu (Knopf "Jetzt
        aktualisieren"), sonst gilt der gemerkte, solange er frisch ist.
        """
        bestand = self.katalog.aktualisieren() if neu else self.katalog.jobs()
        historie = self.verlauf.zusammenfassung()

        raus = [self._zeile(job, historie.pop(job['kennung'], None))
                for job in bestand]
        # Was noch im Verlauf steht, aber nicht mehr im Bestand: der
        # geloeschte oder umbenannte Befehl. Er gehoert sichtbar gemacht.
        for rest in historie.values():
            raus.append(self._zeile({
                'kennung': rest['kennung'], 'name': rest['kennung'],
                'app': '', 'art': 'unbekannt',
                'hilfe': 'Nicht mehr im Bestand — gelöscht oder umbenannt?',
            }, rest))

        raus.sort(key=self._reihenfolge)
        return raus

    @staticmethod
    def _zeitpunkt(iso):
        u"""Aus dem gespeicherten ISO-Text ein ``datetime`` machen.

        Der Verlauf speichert UTC (eindeutig, auch ueber die Zeitumstellung
        hinweg). Als TEXT ausgegeben stuende auf der Seite dann 21:11,
        waehrend die Uhr des Nutzers 23:11 zeigt - genau so ist es beim
        ersten Aufruf am 26.08.2026 auf der Seite gestanden. Als
        ``datetime`` rechnet Django es in die Zeitzone des Projekts um.
        """
        if not iso:
            return None
        try:
            from datetime import datetime

            return datetime.fromisoformat(iso)
        except ValueError:
            return None

    @classmethod
    def _zeile(cls, job, historie):
        letzter = (historie or {}).get('letzter') or {}
        return {
            'kennung': job['kennung'],
            'name': job.get('name') or job['kennung'],
            'app': job.get('app') or '',
            'art': job.get('art') or 'befehl',
            'hilfe': job.get('hilfe') or '',
            'zustand': job.get('zustand') or None,
            'lief_am': letzter.get('zeit') or '',
            'lief_am_zeit': cls._zeitpunkt(letzter.get('zeit')),
            'dauer_s': letzter.get('dauer_s'),
            'erfolg': letzter.get('erfolg'),
            'fehler': letzter.get('fehler') or '',
            'laeufe': (historie or {}).get('laeufe', 0),
            'fehlerzahl': (historie or {}).get('fehler', 0),
            'dauer_schnitt': (historie or {}).get('dauer_schnitt'),
            'nie_gelaufen': not letzter,
        }

    @staticmethod
    def _reihenfolge(zeile):
        u"""Erst die Fehlgeschlagenen, dann die Gelaufenen, dann der Rest.

        Wer die Seite oeffnet, sucht das Kaputte - nicht die alphabetisch
        erste Zeile.
        """
        gescheitert = 0 if zeile['erfolg'] is False else 1
        nie = 1 if zeile['nie_gelaufen'] else 0
        # Juengster Lauf zuerst: absteigend, deshalb der Kunstgriff mit
        # der Umkehrung ueber den negierten Zeitstempel als Text.
        return (gescheitert, nie, _umgekehrt(zeile['lief_am']), zeile['kennung'])

    def stand(self):
        u"""Wann der Bestand zuletzt ermittelt wurde (``datetime``/``None``)."""
        return self.katalog.ermittelt_am()

    def veraltet(self):
        return self.katalog.veraltet()

    def zahlen(self):
        u"""Kopfzeile der Seite: wie viele Jobs, wie viele mit Fehler."""
        zeilen = self.zeilen()
        return {
            'gesamt': len(zeilen),
            'gelaufen': sum(1 for z in zeilen if not z['nie_gelaufen']),
            'fehlerhaft': sum(1 for z in zeilen if z['erfolg'] is False),
            'nie': sum(1 for z in zeilen if z['nie_gelaufen']),
        }


def _umgekehrt(text):
    u"""Sortierschluessel, der Zeitstempel ABSTEIGEND ordnet.

    ``sorted`` kann nicht je Feld die Richtung wechseln. Fuer Zahlen
    nimmt man das Minuszeichen; fuer Text gibt es das nicht. Die
    Umkehrung ueber die Zeichenwerte leistet dasselbe: Aus dem groessten
    Text wird der kleinste Schluessel.
    """
    return tuple(-ord(z) for z in (text or ''))
