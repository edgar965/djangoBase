# -*- coding: utf-8 -*-
u"""Starten, Ereignisse anhaengen, Beenden, Umbenennen, Loeschen.

Getrennt von ``aufzeichnung.py``: Dort steht, WAS eine Aufzeichnung ist und wie
sie auf der Platte liegt; hier, was mit ihr geschieht. Beides in einer Datei
waere ueber der Groessengrenze und mischt Zustand mit Ablauf.

JEDE AENDERUNG LAEUFT UNTER DER SPERRE
======================================
Die Schritte kommen aus dem Browser als eigene Anfragen - bei mehreren Tabs
gleichzeitig. Lesen, aendern und schreiben ohne Schutz wuerde Puffer verlieren,
und zwar still: Die fehlenden Klicks faende niemand, weil der Testfall danach
einfach kuerzer ist.
"""
import logging
from datetime import datetime

from .aufzeichnung import Aufzeichnung, Aufzeichnungen

log = logging.getLogger("djangobase.tests")

__all__ = ["Steuerung"]


class Steuerung:
    u"""Die schreibenden Vorgaenge auf dem Aufzeichnungs-Bestand."""

    #: Ereignisarten, die angenommen werden. Alles andere wird verworfen - der
    #: Browser darf hier nicht beliebige Strukturen ablegen.
    ARTEN = ("klick", "eingabe", "auswahl", "seite", "abruf", "tastatur", "marke")

    def __init__(self, bestand=None):
        self.bestand = bestand or Aufzeichnungen()

    # ---------------------------------------------------------------- Start
    def starten(self, name="", seite=""):
        u"""Neue Aufzeichnung beginnen. Laeuft schon eine, wird SIE geliefert.

        Kein zweiter Start neben einer laufenden: Zwei gleichzeitige Aufnahmen
        haetten dieselben Ereignisse in beiden - und keine waere ein Testfall."""
        with self.bestand._sperre:
            liste = self.bestand._lesen()
            offen = [a for a in liste if a.laeuft]
            if offen:
                return offen[0], False
            jetzt = datetime.now().astimezone()
            kennung = "auf_" + jetzt.strftime("%Y%m%d_%H%M%S")
            neu = Aufzeichnung(
                kennung,
                name or ("Aufzeichnung %s" % jetzt.strftime("%d.%m.%Y %H:%M")),
                jetzt.isoformat(timespec="seconds"), seite=seite)
            liste.append(neu)
            self.bestand._schreiben(liste)
        log.info("Aufzeichnung %s gestartet (%s)", kennung, seite or "-")
        return neu, True

    # ------------------------------------------------------------ Ereignisse
    def anhaengen(self, kennung, schritte):
        u"""Ereignisse an eine LAUFENDE Aufzeichnung haengen. -> Zahl der neuen.

        Eine beendete Aufzeichnung nimmt nichts mehr an: Ein Nachzuegler-Puffer
        aus einem Tab, den der Nutzer offen gelassen hat, wuerde ihr sonst
        Schritte anhaengen, die nach dem Ende passiert sind."""
        sauber = [self._pruefen(s) for s in (schritte or [])]
        sauber = [s for s in sauber if s]
        if not sauber:
            return 0
        with self.bestand._sperre:
            liste = self.bestand._lesen()
            for a in liste:
                if a.id == kennung and a.laeuft:
                    frei = self.bestand.MAX_SCHRITTE - len(a.schritte)
                    if frei <= 0:
                        return 0
                    a.schritte.extend(sauber[:frei])
                    self.bestand._schreiben(liste)
                    return min(frei, len(sauber))
        return 0

    @classmethod
    def _pruefen(cls, s):
        u"""Ein Ereignis auf die erlaubten Felder eindampfen - oder verwerfen.

        Was aus dem Browser kommt, ist Eingabe von aussen. Hier wird sie auf
        bekannte Schluessel und Laengen begrenzt, bevor sie in einer Datei
        landet, die spaeter Testcode erzeugt."""
        if not isinstance(s, dict) or s.get("art") not in cls.ARTEN:
            return None
        def text(k, n=300):
            v = s.get(k)
            return str(v)[:n] if v is not None else ""
        try:
            t = round(float(s.get("t") or 0), 2)
        except (TypeError, ValueError):
            t = 0.0
        aus = {"t": t, "art": s["art"]}
        for feld, laenge in (("ziel", 300), ("text", 200), ("wert", 200),
                             ("seite", 300), ("methode", 10), ("pfad", 300)):
            wert = text(feld, laenge)
            if wert:
                aus[feld] = wert
        if s.get("status") is not None:
            try:
                aus["status"] = int(s["status"])
            except (TypeError, ValueError):
                pass
        return aus

    # ----------------------------------------------------------------- Ende
    def beenden(self, kennung="", logs=None):
        u"""Aufzeichnung schliessen und die Server-Logs des Zeitraums anhaengen."""
        with self.bestand._sperre:
            liste = self.bestand._lesen()
            for a in liste:
                if a.laeuft and (not kennung or a.id == kennung):
                    a.ende = datetime.now().astimezone().isoformat(timespec="seconds")
                    if logs:
                        a.logs = list(logs)
                    self.bestand._schreiben(liste)
                    log.info("Aufzeichnung %s beendet: %d Schritte, %d Log-Zeilen, %.0f s",
                             a.id, len(a.schritte), len(a.logs), a.dauer_s)
                    return a
        return None

    # ------------------------------------------------------------- Verwalten
    def umbenennen(self, kennung, name):
        name = str(name or "").strip()[:120]
        if not name:
            return None
        with self.bestand._sperre:
            liste = self.bestand._lesen()
            for a in liste:
                if a.id == kennung:
                    a.name = name
                    self.bestand._schreiben(liste)
                    return a
        return None

    def loeschen(self, kennung):
        with self.bestand._sperre:
            liste = self.bestand._lesen()
            rest = [a for a in liste if a.id != kennung]
            if len(rest) == len(liste):
                return False
            self.bestand._schreiben(rest)
        log.info("Aufzeichnung %s geloescht", kennung)
        return True
