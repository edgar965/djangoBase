# -*- coding: utf-8 -*-
u"""Reihenfolge - die Nummern-Spalte der Testcase-Tabellen.

    „mach eine Spalte bei den tests mit Nummer […] Die enthält zahlen,
    aufsteigend, die man ändern kann, dann verschieben sich die tests in der
    Tabelle." (Edgar, 17.08.2026)

Die Nummer ist keine Kennung, sondern ein PLATZ: Wer „7" in die Zeile eines
Tests schreibt, will ihn an die siebte Stelle. Die anderen ruecken auf, und die
Reihenfolge haelt ueber Reloads.

WO SIE GILT
===========
INNERHALB des Bereichs. Die Tabelle ist nach Bereich gegliedert (Spalte plus
Abschnittszeile mit eigenem Sammellauf); eine Nummer, die einen Fall aus seinem
Abschnitt heraushebt, wuerde diese Gliederung zerlegen. Sortiert wird also nach
``(Bereich, Nummer, Test-ID)``.

WO SIE LIEGT
============
``BASE_DIR/logs/testreihenfolge.json`` — neben der Laufzeit-Historie, aus
demselben Grund keine Datenbank: Die Seite muss auch dann funktionieren, wenn
die Testdatenbank gerade neu aufgebaut wird, und ein ``migrate`` soll fuer eine
Anzeige-Einstellung nicht noetig sein.

WAS SIE NICHT IST
=================
Keine Ausfuehrungsreihenfolge. ``manage.py test`` bestimmt selbst, in welcher
Folge es faehrt; hier geht es um die ANZEIGE. Alles andere zu behaupten waere
eine Zusage, die das Werkzeug nicht halten kann.
"""
import json
import logging
from pathlib import Path

from django.conf import settings

__all__ = ["Reihenfolge"]

log = logging.getLogger("djangobase.tests")


class Reihenfolge:
    """Vom Nutzer gesetzte Plaetze je Testcase - als JSON im Projekt."""

    DATEINAME = "testreihenfolge.json"
    #: Ohne eigenen Platz stehen Faelle hinten (in ihrer Grundordnung).
    OHNE = 10 ** 6

    def __init__(self, pfad=None):
        self.pfad = Path(pfad) if pfad else self._vorgabe()
        self._raenge = None

    @staticmethod
    def _vorgabe():
        basis = Path(getattr(settings, "BASE_DIR", "."))
        ordner = basis / "logs"
        return (ordner if ordner.is_dir() else basis) / Reihenfolge.DATEINAME

    # ------------------------------------------------------------------ Lesen

    @property
    def raenge(self):
        if self._raenge is None:
            self._raenge = self._laden()
        return self._raenge

    def _laden(self):
        try:
            daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        except OSError:
            # stumm gewollt: Vor der ersten Aenderung gibt es die Datei nicht.
            return {}
        except ValueError:
            log.warning("Test-Reihenfolge %s ist nicht lesbar — sie wird "
                        "verworfen; die Tabelle zeigt die Grundordnung",
                        self.pfad)
            return {}
        raenge = daten.get("raenge") if isinstance(daten, dict) else None
        if not isinstance(raenge, dict):
            return {}
        aus = {}
        for kennung, platz in raenge.items():
            try:
                aus[str(kennung)] = int(platz)
            except (TypeError, ValueError):
                continue
        return aus

    def platz(self, test_id):
        u"""Der Platz eines Falls - :data:`OHNE`, wenn keiner gesetzt ist."""
        return self.raenge.get(str(test_id or ""), self.OHNE)

    def nummer(self, test_id):
        u"""Der Platz, oder ``None`` - für die Anzeige im Eingabefeld."""
        wert = self.raenge.get(str(test_id or ""))
        return wert if isinstance(wert, int) else None

    # -------------------------------------------------------------- Schreiben

    def setzen(self, test_id, nummer, gruppe):
        u"""Einen Fall an Platz ``nummer`` einordnen; ``gruppe`` rueckt auf.

        ``gruppe`` ist die Liste der Kennungen IN DER GERADE ANGEZEIGTEN
        Reihenfolge (die Seite schickt sie mit). Der Server ordnet daraus neu
        und speichert die Plaetze 1..n — damit stimmt die gespeicherte Ordnung
        mit dem ueberein, was der Nutzer vor sich hatte, ohne dass hier die
        Gruppierung der Seite nachgebaut werden muss.

        Zurueck kommt die neue Liste. Ist ``test_id`` nicht in ``gruppe``,
        passiert nichts — dann meinte die Anfrage etwas anderes als die Ansicht.
        """
        kennung = str(test_id or "")
        reihe = [str(g) for g in (gruppe or []) if g]
        if kennung not in reihe:
            return []
        try:
            ziel = max(1, min(int(nummer), len(reihe)))
        except (TypeError, ValueError):
            return []
        reihe.remove(kennung)
        reihe.insert(ziel - 1, kennung)
        for platz, k in enumerate(reihe, start=1):
            self.raenge[k] = platz
        self.schreiben()
        return reihe

    def schreiben(self):
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            self.pfad.write_text(
                json.dumps({"raenge": self.raenge}, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except OSError:
            log.exception("Test-Reihenfolge %s nicht schreibbar — die Nummer "
                          "gilt nur bis zum nächsten Laden", self.pfad)

    def umhaengen(self, alt_praefix, neu_praefix):
        u"""Plaetze mitnehmen, wenn eine Testdatei umzieht.

        Sonst stuende der Fall nach einem Kategorie- oder Bereichswechsel wieder
        hinten — dieselbe Falle wie bei der Laufzeit-Historie.
        """
        if not alt_praefix or alt_praefix == neu_praefix:
            return
        umzug = {k: v for k, v in self.raenge.items()
                 if k.startswith(alt_praefix + ".")}
        if not umzug:
            return
        for alt, platz in umzug.items():
            self.raenge.pop(alt, None)
            self.raenge[neu_praefix + alt[len(alt_praefix):]] = platz
        self.schreiben()
