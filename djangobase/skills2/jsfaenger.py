# -*- coding: utf-8 -*-
u"""JsFaenger - werfende Server-Abrufe, die in keinem try-Block stehen.

DER BEFUND (3DTools, 16.08.2026)
================================
Beim Umstellen von ``fetch`` auf eine Abrufklasse mit Statuspruefung wird die
Fehlerbehandlung schaerfer: Vorher lief eine 400er-Antwort als JSON durch
(``{"ok": false, "error": "..."}``) und der Code zeigte selbst eine Meldung -
danach WIRFT der Abruf bei jedem Status ausser 2xx.

Das ist die bessere Fehlerbehandlung, aber nur dort, wo jemand faengt. Steht der
Aufruf in keinem try-Block, wird aus einer sichtbaren Meldung eine stille
„Unhandled promise rejection" in einer Konsole, die niemand offen hat - genau
die Fehlerklasse, die der Umbau beseitigen sollte.

Im Ursprungsprojekt liefern 200 Stellen im Python-Teil einen echten Fehlerstatus
(``status=400/404/500``) mitsamt JSON-Body. Diese Pruefung listet die
JavaScript-Seiten, an denen so eine Antwort ungefangen bliebe: von 101 Aufrufen
standen 16 ohne Faenger da, zwei davon hinter einem Nutzerklick ohne jede
Rueckmeldung.

WIE GEPRUEFT WIRD
=================
Ab dem Aufruf rueckwaerts nach ``try {``, dann dessen Block ueber die
Klammertiefe verfolgen (`jsklammern`): Dort muss ``catch`` oder ``finally``
stehen. Ein ``catch`` irgendwo unterhalb beweist nichts - es kann zu einem
spaeteren try gehoeren.

GRENZE: Ein Aufruf in einer Funktion, die der AUFRUFER in einem try-Block hat,
gilt trotzdem als offen. Die Aufrufkette verfolgt die Pruefung nicht. Die Liste
ist zum Durchsehen gedacht, keine Fehlerliste.

ANPASSEN: ``DJANGOBASE["skills2_abrufklassen"] = ["Serverabruf", "Api"]`` nennt
die Klassen, deren Methoden werfen.
"""
import re

from django.conf import settings

from .jsklammern import Klammerzaehler
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["JsFaenger"]


class Stelle:
    """Ein Aufruf und die Frage, ob ihn jemand faengt."""

    #: So weit wird nach oben nach einem try gesucht.
    #:
    #: 60 war zu wenig: In `viewer/mesh.js` beginnt der try-Block 110 Zeilen
    #: ueber dem Abruf, und die Stelle erschien als offen, obwohl der catch
    #: direkt darunter steht. Zu gross kann der Wert nicht werden — das
    #: Blockende wird ueber die Klammertiefe geprueft, nicht ueber den Abstand.
    REICHWEITE = 250
    #: So weit wird der try-Block hoechstens verfolgt.
    BLOCKGRENZE = 400

    def __init__(self, datei, zeilen, nummer):
        self.datei = datei
        self.zeilen = zeilen
        self.nummer = nummer          # 0-basiert

    def gefangen(self):
        for anfang in self._try_bloecke():
            ende = self._blockende(anfang)
            if ende is None or ende <= self.nummer:
                continue
            if "catch" in self.zeilen[ende] or "finally" in self.zeilen[ende]:
                return True
        return False

    def _try_bloecke(self):
        """Zeilennummern der try-Bloecke oberhalb, von innen nach aussen."""
        von = max(0, self.nummer - Stelle.REICHWEITE)
        for i in range(self.nummer - 1, von - 1, -1):
            if self.zeilen[i].strip().startswith("try {"):
                yield i

    def _blockende(self, anfang):
        """Zeile, in der der in `anfang` geoeffnete Block wieder zugeht."""
        zaehler = Klammerzaehler()
        zaehler.zeile(self.zeilen[anfang].split("try", 1)[1])
        bis = min(len(self.zeilen), anfang + Stelle.BLOCKGRENZE)
        for i in range(anfang + 1, bis):
            zaehler.zeile(self.zeilen[i])
            # `tiefstand`, nicht die Tiefe am Zeilenende: `} catch (e) {`
            # schliesst den Block im ERSTEN Zeichen.
            if zaehler.tiefstand <= 0:
                return i
        return None

    def als_zeile(self):
        return {"ort": "%s:%d" % (self.datei, self.nummer + 1),
                "text": self.zeilen[self.nummer].strip()[:110]}


class JsFaenger(Werkzeug2):
    slug = "jsfaenger"
    titel = "Server-Abrufe ohne try-Block"
    zweck = ("Findet Aufrufe einer werfenden Abrufklasse (Vorgabe: "
             "`Serverabruf.json/text/senden`), die in keinem try-Block stehen.")
    befund = ("3DTools: 16 von 101 Aufrufen ohne Faenger. Zwei davon hingen "
              "direkt an einer Nutzeraktion (Koerperart wechseln, Pose "
              "anwenden) - ein Serverfehler blieb dort voellig stumm.")
    abhilfe = ("try/catch mit sichtbarer Meldung ergaenzen, oder pruefen, ob "
               "der Aufrufer faengt (dann ist der Treffer ein Fehlalarm).")
    dauer = "unter 1 s"
    kriterium = 13

    NICHT_IM_PFAD = ("vendor", "theatre", "theatre-studio", "dist", "bundle",
                     "node_modules")
    VORGABE_KLASSEN = ("Serverabruf",)
    #: Methoden, die werfen. `jsonOderNull` faengt selbst und zaehlt nicht.
    METHODEN = ("json", "text", "senden", "formular")

    def klassen(self):
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get(
            "skills2_abrufklassen")
        return tuple(eigen) if eigen else JsFaenger.VORGABE_KLASSEN

    def laufen(self):
        klassen = self.klassen()
        muster = re.compile(r"\b(?:%s)\.(?:%s)\s*\("
                            % ("|".join(re.escape(k) for k in klassen),
                               "|".join(JsFaenger.METHODEN)))
        # Die Abrufklasse selbst SOLL werfen.
        eigene = tuple("%s.js" % k.lower() for k in klassen)
        offen, gefangen = [], 0
        for pfad, kurz in self._quellen():
            if kurz.rsplit("/", 1)[-1] in eigene:
                continue
            zeilen = pfad.read_text(encoding="utf-8",
                                    errors="replace").split("\n")
            for nummer, zeile in enumerate(zeilen):
                if not muster.search(zeile):
                    continue
                if zeile.lstrip().startswith(("*", "//")):
                    continue
                stelle = Stelle(kurz, zeilen, nummer)
                if stelle.gefangen():
                    gefangen += 1
                else:
                    offen.append(stelle.als_zeile())
        return Ergebnis(
            ["ort", "text"], offen,
            zusammenfassung="%d Aufrufe, %d in einem try-Block, %d offen"
                            % (gefangen + len(offen), gefangen, len(offen)),
            hinweis="Zum Durchsehen: Ein Aufruf, dessen AUFRUFER faengt, steht "
                    "hier ebenfalls - die Kette wird nicht verfolgt.")

    def _quellen(self):
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for pfad in sorted(wurzel.rglob("*.js")):
            if any(teil in raus for teil in pfad.parts):
                continue
            if any(teil in JsFaenger.NICHT_IM_PFAD for teil in pfad.parts):
                continue
            if ".min." in pfad.name:
                continue
            yield pfad, pfad.relative_to(wurzel).as_posix()
