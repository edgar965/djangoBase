# -*- coding: utf-8 -*-
u"""Anzeigeformat - wohin gehen die Schlüssel eines Rückgabe-Woerterbuchs?

DIE FRAGE, DIE ZWEI DRITTEL DER BEFUNDE ENTSCHEIDET (16.08.2026)
================================================================
„Verlassen sie sofort das Programm (JSON an den Browser), bleiben sie ein
Dictionary." Ob das zutrifft, steht oft nicht im Python: Ein Woerterbuch kann
drei Ebenen weitergereicht werden und am Ende trotzdem im Browser landen.

Also wird von der anderen Seite gefragt: Stehen die SCHLUESSEL woertlich im
JavaScript oder in einer Vorlage? Dann sind sie der Vertrag mit der Oberflaeche,
und eine Klasse davor muesste dieselben Namen ein zweites Mal führen.

    gap_fill_analyse.py:135    15 von 15 Schlüsseln in gap_fill.js  -> Anzeige
    korrelation_gauss.py:74     0 von  6 Schlüsseln im Frontend     -> Kette

Gemessen: 134 von 204 Befunden waren Anzeigeformate - nach dem Auftrag also gar
keine. Ohne diese Frage besteht die Liste zu zwei Dritteln aus Fällen, die der
Auftrag selbst ausnimmt.

WAS ES NICHT ENTSCHEIDET
========================
Ein Treffer im Frontend heißt „geht dorthin", nicht „geht NUR dorthin". Ein
Woerterbuch kann unterwegs gelesen werden und am Ende hinausgehen - dann steht
die Klasse trotzdem zur Debatte. Deshalb wird die Trefferquote ausgewiesen und
kein Urteil gefaellt: Ab welchem Anteil man umbaut, entscheidet der Mensch.
"""
import ast
import re
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug


class FrontendNamen:
    """Alle Bezeichner, die im Frontend vorkommen - einmal gelesen, dann Nachschlag.

    EINMAL ZAEHLEN, DANN NACHSCHLAGEN: je Schlüssel einmal durch alle
    Frontend-Dateien zu suchen wären bei 200 Befunden mit je bis zu 17
    Schlüsseln über tausend Volltextsuchen - genau der Fehler, den „Arbeit in
    Schleifen" nebenan meldet.
    """

    WORT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    MUSTER = ("*.js", "*.mjs", "*.html")

    def __init__(self, wurzel, ausgeschlossen=(), gitfilter=None):
        self.wurzel = wurzel
        self.ausgeschlossen = set(ausgeschlossen)
        #: Optional wie bei ``Frontendquellen`` - ohne Filter wie bisher.
        self.gitfilter = gitfilter
        self._namen = None
        self._dateien = 0

    @property
    def namen(self):
        if self._namen is None:
            z = Counter()
            for muster in self.MUSTER:
                for pfad in self.wurzel.rglob(muster):
                    if any(t in self.ausgeschlossen for t in pfad.parts):
                        continue
                    if (self.gitfilter is not None
                            and not self.gitfilter.erlaubt(pfad)):
                        continue
                    try:
                        z.update(self.WORT.findall(
                            pfad.read_text(encoding="utf-8", errors="replace")))
                    except OSError:
                        continue
                    self._dateien += 1
            self._namen = z
        return self._namen

    @property
    def dateien(self):
        self.namen
        return self._dateien

    def kennt(self, name):
        return self.namen.get(name, 0) > 0


class Anzeigeformat(Werkzeug):
    slug = "anzeigeformat"
    titel = "Geht das Dictionary an die Oberfläche?"
    zweck = ("Für jedes Rückgabe-Dictionary: Wie viele seiner Schlüssel stehen "
             "wörtlich im JavaScript oder in einer Vorlage?")
    befund = ("134 von 204 Kriterium-11-Befunden waren Anzeigeformate — der "
              "Auftrag nimmt sie selbst aus („geht es als JSON an den Browser, "
              "bleibt es ein Dictionary“).")
    abhilfe = ("Bei hoher Quote: Vermerk „Dictionary gewollt: <wohin>“ setzen "
               "und nicht umbauen. Bei null Treffern ist es eine interne Kette "
               "— dort lohnt die Klasse.")
    dauer = "5–12 s"
    kriterium = 11

    MIN_SCHLUESSEL = 4
    #: Schluessel, die ueberall vorkommen und deshalb nichts belegen.
    ZU_HAEUFIG = {"ok", "error", "name", "key", "value", "date", "id", "type",
                  "label", "data", "text", "url", "status", "title", "n", "count"}
    #: Ab diesem Anteil gilt es als Anzeigeformat.
    SCHWELLE = 0.7

    #: Ein Rueckgabe-Woerterbuch, dessen Schluessel woertlich im JavaScript
    #: stehen. Das ist kein Umbaukandidat, sondern ein ANZEIGEFORMAT - der
    #: Auftrag gibt es selbst vor. Von 204 Befunden waren 134 genau das.
    anlassfall = Anlassfall(
        {"api.py": '''def antwort(t):
    return {"kurs": t.kurs, "zeit": t.zeit,
            "menge": t.menge, "richtung": t.richtung}
''',
         "tabelle.js": '''export function zeile(d) {
  return `${d.kurs} ${d.zeit} ${d.menge} ${d.richtung}`;
}
'''},
        erwartet_in="antwort",
        warum="134 von 204 Befunden waren Anzeigeformate — Schlüssel, die die "
              "Oberfläche wörtlich liest und die deshalb bleiben müssen")

    def laufen(self):
        frontend = FrontendNamen(self.wurzel(), self.ausgeschlossen(),
                                 gitfilter=self.gitfilter())
        zeilen = []
        for d in self.dateien():
            if d.baum is None:
                continue
            for f in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                for r in [k for k in ast.walk(f) if isinstance(k, ast.Return)]:
                    zeile = self._pruefen(d, f, r, frontend)
                    if zeile:
                        zeilen.append(zeile)
        zeilen.sort(key=lambda z: (z["urteil"] != "Kette → Klasse", -z["schlüssel"]))
        kette = [z for z in zeilen if z["urteil"] == "Kette → Klasse"]
        anzeige = [z for z in zeilen if z["urteil"] == "Anzeigeformat"]
        return Ergebnis(
            ["datei", "zeile", "funktion", "schlüssel", "im frontend", "urteil"],
            zeilen,
            "%d Rückgabe-Dictionaries — %d Anzeigeformat, %d Kette, %d gemischt "
            "(Frontend: %d Dateien)"
            % (len(zeilen), len(anzeige), len(kette),
               len(zeilen) - len(anzeige) - len(kette), frontend.dateien),
            "„Kette → Klasse“ ist die Liste, die Arbeit macht. „Anzeigeformat“ "
            "nimmt der Auftrag selbst aus — dort genügt der Vermerk im Code.")

    def _pruefen(self, d, funktion, ret, frontend):
        wert = ret.value
        if not isinstance(wert, ast.Dict):
            return None
        feste = [k.value for k in wert.keys
                 if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if len(feste) < self.MIN_SCHLUESSEL:
            return None
        aussagekraeftig = [s for s in feste if s not in self.ZU_HAEUFIG]
        if not aussagekraeftig:
            return None
        treffer = [s for s in aussagekraeftig if frontend.kennt(s)]
        anteil = len(treffer) / len(aussagekraeftig)
        urteil = ("Anzeigeformat" if anteil >= self.SCHWELLE
                  else ("Kette → Klasse" if anteil == 0 else "gemischt"))
        return {"datei": d.name, "zeile": ret.lineno, "funktion": funktion.name,
                "schlüssel": len(feste),
                "im frontend": "%d / %d" % (len(treffer), len(aussagekraeftig)),
                "urteil": urteil}
