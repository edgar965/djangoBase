# -*- coding: utf-8 -*-
u"""Klammerzaehler - Klammertiefe in JavaScript zeilenweise mitzaehlen.

Hilfsklasse, kein Werkzeug: Zwei Pruefungen brauchen sie (`jsfaenger`: wo endet
ein try-Block? `jsbefunde`: wo endet ein mehrzeiliger `fetch(`-Aufruf?).

WARUM MIT GEDAECHTNIS (3DTools, 16.08.2026)
===========================================
Als Funktion je Zeile war es falsch, sobald ein Template-String ueber mehrere
Zeilen geht::

    header.innerHTML = `<span class="cat-chevron">…</span>
        <span class="cat-count">${anims.length}</span>`;

Die zweite Zeile steht komplett IM String. Ein zeilenweiser Zaehler ohne
Gedaechtnis zaehlt die geschweiften Klammern von ``${…}`` mit und meldet den
try-Block 60 Zeilen zu frueh als beendet - in ``animation/baum.js`` galt ein
gefangener Aufruf dadurch als ungefangen.

DER ZWEITE FALLSTRICK: ``tiefstand``
====================================
``} catch (fehler) {`` schliesst den try-Block im ERSTEN Zeichen und oeffnet
gleich wieder einen neuen. Am Zeilenende ist die Tiefe also wieder 1. Wer nur
das Zeilenende ansieht, findet das Ende eines Blocks nie.
"""

__all__ = ["Klammerzaehler"]


class Klammerzaehler:
    """Zaehlt (), [] und {} und ueberspringt Strings und Zeilenkommentare."""

    ZU = {")": "(", "]": "[", "}": "{"}

    def __init__(self, tiefe=0):
        self.tiefe = tiefe
        self.anfuehrung = None      # offenes ' " ` ueber Zeilengrenzen hinweg
        #: Niedrigste Tiefe INNERHALB der letzten Zeile (siehe Modulkopf).
        self.tiefstand = tiefe

    def zeile(self, text):
        """Eine Zeile verarbeiten und die Tiefe danach liefern."""
        entwertet = False
        self.tiefstand = self.tiefe
        i = 0
        while i < len(text):
            zeichen = text[i]
            if self.anfuehrung:
                if entwertet:
                    entwertet = False
                elif zeichen == "\\":
                    entwertet = True
                elif zeichen == self.anfuehrung:
                    self.anfuehrung = None
                i += 1
                continue
            if text.startswith("//", i):
                break                       # Rest der Zeile ist Kommentar
            if zeichen in "'\"`":
                self.anfuehrung = zeichen
            elif zeichen in "([{":
                self.tiefe += 1
            elif zeichen in Klammerzaehler.ZU:
                self.tiefe -= 1
                self.tiefstand = min(self.tiefstand, self.tiefe)
            i += 1
        # Ein einfaches oder doppeltes Anfuehrungszeichen kann in JavaScript
        # nicht ueber die Zeile hinausgehen; nur Backticks koennen es. Ohne
        # diesen Rueckfall verschluckt ein Apostroph in einem Kommentar
        # ("don't") den restlichen Text.
        if self.anfuehrung in ('"', "'"):
            self.anfuehrung = None
        return self.tiefe

    def zeilen(self, texte):
        """Alle Zeilen verarbeiten und die Tiefe danach liefern."""
        for text in texte:
            self.zeile(text)
        return self.tiefe

    @staticmethod
    def anweisungsende(zeilen, start, marke, grenze=20):
        """Letzte Zeile der Anweisung, die in `zeilen[start]` nach `marke` beginnt.

        Beispiel: ``marke='await fetch('`` findet das Ende eines mehrzeiligen
        `fetch(...)`-Aufrufs. Liefert None, wenn die Anweisung innerhalb von
        `grenze` Zeilen nicht schliesst - dann ist die Annahme falsch und das
        Werkzeug soll die Stelle nicht anfassen.
        """
        if marke not in zeilen[start]:
            return None
        zaehler = Klammerzaehler(1)
        tiefe = zaehler.zeile(zeilen[start].split(marke, 1)[1])
        ende = start
        while tiefe > 0:
            ende += 1
            if ende >= len(zeilen) or ende - start > grenze:
                return None
            tiefe = zaehler.zeile(zeilen[ende])
        return ende
