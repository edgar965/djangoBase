# -*- coding: utf-8 -*-
u"""JsVererbung - eine Basisklasse, die ihre eigene Ableitung beim Namen nennt.

DER FALL (shortlongx, 17.08.2026)
=================================
Beim Teilen grosser JS-Klassen wandert die untere Haelfte in eine BASISKLASSE
(``class X extends XBasis``). Der Schnitt ist bewusst so herum: ``this`` bleibt
die vollstaendige Instanz, kein Aufrufer muss mitwandern. Eine Stelle vertraegt
das aber nicht - der Klassenname:

    // in tradesystem_config_basis.js
    clone() { return new TradeSystemConfig(...); }      // <- gibt es hier NICHT

``TradeSystemConfig`` steht in der ABGELEITETEN Datei. Die Basis kennt sie nicht
(sie wird importiert, sie importiert nicht), und ein Import zurueck waere ein
Zirkel. Der Aufruf ist ein ``ReferenceError`` - beim ERSTEN Aufruf, nicht beim
Laden. Unbemerkt blieb es nur, weil ``clone()`` derzeit niemand ruft; die
naechste Verwendung waere ein Fehler mitten im Betrieb.

Richtig ist ``new this.constructor(...)``: Das ist zur Laufzeit die tatsaechliche
Klasse - und funktioniert auch, wenn jemand spaeter ein drittes Mal ableitet.
Dasselbe gilt fuer statische Felder: ``this.constructor.QUELLEN`` statt
``AutomatikSysteme.QUELLEN``.

KOMMENTARE UND ZEICHENKETTEN MUESSEN RAUS - SONST STIMMT DIE ZAHL NICHT
=======================================================================
Eine blosse Textsuche nach dem Klassennamen fand in shortlongx drei Treffer, von
denen zwei keine waren: die Kopfzeile ``/* SignaleBasis - …*/`` und ein
``console.warn('SpaltenLeiste „%s": …')``. Uebrig blieb genau der eine echte
Fall. Deshalb laeuft die Suche ueber :class:`NurCode` - Kommentare und
Zeichenketten werden vorher durch Leerzeichen ersetzt, Zeilennummern bleiben
erhalten.
"""
import re

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2


class NurCode:
    """Quelltext ohne Kommentare und Zeichenketten - Zeilen bleiben stehen."""

    #: Blockkommentar, Zeilenkommentar, die drei Zeichenketten-Formen.
    MUSTER = re.compile(
        r"/\*.*?\*/|//[^\n]*|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\""
        r"|`(?:\\.|[^`\\])*`", re.S)

    def __init__(self, text):
        self.text = self.MUSTER.sub(self._leeren, text)

    @staticmethod
    def _leeren(treffer):
        """Ersetzt durch Leerzeichen - aber Zeilenumbrueche bleiben."""
        return "".join("\n" if z == "\n" else " " for z in treffer.group(0))

    def stellen(self, name):
        """[(Zeile, Text)] - wo der Name als Bezeichner steht."""
        muster = re.compile(r"(?<![.\w$])%s(?![\w$])" % re.escape(name))
        aus = []
        for nr, zeile in enumerate(self.text.split("\n"), 1):
            if muster.search(zeile):
                aus.append((nr, zeile.strip()))
        return aus


class Vererbungspaar:
    """``class Kind extends Basis`` - und wo die Basis definiert ist."""

    ERBT = re.compile(r"(?:export\s+)?class\s+(\w+)\s+extends\s+(\w+)")
    DEFINIERT = re.compile(r"(?:export\s+)?class\s+(\w+)")

    def __init__(self, kind, basis, kinddatei):
        self.kind = kind
        self.basis = basis
        self.kinddatei = kinddatei
        #: Datei, in der die Basisklasse steht - gesetzt von ``JsVererbung``.
        self.basisdatei = ""
        self.treffer = []

    @property
    def gefunden(self):
        return bool(self.treffer)

    def als_zeilen(self, folge):
        return [{"basisdatei": self.basisdatei, "zeile": nr,
                 "nennt": self.kind, "erbt": "%s extends %s" % (self.kind,
                                                                self.basis),
                 "code": text[:110], "folge": folge}
                for nr, text in self.treffer]


class JsVererbung(Werkzeug2):
    slug = "js-vererbung"
    titel = "Basisklasse nennt ihre eigene Ableitung"
    zweck = ("Findet in ``class X extends XBasis``-Paaren jede Stelle, an der "
             "die Basisdatei den Namen ``X`` benutzt — im Code, nicht im "
             "Kommentar.")
    befund = ("In shortlongx stand ``new TradeSystemConfig(…)`` in der "
              "Basisklasse ``TradeSystemConfigBasis``. Der Name existiert dort "
              "nicht; ein Import zurück wäre ein Zirkel. Beim ersten Aufruf "
              "von ``clone()`` hätte es einen ReferenceError gegeben — nichts "
              "davon fällt beim Laden der Seite auf.")
    abhilfe = ("``new this.constructor(…)`` statt des Klassennamens, und "
               "``this.constructor.KONSTANTE`` statt ``Klasse.KONSTANTE``. Das "
               "ist zur Laufzeit die tatsächliche Klasse und überlebt auch "
               "eine zweite Ableitung.")
    kriterium = 3
    dauer = "unter 1 s"

    SPALTEN = ("basisdatei", "zeile", "nennt", "erbt", "code", "folge")

    #: Der Fall vom 17.08.2026. Drei Fallen auf einmal, damit eine Verschaerfung
    #: nicht unbemerkt eine davon verliert:
    #:   * ``new Kind(…)`` in der Basis          -> muss gemeldet werden
    #:   * derselbe Name im KOPFKOMMENTAR        -> darf NICHT zaehlen
    #:   * derselbe Name in einer Zeichenkette   -> darf NICHT zaehlen
    #: Erwartet wird deshalb GENAU EIN Befund, nicht „mindestens einer".
    anlassfall = Anlassfall(
        {"kind.js": """import { KindBasis } from './kind_basis.js';

export class Kind extends KindBasis {
  static ANZAHL = 3;
}
""",
         "kind_basis.js": """/* KindBasis - die untere Haelfte von kind.js.
   Der Name Kind steht hier absichtlich im Kommentar. */

export class KindBasis {

  kopie() { return new Kind(this.stand); }

  melden() { console.warn('Kind: %d Zellen ohne Rolle', this.n); }
}
"""},
        mindestens=1,
        erwartet_in="kopie",
        warum="``clone()`` rief ``new TradeSystemConfig(…)`` in der "
              "Basisklasse — ReferenceError beim ersten Aufruf (17.08.2026)")

    def laufen(self):
        dateien = {p.name: p.read_text(encoding="utf-8", errors="replace")
                   for p in self.dateien(".js")}
        paare = self._paare(dateien)
        wo = self._klassenorte(dateien)
        global_gesetzt = self._globale(dateien)

        zeilen, geprueft, ueber_fenster = [], 0, 0
        for paar in paare:
            paar.basisdatei = wo.get(paar.basis, "")
            if not paar.basisdatei or paar.basisdatei == paar.kinddatei:
                continue                      # Basis extern oder selbe Datei
            geprueft += 1
            quelle = dateien[paar.basisdatei]
            paar.treffer = NurCode(quelle).stellen(paar.kind)
            if not paar.gefunden:
                continue
            if paar.kind in global_gesetzt:
                ueber_fenster += len(paar.treffer)
            zeilen += paar.als_zeilen(self._folge(quelle, paar.kind,
                                                  global_gesetzt))

        return Ergebnis(
            list(self.SPALTEN), zeilen, self._fazit(zeilen, geprueft,
                                                    ueber_fenster),
            "Kommentare und Zeichenketten sind ausgenommen — eine reine "
            "Textsuche meldete hier dreimal so viel, davon zwei Kopfzeilen "
            "und einen ``console.warn``-Text.")

    @staticmethod
    def _fazit(zeilen, geprueft, ueber_fenster):
        if not zeilen:
            return ("Keine Basisklasse nennt ihre Ableitung (%d Vererbungspaare "
                    "geprüft)." % geprueft)
        hart = len(zeilen) - ueber_fenster
        teile = ["%d Stelle(n) in %d Vererbungspaaren" % (len(zeilen), geprueft)]
        if hart:
            teile.append("%d davon brechen beim Aufruf" % hart)
        if ueber_fenster:
            teile.append("%d laufen über ``window`` (funktionieren, hängen "
                         "aber an einer Zuweisung in einer anderen Datei)"
                         % ueber_fenster)
        return ", ".join(teile) + "."

    @classmethod
    def _folge(cls, quelle, name, global_gesetzt):
        """Die drei Stufen - von harmlos bis Absturz."""
        if cls._importiert(quelle, name):
            return "Zirkel: die Basis importiert ihre eigene Ableitung"
        if name in global_gesetzt:
            return ("läuft über ``window`` — funktioniert, solange die andere "
                    "Datei geladen ist")
        return "ReferenceError beim Aufruf — der Name existiert hier nicht"

    #: ``window.X = X`` und ``Object.assign(window, {…, X, …})`` - beides macht
    #: den Namen global. Ohne diese Prüfung meldete das Werkzeug ``SignaleTab``
    #: als Absturz, obwohl ``signale_tab.js`` ihn ausdrücklich ans Fenster
    #: hängt und der Kopfkommentar die Absicht erklärt.
    FENSTER = re.compile(r"window\.(\w+)\s*=")
    ZUWEISUNG = re.compile(r"Object\.assign\s*\(\s*window\s*,\s*\{([^}]*)\}",
                           re.S)

    @classmethod
    def _globale(cls, dateien):
        aus = set()
        for text in dateien.values():
            rein = NurCode(text).text
            aus.update(cls.FENSTER.findall(rein))
            for block in cls.ZUWEISUNG.findall(rein):
                aus.update(re.findall(r"(?:^|[,{\s])(\w+)\s*(?=[,}:]|$)",
                                      block))
        return aus

    @classmethod
    def _paare(cls, dateien):
        aus = []
        for name, text in dateien.items():
            for kind, basis in Vererbungspaar.ERBT.findall(text):
                aus.append(Vererbungspaar(kind, basis, name))
        return aus

    @classmethod
    def _klassenorte(cls, dateien):
        """{Klassenname: Datei} - wo jede Klasse DEFINIERT wird."""
        aus = {}
        for name, text in dateien.items():
            for klasse in Vererbungspaar.DEFINIERT.findall(text):
                aus.setdefault(klasse, name)
        return aus

    @staticmethod
    def _importiert(quelle, name):
        return bool(re.search(r"^\s*import\s[^;]*\b%s\b" % re.escape(name),
                              quelle, re.M))
