# -*- coding: utf-8 -*-
u"""RueckgabeDict - Dictionaries mit vielen festen Schluesseln.

DIE UNTERSCHEIDUNG IST DER GANZE PUNKT
======================================
Ein Dictionary, das direkt als ``JsonResponse`` hinausgeht oder so in der
Datenbank liegt, IST das Ausgabeformat - eine Klasse davor waere eine
Verkleidung. Ein Dictionary, das durch drei Funktionen wandert und dort per
``d["schluessel"]`` gelesen wird, ist ein Objekt ohne Klasse: Jeder Tippfehler
im Schluessel ist ein stiller Fehler oder ein neuer, nie gelesener Eintrag.

Deshalb prueft dieses Werkzeug nicht „hat mehr als drei Schluessel", sondern:
mehr als drei FESTE Schluessel UND der Rueckgabewert geht nicht unmittelbar in
eine Antwort.

WAS STATISCH NICHT ENTSCHEIDBAR IST
===================================
Ob ein Dictionary „das Programm verlaesst", steht oft erst beim Aufrufer:

    erg = Simulation(body).lauf()                 # ein Dict mit 25 Schluesseln
    return JsonResponse({"ok": True, "result": erg})

Zwei Ebenen weiter, in einer anderen Datei. Diese Kette laesst sich nicht
zuverlaessig verfolgen. Deshalb traegt die Stelle selbst den Vermerk:

    # Dictionary gewollt: geht als JSON an die Seite und in die DB

Der Vermerk stuft den Befund ab - und zwingt dazu, die Frage einmal wirklich zu
beantworten: Wohin gehen diese Daten?
"""
import ast
import re
from collections import Counter

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug


class FrontendVertrag:
    """Welche Bezeichner kommen in JavaScript und Vorlagen vor?

    DIE FRAGE, DIE DIESES WERKZEUG BRAUCHBAR MACHT (16.08.2026)
    ==========================================================
    Ob ein Dictionary „das Programm verlässt", steht oft nicht im Python: Es kann
    drei Ebenen weitergereicht werden und am Ende trotzdem im Browser landen. Der
    VERTRAG steht dann im Frontend — dort, wo ``exp.expected_end_of_day`` gelesen
    wird.

    Also wird von der anderen Seite gefragt: Stehen die SCHLÜSSEL wörtlich im
    JavaScript oder in einer Vorlage? Dann sind sie das Ausgabeformat, und eine
    Klasse davor müsste dieselben Namen ein zweites Mal führen — beim nächsten
    Umbenennen laufen die beiden auseinander.

    Gemessen (shortlongx, 16.08.2026): **133 von 204 Befunden** waren solche
    Anzeigeformate. Stichprobe in beide Richtungen belegt: eine Gap-Analyse
    (15/15 Schlüssel im zugehörigen JS) gegen eine interne Korrelationskette
    (0/6). Ohne diese Frage besteht die Liste zu zwei Dritteln aus Fällen, die
    der Auftrag selbst ausnimmt.

    EINMAL LESEN, DANN NACHSCHLAGEN: je Schlüssel einmal durch alle
    Frontend-Dateien zu suchen wären bei 200 Befunden über tausend
    Volltextsuchen — genau der Fehler, den „Arbeit in Schleifen" nebenan meldet.
    """

    WORT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    MUSTER = ("*.js", "*.mjs", "*.html")
    #: Schlüssel, die überall vorkommen und deshalb nichts belegen.
    ZU_HAEUFIG = {"ok", "error", "name", "key", "value", "date", "id", "type",
                  "label", "data", "text", "url", "status", "title", "n", "count"}
    #: Ab diesem Anteil aussagekräftiger Schlüssel gilt es als Anzeigeformat.
    SCHWELLE = 0.7

    def __init__(self, wurzel, ausgeschlossen=(), gitfilter=None):
        self.wurzel = wurzel
        self.ausgeschlossen = set(ausgeschlossen)
        #: Optional wie bei ``Frontendquellen`` - ohne Filter wie bisher.
        self.gitfilter = gitfilter
        self._namen = None

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
            self._namen = z
        return self._namen

    def ist_anzeigeformat(self, schluessel):
        aussagekraeftig = [s for s in schluessel if s not in self.ZU_HAEUFIG]
        if not aussagekraeftig:
            return False
        treffer = sum(1 for s in aussagekraeftig if self.namen.get(s, 0) > 0)
        return treffer / len(aussagekraeftig) >= self.SCHWELLE


class RueckgabeDict(Werkzeug):
    slug = "rueckgabedict"
    titel = "Dictionary oder Klasse?"
    zweck = ("Rückgabe-Dictionaries mit mehr als drei festen Schlüsseln, die "
             "nicht unmittelbar in eine Antwort verpackt werden.")
    befund = ("Datensätze, die durch mehrere Funktionen wandern und per "
              "[\"schlüssel\"] gelesen werden: Jeder Tippfehler ist ein stiller "
              "Fehler, jeder neue Eintrag wird nie gelesen.")
    abhilfe = ("Klasse mit benannten Feldern. Wo die Daten wirklich hinausgehen "
               "(JSON, Datenbank), bleibt das Dictionary — dann den Vermerk "
               "„Dictionary gewollt: <wohin>“ setzen.")
    dauer = "3–8 s"
    kriterium = 11

    MIN_SCHLUESSEL = 4
    MARKER = "Dictionary gewollt"
    #: Aufrufe, deren Ergebnis SOFORT das Programm verlaesst.
    AUSGANG = {"JsonResponse", "HttpResponse", "render", "dumps", "json_response"}
    #: Serialisierungs-Methoden - ihr Dictionary IST die Speicherform.
    SERIALISIERUNG = {"to_dict", "als_dict", "as_dict", "serialize", "to_json",
                      "als_json", "speicherform"}

    #: Zwei Rueckgabe-Woerterbuecher mit je vier festen Schluesseln - eines
    #: OHNE Marker (Befund), eines MIT (darf nicht zaehlen). Der Marker ist die
    #: Abkuerzung fuer „geht unveraendert als JSON hinaus"; wer ihn ignoriert,
    #: meldet jede Serialisierung als Umbaubedarf.
    anlassfall = Anlassfall(
        {"auswertung.py": '''def bilanz(werte):
    return {"n": len(werte), "summe": sum(werte),
            "min": min(werte), "max": max(werte)}


def als_json(werte):
    # Dictionary gewollt: geht unveraendert als JSON an die Seite.
    return {"n": len(werte), "summe": sum(werte),
            "min": min(werte), "max": max(werte)}
'''},
        mindestens=1, hoechstens=1,
        erwartet_in="bilanz",
        warum="Kriterium 11: Datensatz mit mehr als drei festen Schlüsseln "
              "gehört in eine Klasse")

    def laufen(self):
        zeilen = []
        frontend = FrontendVertrag(self.wurzel(), self.ausgeschlossen(),
                                   gitfilter=self.gitfilter())
        for d in self.dateien():
            if d.baum is None:
                continue
            # EIN VORGEGEBENES ERGEBNISFORMAT IST KEIN BEFUND (16.08.2026):
            # Der Test-Runner erwartet von jeder Prüfung genau
            # {"success", "error", "stats", "values"} - vier feste Schlüssel.
            # Diese Wörterbücher zu melden hieße, gegen die eigene Suite zu
            # arbeiten; im shortlongx-Lauf waren es über fünfzig Befunde mit
            # ein und derselben Ursache.
            pruefmodul = "/pruefungen/" in d.name or "/tests" in d.name
            for f in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                if f.name in self.SERIALISIERUNG:
                    continue
                if pruefmodul and f.name.startswith(("run_", "test_")):
                    continue
                for r in [k for k in ast.walk(f) if isinstance(k, ast.Return)]:
                    zeile = self._pruefen(d, f, r, frontend)
                    if zeile:
                        zeilen.append(zeile)
        zeilen.sort(key=lambda z: (z["bewertung"] != "prüfen", -z["schlüssel"]))
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        anzeige = [z for z in zeilen if z["bewertung"] == "Anzeigeformat"]
        return Ergebnis(
            ["datei", "zeile", "funktion", "schlüssel", "namen", "bewertung"],
            zeilen,
            "%d Rückgabe-Dictionaries — %d zu prüfen, %d Anzeigeformat, %d belegt"
            % (len(zeilen), len(offen), len(anzeige),
               len(zeilen) - len(offen) - len(anzeige)),
            "Nicht jeder Eintrag ist ein Fehler. Die Frage lautet: Wandert der "
            "Datensatz durch mehrere Funktionen — oder geht er hinaus? "
            "„Anzeigeformat“ heißt: die Schlüssel stehen wörtlich im Frontend.")

    def _pruefen(self, d, funktion, ret, frontend=None):
        wert = ret.value
        if wert is None:
            return None
        if isinstance(wert, ast.Call) and self._name_von(wert.func) in self.AUSGANG:
            return None
        if not isinstance(wert, ast.Dict):
            return None
        feste = [k.value for k in wert.keys
                 if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if len(feste) < self.MIN_SCHLUESSEL:
            return None
        if self._nur_eigene_felder(wert):
            # DIE KLASSE IST SCHON DA. Ein Wörterbuch, das nur ``self.<feld>``
            # einsammelt, IST die Ausgabeform eines Objekts - egal wie die
            # Methode heißt. Die feste Namensliste (``as_dict``, ``to_dict``)
            # traf nur die üblichen Fälle; dieses Merkmal trifft die Sache.
            bewertung = "Serialisierung"
        elif self._begruendet(d, ret.lineno):
            bewertung = "belegt"
        elif frontend is not None and frontend.ist_anzeigeformat(feste):
            # Der Auftrag nimmt diesen Fall selbst aus: Was als JSON an die Seite
            # geht, IST das Ausgabeformat. Gemessen statt geraten — die Schlüssel
            # stehen wörtlich im Frontend (siehe FrontendVertrag oben).
            bewertung = "Anzeigeformat"
        else:
            bewertung = "prüfen"
        return {"datei": d.name, "zeile": ret.lineno, "funktion": funktion.name,
                "schlüssel": len(feste),
                "namen": ", ".join(sorted(feste)[:6]),
                "bewertung": bewertung}

    @staticmethod
    def _nur_eigene_felder(wert):
        """Sammelt dieses Wörterbuch NUR ``self.<attribut>`` ein?

            def kennzahlen(self):
                return {"konto": self.konto, "gv_offen": self.gv_offen, …}

        Die Klasse FÜHRT diese Werte bereits als Felder. „Gehört in eine Klasse"
        zu melden wäre hier zirkulär: Sie ist eine. Verlangt wird, dass die
        Mehrheit der Werte reine Attributzugriffe sind — einzelne gerechnete
        Felder (``len(self.assets)``) ändern nichts daran."""
        if not wert.values:
            return False
        eigene = sum(1 for v in wert.values
                     if isinstance(v, ast.Attribute)
                     and isinstance(v.value, ast.Name) and v.value.id == "self")
        return eigene >= max(3, len(wert.values) * 0.6)

    def _begruendet(self, d, zeile):
        zeilen = d.text.splitlines()
        von = max(0, zeile - 7)
        return any(self.MARKER in z for z in zeilen[von:zeile])

    @staticmethod
    def _name_von(knoten):
        return getattr(knoten, "id", None) or getattr(knoten, "attr", None) or ""
