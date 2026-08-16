# -*- coding: utf-8 -*-
u"""Namensvarianten - dasselbe Ding, zwei Schreibweisen.

    Kriterium 7 des Auftrags: „keine abweichenden Namen"

WO DAS WEHTUT
=============
Zwischen Python und JavaScript liegen in einer Django-Anwendung mehrere
Uebersetzungen: Formularfeld -> JSON-Schluessel -> Modellfeld. Heisst dasselbe
Ding dort ``fill_delay``, ``fillDelay`` und ``filldelay``, dann funktioniert
alles - bis jemand eine der drei Stellen umbenennt. Danach ist nichts rot, es
wird nur still ein anderer Wert gerechnet.

In shortlongx hat genau das zwei Parameter gekostet: Einer war seit Tagen
wirksam, aber nicht bedienbar (jedes Speichern setzte ihn auf 0), der andere kam
beim Laden nie durch. Beide Male stimmten die Namen bis auf eine Schreibweise.

WAS DAS WERKZEUG TUT
====================
Es sammelt Bezeichner aus Python (Zuweisungen, Dict-Schluessel, Argumente) und
aus JS/Vorlagen (Objektschluessel, ``data-``-Attribute, ``id=``) und meldet
Namen, die sich NUR in Schreibweise oder Trennzeichen unterscheiden.

Nicht jeder Treffer ist ein Fehler - ``max_tage`` als Python-Feld und
``maxTage`` als JS-Variable koennen absichtlich verschieden heissen. Der Befund
sagt: Diese beiden gehoeren zusammen, sieh nach, ob sie es auch tun.
"""
import ast
import re
from collections import defaultdict

from .werkzeug import Ergebnis, Werkzeug2


class Namensvarianten(Werkzeug2):
    slug = "namensvarianten"
    titel = "Dasselbe Ding, zwei Schreibweisen"
    zweck = ("Bezeichner, die sich nur in Groß-/Kleinschreibung oder "
             "Trennzeichen unterscheiden — über Python, JS und Vorlagen hinweg.")
    befund = ("Zwei Parameter waren wirkungslos, weil Formular, JSON und Engine "
              "denselben Wert leicht verschieden schrieben. Nichts wurde rot; es "
              "wurde nur still etwas anderes gerechnet.")
    abhilfe = ("Eine Schreibweise festlegen und die Übersetzungen an den "
               "Schnittstellen einmalig prüfen — dort, wo der Wert die Sprache "
               "wechselt.")
    dauer = "5–15 s"
    kriterium = 7

    #: Zu kurze Namen erzeugen nur Rauschen.
    MIN_LAENGE = 5
    #: Namen, die ueberall vorkommen und nichts aussagen.
    RAUSCHEN = {"value", "values", "index", "result", "results", "config",
                "params", "options", "context", "request", "response"}

    def laufen(self):
        vorkommen = defaultdict(lambda: defaultdict(set))   # kern -> name -> dateien
        for d in self.dateien():
            if d.baum is None:
                continue
            for name in self._python_namen(d):
                self._merken(vorkommen, name, d.name)
        for p in self.dateien(".js") + self.dateien(".html"):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for name in self._web_namen(text):
                self._merken(vorkommen, name, p.name)

        zeilen = []
        for kern, namen in vorkommen.items():
            if len(namen) < 2:
                continue
            # NUR SCHREIBWEISEN-BRÜCHE, NICHT JEDE GROSSSCHREIBUNG (Korrektur
            # beim ersten Lauf): Ohne diese Bedingung meldete das Werkzeug 1.279
            # Paare - darunter jedes ``TradeSystem``/``tradeSystem``, also die
            # ganz normale Klasse-neben-Instanz. Interessant ist der Bruch
            # zwischen den Welten: mit Trennzeichen (Python) gegen ohne (JS).
            mit_trenner = {n for n in namen if "_" in n or "-" in n}
            ohne_trenner = set(namen) - mit_trenner
            if not (mit_trenner and ohne_trenner):
                continue
            geordnet = sorted(namen.items(), key=lambda x: -len(x[1]))
            zeilen.append({
                "kern": kern,
                "varianten": " · ".join(n for n, _ in geordnet[:4]),
                "anzahl": len(namen),
                "wo": ", ".join(sorted({d for _, ds in geordnet for d in ds})[:3]),
            })
        zeilen.sort(key=lambda z: (-z["anzahl"], z["kern"]))
        return Ergebnis(
            ["kern", "varianten", "anzahl", "wo"], zeilen,
            "%d Namen mit mehreren Schreibweisen" % len(zeilen),
            "Nicht jeder Treffer ist ein Fehler — Python und JavaScript dürfen "
            "verschieden schreiben. Der Befund sagt nur: Diese gehören zusammen.")

    def _merken(self, vorkommen, name, datei):
        if len(name) < self.MIN_LAENGE or name.lower() in self.RAUSCHEN:
            return
        kern = re.sub(r"[^a-z0-9]", "", name.lower())
        if len(kern) < self.MIN_LAENGE:
            return
        vorkommen[kern][name].add(datei)

    @staticmethod
    def _python_namen(d):
        aus = set()
        for k in ast.walk(d.baum):
            if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Store):
                aus.add(k.id)
            elif isinstance(k, ast.arg):
                aus.add(k.arg)
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                if re.fullmatch(r"[A-Za-z][\w-]{3,40}", k.value):
                    aus.add(k.value)
            elif isinstance(k, ast.Attribute):
                aus.add(k.attr)
        return aus

    @staticmethod
    def _web_namen(text):
        aus = set()
        for m in re.finditer(r"\b([a-zA-Z][\w-]{3,40})\s*:", text):     # Objektschlüssel
            aus.add(m.group(1))
        for m in re.finditer(r'\bdata-([\w-]{3,40})=', text):
            aus.add(m.group(1))
        for m in re.finditer(r'\bid="([\w-]{3,40})"', text):
            aus.add(m.group(1))
        return aus
