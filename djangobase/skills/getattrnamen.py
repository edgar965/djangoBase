# -*- coding: utf-8 -*-
u"""GetattrNamen - ``getattr(x, "name", vorgabe)`` auf einen Namen, den es nicht gibt.

DER ANLASS (shortlongx, 16.08.2026)
===================================
``depot/IB/orb_position.nacht`` fragte ``getattr(self.ts, "orb_nacht", False)``.
Das Feld heisst seit jeher ``position_ueber_nacht``; ``orb_nacht`` hat es NIE
gegeben. Die Vorgabe schluckte den Tippfehler - der Live-Autotrader stellte
deshalb jede Position am Fensterende glatt, waehrend der Backtest daneben den
Uebernacht-Carry rechnete. Zwei Wege, die genau bei dem Merkmal auseinander-
liefen, an dem ueber Nacht Geld haengt.

Nichts wird dabei rot. Ein ``getattr`` MIT Vorgabe meldet einen falschen Namen
nicht, es liefert die Vorgabe - dieselbe stille Bauart wie ein Import, den
niemand zieht, oder eine Umleitung, die ins Leere greift.

DER MASSSTAB KOMMT AUS DEM CODE, NICHT AUS EINER FELDLISTE
==========================================================
Die urspruengliche Fassung in shortlongx hielt die erlaubten Feldnamen als
Konstante - projektgebunden und schon beim naechsten neuen Feld veraltet. Hier
gilt ein Name als bekannt, wenn er im Projekt irgendwo als Attribut (``x.name``,
``self.name = …``) oder als Bezeichner (Zuweisung, Parameter, Funktion, Klasse,
Schluesselwort-Argument) vorkommt.

DIE DRITTE BEDINGUNG WAR EIN FEHLGRIFF - GEMESSEN, NICHT VERMUTET
=================================================================
Die erste Fassung liess zusaetzlich JEDE Zeichenkette im Projekt als Beleg
gelten (Gedanke: dynamisch gefuehrte Felder stehen nur in Listen wie
``FELDER = ["stop", "ziel", …]``). An shortlongx gemessen, 1.024 Dateien,
290 ``getattr``-Aufrufe mit Vorgabe:

    nur ``x.name``                    9 unbekannte Namen
    + Bezeichner                      2          <- ausgeliefert
    + Zeichenketten                   0

Null sah nach einem sauberen Projekt aus und war Blindheit: ``orb_nacht`` steht
als Zeichenkette in der Pruefung, die den Fall dokumentiert - die Fassung haette
ihren eigenen Anlassfall nicht gefunden. Die Gegenprobe („faende sie den Fall vom
16.08.2026?") laeuft in ``werkzeug/_getattr_namen_messung.py`` mit.

Zeichenketten werden trotzdem gesammelt, aber nur als ENTLASTUNG in der Spalte
„bekannt": Ein Name, der irgendwo als Zeichenkette steht, ist eher ein dynamisch
gefuehrtes Feld als ein Tippfehler - das entscheidet der Mensch, nicht der Filter.

WAS ES NICHT WISSEN KANN
========================
Attribute von Fremdbibliotheken. ``getattr(ticker, "marketDataType", None)``
steht zurecht da - der Name gehoert ``ib_async`` und kommt im Projekt nirgends
vor. Deshalb meldet dieses Werkzeug einen VERDACHT, keinen Fehler.

Gezaehlt werden nur Aufrufe MIT Vorgabe: ``getattr(x, "n")`` ohne dritten
Parameter wirft von selbst und braucht keine Pruefung.
"""
import ast
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2


class Namensbestand:
    """Alle Namen, die das Projekt kennt - der Massstab.

    ``kennt()`` fragt Attribute und Bezeichner. Zeichenketten stehen daneben und
    fliessen NICHT in die Entscheidung ein (siehe Modulkopf: sie haben die
    Trefferzahl auf null gedrueckt, einschliesslich des Anlassfalls)."""

    def __init__(self):
        #: Attributzugriffe: ``x.name`` (lesend wie schreibend)
        self.attribute = set()
        #: Zuweisungen, Parameter, Funktions- und Klassennamen
        self.bezeichner = set()
        #: Jede Zeichenkette im Code - nur zur Entlastung, nicht als Filter
        self.zeichenketten = set()

    def aufnehmen(self, baum):
        for k in ast.walk(baum):
            if isinstance(k, ast.Attribute):
                self.attribute.add(k.attr)
            elif isinstance(k, ast.Name):
                self.bezeichner.add(k.id)
            elif isinstance(k, ast.arg):
                self.bezeichner.add(k.arg)
            elif isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.ClassDef)):
                self.bezeichner.add(k.name)
            elif isinstance(k, ast.keyword) and k.arg:
                self.bezeichner.add(k.arg)
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                self.zeichenketten.add(k.value)

    def kennt(self, name):
        return name in self.attribute or name in self.bezeichner

    def einstufung(self, name):
        """Wie stark der Verdacht ist - in Worten, die in der Tabelle stehen."""
        if name in self.zeichenketten:
            return "nur als Zeichenkette (evtl. dynamisches Feld)"
        return "nirgends im Projekt"


class GetattrStelle:
    """Ein einzelner ``getattr(empfaenger, "feld", vorgabe)``-Aufruf."""

    def __init__(self, datei, knoten):
        self.datei = datei
        self.zeile = knoten.lineno
        self.feld = knoten.args[1].value
        self.empfaenger = self._ausdruck(knoten.args[0])
        self.vorgabe = self._kurz(knoten.args[2])

    @staticmethod
    def _ausdruck(k):
        """``self.ts`` statt ``<ast.Attribute>`` - lesbar in der Tabelle."""
        if isinstance(k, ast.Name):
            return k.id
        if isinstance(k, ast.Attribute):
            return "%s.%s" % (GetattrStelle._ausdruck(k.value), k.attr)
        if isinstance(k, ast.Call):
            return "%s(…)" % GetattrStelle._ausdruck(k.func)
        if isinstance(k, ast.Subscript):
            return "%s[…]" % GetattrStelle._ausdruck(k.value)
        return "…"

    @staticmethod
    def _kurz(k):
        if isinstance(k, ast.Constant):
            return repr(k.value)
        return type(k).__name__

    def als_zeile(self, bestand):
        return {"datei": self.datei, "zeile": self.zeile,
                "empfänger": self.empfaenger, "gefragtes Feld": self.feld,
                "Vorgabe": self.vorgabe, "belegt": bestand.einstufung(self.feld)}


class GetattrNamen(Werkzeug2):
    slug = "getattr-namen"
    titel = "getattr auf Felder, die es nicht gibt"
    zweck = ("Findet ``getattr(x, \"name\", vorgabe)``, wo der Name im Projekt "
             "weder als Attribut noch als Bezeichner vorkommt.")
    befund = ("In shortlongx fragte der Live-Autotrader ``getattr(self.ts, "
              "\"orb_nacht\", False)``; das Feld heißt ``position_ueber_nacht`` "
              "und hat nie anders geheißen. Der Autotrader schloss deshalb jede "
              "Position am Fensterende, während der Backtest daneben über Nacht "
              "hielt — ohne eine einzige Fehlermeldung.")
    abhilfe = ("Namen richtigstellen. Ist das Feld absichtlich optional (ältere "
               "gespeicherte Objekte kennen es nicht), gehört es trotzdem "
               "einmal in die Feldliste der Klasse — dann ist es belegt. Gehört "
               "der Name einer Fremdbibliothek, ist die Zeile in Ordnung.")
    kriterium = 7
    dauer = "5–10 s"

    SPALTEN = ("datei", "zeile", "empfänger", "gefragtes Feld", "Vorgabe",
               "belegt")

    #: Der Fall vom 16.08.2026, auf das Noetige eingedampft. ``position_ueber_
    #: nacht`` ist das echte Feld, ``orb_nacht`` der Tippfehler. Die erste
    #: Fassung dieses Werkzeugs haette ihn NICHT gefunden - sie liess jede
    #: Zeichenkette als Beleg gelten, und der Name steht als Zeichenkette in der
    #: Pruefung, die ihn dokumentiert. Genau dafuer gibt es diesen Anlassfall.
    anlassfall = Anlassfall(
        {"handel.py": '''# -*- coding: utf-8 -*-


class System:
    def __init__(self):
        self.position_ueber_nacht = False


def haelt_ueber_nacht(ts):
    return getattr(ts, "orb_nacht", False)


def haelt_wirklich(ts):
    return getattr(ts, "position_ueber_nacht", False)
'''},
        erwartet_in="orb_nacht",
        warum="Autotrader fragte ``orb_nacht``; das Feld heißt "
              "``position_ueber_nacht`` (16.08.2026)")

    def laufen(self):
        dateien = [d for d in self.dateien(".py") if d.baum is not None]
        bestand = Namensbestand()
        for d in dateien:
            bestand.aufnehmen(d.baum)

        stellen, gesamt = [], 0
        for d in dateien:
            for k in ast.walk(d.baum):
                if not self._ist_getattr_mit_vorgabe(k):
                    continue
                gesamt += 1
                stelle = GetattrStelle(d.name, k)
                if not bestand.kennt(stelle.feld):
                    stellen.append(stelle)

        stellen.sort(key=lambda s: (s.datei, s.zeile))
        return Ergebnis(
            list(self.SPALTEN),
            [s.als_zeile(bestand) for s in stellen],
            self._fazit(stellen, gesamt, len(dateien)),
            "Jede Zeile von Hand prüfen: Der Name kann von außen kommen "
            "(Fremdbibliothek, Django-Interna). Das Werkzeug meldet einen "
            "begründeten Verdacht — keinen Fehler.")

    @staticmethod
    def _fazit(stellen, gesamt, dateien):
        if not stellen:
            # Null ist hier ein Zwischenstand, keine Auszeichnung: Genau diese
            # Null hatte die erste Fassung ausgewiesen, weil ihr Massstab zu
            # weit war (Modulkopf). Der Satz sagt deshalb, WORAN gemessen wurde.
            return ("Kein unbekannter Name unter %d ``getattr``-Aufrufen mit "
                    "Vorgabe (%d Dateien). Gemessen gegen alle Attribute und "
                    "Bezeichner des Projekts — Namen aus Fremdbibliotheken "
                    "sieht diese Prüfung nicht." % (gesamt, dateien))
        haeufig = Counter(s.empfaenger for s in stellen).most_common(1)[0]
        return ("%d von %d ``getattr``-Aufrufen mit Vorgabe nennen ein Feld, "
                "das das Projekt sonst nicht kennt (häufigster Empfänger: %s, "
                "%dx)." % (len(stellen), gesamt, haeufig[0], haeufig[1]))

    @staticmethod
    def _ist_getattr_mit_vorgabe(k):
        return (isinstance(k, ast.Call)
                and isinstance(k.func, ast.Name) and k.func.id == "getattr"
                and len(k.args) == 3
                and isinstance(k.args[1], ast.Constant)
                and isinstance(k.args[1].value, str))
