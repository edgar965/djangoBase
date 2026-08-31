# -*- coding: utf-8 -*-
u"""Befund, Befundsatz, BefundWerkzeug - die zweite Bauform, EINE Basis.

    „ich brauche keine AlteBasis, merge alles" (Edgar, 18.08.2026)

VORGESCHICHTE
=============
Es gab zwei Werkzeugkaesten mit je eigener Basisklasse: ``Werkzeug`` (Befunde:
Ort, Was, Warum, Gewicht) und ``Werkzeug2`` (Tabelle: Spalten und Zeilen). Beim
Zusammenlegen wurde die alte Welt zunaechst nur UMSCHLOSSEN — ``AltWerkzeug``
rechnete zur Laufzeit um. Das lief, hinterliess aber zwei Basisklassen, zwei
Dateisuchen, zwei Ausschlusslisten und einen Adapter dazwischen; wer ein
Werkzeug anfasste, musste erst herausfinden, in welcher Welt er ist.

Jetzt gibt es EINE Basis (:class:`~.werkzeug.Werkzeug`) und hier eine duenne
Zwischenschicht für die Werkzeuge, die ihre Funde als BEFUNDE beschreiben statt
als freie Tabelle. Sie erben damit alles, was die Basis kann — Projektwurzel
über das Git-Repo, EINE Ausschlussliste, Quelldatei-Cache — und liefern
trotzdem weiter ``Befund``-Objekte.

WARUM NICHT ALLES AUF SPALTEN UMSCHREIBEN
=========================================
Weil die vier Befund-Felder verlustfrei auf vier Spalten abbilden und die Form
etwas taugt: „wo, was, warum, wie schwer" ist bei einer Code-Prüfung fast immer
die richtige Frage. Elf Werkzeuge dafür Zeile für Zeile umzuschreiben wäre
Arbeit ohne Ertrag — und jede Umschreibung ein Anlass für neue Fehler.
"""
import time

from .pfadteile import Pfadteile
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["Befund", "Befundsatz", "BefundWerkzeug"]


class Befund:
    u"""Ein einzelner Fund: wo, was, warum - und wie schwer.

    Eigene Klasse statt Dictionary — genau die Regel, die dieser Durchgang
    hervorgebracht hat: Ein Datensatz mit mehr als drei Feldern, der seine
    Ursprungsfunktion verlässt und anderswo per ["schlüssel"] gelesen wird,
    gehört in eine Klasse.
    """

    __slots__ = ("ort", "was", "warum", "gewicht")

    #: Gewichte, aufsteigend nach Dringlichkeit. Die Namen bleiben, wie sie
    #: waren: Elf Werkzeuge schreiben ``Befund.WARNUNG``, und eine Umbenennung
    #: haette dem Merge nichts gebracht ausser Arbeit.
    HINWEIS = "hinweis"
    WARNUNG = "warnung"
    FEHLER = "fehler"

    def __init__(self, ort, was, warum="", gewicht=HINWEIS):
        self.ort = ort
        self.was = was
        self.warum = warum
        self.gewicht = gewicht

    @property
    def zeile(self):
        """Eine Zeile Klartext - für Berichte, die kopiert werden."""
        teile = ["%s: %s" % (self.ort, self.was)]
        if self.warum:
            teile.append("(%s)" % self.warum)
        return " ".join(teile)


class Befundsatz:
    """Was ein Befund-Werkzeug gefunden hat: Kopfzeilen plus Befunde."""

    def __init__(self, titel, kopf=None, befunde=None, fehler=""):
        self.titel = titel
        #: Kurze Kennzahlen ueber dem Ergebnis („412 Dateien geprueft").
        self.kopf = list(kopf or [])
        self.befunde = list(befunde or [])
        self.fehler = fehler

    @property
    def anzahl(self):
        return len(self.befunde)

    @property
    def sauber(self):
        return not self.befunde and not self.fehler


class BefundWerkzeug(Werkzeug):
    """Ein Werkzeug, das Befunde liefert statt einer freien Tabelle.

    Unterklassen ueberschreiben :meth:`pruefen` und geben einen
    :class:`Befundsatz` zurueck. ``laufen()`` macht daraus die Tabelle, die die
    Seite von JEDEM Werkzeug erwartet.
    """

    #: Die vier Befund-Felder als Tabellenspalten.
    SPALTEN = ["schwere", "ort", "befund", "hinweis"]
    #: Optionales Textfeld auf der Seite: (name, beschriftung, vorgabe)
    eingabe = None
    #: True, wenn das Werkzeug Endpunkte des laufenden Servers aufruft.
    ruft_endpunkte_auf = False

    def pruefen(self, **argumente):          # pragma: no cover - Schnittstelle
        raise NotImplementedError

    def laufen(self, **argumente):
        u"""Prüfen, Fehler abfangen, in die Tabelle umrechnen.

        Der Fehlerfall wird zu einem HINWEIS, nicht zu einer Ausnahme: Ein
        Werkzeug ist ein Hilfsmittel, und ein Hilfsmittel darf die Hilfe-Seite
        nicht zerlegen.
        """
        start = time.perf_counter()
        try:
            satz = self.pruefen(**argumente)
        except Exception as fehler:  # noqa: BLE001
            return Ergebnis(self.SPALTEN, [], "",
                            "FEHLER: %s: %s" % (type(fehler).__name__, fehler))
        dauer = time.perf_counter() - start
        if satz.fehler:
            return Ergebnis(self.SPALTEN, [], " · ".join(satz.kopf),
                            "FEHLER: %s" % satz.fehler)
        zeilen = [{"schwere": b.gewicht, "ort": str(b.ort),
                   "befund": b.was, "hinweis": b.warum} for b in satz.befunde]
        kopf = list(satz.kopf)
        if dauer >= 1:
            kopf.append("%.1f s" % dauer)
        return Ergebnis(self.SPALTEN, zeilen, " · ".join(kopf), "")

    # ------------------------------------------------------------ Hilfsmittel

    def projektdateien(self, endung=".py", ausser=None):
        u"""Alle Projektdateien mit dieser Endung - als Pfade.

        Führt über :meth:`~.werkzeug.Werkzeug.dateien`, also über DIESELBE
        Wurzel und DIESELBE Ausschlussliste wie jedes andere Werkzeug. Vorher
        hatte diese Bauform ihre eigene Suche ab ``BASE_DIR`` und eine eigene
        Liste — die beiden liefen auseinander, und ``doppelcode`` meldete
        weiter 183 von 200 Befunden aus ``vendor/``, während die neue Basis
        dort laengst nicht mehr hinsah.
        """
        raus = set(ausser or ())
        for eintrag in self.dateien(endung):
            pfad = getattr(eintrag, "pfad", eintrag)
            if Pfadteile.trifft(pfad, self.wurzel(), raus):
                continue
            yield pfad

    def kurz(self, pfad):
        """Der Pfad relativ zur Projektwurzel - für die Anzeige."""
        try:
            return str(pfad.relative_to(self.wurzel())).replace("\\", "/")
        except (ValueError, AttributeError):
            return str(pfad)
