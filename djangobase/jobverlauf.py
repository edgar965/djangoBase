# -*- coding: utf-8 -*-
u"""Der Verlauf der Job-Laeufe: wann, wie lange, mit welchem Ausgang.

Angelegt am 26.08.2026 (Ansage Edgar): "eine Seite unter Hilfe, die
zeigt, welcher Job wann zuletzt lief, wie lange er brauchte und ob er
Fehler warf."

WAS ES SCHON GAB - UND WARUM ES NICHT REICHT
============================================
``djangobase.jobs`` fuehrt eine Registry der LAUFENDEN Hintergrund-Jobs.
Sie haelt den Momentanzustand im Speicher: Was tut der Thread gerade?
Nach einem Neustart ist sie leer, und ein Management-Command, der einmal
am Tag laeuft, taucht dort ueberhaupt nicht auf.

Der Verlauf beantwortet die andere Frage: Was ist PASSIERT? Er ueberlebt
den Neustart und kennt auch Laeufe, die laengst beendet sind.

WARUM EINE DATEI UND KEINE TABELLE
==================================
Eine Tabelle braeuchte eine Migration - und djangoBase steckt in sechs
Projekten. Jedes muesste migrieren, bevor die Seite dort funktioniert.
Die Einstellungen (``.djangobase.json``) und die Testhistorie
(``logs/testhistorie.json``) gehen denselben Weg: Datei statt Tabelle.

WARUM EINE ZEILE JE LAUF (JSONL)
================================
Management-Commands laufen als EIGENE PROZESSE, oft mehrere gleichzeitig
(ein Indexlauf, waehrend der Mail-Abruf schreibt). Wuerde jeder Prozess
die ganze Datei lesen, ergaenzen und zurueckschreiben, ueberschriebe der
langsamere den schnelleren - der Lauf waere weg, ohne Fehlermeldung.
Anhaengen einer Zeile hat dieses Problem nicht.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ['Jobverlauf']


class Jobverlauf(object):
    u"""Liest und schreibt die Laufhistorie.

    Ueblicher Gebrauch::

        verlauf = Jobverlauf()
        verlauf.notieren('mail_sync', dauer_s=12.4, erfolg=True)
        verlauf.letzter('mail_sync')   # -> dict oder None
    """

    #: Ab wie vielen Zeilen die Datei gekuerzt wird. 5.000 Laeufe sind
    #: bei taeglichen Jobs mehrere Jahre und noch keine 2 MB.
    GRENZE = 5000

    #: Wie viele Zeilen nach dem Kuerzen uebrig bleiben.
    BEHALTEN = 3000

    def __init__(self, pfad=None):
        self.pfad = Path(pfad) if pfad else self._standardpfad()

    @staticmethod
    def _standardpfad():
        u"""``BASE_DIR/logs/joblaeufe.jsonl`` - neben den Logdateien."""
        from django.conf import settings

        wurzel = Path(getattr(settings, 'BASE_DIR', '.'))
        return wurzel / 'logs' / 'joblaeufe.jsonl'

    # ------------------------------------------------------------ schreiben
    def notieren(self, kennung, dauer_s, erfolg, fehler='', hinweis='',
                 cpu_s=None, argumente=None, eigenstaendig=True):
        u"""Einen beendeten Lauf festhalten.

        Wirft NIE: Ein kaputter Verlauf darf keinen Job scheitern lassen -
        er ist eine Beobachtung, kein Teil der Arbeit.

        ``cpu_s`` (verbrauchte CPU-Sekunden) und ``argumente`` (die
        gesetzten Optionen des Befehls) kommen seit dem 02.09.2026 von der
        ``Jobaufzeichnung`` mit; aeltere Zeilen haben die Felder nicht, und
        wer sie liest, muss damit rechnen.
        """
        zeile = {
            'kennung': kennung,
            'zeit': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'dauer_s': round(float(dauer_s), 3),
            'erfolg': bool(erfolg),
            'fehler': (fehler or '')[:500],
            'hinweis': (hinweis or '')[:200],
        }
        if cpu_s is not None:
            zeile['cpu_s'] = round(float(cpu_s), 3)
        if argumente:
            zeile['argumente'] = dict(argumente)
        if not eigenstaendig:
            # Nur der Sonderfall wird vermerkt: ``call_command`` aus einem
            # Server-Thread. Alte Zeilen ohne das Feld sind eigenstaendig.
            zeile['im_server'] = True
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open('a', encoding='utf-8') as datei:
                datei.write(json.dumps(zeile, ensure_ascii=False) + '\n')
            self._kuerzen_wenn_noetig()
        except Exception:
            logger.exception('Jobverlauf.notieren: Lauf nicht gespeichert')

    def _kuerzen_wenn_noetig(self):
        u"""Alte Zeilen wegwerfen, damit die Datei nicht unbegrenzt waechst."""
        try:
            if not self.pfad.exists():
                return
            with self.pfad.open('r', encoding='utf-8') as datei:
                zeilen = datei.readlines()
            if len(zeilen) <= self.GRENZE:
                return
            neu = self.pfad.with_suffix('.jsonl.neu')
            with neu.open('w', encoding='utf-8') as datei:
                datei.writelines(zeilen[-self.BEHALTEN:])
            # Ersetzen statt Ueberschreiben: Ein gleichzeitiger Schreiber
            # verliert hoechstens seine eine Zeile, nie die ganze Datei.
            os.replace(str(neu), str(self.pfad))
        except Exception:
            logger.exception('Jobverlauf._kuerzen_wenn_noetig: Exception gefangen')

    # --------------------------------------------------------------- lesen
    def laeufe(self, kennung=None, hoechstens=None):
        u"""Alle Laeufe, juengster zuerst. ``kennung`` filtert auf einen Job."""
        raus = []
        try:
            if not self.pfad.exists():
                return raus
            with self.pfad.open('r', encoding='utf-8') as datei:
                for zeile in datei:
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    try:
                        satz = json.loads(zeile)
                    except ValueError:
                        # Eine abgeschnittene Zeile (Absturz beim Schreiben)
                        # macht den Rest der Datei nicht wertlos.
                        continue
                    if kennung and satz.get('kennung') != kennung:
                        continue
                    raus.append(satz)
        except Exception:
            logger.exception('Jobverlauf.laeufe: Exception gefangen')
        raus.reverse()
        return raus[:hoechstens] if hoechstens else raus

    def letzter(self, kennung):
        u"""Der juengste Lauf eines Jobs, oder ``None``."""
        treffer = self.laeufe(kennung, hoechstens=1)
        return treffer[0] if treffer else None

    def zusammenfassung(self):
        u"""Je Job eine Zeile: letzter Lauf, Dauer, Anzahl, Fehlerzahl.

        Ein Durchgang durch die Datei statt einer je Job - bei hundert
        Jobs waeren das sonst hundert Durchgaenge.
        """
        je_job = {}
        for satz in self.laeufe():          # juengster zuerst
            kennung = satz.get('kennung')
            if not kennung:
                continue
            eintrag = je_job.setdefault(kennung, {
                'kennung': kennung, 'letzter': satz, 'laeufe': 0,
                'fehler': 0, 'dauer_summe': 0.0,
            })
            eintrag['laeufe'] += 1
            eintrag['dauer_summe'] += satz.get('dauer_s') or 0.0
            if not satz.get('erfolg'):
                eintrag['fehler'] += 1
        for eintrag in je_job.values():
            eintrag['dauer_schnitt'] = (eintrag['dauer_summe'] / eintrag['laeufe']
                                        if eintrag['laeufe'] else 0.0)
        return je_job
