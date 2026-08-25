# -*- coding: utf-8 -*-
u"""Welches Werkzeug behebt DIESEN Befund? - die Antwort am Fehlschlag.

DER AUFTRAG (25.08.2026, Edgar)
===============================
    „Überlege, ob wir nicht alle Testcases ändern sollen und gleich die
     Werkzeuge, die sich für den Fix des spezifischen Testcases gibt,
     anbiete, damit nicht jede andere Session sich eigene Fix-Werkzeuge baut"

DER FALL DAHINTER
=================
Ein Durchgang im Projekt ``assistant`` meldete 174 tote Importe. Statt
nachzusehen, was der Werkzeugkasten dafür hat, entstanden zwei neue Dateien -
beide mit denselben vier Sicherungen, die ``fix_importe.ImportFixer`` seit dem
17.08.2026 mitbringt. Der vorhandene Fixer war gründlicher: nach dem Nachbau
fand er noch 45 weitere Stellen.

WARUM NICHT ALLE TESTS ANFASSEN
===============================
Der naheliegende Weg wäre ein Feld an jedem Testfall. Bei über 240 Fällen ist
das die teuerste Lösung mit dem schlechtesten Verhältnis: 240 Stellen zu
pflegen, und wer künftig einen Test schreibt, vergisst das Feld - dann steht
dort nichts, und niemand merkt es.

Diese Klasse dreht die Richtung um: **Das Werkzeug sagt, was es behebt.** Das
sind 57 Stellen statt 240, gepflegt von dem, der es am besten weiß.

DREI EBENEN, IN DIESER REIHENFOLGE
==================================
1. ``behebt`` am Werkzeug - ausdrücklich benannt, gilt als sicher.
2. Das ``kriterium``. Werkzeug und Prüfung tragen dieselbe Nummer des
   Auftrags-Kriteriums; 43 von 50 Werkzeugen haben sie bereits. Das deckt den
   größten Teil ab, ohne eine einzige neue Zeile.
3. Namensähnlichkeit - als VERMUTUNG gekennzeichnet, nie als Tatsache. Die
   Mechanik steht schon in ``werkzeugkatalog._wortformen``; sie findet dort
   Nachbauten, hier Treffer.

Ein Test darf übersteuern (``werkzeuge = (...)`` am Testfall), wenn die
Automatik danebenliegt. Das ist die Ausnahme, nicht die Regel.

WO DAS ERGEBNIS HINGEHÖRT - UND WO NICHT
========================================
An den FEHLSCHLAG, nicht in den Bericht. ``GrundtestWerkzeugkatalog`` druckt
heute alle 57 Einträge in jeden Lauf; das ist derselbe Fehler wie beim Katalog
selbst, nur eine Ebene höher. Der Commit-Text vom 25.08.2026 sagt es: „Ein
Verzeichnis, das man aufschlagen KANN, wird nicht aufgeschlagen." Eine Liste,
die bei jedem Lauf vollständig dasteht, wird nach dem dritten Mal überscrollt.
Gelesen wird der rote Test.
"""
import re

__all__ = ["Werkzeugwahl"]

#: Wörter, die in fast jedem Namen vorkommen und deshalb nichts unterscheiden.
#: Ohne sie träfe „test_datei_groesse" auf jedes Werkzeug mit „datei" im Namen.
FUELLWOERTER = frozenset((
    "test", "tests", "pruefung", "pruefen", "prueft", "check", "run",
    "djangobase", "grundtest", "konform", "js", "py", "der", "die", "das",
    "und", "oder", "ein", "eine", "im", "in", "auf", "mit", "von", "fuer",
))


class Werkzeugwahl:
    u"""Sucht zu einem Befund die Werkzeuge, die ihn beheben."""

    #: Ab so vielen gemeinsamen Wortteilen gilt ein Namenstreffer als Vermutung
    #: wert. EINS reicht nicht: „tote-importe" und „test_importe_sortiert"
    #: teilen sich „importe" und meinen Verschiedenes.
    NAMENSSCHWELLE = 2

    def __init__(self, werkzeuge=None, fixer=None):
        u"""Ohne Argumente holt sie sich beide Listen selbst.

        Die Übergabe gibt es für Prüfungen dieser Klasse: Sie sollen gegen
        erfundene Werkzeuge laufen können, nicht gegen den echten Bestand -
        der ändert sich, und ein Test, der mit dem Bestand kippt, prüft den
        Bestand statt die Logik.
        """
        if werkzeuge is None or fixer is None:
            from . import werkzeuge as _w, fixer as _f
            werkzeuge = list(_w()) if werkzeuge is None else werkzeuge
            fixer = list(_f()) if fixer is None else fixer
        self.alle = list(werkzeuge) + list(fixer)

    # ------------------------------------------------------------- Zerlegung
    @staticmethod
    def _teile(name):
        u"""Ein Name in seine bedeutungstragenden Wortteile.

        ``test_tote_importe`` und ``fix-importe`` sollen sich treffen, also
        wird an allem getrennt, was kein Buchstabe ist, und die Füllwörter
        fliegen raus.
        """
        roh = re.split(r"[^a-zA-ZäöüÄÖÜß0-9]+", (name or "").lower())
        return {t for t in roh if len(t) > 2 and t not in FUELLWOERTER}

    # ---------------------------------------------------------------- Ebenen
    def _genannt(self, kennung):
        u"""Ebene 1: Das Werkzeug nennt diesen Befund ausdrücklich."""
        k = (kennung or "").lower()
        treffer = []
        for w in self.alle:
            behebt = getattr(w, "behebt", ()) or ()
            if any(k == str(b).lower() for b in behebt):
                treffer.append(w)
        return treffer

    def _slug_steckt_drin(self, kennung):
        u"""Ebene 1b: Der Name enthält den Slug des Werkzeugs vollständig.

        ``test_tote_importe`` enthält ``tote-importe`` - nur mit Unterstrich
        statt Bindestrich. Das ist kein Raten mehr, sondern ein Treffer, und er
        gehört deshalb zu ``sicher``.

        Aufgefallen beim ersten Anschluss an einen Testlauf (25.08.2026): Ohne
        diese Ebene landete ausgerechnet ``tote-importe`` unter „Vermutlich
        verwandt", während der Testname es wörtlich enthielt. Solange
        ``behebt`` an den Werkzeugen nicht gepflegt ist, trägt sonst nur die
        Namensähnlichkeit - und die traut sich zu Recht nichts zu.
        """
        k = re.sub(r"[^a-z0-9]+", "_", (kennung or "").lower())
        treffer = []
        for w in self.alle:
            slug = re.sub(r"[^a-z0-9]+", "_", getattr(w, "slug", "").lower())
            # Auf Wortgrenzen, sonst trifft „importe" in „reimportest".
            if slug and re.search(r"(^|_)%s(_|$)" % re.escape(slug), k):
                treffer.append(w)
        return treffer

    def _ueber_kriterium(self, nummer):
        u"""Ebene 2: dieselbe Nummer des Auftrags-Kriteriums."""
        if not nummer:
            return []
        return [w for w in self.alle if getattr(w, "kriterium", 0) == nummer]

    def _ueber_namen(self, kennung, titel=""):
        u"""Ebene 3: Namensähnlichkeit - ausdrücklich eine Vermutung.

        Sortiert nach Anzahl gemeinsamer Wortteile, damit der plausibelste
        Treffer oben steht. Bei Gleichstand entscheidet der Name, damit die
        Reihenfolge zwischen zwei Läufen gleich bleibt - sonst sähe ein
        Testbericht bei jedem Lauf anders aus.
        """
        gesucht = self._teile(kennung) | self._teile(titel)
        if not gesucht:
            return []
        bewertet = []
        for w in self.alle:
            eigen = self._teile(getattr(w, "slug", "")) | self._teile(getattr(w, "titel", ""))
            gemeinsam = len(gesucht & eigen)
            if gemeinsam >= self.NAMENSSCHWELLE:
                bewertet.append((gemeinsam, getattr(w, "slug", ""), w))
        bewertet.sort(key=lambda x: (-x[0], x[1]))
        return [w for _n, _s, w in bewertet]

    # ---------------------------------------------------------------- Antwort
    def fuer(self, kennung, kriterium=0, titel="", grenze=4):
        u"""``{"sicher": [...], "vermutlich": [...]}`` - beides Werkzeug-Objekte.

        ``sicher`` sind Ebene 1 und 2, ``vermutlich`` ist Ebene 3. Die Trennung
        ist wichtig: Eine geratene Empfehlung, die wie eine gesicherte aussieht,
        schickt den Leser auf die falsche Fährte - und beim zweiten Mal glaubt
        er der Zeile gar nicht mehr.

        ``grenze`` deckelt jede der beiden Listen. Wer bei einem roten Test
        zwölf Vorschläge liest, liest keinen.

        Wörterbuch gewollt: zwei benannte Listen, die als Ganzes an die
        Berichtserzeugung gehen.
        """
        sicher = self._genannt(kennung)
        gesehen = {id(w) for w in sicher}
        for w in self._slug_steckt_drin(kennung):
            if id(w) not in gesehen:
                sicher.append(w)
                gesehen.add(id(w))
        # DIE GESCHWISTER AUS DEM KRITERIUM NACH NAMENSNAEHE SORTIEREN
        # (beim ersten Lauf aufgefallen, 25.08.2026): Kriterium 5 hat fuenf
        # Werkzeuge. Unsortiert und auf vier gedeckelt fiel ausgerechnet
        # ``tote-importe`` heraus, wenn man nach „tote-importe" suchte -
        # empfohlen wurden vier Nachbarn. Eine Empfehlungsliste, die das
        # Naheliegende weglaesst, ist schlimmer als keine.
        nah = {id(w): n for n, w in enumerate(self._ueber_namen(kennung, titel))}
        geschwister = sorted(self._ueber_kriterium(kriterium),
                             key=lambda w: (nah.get(id(w), 9999),
                                            getattr(w, "slug", "")))
        for w in geschwister:
            if id(w) not in gesehen:
                sicher.append(w)
                gesehen.add(id(w))
        vermutlich = [w for w in self._ueber_namen(kennung, titel)
                      if id(w) not in gesehen]
        return {"sicher": sicher[:grenze], "vermutlich": vermutlich[:grenze]}

    def zeilen(self, kennung, kriterium=0, titel="", grenze=4):
        u"""Dasselbe als fertige Textzeilen für einen Testbericht.

        Leere Liste, wenn nichts gefunden wurde - dann hängt der Aufrufer auch
        nichts an. Eine Überschrift ohne Inhalt („Passende Werkzeuge: keine")
        ist Rauschen: Sie steht dann unter JEDEM Fehlschlag, bei dem es nichts
        zu empfehlen gibt, und das sind die meisten.
        """
        fund = self.fuer(kennung, kriterium, titel, grenze)
        if not fund["sicher"] and not fund["vermutlich"]:
            return []
        aus = []
        if fund["sicher"]:
            aus.append("Dafür gibt es bereits ein Werkzeug:")
            aus.extend(self._zeile(w) for w in fund["sicher"])
        if fund["vermutlich"]:
            aus.append("Vermutlich verwandt:")
            aus.extend(self._zeile(w) for w in fund["vermutlich"])
        return aus

    @staticmethod
    def _zeile(w):
        u"""Ein Werkzeug in einer Zeile: Kennung, was es tut, wo man es startet.

        ``tut`` ist der Text der Fixer, ``zweck`` der der Prüfwerkzeuge - beide
        Namen abfragen, statt einen davon zu erfinden. (Beim Bau hatte ich nur
        ``zweck`` gefragt und daraus geschlossen, die Fixer seien unbeschriftet;
        sie sind es nicht.)
        """
        slug = getattr(w, "slug", "?")
        # DIE ART GEHOERT DAZU (25.08.2026, beim ersten Lauf aufgefallen):
        # ``tote-importe`` gibt es ZWEIMAL - einmal als Pruefer, der findet,
        # einmal als Fixer, der entfernt. Beide gehoeren in die Empfehlung,
        # aber ohne Kennzeichnung sieht die Liste nach einer Dublette aus, und
        # wer den falschen von beiden startet, bekommt nicht, was er wollte.
        # Erkannt am ``tut``: nur Fixer fuehren es, Pruefwerkzeuge ``zweck``.
        art = "behebt" if getattr(w, "tut", "") else "findet"
        text = (getattr(w, "tut", "") or getattr(w, "zweck", "") or
                getattr(w, "titel", "") or "")
        zeile = "  %-20s [%s] %s" % (slug, art, text.strip()[:64])
        return zeile + "\n" + " " * 24 + "/hilfe/skills/?run=" + slug

    # --------------------------------------------- aus einem Testlauf lesen
    #: ``FAIL: test_tote_importe (paket.modul.Klasse.test_tote_importe)``
    MUSTER = re.compile(r"^(?:FAIL|ERROR):\s+(\w+)", re.M)

    def zu_ausgabe(self, text, grenze=3):
        u"""Empfehlungen zu den Fehlschlägen einer Testlauf-Ausgabe.

        Liest die ``FAIL:``- und ``ERROR:``-Zeilen, sucht zu jedem Namen die
        passenden Werkzeuge und gibt einen fertigen Textblock zurück - oder
        eine leere Zeichenkette, wenn nichts zu empfehlen ist.

        HÖCHSTENS DREI FEHLSCHLÄGE: Wer vierzig rote Tests hat, hat ein anderes
        Problem als fehlende Werkzeuge, und vierzig Empfehlungsblöcke machen
        die Ausgabe unlesbar. Die ersten drei sind ohnehin die, die man zuerst
        ansieht.

        KEIN KRITERIUM ZUR HAND: Aus einem Testnamen lässt sich die Nummer des
        Auftrags-Kriteriums nicht ablesen - Ebene 2 fällt hier also aus, es
        bleiben die ausdrückliche Nennung und die Namensähnlichkeit. Genau
        deshalb sollte ``behebt`` an den Werkzeugen gepflegt werden: ohne sie
        trägt hier nur das Raten.
        """
        namen, gesehen = [], set()
        for n in self.MUSTER.findall(text or ""):
            if n not in gesehen:
                gesehen.add(n)
                namen.append(n)
        bloecke = []
        for n in namen[:grenze]:
            zeilen = self.zeilen(n, kriterium=0, titel=n)
            if zeilen:
                bloecke.append(n + ":\n" + "\n".join(zeilen))
        if not bloecke:
            return ""
        strich = "=" * 70
        return ("\n" + strich + "\nWERKZEUGE, DIE DAS BEHEBEN\n" + strich
                + "\n" + "\n\n".join(bloecke) + "\n")
