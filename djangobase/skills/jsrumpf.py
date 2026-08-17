# -*- coding: utf-8 -*-
u"""Rumpf - der Inhalt eines JavaScript-Blocks und die Frage, ob darin etwas passiert.

Hilfsklasse, kein Werkzeug. ``jsstumm`` braucht sie viermal: fuer den Rumpf eines
``catch``, eines ``.catch(() => { … })``, eines Waechter-Blocks und einer
Funktion. Die Klammertiefe kommt aus :class:`~.jsklammern.Klammerzaehler` - der
Abstand zur naechsten schliessenden Klammer waere geraten (Template-Strings,
verschachtelte Bloecke).

WARUM „NICHTS PASSIERT\" ENG GEFASST IST
=======================================
Ein ``catch (e) { return null; }`` ist ein RUECKFALL: Der Aufrufer bekommt einen
Wert, mit dem er weiterarbeiten kann, und muss ihn pruefen. Ein
``catch (e) { }`` ist etwas anderes - dort passiert gar nichts, der Ablauf laeuft
weiter, als waere nie ein Fehler aufgetreten.

Nur der zweite Fall gilt als stumm. Die Grenze ist mit Absicht so gezogen: Sie
ist am Code ablesbar, statt zu raten, ob ein Rueckfallwert „gut genug\" ist.
Gemessen im Projekt assistant war das der Unterschied zwischen 15 belegten und
gut 90 vermuteten Fundstellen (17.08.2026).
"""
import re

from .jsklammern import Klammerzaehler

__all__ = ["Rumpf"]


class Rumpf:
    """Der Text zwischen ``{`` und dem passenden ``}``."""

    #: So viele Zeilen weit wird ein Block hoechstens verfolgt. Schliesst er
    #: darin nicht, ist die Annahme falsch und die Stelle wird nicht angefasst -
    #: lieber ein fehlender Befund als ein erfundener.
    GRENZE = 400

    KOMMENTAR_BLOCK = re.compile(r"/\*.*?\*/", re.S)
    KOMMENTAR_ZEILE = re.compile(r"//[^\n]*")
    #: Eine Zeile, in der nichts geschieht: leer, oder ein Abbruch OHNE Wert.
    #: ``return null`` faellt bewusst NICHT darunter (siehe Modulkopf).
    OHNE_WIRKUNG = re.compile(r"^(?:return|break|continue)?\s*;?$")

    def __init__(self, text, endzeile):
        self.text = text
        self.endzeile = endzeile

    def __bool__(self):
        return self.text is not None

    @classmethod
    def ab(cls, zeilen, nummer, spalte):
        u"""Rumpf des Blocks, dessen ``{`` in ``zeilen[nummer]`` vor ``spalte`` steht.

        ``spalte`` zeigt HINTER die geschweifte Klammer (``treffer.end()`` eines
        Musters, das mit ``{`` endet). Ohne Fund: ein Rumpf, der ``False`` ist.
        """
        rest = zeilen[nummer][spalte:]
        zaehler = Klammerzaehler(1)
        if zaehler.zeile(rest) <= 0:
            # Einzeiler: `catch (e) { }` — alles vor der schliessenden Klammer.
            return cls(rest[:rest.rindex("}")] if "}" in rest else rest, nummer)
        stuecke = [rest]
        bis = min(len(zeilen), nummer + 1 + cls.GRENZE)
        for i in range(nummer + 1, bis):
            zaehler.zeile(zeilen[i])
            # `tiefstand`, nicht die Tiefe am Zeilenende: `} else {` schliesst
            # den Block im ersten Zeichen und oeffnet gleich wieder einen.
            if zaehler.tiefstand <= 0:
                stuecke.append(zeilen[i].split("}")[0])
                return cls("\n".join(stuecke), i)
            stuecke.append(zeilen[i])
        return cls(None, None)

    def ohne_kommentare(self):
        """Der Rumpf ohne Kommentare - was BLEIBT, ist der Code."""
        text = self.KOMMENTAR_BLOCK.sub("", self.text or "")
        return self.KOMMENTAR_ZEILE.sub("", text)

    def nichts_passiert(self):
        u"""Keine Anweisung mit Wirkung - der Fehler ist damit weg.

        ``self.text is None`` heisst „kein Block gefunden"; ein LEERER Text ist
        dagegen der Kern des Befunds. Die erste Fassung schrieb ``if not
        self.text`` und uebersah damit genau den eindeutigsten Fall,
        ``.catch(() => {})`` — drei von vier Bauarten im eigenen Anlassfall
        gefunden, die vierte nicht (17.08.2026).
        """
        if self.text is None:
            return False
        return all(self.OHNE_WIRKUNG.match(z.strip())
                   for z in self.ohne_kommentare().split("\n"))

    def enthaelt(self, muster):
        """Passt ``muster`` (kompiliertes Regex) auf den Code des Rumpfs?"""
        return bool(muster.search(self.ohne_kommentare()))

    def kommentare(self):
        """Nur die Kommentare - dort steht ein Vermerk, falls es einen gibt."""
        text = self.text or ""
        return " ".join(self.KOMMENTAR_BLOCK.findall(text)
                        + self.KOMMENTAR_ZEILE.findall(text))

    @staticmethod
    def kommentarblock_ueber(zeilen, nummer):
        u"""Der zusammenhaengende Kommentarblock direkt UEBER ``zeilen[nummer]``.

        Nur der unmittelbar angrenzende: So kann ein Vermerk nicht auf einen
        fremden Block abfaerben. Dieselbe Bauform wie in ``protokoll._ausnahme``,
        wo die erste Fassung erst ab der ``except``-Zeile las und den Vermerk
        deshalb nie fand.
        """
        aus = []
        i = nummer - 1
        while i >= 0 and zeilen[i].strip().startswith(("//", "*", "/*")):
            aus.insert(0, zeilen[i])
            i -= 1
        return "\n".join(aus)
