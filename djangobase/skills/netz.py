# -*- coding: utf-8 -*-
u"""Umbaunetz - der Beweis, dass ein Umbau nichts verloren hat.

WOZU
====
Eine 4.900-Zeilen-Datei in Module zu schneiden ist keine Entscheidung, die ein
Werkzeug treffen kann - aber die Frage „ist dabei etwas verlorengegangen?" ist
mechanisch beantwortbar, und genau daran scheitern Umbauten. Beim Aufteilen von
``modus_sicht.js`` verschwand eine Methode, weil sie zwischen zwei
ausgeschnittenen Bloecken lag; kein Test sah es (siehe ``skills2/dateigroesse``).

Also: VORHER eine Abnahme, NACHHER der Vergleich.

WAS EIN NAIVES NETZ FALSCH MACHT
================================
Vergliche man „welcher Name steht in welcher Datei", meldete ein Schnitt von 109
Funktionen 109 Fehler - denn jede wechselt das Modul. Das IST der Umbau. Deshalb
unterscheidet dieses Netz:

    verschwunden   Name existiert nirgends mehr          -> FEHLER
    verschoben     Name lebt in einem anderen Modul      -> genau das war der Plan
    umgehaengt     URL zeigt auf einen ANDEREN Namen     -> FEHLER
    urls_weg       URL löst gar nicht mehr auf          -> FEHLER
    signatur       Name lebt, nimmt aber andere Argumente-> WARNUNG

DIE URL-PRUEFUNG IST DER KERN
=============================
Bei Django-Views hängt alles daran, dass ``urls.py`` noch auf dieselbe Funktion
zeigt. Das Aufloesen der URLs importiert dabei JEDES View-Modul - ein Modul, das
nach dem Schnitt nicht mehr importierbar ist, fällt hier auf, ohne dass man es
eigens prüfen muss.

Die Abnahme liegt in ``BASE_DIR/.djangobase-netz.json`` - Dateiname wie beim
Einstellungs-Speicher, damit kein neuer Ordner entsteht, den die Pruefwerkzeuge
danach selbst als Altlast melden.
"""
import ast
import json
import time
from pathlib import Path

from django.conf import settings

__all__ = ["Abnahme", "Umbaunetz"]

RAUS = ("__pycache__", "migrations", "node_modules", "venv", "pythonVENV",
        ".venv", "site-packages", "staticfiles", ".git", "sicherung", "backup",
        "archiv", "dist", "build", "vendor", "models", "unsloth_compiled_cache")


class Abnahme:
    """Ein Zustand des Projekts: welche Namen es gibt und wohin die URLs zeigen."""

    def __init__(self, namen=None, signaturen=None, urls=None, stand=""):
        #: {Name: [Modul, ...]} - Klassen und Funktionen auf Modulebene.
        self.namen = namen or {}
        #: {Name: "arg, arg, ..."} - erste Fundstelle je Name.
        self.signaturen = signaturen or {}
        #: {URL-Muster: Name der Zielfunktion}
        self.urls = urls or {}
        self.stand = stand

    # ------------------------------------------------------------- aufnehmen

    @classmethod
    def aufnehmen(cls, wurzel):
        from .gitfilter import GitFilter
        # Ignorierter Code gehoert nicht zur Abnahme: Sonst gilt eine
        # Sicherungskopie als „verschwunden", sobald jemand sie aufraeumt.
        git = GitFilter(wurzel)
        namen, signaturen = {}, {}
        for pfad in sorted(Path(wurzel).rglob("*.py")):
            if any(t in RAUS for t in pfad.parts) or not git.erlaubt(pfad):
                continue
            try:
                baum = ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError, ValueError):
                continue
            modul = pfad.relative_to(wurzel).as_posix()
            for k in baum.body:
                if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                    continue
                namen.setdefault(k.name, []).append(modul)
                if k.name not in signaturen and not isinstance(k, ast.ClassDef):
                    signaturen[k.name] = cls._signatur(k)
        return cls(namen, signaturen, cls._urls(),
                   time.strftime("%d.%m.%Y %H:%M:%S"))

    @staticmethod
    def _signatur(knoten):
        a = knoten.args
        teile = [x.arg for x in list(getattr(a, "posonlyargs", [])) + list(a.args)]
        if a.vararg:
            teile.append("*" + a.vararg.arg)
        teile += [x.arg for x in a.kwonlyargs]
        if a.kwarg:
            teile.append("**" + a.kwarg.arg)
        return ", ".join(teile)

    @staticmethod
    def _urls():
        """{Muster: Zielname}. Loest die URL-Tabelle auf - das importiert dabei
        jedes View-Modul, ein kaputtes fällt also hier auf."""
        try:
            from django.urls import get_resolver
            wurzel = get_resolver()
        except Exception:                                       # noqa: BLE001
            return {}
        aus = {}

        def gehen(muster, praefix=""):
            for p in muster:
                if hasattr(p, "url_patterns"):
                    try:
                        gehen(p.url_patterns, praefix + str(p.pattern))
                    except Exception:                           # noqa: BLE001
                        aus[praefix + str(p.pattern)] = "!! nicht aufloesbar"
                    continue
                ziel = getattr(p.callback, "__name__", None) or "?"
                aus[praefix + str(p.pattern)] = ziel
        try:
            gehen(wurzel.url_patterns)
        except Exception:                                       # noqa: BLE001
            pass
        return aus

    # ------------------------------------------------------------- speichern

    @staticmethod
    def datei():
        return Path(str(settings.BASE_DIR)) / ".djangobase-netz.json"

    def speichern(self):
        self.datei().write_text(json.dumps(
            {"stand": self.stand, "namen": self.namen,
             "signaturen": self.signaturen, "urls": self.urls},
            ensure_ascii=False, indent=1), encoding="utf-8")
        return self.datei()

    @classmethod
    def laden(cls):
        try:
            d = json.loads(cls.datei().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return cls(d.get("namen"), d.get("signaturen"), d.get("urls"),
                   d.get("stand", ""))


class Umbaunetz:
    """Abnahme vor dem Umbau, Vergleich danach."""

    slug = "umbaunetz"
    titel = "Umbau-Netz (vorher/nachher)"
    tut = ("Nimmt vor einem Umbau alle Namen, Signaturen und URL-Ziele auf und "
           "weist danach nach, dass nichts verschwunden oder umgehängt ist.")
    warum = ("Beim Aufteilen großer Dateien geht Code zwischen zwei "
             "ausgeschnittenen Blöcken verloren, ohne dass ein Test es sieht. "
             "Verschieben ist erlaubt — verschwinden nicht.")
    grenzen = ("Sieht nur Namen auf Modulebene und URL-Ziele. Ob die Funktion "
               "noch das Richtige TUT, sagen die Tests, nicht dieses Netz.")

    def abnehmen(self, wurzel):
        a = Abnahme.aufnehmen(wurzel)
        a.speichern()
        return ("ABNAHME (%s)\n%d Namen, %d URL-Ziele aufgenommen.\nAblage: %s\n"
                "Jetzt umbauen — danach 'Vergleich' druecken."
                % (a.stand, len(a.namen), len(a.urls), Abnahme.datei()))

    def vergleichen(self, wurzel):
        vorher = Abnahme.laden()
        if vorher is None:
            return "Keine Abnahme vorhanden — zuerst 'Abnahme (vorher)' druecken.", {}
        nachher = Abnahme.aufnehmen(wurzel)
        b = self._befunde(vorher, nachher)
        zeilen = ["VERGLEICH gegen Abnahme vom %s" % vorher.stand,
                  "%d verschwunden · %d URL umgehaengt · %d URL weg · "
                  "%d Signatur geändert · %d verschoben (gewollt)"
                  % (len(b["verschwunden"]), len(b["umgehaengt"]),
                     len(b["urls_weg"]), len(b["signatur"]), len(b["verschoben"])),
                  ""]
        schwer = b["verschwunden"] + b["umgehaengt"] + b["urls_weg"]
        zeilen.append("BESTANDEN — nichts verloren, keine URL umgehaengt."
                      if not schwer else "NICHT BESTANDEN — siehe unten.")
        for art in ("verschwunden", "umgehaengt", "urls_weg", "signatur",
                    "verschoben"):
            if not b[art]:
                continue
            zeilen += ["", "%s (%d):" % (art.upper(), len(b[art]))]
            zeilen += ["   " + z for z in b[art][:40]]
            if len(b[art]) > 40:
                zeilen.append("   … %d weitere" % (len(b[art]) - 40))
        return "\n".join(zeilen), b

    @staticmethod
    def _befunde(vorher, nachher):
        b = {"verschwunden": [], "verschoben": [], "umgehaengt": [],
             "urls_weg": [], "signatur": []}
        for name, module in sorted(vorher.namen.items()):
            neu = nachher.namen.get(name)
            if not neu:
                b["verschwunden"].append("%s (war in %s)" % (name, ", ".join(module[:2])))
                continue
            if set(neu) != set(module):
                b["verschoben"].append("%s: %s -> %s"
                                       % (name, ", ".join(module[:2]), ", ".join(neu[:2])))
            alt_sig = vorher.signaturen.get(name)
            neu_sig = nachher.signaturen.get(name)
            if alt_sig is not None and neu_sig is not None and alt_sig != neu_sig:
                b["signatur"].append("%s: (%s) -> (%s)" % (name, alt_sig, neu_sig))
        for muster, ziel in sorted(vorher.urls.items()):
            neu = nachher.urls.get(muster)
            if neu is None:
                b["urls_weg"].append("%s (zeigte auf %s)" % (muster, ziel))
            elif neu != ziel:
                # Modulwechsel ist erlaubt, Namenswechsel nicht: die URL wuerde
                # eine andere Funktion bedienen.
                b["umgehaengt"].append("%s: %s -> %s" % (muster, ziel, neu))
        return b
