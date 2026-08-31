# -*- coding: utf-8 -*-
u"""Frontendquellen - welche JS- und HTML-Dateien ein Werkzeug ansehen darf.

WARUM ES DIESE KLASSE GIBT (17.08.2026)
=======================================
Die Liste ``NICHT_IM_PFAD`` stand ACHTMAL im Paket - in ``frontendadressen``,
``jsbefunde``, ``jsfaenger``, ``jsfunktionen``, ``jsregistrierung``,
``jsstilfassungen``, ``jssyntax`` und ``jswaisen``. Und zwar in VIER Fassungen:
manche mit ``staticfiles``, manche ohne ``node_modules``. Die Werkzeuge waren sich
also nicht einig, welche Dateien zum Projekt gehoeren - bei acht Kopien faellt das
niemandem auf, und jede Zahl bezieht sich auf eine andere Menge.

Dazu kam siebenmal derselbe ``_quellen()``-Generator: ``rglob``, drei Filter,
``yield``. Sieben Kopien von fuenf Zeilen.

ERZEUGTER CODE WIRD GEMESSEN, NICHT GERATEN
===========================================
Die Ordnerliste allein reicht nicht - sie RAET. ``static/theatre/theatre-app.js``
und ``static/theatre-studio/studio-app.js`` sind Vite-Buendel; sie standen nur
deshalb nicht in den Befunden, weil zufaellig „theatre" in der Liste steht. Beim
naechsten Buendel in einem anders benannten Ordner waere es anders.

Gemessen in 3DTools (Zeilen ueber 1.000 Zeichen):

    theatre-app.js (Vite)   7.163 Zeilen, 114 lange, laengste 221.758
    presets.js (Hand)         318 Zeilen,   1 lange, laengste   2.235
    character.js (Hand)       263 Zeilen,   0 lange, laengste     232

MEHRERE lange Zeilen machen die Datei erzeugt, nicht eine. Die erste Fassung
dieses Massstabs nahm eine einzige - und schloss damit zwei handgeschriebene
Dateien aus, die einen CSS-Block als Template-String fuehren. Aufgefallen ist es,
weil ``jswaisen`` danach vier Importe „ins Leere" meldete: Die Ziele waren nicht
verschwunden, sie waren nur nicht mehr geprueft. Ein Massstab, der zu viel
ausschliesst, macht aus einem sauberen Projekt ein kaputtes.

DER ORDNERNAME IST KEIN MASSSTAB
================================
Die Liste enthielt ``theatre`` und ``theatre-studio`` - 3DTools-Ordner in einer
Bibliothek, die sechs Projekte benutzen. Beim Herausnehmen kam heraus, was der
Name verdeckt hatte: ``static/theatre-studio/studio-app.js`` war KEIN Buendel,
sondern eine handgeschriebene Debugseite mit 25 ``console.log``, die keine
Vorlage mehr laedt - eine Waise, seit April unangetastet. Der Ordnername hatte
sie vor jedem Werkzeug versteckt.

Ohne die Messung meldete ``protokoll`` in 3DTools 40 ``console.*``-Stellen aus
dem Vite-Buendel - Code, den niemand geschrieben hat, und dessen Quelle
(``main.js``) daneben nochmal.
"""
import re
from pathlib import Path

from .pfadteile import Pfadteile

__all__ = ["Frontendquellen"]


class Frontendquellen:
    """Die Frontend-Dateien eines Projekts - für alle Werkzeuge dieselben."""

    #: Ordnernamen mit fremdem oder erzeugtem Code — projektunabhaengig.
    #: ``theatre`` und ``theatre-studio`` standen hier ebenfalls: 3DTools-Ordner
    #: in einer Bibliothek, die sechs Projekte benutzen. Sie sind raus, und die
    #: Messung unten hat den echten Buendel sofort wiedergefunden. Der zweite
    #: „Buendel"-Ordner enthielt dagegen eine HANDGESCHRIEBENE Debugseite mit
    #: 25 ``console.log``, die niemand mehr lud — vom Ordnernamen verdeckt und
    #: seither geloescht.
    NICHT_IM_PFAD = ("vendor", "dist", "bundle", "node_modules", "staticfiles")
    #: Ab dieser Zeilenlaenge zaehlt eine Zeile als maschinengeschrieben.
    ERZEUGT_AB = 1000
    #: So viele solche Zeilen machen die DATEI erzeugt. Eine allein reicht
    #: nicht: `presets.js` (handgeschrieben) hat EINE Zeile mit 2.235 Zeichen —
    #: ein CSS-Block als Template-String. Gemessen in 3DTools:
    #:
    #:     theatre-app.js (Vite)   7.163 Zeilen, 114 lange, laengste 221.758
    #:     presets.js (Hand)         318 Zeilen,   1 lange, laengste   2.235
    #:     smpl.js (Hand)            307 Zeilen,   1 lange, laengste   1.010
    ERZEUGT_ZEILEN = 3
    #: Eine EINZIGE Zeile ab dieser Laenge genuegt. Sie muss dabei sein, weil die
    #: Probe unten nach ``PROBE_BYTE`` abschneidet: Zeile 1 von ``theatre-app.js``
    #: hat 221.758 Zeichen, in 64 KB steckt also nur ein einziges Stueck ohne
    #: Zeilenumbruch — die Zaehlung sah EINE lange Zeile und gab die Datei frei.
    #: Der Buendel stand danach mit 2.295 Befunden in der Liste (17.08.2026).
    ERZEUGT_HART = 20000
    #: So viel wird zum Pruefen gelesen. Ein Buendel hat die lange Zeile am
    #: Anfang; eine handgeschriebene Datei von 260 KB muss deshalb nicht ganz
    #: gelesen werden, nur um sie freizugeben.
    PROBE_BYTE = 64 * 1024

    def __init__(self, wurzel, raus=(), gitfilter=None):
        self.wurzel = Path(wurzel)
        self.raus = set(raus)
        self._erzeugt = {}
        #: Was in der ``.gitignore`` steht, ist nicht der Code des Projekts
        #: (18.08.2026). Optional, damit alte Aufrufer unveraendert laufen -
        #: ohne Filter wird geprueft wie bisher. Einzelheiten in gitfilter.py.
        self.gitfilter = gitfilter

    #: Dateien, deren Konsolenausgabe ihr Zweck ist.
    AUSGABEKLASSEN = ("protokoll.js", "logger.js")
    #: Test- und Debug-Dateien: Dort IST die Ausgabe das Ergebnis. Ein
    #: Playwright-Test, der nichts ausgibt, ist wertlos.
    TESTMUSTER = re.compile(r"(^|/)(test_|tests?/)|\.spec\.js$|playwright")
    #: So viele Zeilen am Dateianfang gelten als Kopf.
    KOPFZEILEN = 40

    @classmethod
    def ausgabe_gewollt(cls, kurz, zeilen):
        u"""Darf diese Datei in die Konsole schreiben, ohne dass es ein Befund ist?

        DREI WEGE, und der dritte ist der wichtige: **``dauerhaft gewollt`` im
        Dateikopf** nimmt die ganze Datei aus. Damit steht die Begründung DORT,
        wo die Ausgabe gewollt ist, statt als Pfad in einer Liste im Prüfer.

        WARUM HIER UND NICHT IN EINEM WERKZEUG (17.08.2026): ``jsregeln`` hatte
        diese drei Ausnahmen, ``protokoll`` keine — zwei Werkzeuge, die dasselbe
        zählen, mit verschiedenen Massstaeben. ``protokoll`` meldete deshalb 189
        ``console.*``-Stellen, darunter 24 aus einem Playwright-Laeufer, dessen
        Ausgabe das Ergebnis IST.
        """
        if kurz.rsplit("/", 1)[-1] in cls.AUSGABEKLASSEN:
            return True
        if cls.TESTMUSTER.search(kurz):
            return True
        return "dauerhaft gewollt" in "\n".join(zeilen[:cls.KOPFZEILEN])

    def paare(self, *endungen):
        """[(Pfad, kurzer Pfad)] - kurzer Pfad relativ zur Wurzel, mit ``/``."""
        return [(p, p.relative_to(self.wurzel).as_posix())
                for p in self.pfade(*endungen)]

    def pfade(self, *endungen):
        """Nur die Pfade, sortiert. Vorgabe: ``.js``."""
        aus = []
        for endung in (endungen or (".js",)):
            for pfad in sorted(self.wurzel.rglob("*" + endung)):
                if self._ueberspringen(pfad):
                    continue
                aus.append(pfad)
        return aus

    def texte(self, *endungen):
        """[(kurzer Pfad, Zeilenliste)] - für Werkzeuge, die über Zeilen gehen."""
        aus = []
        for pfad, kurz in self.paare(*endungen):
            try:
                aus.append((kurz, pfad.read_text(encoding="utf-8",
                                                 errors="replace").split("\n")))
            except OSError:
                continue
        return aus

    # ------------------------------------------------------------------ Filter

    def _ueberspringen(self, pfad):
        if Pfadteile.trifft(pfad, self.wurzel, self.raus):
            return True
        # ZUERST git fragen: Der Arbeitsordner eines Testlaeufers laedt
        # naturgemaess niemand, und fremder Code geht das Projekt nichts an.
        # In shortlongx waren 21 von 63 „Waisen" genau das (18.08.2026).
        if self.gitfilter is not None and not self.gitfilter.erlaubt(pfad):
            return True
        if Pfadteile.trifft(pfad, self.wurzel,
                            Frontendquellen.NICHT_IM_PFAD):
            return True
        if ".min." in pfad.name:
            return True
        return self.erzeugt(pfad)

    def erzeugt(self, pfad):
        """Ist das erzeugter Code? Gemessen an der laengsten Zeile."""
        if pfad not in self._erzeugt:
            self._erzeugt[pfad] = self._messen(pfad)
        return self._erzeugt[pfad]

    @classmethod
    def _messen(cls, pfad):
        try:
            with pfad.open("r", encoding="utf-8", errors="replace") as datei:
                probe = datei.read(cls.PROBE_BYTE)
        except OSError:
            return False
        laengen = [len(z) for z in probe.split("\n")]
        if max(laengen, default=0) > cls.ERZEUGT_HART:
            return True
        return sum(1 for n in laengen if n > cls.ERZEUGT_AB) >= cls.ERZEUGT_ZEILEN
