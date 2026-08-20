# -*- coding: utf-8 -*-
u"""Aufzeichnung - was der Nutzer im UI tut, als Rohstoff fuer einen Testfall.

DER AUFTRAG (Edgar, 20.08.2026)
==============================
    „mach in djangoBase auf /hilfe/tests/ einen neuen Tab: Testcase aufzeichnen.
     … Ein Aufzeichnen Button soll erscheinen, der deaktiviert ist. wenn ich den
     aktiviere, werden logs und aktionen erfasst und gespeichert, damit die
     Aktionen die ich im UI mache, aufgezeichnet werden. … Ziel ist es, dass du
     aus diesen Aufzeichnungen echte Tests erstellen kannst."

WARUM DER ZUSTAND AUF DEN SERVER GEHOERT
========================================
Aufgezeichnet wird, was der Nutzer TUT - und dabei wechselt er die Seite. Laege
der Schalter nur im Browser, waere die Aufzeichnung beim ersten Klick auf einen
Menuepunkt vorbei; genau die Wege ueber mehrere Seiten sind aber die
interessanten. Deshalb steht hier, OB gerade aufgezeichnet wird, und jede Seite
fragt es beim Laden ab.

ZWEI QUELLEN, EINE ZEITACHSE
============================
    Schritte   was im Browser passiert (Klick, Eingabe, Seitenwechsel, Abruf)
    Logs       was der Server dabei protokolliert

Beide tragen einen Zeitstempel relativ zum Start. Erst zusammen ergeben sie
einen Testfall: Die Schritte sagen, was zu tun ist, die Logs, was dabei
herauskommen muss.

WO ES LIEGT
===========
``BASE_DIR/logs/aufzeichnungen.json`` - im Projekt, nie in System-Temp (harte
Vorgabe wegen rund 100 GB Datenmuell auf C:). Keine Datenbank und keine
Migration: djangoBase laeuft in sechs Projekten, und ein neues Modell zwaenge
jedem davon ein ``migrate`` auf.

GRENZEN, DAMIT NICHTS DAVONLAEUFT
=================================
Eine Aufzeichnung sammelt Ereignisse im Sekundentakt. Ohne Deckel waere die
Datei nach einer vergessenen Sitzung Megabyte gross - deshalb ``MAX_SCHRITTE``
je Aufzeichnung, ``MAX_AUFZEICHNUNGEN`` insgesamt (die aeltesten fallen heraus)
und ``MAX_LAUFZEIT_S``, nach der eine offene Aufzeichnung von selbst endet.
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from django.conf import settings

log = logging.getLogger("djangobase.tests")

__all__ = ["Aufzeichnung", "Aufzeichnungen"]


class Aufzeichnung:
    u"""EINE Aufzeichnung: Kopf, Schritte, Log-Zeilen."""

    __slots__ = ("id", "name", "start", "ende", "schritte", "logs", "seite")

    def __init__(self, kennung, name, start, ende="", schritte=None, logs=None,
                 seite=""):
        self.id = kennung
        self.name = name
        self.start = start
        self.ende = ende
        self.schritte = list(schritte or [])
        self.logs = list(logs or [])
        #: Seite, auf der gestartet wurde - der Einstiegspunkt des Testfalls.
        self.seite = seite

    @property
    def laeuft(self):
        return not self.ende

    @property
    def dauer_s(self):
        u"""Sekunden zwischen Start und Ende - oder bis jetzt, wenn sie laeuft."""
        try:
            a = datetime.fromisoformat(self.start)
        except (TypeError, ValueError):
            return 0.0
        b = datetime.fromisoformat(self.ende) if self.ende else datetime.now(a.tzinfo)
        return max(0.0, round((b - a).total_seconds(), 1))

    def as_dict(self):
        return {"id": self.id, "name": self.name, "start": self.start,
                "ende": self.ende, "schritte": self.schritte, "logs": self.logs,
                "seite": self.seite}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("id", ""), d.get("name", ""), d.get("start", ""),
                   d.get("ende", ""), d.get("schritte"), d.get("logs"),
                   d.get("seite", ""))

    # ------------------------------------------------------------- Auskunft
    def kurz(self):
        u"""Der Kopf ohne die Ereignisse - fuer Listen und Tabellen."""
        return {"id": self.id, "name": self.name, "start": self.start,
                "ende": self.ende, "seite": self.seite, "laeuft": self.laeuft,
                "dauer_s": self.dauer_s, "n_schritte": len(self.schritte),
                "n_logs": len(self.logs)}


class Aufzeichnungen:
    u"""Der Bestand - als JSON im Projekt, mit genau einer laufenden Aufnahme."""

    DATEINAME = "aufzeichnungen.json"
    #: Mehr Ereignisse nimmt eine Aufzeichnung nicht auf (Schutz vor Weglaufen).
    MAX_SCHRITTE = 2000
    #: So viele Aufzeichnungen werden behalten; die aeltesten fallen heraus.
    MAX_AUFZEICHNUNGEN = 50
    #: Eine offene Aufzeichnung endet spaetestens nach dieser Zeit von selbst.
    MAX_LAUFZEIT_S = 3600

    #: Datei-Zugriff serialisieren: Die Schritte kommen aus mehreren Tabs und
    #: als eigene Anfragen - ohne Sperre wuerde ein Puffer den anderen
    #: ueberschreiben (lesen, aendern, schreiben ohne Schutz).
    _sperre = threading.Lock()

    def __init__(self, pfad=None):
        self.pfad = Path(pfad) if pfad else self._vorgabe()

    @staticmethod
    def _vorgabe():
        u"""``<logs>/aufzeichnungen.json`` - im SELBEN Ordner wie die Logs.

        NICHT blind ``BASE_DIR/logs`` (Befund 20.08.2026): In shortlongx ist
        ``BASE_DIR`` das Django-Verzeichnis, der logs-Ordner liegt aber eine
        Ebene darueber in der Repo-Wurzel (``dblog.config(REPO_DIR / "logs")``).
        Die erste Fassung legte deshalb ein ZWEITES ``shortlongxWeb/logs/`` an
        und schrieb dorthin - neben dem Ordner, in dem alles andere liegt.

        Gesucht wird der Ordner, den es WIRKLICH gibt; nur wenn keiner
        existiert, wird ``BASE_DIR/logs`` angelegt."""
        basis = Path(getattr(settings, "BASE_DIR", "."))
        for kandidat in (basis / "logs", basis.parent / "logs"):
            if kandidat.is_dir():
                return kandidat / Aufzeichnungen.DATEINAME
        return basis / "logs" / Aufzeichnungen.DATEINAME

    # ------------------------------------------------------------- Persistenz
    def _lesen(self):
        try:
            with open(self.pfad, encoding="utf-8") as f:
                roh = json.load(f)
        except (OSError, ValueError):
            return []
        return [Aufzeichnung.from_dict(d) for d in roh if isinstance(d, dict)]

    def _schreiben(self, liste):
        liste = liste[-self.MAX_AUFZEICHNUNGEN:]
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pfad, "w", encoding="utf-8") as f:
                json.dump([a.as_dict() for a in liste], f, ensure_ascii=False, indent=1)
        except OSError:
            log.exception("Aufzeichnungen konnten nicht gespeichert werden (%s)",
                          self.pfad)

    # ---------------------------------------------------------------- Lesen
    def alle(self):
        u"""Alle Aufzeichnungen, neueste zuerst."""
        return sorted(self._lesen(), key=lambda a: a.start, reverse=True)

    def holen(self, kennung):
        for a in self._lesen():
            if a.id == kennung:
                return a
        return None

    def laufende(self):
        u"""Die eine offene Aufzeichnung - oder None.

        Laeuft eine laenger als ``MAX_LAUFZEIT_S``, wird sie hier beendet statt
        ewig weiterzuzaehlen: Eine Aufnahme, die der Nutzer vergessen hat, soll
        die naechste nicht blockieren."""
        with self._sperre:
            liste = self._lesen()
            for a in liste:
                if a.laeuft:
                    if a.dauer_s > self.MAX_LAUFZEIT_S:
                        a.ende = datetime.now().astimezone().isoformat(timespec="seconds")
                        log.info("Aufzeichnung %s nach %.0f s automatisch beendet",
                                 a.id, a.dauer_s)
                        self._schreiben(liste)
                        return None
                    return a
        return None
