# -*- coding: utf-8 -*-
u"""JsWaisen - Browser-Module, die niemand laedt, und Importe ins Leere.

DER BEFUND (3DTools, 16.08.2026)
================================
``photo_to_3d/facial_expression.js`` meldete ``fn.applyFacialExpression`` in der
Registrierung an - wurde aber von KEINER Datei importiert und in KEINEM Template
eingebunden. Der Aufruf lief deshalb immer in ein „is not a function",
verschluckt vom umgebenden ``try``; alles danach (Hautfarbe setzen, Rohdaten
anzeigen) wurde uebersprungen. Drei Module waren so verwaist, drei Funktionen
der Seite damit tot - ohne eine einzige Fehlermeldung.

Ein Modul, das sich selbst in einer Registrierung anmeldet, faellt ohne Import
nicht auf: Es gibt keinen unbenutzten Import und keine unaufgeloeste Referenz,
nur eine Funktion, die zur Laufzeit fehlt.

DREI ARTEN VON FUND
===================
* **verwaist** - niemand importiert die Datei, kein Template laedt sie.
* **verwaist + angemeldet** - dazu meldet sie Funktionen in einer Registrierung
  an. Der gefaehrliche Fall: Andere Dateien rufen diese Namen auf.
* **Import ins Leere** - ein Import zeigt auf eine Datei, die es nicht gibt.
  ``scene/kleider_anpassen.js`` importierte dynamisch ``../model_generator.js``,
  aufgeteilt am Vortag. Ein ``await import(...)`` mitten in einer Funktion
  faellt erst auf, wenn genau dieser Zweig laeuft.

WARUM ERREICHBARKEIT und nicht „wird irgendwo importiert"
=========================================================
Wer nur zaehlt, welche Datei irgendwo importiert wird, uebersieht ganze
Altlast-Ketten: ``scene_state.js`` wurde von drei alten Modulen importiert - und
alle vier lud niemand. Erst der Lauf von den Vorlagen aus zeigt das.
"""
import re
from pathlib import Path

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["JsWaisen"]

#: `import … from './x.js'` und `import './x.js'`, mit optionalem ?v=
IMPORT = re.compile(r"""(?:import|export)[^'"]*?['"]([^'"]+\.js)(?:\?[^'"]*)?['"]""")
#: Dynamischer Import, auch mit absolutem Pfad
DYNAMISCH = re.compile(r"""import\s*\(\s*['"]([^'"]+\.js)(?:\?[^'"]*)?['"]""")
#: Einbindung in einer Vorlage (src=, {% static %}, importmap)
IM_TEMPLATE = re.compile(r"""['"]([^'"]*?\.js)(?:\?[^'"]*)?['"]""")
#: Anmeldung in einer Registrierung: `fn.name =` oder `window.name =`
ANMELDUNG = re.compile(r"^\s*(?:fn|window)\.(\w+)\s*=", re.MULTILINE)
#: Merkmale einer Datei, die AUSGEFUEHRT wird (Node, Bauwerkzeug, Testlaeufer)
#: statt von einer Seite geladen zu werden.
#:
#: WARUM AM CODE UND NICHT AM ORDNER (17.08.2026): Vorher standen
#: `vite.config.js`, `playwright.config.js` und `test_anim_debug.js` unter
#: „laedt niemand" — mit dem Hinweis, das sei zu Recht so. Ein Befund, der
#: „zu Recht" dasteht, ist keiner: Er faelscht die Zahl und die Abhilfe lautete
#: „importieren oder loeschen" fuer lebenden Code. Wer stattdessen eine
#: Ordnerliste pflegt, liegt beim naechsten Projekt daneben. Diese Merkmale
#: kann der Browser gar nicht ausfuehren, also ist die Datei ein Laeufer:
LAEUFER = (
    "require(",         # CommonJS — im Browser-Modul unmoeglich
    "module.exports",   # dito
    "__dirname",        # Node
    "process.env",      # Node
    "defineConfig(",    # Vite/Playwright/Jest-Konfiguration
)


def ohne_kommentarzeilen(text):
    u"""Reine Kommentarzeilen entfernen.

    Ohne das melden Kommentare, die einen Import ERWAEHNEN, einen Treffer -
    genau das passierte beim eigenen Hinweis „holte sein Netz per
    ``await import('../model_generator.js')``". Es werden nur Zeilen verworfen,
    die mit //, * oder /* beginnen: Zeilen mit Code bleiben unangetastet, damit
    kein echter Import verloren geht.
    """
    behalten = []
    for zeile in text.split("\n"):
        blank = zeile.lstrip()
        if blank.startswith(("//", "*", "/*")):
            continue
        behalten.append(zeile)
    return "\n".join(behalten)


class Modulinventar:
    """Alle JS-Dateien unter einer Wurzel und wer sie laedt."""

    def __init__(self, dateien, vorlagen):
        self.dateien = [p.resolve() for p in dateien]
        self.vorlagen = list(vorlagen)
        self.anmeldungen = {}
        self.importe = {}
        self.rohimporte = {}
        self.geladen = set()
        self.laeufer = set()

    def erheben(self):
        bekannt = set(self.dateien)
        for pfad in self.dateien:
            text = ohne_kommentarzeilen(
                pfad.read_text(encoding="utf-8", errors="replace"))
            if any(marke in text for marke in LAEUFER):
                self.laeufer.add(pfad)
            self.anmeldungen[pfad] = sorted(set(ANMELDUNG.findall(text)))
            treffer = IMPORT.findall(text) + DYNAMISCH.findall(text)
            self.rohimporte[pfad] = [t for t in treffer if t.startswith(".")]
            ziele = set()
            for angabe in treffer:
                ziel = self._aufloesen(pfad, angabe, bekannt)
                if ziel:
                    ziele.add(ziel)
            self.importe[pfad] = ziele
        self.geladen = self._erreichbar(self._einstiegspunkte())
        return self

    def _aufloesen(self, von, angabe, bekannt):
        """Angabe zu einem Pfad machen; absolute Pfade ueber den Dateinamen."""
        if angabe.startswith("."):
            ziel = (von.parent / angabe).resolve()
            return ziel if ziel in bekannt else None
        name = angabe.split("/")[-1]
        passende = [p for p in self.dateien if p.name == name]
        return passende[0] if len(passende) == 1 else None

    def _erreichbar(self, start):
        gesehen = set(start)
        offen = list(start)
        while offen:
            for ziel in self.importe.get(offen.pop(), ()):
                if ziel in gesehen:
                    continue
                gesehen.add(ziel)
                offen.append(ziel)
        return gesehen

    def _einstiegspunkte(self):
        """Dateien, die eine Vorlage laedt - ueber {% static %} oder als src."""
        nach_name = {}
        for pfad in self.dateien:
            nach_name.setdefault(pfad.name, []).append(pfad)
        einstieg = set()
        for pfad in self.vorlagen:
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for treffer in IM_TEMPLATE.findall(text):
                for datei in nach_name.get(treffer.split("/")[-1], ()):
                    einstieg.add(datei)
        return einstieg

    def verwaist(self):
        u"""Dateien, die keine Seite laedt — Laeufer ausgenommen.

        Ein Laeufer (Node-Skript, Bauwerkzeug, Testlaeufer) gehoert nicht zu den
        Seiten und MUSS unerreichbar sein. Er unter „laedt niemand" zu fuehren
        heisst, einen Loeschvorschlag fuer lebenden Code zu machen.
        """
        return [p for p in self.dateien
                if p not in self.geladen and p not in self.laeufer]

    def fehlende(self):
        """Importe, die auf eine Datei zeigen, die es nicht gibt."""
        bekannt = set(self.dateien)
        offen = []
        for pfad, angaben in self.rohimporte.items():
            for angabe in angaben:
                if self._aufloesen(pfad, angabe, bekannt) is None:
                    offen.append((pfad, angabe))
        return offen


class JsWaisen(Werkzeug2):
    slug = "jswaisen"
    titel = "Browser-Module: Waisen und Importe ins Leere"
    zweck = ("Laeuft von den Vorlagen aus durch alle Importe: Welche .js-Datei "
             "laedt niemand, und welcher Import zeigt auf eine Datei, die es "
             "nicht gibt?")
    befund = ("3DTools: drei Module waren verwaist und meldeten trotzdem "
              "Funktionen an - Fotoanalyse, Ausricht-Assistent und Textur-Reiter "
              "waren dadurch ohne Wirkung, ohne eine Fehlermeldung.")
    abhilfe = ("Verwaist + angemeldet: importieren oder loeschen. Import ins "
               "Leere: Pfad korrigieren - meist ist die Datei umgezogen.")
    dauer = "unter 1 s"
    kriterium = 5

    NICHT_IM_PFAD = ("vendor", "theatre", "theatre-studio", "dist", "bundle",
                     "node_modules")

    #: Drei Module, eine Vorlage: ``geladen.js`` haengt an der Seite und zieht
    #: ``teil.js`` nach - ``waise.js`` zieht niemand. Genau so waren
    #: ``ib_aktionen.js`` und ``ib_spielmodus.js`` verwaist, und damit war jeder
    #: Spielmodus- und Bracket-Knopf tot, ohne eine Zeile in der Konsole.
    anlassfall = Anlassfall(
        {"templates/seite.html": '''<script type="module"
        src="/static/app/geladen.js"></script>
''',
         "static/app/geladen.js": '''import { hilf } from './teil.js';

export function start() { return hilf(); }
''',
         "static/app/teil.js": '''export function hilf() { return 1; }
''',
         "static/app/waise.js": '''export function niemandLaedtMich() { return 2; }
'''},
        erwartet_in="waise.js",
        warum="Zwei verwaiste Teildateien machten alle Spielmodus- und "
              "Bracket-Knöpfe wirkungslos — ohne Fehlermeldung")

    def laufen(self):
        wurzel = self.wurzel()
        inventar = Modulinventar(self._quellen(), self._vorlagen()).erheben()
        zeilen = []
        for pfad, angabe in inventar.fehlende():
            zeilen.append({"art": "Import ins Leere",
                           "ort": pfad.relative_to(wurzel).as_posix(),
                           "text": angabe})
        for pfad in inventar.verwaist():
            namen = inventar.anmeldungen.get(pfad, [])
            zeilen.append({
                "art": "verwaist + angemeldet" if namen else "verwaist",
                "ort": pfad.relative_to(wurzel).as_posix(),
                "text": ", ".join(namen[:6]) if namen else ""})
        # Der gefaehrliche Fall zuerst.
        rang = {"Import ins Leere": 0, "verwaist + angemeldet": 1, "verwaist": 2}
        zeilen.sort(key=lambda z: (rang[z["art"]], z["ort"]))
        return Ergebnis(
            ["art", "ort", "text"], zeilen,
            zusammenfassung="%d JS-Dateien, %d davon laedt niemand, %d Importe "
                            "ins Leere (%d Laeufer nicht gezaehlt)"
                            % (len(inventar.dateien), len(inventar.verwaist()),
                               len(inventar.fehlende()), len(inventar.laeufer)),
            hinweis="Laeufer (Node-Skripte, vite.config.js, Playwright-Tests) "
                    "sind ausgenommen — sie werden ausgefuehrt, nicht von einer "
                    "Seite geladen, und am Code erkannt (require/module.exports/"
                    "__dirname/process.env/defineConfig), nicht am Ordner.")

    def _quellen(self):
        raus = self.ausgeschlossen()
        for pfad in sorted(self.wurzel().rglob("*.js")):
            if any(teil in raus for teil in pfad.parts):
                continue
            if any(teil in JsWaisen.NICHT_IM_PFAD for teil in pfad.parts):
                continue
            if ".min." not in pfad.name:
                yield pfad

    def _vorlagen(self):
        raus = self.ausgeschlossen()
        for pfad in sorted(self.wurzel().rglob("*.html")):
            if any(teil in raus for teil in pfad.parts):
                continue
            yield pfad
