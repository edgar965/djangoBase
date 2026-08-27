# -*- coding: utf-8 -*-
u"""Cssdubletten — dieselbe CSS-Regel in mehreren Vorlagen.

WARUM NICHT ``doppelcode``
==========================
``doppelcode`` sucht mit einem GLEITENDEN FENSTER ueber Zeilen. Ein doppelter
Block von 20 Zeilen erzeugt dort 15 Eintraege, und CSS-Regeln zerfallen in
Bruchstuecke, die einzeln nichts bedeuten. Dieses Werkzeug fragt nach der
vollstaendigen Regel (Selektor + Rumpf) und sagt, in wie vielen Dateien sie
wortgleich steht — also danach, was sich als Klasse in einer gemeinsamen
Stildatei wirklich lohnt.

WARUM NICHT ``jsstilfassungen``
===============================
Das zaehlt ``style="…"`` AM ELEMENT. Hier geht es um Regeln in
``<style>``-Bloecken und in den Stildateien.

DER KOMMENTAR MUSS VOR DEM ZERLEGEN RAUS
========================================
Sonst wandert der Kommentarblock ueber einer Regel in den „Selektor". In
3DTools steht ueber jedem erzeugten Stilblock derselbe Herkunftsvermerk — der
erste Wurf meldete diesen Vermerk als haeufigste Dublette (achtmal), und die
echten Regeln standen darunter.
"""
import re
from collections import defaultdict

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Cssdubletten"]


class Cssdubletten(BefundWerkzeug):
    """Vollstaendige CSS-Regeln, die in mehreren Dateien wortgleich stehen."""

    slug = "css-dubletten"
    titel = "CSS: dieselbe Regel in mehreren Vorlagen"
    zweck = ("Vergleicht vollstaendige Regeln (Selektor + Rumpf) statt "
             "Zeilenfenster. Was in mehreren Vorlagen wortgleich steht, "
             "gehoert in eine gemeinsame Stildatei.")
    befund = ("`doppelcode` meldet CSS als Bruchstuecke — 20 doppelte Zeilen "
              "ergeben dort 15 Eintraege, aus denen niemand ablesen kann, "
              "WELCHE Regel sich lohnt.")
    abhilfe = ("Die Regel in eine Stildatei ziehen und die Vorlagen darauf "
               "verweisen lassen.")
    dauer = "unter 1 s"
    kriterium = 6
    eingabe = ("ab", "Ab wie vielen Dateien melden?", "3")

    anlassfall = Anlassfall(
        {"templates/a.html": (
            "<style>/* Vermerk */ .karte{padding:8px;color:red}\n"
            ".nur-hier{margin:0}</style>\n"),
         "templates/b.html": (
            "<style>/* Vermerk */ .karte { padding: 8px; color: red; }"
            "</style>\n"),
         "templates/c.html": (
            "<style>.karte{padding:8px;color:red}</style>\n")},
        mindestens=1, hoechstens=1, erwartet_in=".karte",
        warum="`.karte` steht in drei Vorlagen wortgleich — einmal mit "
              "Leerzeichen, einmal ohne. `.nur-hier` und der Kommentar "
              "`/* Vermerk */` stehen daneben: Der Kommentar wanderte im "
              "ersten Wurf in den Selektor und wurde selbst als Dublette "
              "gemeldet.")

    #: Der ``<style>``-Block einer Vorlage.
    STILBLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
    #: Eine Regel: Selektor bis ``{``, dann der Rumpf bis ``}``. Verschachtelte
    #: At-Regeln (``@media``) werden nicht zerlegt — sie kommen als Ganzes.
    REGEL = re.compile(r"([^{}]+)\{([^{}]*)\}")
    #: Kommentare MUESSEN vor dem Zerlegen raus — siehe Modul-Docstring.
    KOMMENTAR = re.compile(r"/\*.*?\*/", re.S)

    def pruefen(self, ab="3", **_argumente):
        try:
            grenze = max(2, int(str(ab).strip() or 3))
        except ValueError:
            grenze = 3
        vorkommen = defaultdict(set)
        umfang = {}
        dateien = 0
        for pfad in self._quellen():
            dateien += 1
            kurz = self.kurz(pfad)
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for selektor, rumpf in self._regeln(pfad, text):
                schluessel = self._normal(selektor, rumpf)
                if not schluessel:
                    continue
                vorkommen[schluessel].add(kurz)
                umfang[schluessel] = rumpf.count(";") + 2
        return self._satz(vorkommen, umfang, grenze, dateien)

    def _quellen(self):
        for pfad in self.projektdateien(".html"):
            if "templates" in pfad.parts:
                yield pfad
        for pfad in self.projektdateien(".css"):
            yield pfad

    def _regeln(self, pfad, text):
        """(Selektor, Rumpf) — aus ``<style>``-Bloecken bzw. der ganzen Datei."""
        if pfad.suffix == ".css":
            return self.REGEL.findall(self.KOMMENTAR.sub("", text))
        raus = []
        for block in self.STILBLOCK.findall(text):
            raus += self.REGEL.findall(self.KOMMENTAR.sub("", block))
        return raus

    @classmethod
    def _normal(cls, selektor, rumpf):
        """Selektor und Rumpf ohne Leerraum — sonst zaehlt Formatierung mit.

        Der Leerraum muss BIS IN die einzelne Angabe hinein weg. Im ersten
        Wurf blieb er hinter dem Doppelpunkt stehen, und
        ``padding:8px`` galt als etwas anderes als ``padding: 8px`` — der
        eigene Anlassfall fiel damit durch, obwohl dieselbe Regel dreimal
        dastand. Genau diese zwei Schreibweisen stehen nebeneinander, sobald
        zwei Leute an denselben Vorlagen arbeiten.
        """
        sel = " ".join(selektor.split())
        koerper = ";".join(cls._angabe(t) for t in rumpf.split(";") if t.strip())
        if not sel or not koerper or sel.startswith("@"):
            return ""
        return "%s{%s}" % (sel, koerper)

    @staticmethod
    def _angabe(text):
        """``  padding :  8px  `` -> ``padding:8px``."""
        name, doppelpunkt, wert = text.partition(":")
        if not doppelpunkt:
            return " ".join(text.split())
        return "%s:%s" % (" ".join(name.split()), " ".join(wert.split()))

    def _satz(self, vorkommen, umfang, grenze, dateien):
        mehrfach = {k: v for k, v in vorkommen.items() if len(v) >= grenze}
        gespart = sum(umfang[k] * (len(v) - 1) for k, v in mehrfach.items())
        befunde = []
        for schluessel, orte in sorted(mehrfach.items(),
                                       key=lambda p: (-len(p[1]), p[0])):
            befunde.append(Befund(
                sorted(orte)[0],
                "%dx: %s" % (len(orte), schluessel[:70]),
                "Steht wortgleich in: %s" % ", ".join(sorted(orte)[:4]),
                Befund.WARNUNG if len(orte) >= 5 else Befund.HINWEIS))
        kopf = ["%d Dateien gelesen" % dateien,
                "%d verschiedene Regeln" % len(vorkommen),
                "%d davon in mindestens %d Dateien" % (len(mehrfach), grenze),
                "etwa %d Zeilen zu sparen" % gespart]
        return Befundsatz(self.titel, kopf, befunde)
