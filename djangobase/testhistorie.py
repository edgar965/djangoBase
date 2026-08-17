# -*- coding: utf-8 -*-
u"""Testhistorie - wie lange jeder Testcase in den letzten Laeufen gebraucht hat.

WOZU (Ansage Edgar, 17.08.2026)
===============================
    „bei jedem Testcase soll auch die Performance aufnotiert werden, die letzten
    4 Laeufe mit datum /Uhrzeit - im djangoBase UI: /tests/"

Eine einzelne Laufzeit sagt wenig. Erst die Reihe zeigt, was passiert ist: Ein
Test, der gestern 0,3 s brauchte und heute 4 s, hat etwas mitbekommen - eine
Abfrage je Zeile, ein neuer Netzaufruf, ein Index weg. Deshalb stehen VIER Laeufe
mit Datum und Uhrzeit neben jedem Testcase, nicht nur der letzte.

WO ES LIEGT
===========
``BASE_DIR/logs/testhistorie.json`` - im Projekt, nie in System-Temp (harte
Vorgabe: rund 100 GB Datenmuell auf C: durch Temp-Dateien). Keine Datenbank:
Die Seite muss auch dann Zahlen zeigen, wenn die Testdatenbank gerade neu
aufgebaut wird - und die Historie soll einen ``migrate`` nicht brauchen.

WARUM VIER UND NICHT ALLE
=========================
Vier Werte passen in eine Tabellenzeile, ohne sie zu sprengen, und decken den
Fall ab, um den es geht („seit wann ist der langsam?"). Eine vollstaendige
Historie waere eine Zeitreihen-Datenbank; das ist eine andere Aufgabe.
"""
import json
from pathlib import Path

from django.conf import settings

__all__ = ["Testhistorie"]


class Testhistorie:
    """Die letzten Laufzeiten je Testcase und je Suite - als JSON im Projekt."""

    #: So viele Laeufe werden je Eintrag behalten.
    TIEFE = 4
    DATEINAME = "testhistorie.json"

    def __init__(self, pfad=None):
        self.pfad = Path(pfad) if pfad else self._vorgabe()
        self._daten = None

    @staticmethod
    def _vorgabe():
        basis = Path(getattr(settings, "BASE_DIR", "."))
        ordner = basis / "logs"
        return (ordner if ordner.is_dir() else basis) / Testhistorie.DATEINAME

    # ------------------------------------------------------------------ Lesen

    @property
    def daten(self):
        if self._daten is None:
            self._daten = self._laden()
        return self._daten

    def _laden(self):
        try:
            rohtext = self.pfad.read_text(encoding="utf-8")
        except OSError:
            # stumm gewollt: Beim ersten Lauf gibt es die Datei nicht — das ist
            # der Normalfall und keine Stoerung.
            return {"tests": {}, "suiten": {}}
        try:
            daten = json.loads(rohtext)
        except ValueError:
            # Eine beschaedigte Historie darf die Seite nicht kosten. Sie wird
            # verworfen und beim naechsten Lauf neu aufgebaut; die Meldung geht
            # ins Log, damit es nicht lautlos passiert.
            import logging
            logging.getLogger("django").warning(
                "Testhistorie %s ist nicht lesbar — sie wird neu aufgebaut",
                self.pfad)
            return {"tests": {}, "suiten": {}}
        daten.setdefault("tests", {})
        daten.setdefault("suiten", {})
        return daten

    # --------------------------------------------------------------- Schreiben

    def merken(self, zeit, dauern, suite=None):
        u"""Einen Lauf eintragen.

        ``zeit``   Zeichenkette „17.08.2026 16:55:03" (die Seite zeigt sie so an)
        ``dauern`` ``{test_id: sekunden}`` - aus der ``--durations``-Ausgabe
        ``suite``  ``{"slug","name","dauer","ok","tests"}`` des Sammellaufs
        """
        for test_id, sek in (dauern or {}).items():
            reihe = self.daten["tests"].setdefault(test_id, [])
            reihe.insert(0, {"zeit": zeit, "dauer": round(float(sek), 3)})
            del reihe[self.TIEFE:]
        if suite:
            reihe = self.daten["suiten"].setdefault(suite["slug"], [])
            reihe.insert(0, {"zeit": zeit, "dauer": round(float(suite.get("dauer") or 0), 1),
                             "ok": bool(suite.get("ok")),
                             "tests": int(suite.get("tests") or 0)})
            del reihe[self.TIEFE:]
        self.schreiben()

    def schreiben(self):
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            self.pfad.write_text(json.dumps(self.daten, ensure_ascii=False,
                                            indent=1), encoding="utf-8")
        except OSError:
            import logging
            logging.getLogger("django").exception(
                "Testhistorie %s nicht schreibbar — die Laufzeiten dieses "
                "Durchgangs sind verloren", self.pfad)

    # ---------------------------------------------------------------- Abfragen

    def laeufe(self, test_id):
        """Die letzten Laeufe eines Testcases, neuester zuerst."""
        return self.daten["tests"].get(test_id, [])

    def suitenlaeufe(self, slug):
        return self.daten["suiten"].get(slug, [])

    def letzte(self, test_id):
        """Sekunden des letzten Laufs - oder None."""
        reihe = self.laeufe(test_id)
        return reihe[0]["dauer"] if reihe else None

    def schnitt(self, test_id):
        """Mittel ueber die vorhandenen Laeufe - oder None."""
        reihe = self.laeufe(test_id)
        if not reihe:
            return None
        return round(sum(x["dauer"] for x in reihe) / len(reihe), 3)

    def trend(self, test_id):
        u"""Wie sich der letzte Lauf zum Mittel der VORIGEN verhaelt.

        Zurueck kommt ``(text, klasse)``. Ohne Vergleichswert bleibt es leer -
        eine Prozentzahl aus einem einzigen Lauf waere erfunden.
        """
        reihe = self.laeufe(test_id)
        if len(reihe) < 2:
            return "", ""
        vorher = [x["dauer"] for x in reihe[1:]]
        mittel = sum(vorher) / len(vorher)
        if mittel <= 0:
            return "", ""
        anteil = (reihe[0]["dauer"] - mittel) / mittel * 100
        if abs(anteil) < 25:            # Rauschen, nicht Trend
            return "", ""
        klasse = "schlecht" if anteil > 0 else "gut"
        return "%+.0f %%" % anteil, klasse
