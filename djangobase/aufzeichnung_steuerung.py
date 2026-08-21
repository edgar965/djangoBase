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
                    n = self._einfuegen(a.schritte, sauber[:frei])
                    self.bestand._schreiben(liste)
                    return n
        return 0

    #: Ereignisse, die einen neuen Abschnitt beginnen - alles danach gehoert zu
    #: IHNEN. Ein Abruf wird nur innerhalb desselben Abschnitts zusammengefasst.
    MARKEN = ("klick", "eingabe", "auswahl", "seite")

    @staticmethod
    def _signatur(schritt):
        u"""Was eine Marke eindeutig macht: Zeitpunkt und Ziel."""
        return (schritt.get("t"), schritt.get("art"),
                schritt.get("ziel") or schritt.get("seite") or "")

    @classmethod
    def _einfuegen(cls, vorhandene, neue):
        u"""Neue Ereignisse anhaengen - wiederkehrende Abrufe dabei ZAEHLEN.

        WARUM (gemessen 21.08.2026, ShortLongX): Die Paper-Seite fragt im
        Sekundentakt drei Endpunkte ab. Sechs Sekunden Klicken ergaben **115
        Schritte**, davon rund hundert Poll-Wiederholungen - ein daraus gebauter
        Testfall pruefte hundertmal dasselbe und verlor die zwei Klicks, um die
        es ging.

        Die Verdichtung gehoert HIERHER und nicht in den Browser: Dort wechseln
        sich die Endpunkte ab (A, B, C, A, B, C), ein Vergleich mit dem
        unmittelbaren Vorgaenger griffe nie, und der Puffer geht ohnehin alle
        drei Sekunden raus. Serverseitig liegt die ganze Liste vor.

        ABSCHNITTSWEISE (das ist der Punkt): Gezaehlt wird nur bis zum letzten
        Klick/Seitenwechsel. Damit bleibt die Aussage erhalten, die ein Testfall
        braucht - „nach DIESEM Klick kamen DIESE Abrufe" -, statt alle Abrufe
        einer halben Stunde in einer Zeile zu verschmelzen.

        Ein Abruf mit anderem Status faellt NICHT zusammen: Ein Poll, der
        ploetzlich 500 liefert, ist die interessanteste Zeile der Aufnahme."""
        # WIEDERHOLTE MARKEN ABWEISEN (21.08.2026): Der Browser entnimmt seinen
        # Puffer beim Senden, ein Doppelversand sollte also nicht vorkommen -
        # aber garantieren muss es die Stelle, die SCHREIBT. Ein
        # ``keepalive``-Request darf vom Browser wiederholt werden, und ein
        # zweiter Tab derselben Sitzung schickt denselben Weg noch einmal.
        # Passiert das, stuende jeder Klick zweimal in der Aufnahme, und der
        # erzeugte Testfall fuehre ihn zweimal nach.
        #
        # Erkennbar sind Wiederholungen an der SIGNATUR einer Marke: Sekunde
        # seit Beginn plus Ziel. Zwei ECHTE Klicks auf dasselbe Ziel in
        # derselben Zehntelsekunde faenden hier zusammen - ein Doppelklick, der
        # als einer gilt. Das ist der guenstigere Fehler: eine verdoppelte
        # Aufnahme ist unbrauchbar, ein verschluckter Doppelklick eine Nuance.
        vorhanden = {cls._signatur(a) for a in vorhandene
                     if a.get("art") in cls.MARKEN}
        neu_gezaehlt = 0
        for s in neue:
            if s.get("art") in cls.MARKEN:
                sig = cls._signatur(s)
                if sig in vorhanden:
                    continue
                vorhanden.add(sig)
            treffer = None
            if s.get("art") == "abruf":
                for alt in reversed(vorhandene):
                    if alt.get("art") in cls.MARKEN:
                        break                       # Abschnittsgrenze erreicht
                    if (alt.get("art") == "abruf"
                            and alt.get("methode") == s.get("methode")
                            and alt.get("pfad") == s.get("pfad")
                            and alt.get("status") == s.get("status")):
                        treffer = alt
                        break
            if treffer is not None:
                treffer["n"] = int(treffer.get("n") or 1) + int(s.get("n") or 1)
                treffer["t_bis"] = s.get("t_bis", s.get("t"))
                continue
            vorhandene.append(s)
            neu_gezaehlt += 1
        return neu_gezaehlt

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
        # ``n``/``t_bis`` tragen die Verdichtung des Browsers. Ohne sie hier
        # durchzulassen, kaeme jede zusammengefasste Wiederholung als EIN
        # Ereignis an - die Zahl waere still falsch.
        for feld, grenze in (("n", 100000), ("t_bis", None)):
            if s.get(feld) is None:
                continue
            try:
                wert = int(s[feld]) if grenze else round(float(s[feld]), 2)
            except (TypeError, ValueError):
                continue
            aus[feld] = min(wert, grenze) if grenze else wert
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
