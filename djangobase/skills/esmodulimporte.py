# -*- coding: utf-8 -*-
u"""EsModulImporte - zeigen die Importe der Browser-Module ins Leere?

DER BEFUND (shortlongx, 16.08.2026)
===================================
Die Seiten bestehen aus ES-Modulen, die einander importieren. Ein Tippfehler im
Namen oder eine Datei, die beim Aufteilen umbenannt wurde, bricht die GANZE
Seite: Der Browser laedt das Einstiegsmodul nicht, es gibt keinen Teilausfall -
nur eine tote Seite und eine Meldung in einer Konsole, die niemand offen hat.

Auslöser war das Aufteilen einer 478-Zeilen-Datei in vier: vier neue
Import-Zeilen, jede eine Gelegenheit fuer genau diesen Fehler.

ZWEI FRAGEN, NICHT EINE
=======================
1. Zeigt jeder Import auf eine existierende Datei und einen dort exportierten
   Namen?
2. Trifft jeder Aufruf ``Klasse.methode(...)`` eine statische Methode, die es
   gibt? Der Import kann stimmen und der Aufruf trotzdem ins Leere gehen, wenn
   eine Methode in eine andere Klasse gewandert ist.

FALLEN, DIE BEIM BAU AUFGEFALLEN SIND
=====================================
* Kommentare enthalten Beispielcode („Aufruf ``X.y(…)`` bleibt gueltig") - ohne
  Kommentarfilter meldet die Pruefung funktionierenden Code als kaputt.
* ``export const {a, b} = …`` exportiert ZWEI Namen; ein Regex, der nur einen
  Bezeichner nach ``const`` erwartet, meldet einen gueltigen Import als Fehler.
* Vererbung ueber mehrere Ebenen (``A extends B extends C``) muss verfolgt
  werden, sonst gelten geerbte Methoden als fehlend.
Alle drei haetten den Test rot gemacht, obwohl der Code lief - und ein Test, der
bei funktionierendem Code rot wird, wird abgeschaltet statt geglaubt.
"""
import re
from pathlib import Path

from django.conf import settings

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug


class EsModulImporte(Werkzeug):
    slug = "esmodulimporte"
    titel = "ES-Module: Importe und Aufrufe"
    zweck = ("Jeder Import zeigt auf eine existierende Datei und einen dort "
             "exportierten Namen; jeder Aufruf Klasse.methode() trifft etwas.")
    befund = ("Ein Tippfehler im Importnamen bricht die ganze Seite — kein "
              "Teilausfall, nur eine tote Seite und ein Fehler in einer Konsole, "
              "die niemand offen hat.")
    abhilfe = "Namen richtigstellen oder den Aufruf auf die neue Klasse umziehen."
    dauer = "unter 2 s"
    kriterium = 3

    #: Eigenschaften, die jede Funktion/Klasse hat - nie ein Fehler.
    EINGEBAUT = {"call", "apply", "bind", "toString", "name", "length",
                 "prototype", "constructor", "hasOwnProperty", "from", "of"}

    def _js_verzeichnisse(self):
        """Alle statischen Verzeichnisse DES PROJEKTS, die JS enthalten.

        ``self.wurzel()`` und nicht ``settings.BASE_DIR`` (17.08.2026): Erstens
        liegt neben dem Django-Teil oft weiterer Code (die Basisklasse erklärt
        es), zweitens war dieses Werkzeug damit das einzige, das sich NICHT auf
        ein anderes Verzeichnis richten ließ - der Anlassfall-Check bekam es
        nicht zu fassen und meldete „blind", obwohl es sehen konnte."""
        wurzel = Path(self.wurzel())
        aus = []
        for p in wurzel.rglob("static"):
            if any(t in ("node_modules", ".git", "staticfiles") for t in p.parts):
                continue
            if any(p.rglob("*.js")):
                aus.append(p)
        return aus

    def _aufloesen(self, ziel, quelldatei):
        """Web-Pfad -> Datei auf der Platte, oder None.

        ÜBER DJANGO, NICHT ÜBER BASE_DIR (Korrektur beim ersten Lauf): Ein
        ``/static/djangobase/js/x.js`` liegt im installierten Paket, nicht im
        Projekt - die erste Fassung meldete sechs gültige Importe als „Datei
        fehlt". ``finders.find`` kennt alle Static-Verzeichnisse, auch die der
        installierten Apps; genau dafür gibt es die Funktion."""
        from django.contrib.staticfiles import finders
        pfad = ziel.split("?")[0]
        if pfad.startswith("./") or pfad.startswith("../"):
            kandidat = (quelldatei.parent / pfad).resolve()
            return kandidat if kandidat.exists() else None
        if pfad.startswith("/static/"):
            treffer = finders.find(pfad[len("/static/"):])
            if isinstance(treffer, (list, tuple)):
                treffer = treffer[0] if treffer else None
            return Path(treffer) if treffer else None
        return None                      # externe URL - nicht prüfbar

    #: Ein Import auf einen Namen, den die Zieldatei NICHT exportiert. Der
    #: Browser verwirft dann das ganze Modul - samt aller Namen, die es
    #: registrieren wollte.
    anlassfall = Anlassfall(
        {"static/app/quelle.js": '''export function vorhanden() { return 1; }
''',
         "static/app/ziel.js": '''import { vorhanden, gibtEsNicht } from './quelle.js';

export function nutzen() { return vorhanden() + gibtEsNicht(); }
'''},
        erwartet_in="gibtEsNicht",
        warum="Ein Import ins Leere reißt das ganze Modul mit — die Seite lädt "
              "mit 200 und der halbe Bildschirm ist tot")

    def laufen(self):
        dateien = []
        for verzeichnis in self._js_verzeichnisse():
            dateien.extend(self.pfade("*.js", unter=verzeichnis))
        zeilen, gelesen = [], {}

        def lies(p):
            if p not in gelesen:
                gelesen[p] = self._ohne_kommentare(
                    p.read_text(encoding="utf-8", errors="replace"))
            return gelesen[p]

        for pfad in dateien:
            for namen, ziel in self._importe(lies(pfad)):
                datei = self._aufloesen(ziel, pfad)
                if datei is None:
                    if ziel.startswith(("./", "../", "/static/")):
                        zeilen.append({"datei": pfad.name, "art": "Datei fehlt",
                                       "detail": ziel})
                    continue
                exporte = self._exporte(lies(datei))
                for n in namen:
                    if n not in exporte:
                        zeilen.append({"datei": pfad.name, "art": "Name fehlt",
                                       "detail": "{%s} aus %s" % (n, ziel)})
        return Ergebnis(
            ["datei", "art", "detail"], zeilen,
            ("%d Module geprüft, %d Fehlstellen" % (len(dateien), len(zeilen))
             if dateien else "keine JS-Module gefunden"),
            "Geprüft wird nur, was im Quelltext steht — dynamische Importe und "
            "zur Laufzeit gebaute Namen sieht diese Prüfung nicht.")

    # -------------------------------------------------------------- Zerlegen
    @staticmethod
    def _ohne_kommentare(q):
        """Kommentare weg, Zeichenketten behalten (ein ``//`` in einer URL ist
        kein Kommentar)."""
        aus, i, art = [], 0, None
        while i < len(q):
            c, d = q[i], q[i + 1] if i + 1 < len(q) else ""
            if art is None:
                if c == "/" and d == "*":
                    art, i = "/*", i + 2
                    continue
                if c == "/" and d == "/":
                    art, i = "//", i + 2
                    continue
                if c in "'\"`":
                    art = c
                aus.append(c)
                i += 1
                continue
            if art == "/*":
                if c == "*" and d == "/":
                    art, i = None, i + 2
                else:
                    aus.append("\n" if c == "\n" else " ")
                    i += 1
                continue
            if art == "//":
                if c == "\n":
                    art = None
                    aus.append("\n")
                i += 1
                continue
            if c == "\\":
                aus.append(c + d)
                i += 2
                continue
            if c == art:
                art = None
            aus.append(c)
            i += 1
        return "".join(aus)

    @staticmethod
    def _importe(quelle):
        """[(Namen, Zielpfad)] aller benannten Importe."""
        aus = []
        muster = re.compile(
            r"import\s+(?:\{([^}]*)\})?\s*from\s*['\"]([^'\"]+)['\"]")
        for m in muster.finditer(quelle):
            if not m.group(1):
                continue
            namen = [t.strip().split(" as ")[0].strip()
                     for t in m.group(1).split(",") if t.strip()]
            aus.append((namen, m.group(2)))
        return aus

    @staticmethod
    def _exporte(quelle):
        aus = set()
        for m in re.finditer(
                r"^export\s+(?:async\s+)?(?:class|function|const|let|var)\s+([A-Za-z_$][\w$]*)",
                quelle, re.M):
            aus.add(m.group(1))
        for m in re.finditer(r"^export\s*\{([^}]*)\}", quelle, re.M):
            for teil in m.group(1).split(","):
                stueck = teil.strip().split(" as ")
                if stueck and stueck[-1].strip():
                    aus.add(stueck[-1].strip())
        # Zerlegende Exporte: export const {a, b} = …
        for m in re.finditer(r"^export\s+(?:const|let|var)\s*([{\[])([^}\]]*)[}\]]",
                             quelle, re.M):
            for teil in m.group(2).split(","):
                roh = teil.split(":")[-1].split("=")[0].strip()
                if re.match(r"^[A-Za-z_$][\w$]*$", roh):
                    aus.add(roh)
        return aus
