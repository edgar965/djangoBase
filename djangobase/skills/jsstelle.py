# -*- coding: utf-8 -*-
u"""Stelle - eine Zeile in einer JS-Datei und die Frage, ob sie im try steht.

Aus ``jsfaenger.py`` herausgeloest (17.08.2026): Die Datei war beim Nachziehen
der Aufrufkette auf 402 Zeilen gewachsen und trug drei Aufgaben. Hier steht nur
noch die eine Frage, die auch ``Aufrufkette`` braucht:

    Deckt ein try-Block mit ``catch`` oder ``finally`` diese Zeile?

Gesucht wird ab dem Aufruf rueckwaerts nach ``try {``; das Blockende kommt aus
der Klammertiefe (`jsklammern`), nicht aus dem Abstand. Ein ``catch`` irgendwo
unterhalb beweist nichts - es kann zu einem spaeteren try gehoeren.
"""
import re

from .jsklammern import Klammerzaehler

__all__ = ["Stelle", "SCHLUESSELWORTE"]

#: Sieht wie eine Funktionsdefinition aus, ist aber Ablaufsteuerung. Ohne diese
#: Liste gilt jedes `if (…) {` als umgebende Funktion.
SCHLUESSELWORTE = {"if", "for", "while", "switch", "catch", "else", "do",
                   "try", "return", "typeof", "function", "class"}


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
    #: So weit wird nach oben nach der umgebenden Funktion gesucht.
    FUNKTIONSSUCHE = 120

    #: Eine Funktions- oder Methodendefinition am Zeilenanfang.
    DEFINITION = re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:static\s+)?(?:async\s+)?"
        r"(?:function\s*\*?\s*)?([A-Za-z_$][\w$]*)\s*\([^;]*\)\s*\{\s*$")

    def __init__(self, datei, zeilen, nummer):
        self.datei = datei
        self.zeilen = zeilen
        self.nummer = nummer          # 0-basiert

    def gefangen(self):
        for anfang in self._try_bloecke():
            ende = self._blockende(anfang)
            # `< self.nummer`: Ein Block, der VOR dem Aufruf zugeht, deckt ihn
            # nicht. Gleichheit muss erlaubt sein — sonst faellt der Einzeiler
            # `try { … } catch (e) { … }` durch, und genau der steht in 3DTools
            # als Aufrufer von `fetchMorphDefs()` (17.08.2026).
            if ende is None or ende < self.nummer:
                continue
            if self._faengt_ab(ende):
                return True
        return False

    def _faengt_ab(self, ende):
        """Steht ``catch``/``finally`` in der Schlusszeile — oder darunter?

        Beide Schreibweisen kommen vor:

            } catch (e) { … }        <- in der Schlusszeile
            }
            catch (e) { … }          <- eine Zeile tiefer

        Die zweite fiel durch, solange nur ``zeilen[ende]`` geprueft wurde. Nur
        LEERZEILEN werden uebersprungen; alles andere dazwischen hiesse, dass
        der Block ohne Faenger endet.
        """
        for i in range(ende, min(len(self.zeilen), ende + 3)):
            text = self.zeilen[i]
            if i > ende and not text.strip():
                continue
            if "catch" in text or "finally" in text:
                return True
            if i > ende:
                break
        return False

    def _try_bloecke(self):
        """Zeilennummern der try-Bloecke oberhalb, von innen nach aussen.

        Die EIGENE Zeile zaehlt mit: Beim Einzeiler steht `try` davor und
        `catch` dahinter, alles in derselben Zeile.
        """
        von = max(0, self.nummer - Stelle.REICHWEITE)
        for i in range(self.nummer, von - 1, -1):
            if self.zeilen[i].strip().startswith("try {"):
                yield i

    def _blockende(self, anfang):
        """Zeile, in der der in `anfang` geoeffnete Block wieder zugeht."""
        zaehler = Klammerzaehler()
        # `tiefe` NACH der Zeile, nicht `tiefstand`: Der Tiefstand ist beim
        # Zeilenstart 0 und bleibt es, solange nur geoeffnet wird — damit galt
        # kurz JEDER try-Block als Einzeiler und die Zahl der gefangenen Aufrufe
        # fiel von 128 auf 0 (17.08.2026, beim Bauen dieser Zeile).
        if zaehler.zeile(self.zeilen[anfang].split("try", 1)[1]) <= 0:
            return anfang                      # Einzeiler, in sich geschlossen
        bis = min(len(self.zeilen), anfang + Stelle.BLOCKGRENZE)
        for i in range(anfang + 1, bis):
            zaehler.zeile(self.zeilen[i])
            # `tiefstand`, nicht die Tiefe am Zeilenende: `} catch (e) {`
            # schliesst den Block im ERSTEN Zeichen.
            if zaehler.tiefstand <= 0:
                return i
        return None

    def umgebende_funktion(self):
        """Name der Funktion, in der der Aufruf steht - oder ``""``.

        Rueckwaerts bis zur ersten Definitionszeile. Schluesselwoerter wie ``if``
        oder ``for`` sehen mit Klammer und Klammeraffe genauso aus und sind
        ausgenommen; sonst gilt jede Schleife als Funktion.
        """
        von = max(-1, self.nummer - Stelle.FUNKTIONSSUCHE)
        for i in range(self.nummer - 1, von, -1):
            treffer = Stelle.DEFINITION.match(self.zeilen[i])
            if treffer and treffer.group(1) not in SCHLUESSELWORTE:
                return treffer.group(1)
        return ""

    def als_zeile(self, aufrufer=""):
        return {"ort": "%s:%d" % (self.datei, self.nummer + 1),
                "text": self.zeilen[self.nummer].strip()[:110],
                "aufrufer": aufrufer}

    @staticmethod
    def in_zeichenkette(zeile, stelle):
        u"""Steht die Fundstelle innerhalb von Anfuehrungszeichen?

        `retarget_hybrid.js:54` lautet
        ``throw new Error('loadRetargetConfig() must be called …')`` — der
        Funktionsname steht dort in einer MELDUNG, nicht als Aufruf. Ohne diese
        Pruefung meldete sich das Werkzeug selbst als ungefangenen Aufrufer
        (17.08.2026).
        """
        offen = None
        i = 0
        while i < stelle:
            zeichen = zeile[i]
            if zeichen == "\\":
                i += 2
                continue
            if zeichen in "\"'`":
                if offen is None:
                    offen = zeichen
                elif offen == zeichen:
                    offen = None
            i += 1
        return offen is not None
