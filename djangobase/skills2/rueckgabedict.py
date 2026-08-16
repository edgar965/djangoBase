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

from .werkzeug import Ergebnis, Werkzeug2


class RueckgabeDict(Werkzeug2):
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

    def laufen(self):
        zeilen = []
        for d in self.dateien():
            if d.baum is None:
                continue
            for f in d.knoten(ast.FunctionDef, ast.AsyncFunctionDef):
                if f.name in self.SERIALISIERUNG:
                    continue
                for r in [k for k in ast.walk(f) if isinstance(k, ast.Return)]:
                    zeile = self._pruefen(d, f, r)
                    if zeile:
                        zeilen.append(zeile)
        zeilen.sort(key=lambda z: (z["bewertung"] != "prüfen", -z["schlüssel"]))
        offen = [z for z in zeilen if z["bewertung"] == "prüfen"]
        return Ergebnis(
            ["datei", "zeile", "funktion", "schlüssel", "namen", "bewertung"],
            zeilen,
            "%d Rückgabe-Dictionaries, davon %d ohne Vermerk" % (len(zeilen), len(offen)),
            "Nicht jeder Eintrag ist ein Fehler. Die Frage lautet: Wandert der "
            "Datensatz durch mehrere Funktionen — oder geht er hinaus?")

    def _pruefen(self, d, funktion, ret):
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
        belegt = self._begruendet(d, ret.lineno)
        return {"datei": d.name, "zeile": ret.lineno, "funktion": funktion.name,
                "schlüssel": len(feste),
                "namen": ", ".join(sorted(feste)[:6]),
                "bewertung": "belegt" if belegt else "prüfen"}

    def _begruendet(self, d, zeile):
        zeilen = d.text.splitlines()
        von = max(0, zeile - 7)
        return any(self.MARKER in z for z in zeilen[von:zeile])

    @staticmethod
    def _name_von(knoten):
        return getattr(knoten, "id", None) or getattr(knoten, "attr", None) or ""
