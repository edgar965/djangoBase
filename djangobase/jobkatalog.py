# -*- coding: utf-8 -*-
u"""Der gemerkte Bestand der Jobs - taeglich aufgefrischt.

Angelegt am 26.08.2026 (Ansage Edgar): "die jobs sollen gecacht werden,
und die Seite soll täglich aktualisiert werden, weitere Knopfdruck:
Jetzt aktualisieren".

WARUM GEMERKT
=============
``Joberkennung.ermitteln()`` liest nicht nur Namen: Fuer die Beschreibung
muss jede Befehlsklasse IMPORTIERT werden. In assistant sind das 93
Importe, von denen manche Modelle laden, Bibliotheken ziehen oder ein
Modell in den Speicher holen. Das bei jedem Seitenaufruf zu tun, waere
teuer und in Teilen sogar riskant.

Der Bestand aendert sich hoechstens, wenn jemand eine Datei anlegt - also
selten. Einmal am Tag reicht; wer nicht warten will, drueckt "Jetzt
aktualisieren".

WARUM EINE DATEI UND KEIN CACHE-FRAMEWORK
=========================================
``django.core.cache`` ist in den Konsumenten unterschiedlich (teils
LocMem, teils gar nicht) konfiguriert. LocMem lebt je Prozess: Der
Entwicklungsserver haette zwei davon, und ein Management-Command sieht
keinen. Eine Datei neben den Logdateien sehen alle - wie
``logs/testhistorie.json`` und ``logs/joblaeufe.jsonl``.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ['Jobkatalog']


class Jobkatalog(object):
    u"""Haelt die ermittelten Jobs und weiss, wann sie zu alt sind.

        katalog = Jobkatalog()
        jobs = katalog.jobs()             # ermittelt bei Bedarf selbst
        jobs = katalog.aktualisieren()    # ermittelt in jedem Fall neu
    """

    #: Wie lange ein Bestand gilt. Taeglich - siehe Klassendoku.
    FRIST = timedelta(days=1)

    def __init__(self, pfad=None, erkennung=None):
        self.pfad = Path(pfad) if pfad else self._standardpfad()
        #: Wer die Jobs findet. Austauschbar, damit ein Test nicht die
        #: echten 93 Befehle des Projekts importieren muss.
        self._erkennung = erkennung

    @staticmethod
    def _standardpfad():
        from django.conf import settings

        wurzel = Path(getattr(settings, 'BASE_DIR', '.'))
        return wurzel / 'logs' / 'jobkatalog.json'

    @property
    def erkennung(self):
        if self._erkennung is None:
            from .joberkennung import Joberkennung

            self._erkennung = Joberkennung()
        return self._erkennung

    # -------------------------------------------------------------- lesen
    def gemerkt(self):
        u"""Der gespeicherte Bestand als dict - oder ``None``.

        ``None`` heisst: nichts da oder unbrauchbar. Beides fuehrt zum
        selben Verhalten (neu ermitteln), deshalb wird nicht unterschieden.
        """
        try:
            if not self.pfad.exists():
                return None
            with self.pfad.open('r', encoding='utf-8') as datei:
                daten = json.load(datei)
            if not isinstance(daten, dict) or 'jobs' not in daten:
                return None
            return daten
        except Exception:
            logger.exception('Jobkatalog.gemerkt: Bestand nicht lesbar')
            return None

    def ermittelt_am(self):
        u"""Wann zuletzt ermittelt wurde - als ``datetime`` oder ``None``."""
        daten = self.gemerkt()
        if not daten:
            return None
        try:
            return datetime.fromisoformat(daten['ermittelt_am'])
        except (KeyError, ValueError):
            return None

    def veraltet(self):
        u"""``True``, wenn nichts da ist oder die Frist abgelaufen ist."""
        wann = self.ermittelt_am()
        if wann is None:
            return True
        return (datetime.now(timezone.utc) - wann) >= self.FRIST

    def jobs(self):
        u"""Der Bestand. Ermittelt selbst neu, wenn er zu alt ist."""
        if self.veraltet():
            return self.aktualisieren()
        daten = self.gemerkt()
        return (daten or {}).get('jobs', [])

    # --------------------------------------------------------- schreiben
    def aktualisieren(self):
        u"""Neu ermitteln und merken. Gibt die gefundenen Jobs zurueck."""
        gefunden = self.erkennung.ermitteln()
        self._schreiben(gefunden)
        return gefunden

    def _schreiben(self, jobs):
        daten = {
            'ermittelt_am': datetime.now(timezone.utc).isoformat(
                timespec='seconds'),
            'jobs': jobs,
        }
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            # Erst daneben, dann umbenennen: Bricht das Schreiben ab,
            # bleibt der alte Bestand heil statt halb ueberschrieben.
            neben = self.pfad.with_suffix('.json.neu')
            with neben.open('w', encoding='utf-8') as datei:
                json.dump(daten, datei, ensure_ascii=False, indent=1)
            import os

            os.replace(str(neben), str(self.pfad))
        except Exception:
            logger.exception('Jobkatalog._schreiben: Bestand nicht gespeichert')
