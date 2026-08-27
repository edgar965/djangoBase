# -*- coding: utf-8 -*-
u"""Die Workflows des Projekts — ermittelt, sortiert, gruppiert.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „die workflows sollst du aber ermitteln, schau dir jede Seite durch
     und ermittle 20-50 Workflows"
    „ordne sie an nach Komplexität (Anzahl der beteiligten Klassen)"

``einstiege.py`` findet, WO etwas anfaengt. ``wegenetz.py`` verfolgt, WAS
von dort aus passiert. Hier kommt beides zusammen und wird zu einer Liste,
die man von oben lesen kann.

DIE SORTIERUNG IST DIE AUSSAGE
==============================
Nach Anzahl der beteiligten Klassen. Das ist nicht dasselbe wie „wie oft
benutzt" oder „wie wichtig" — es ist das Mass dafuer, wie viel man
verstehen muss, um diesen einen Vorgang zu aendern. Genau die Frage, mit
der man vor einem fremden Projekt sitzt.

Ein Einstieg mit einer beteiligten Klasse ist eine Seite, die eine Vorlage
ausliefert. Einer mit dreissig ist eine Kette quer durch das Projekt — und
der gehoert ins Bild.

WARUM NICHT ALLE 313 EINSTIEGE INS BILD KOMMEN
==============================================
Weil die meisten nichts erzaehlen. ``GRENZE`` schneidet ab: Was weniger
als eine Handvoll Klassen beruehrt, ist kein Workflow, sondern ein
Handgriff. Was uebrig bleibt, sind die 20 bis 50, nach denen gefragt war.
"""
from pathlib import Path

from .ablage import Speicher
from .einstiege import Einstiegssucher
from .wegenetz import Verzeichnis, Wegsucher

#: Ab wie vielen beteiligten Klassen ein Einstieg als Workflow zaehlt.
GRENZE = 5

#: Hoechstens so viele in der Liste — sonst ist es wieder eine Tapete.
DECKEL = 50

#: Die Reiter der Seite. Ein Einstieg landet im ERSTEN Reiter, dessen
#: Muster auf seine Adresse passt; ``''`` faengt den Rest.
REITER = (
    ('aufnahme', u'Aufnahme und Erkennung',
     ('record_streams', 'live_detect', 'process_faces', 'trt_warmup',
      'capture_snapshots', 'faden:')),
    ('ansehen', u'Ansehen und Abspielen',
     ('recordings', 'kameras', 'live/', 'snippet', 'schnipsel', 'media',
      'treffer', 'analyze-recording', 'calendar')),
    ('personen', u'Personen und Treffer',
     ('persons', 'personen', 'sighting', 'cluster', 'merge', 'enrollment',
      'foto', 'reembed', 'recluster', 'recognition', 'backfill')),
    ('verwalten', u'Einrichten und Verwalten',
     ('settings', 'cameras', 'storage', 'help', 'hilfe', 'test', 'cleanup',
      'export', 'marzahn', 'fernzugriff', 'gesundheit', 'cron')),
)


class Workflowliste:
    u"""Alle Workflows eines Projekts, sortiert nach Komplexitaet."""

    def __init__(self, wurzel, tiefe=5, grenze=GRENZE, deckel=DECKEL):
        self.wurzel = wurzel
        self.tiefe = tiefe
        self.grenze = grenze
        self.deckel = deckel
        self.wege = []
        self.verworfen = 0
        self.kennzahlen = {}
        #: Bleibt erhalten, damit die Ablauf-Ansicht Ziele aufloesen kann,
        #: ohne das Projekt ein zweites Mal zu lesen.
        self.verzeichnis = None

    def lesen(self):
        verzeichnis = Verzeichnis(self.wurzel).lesen()
        self.verzeichnis = verzeichnis
        self.kennzahlen = verzeichnis.kennzahlen()
        sucher = Wegsucher(verzeichnis, tiefe=self.tiefe)
        alle = []
        for einstieg in Einstiegssucher(self.wurzel).alle():
            start = self._start(verzeichnis, einstieg)
            if start is None:
                continue
            weg = sucher.verfolgen(einstieg, start)
            if len(weg.klassen) < self.grenze:
                self.verworfen += 1
                continue
            alle.append(weg)
        alle.sort(key=lambda w: (-len(w.klassen), -len(w.schritte),
                                 w.einstieg.titel))
        self.wege = self._entdoppeln(alle)[:self.deckel]
        self.kennzahlen['einstiege'] = len(alle) + self.verworfen
        self.kennzahlen['workflows'] = len(self.wege)
        return self

    @staticmethod
    def _start(verzeichnis, einstieg):
        u"""Der Bezug, bei dem das Verfolgen anfaengt."""
        name = einstieg.ziel
        if einstieg.art in ('befehl', 'faden'):
            for kandidat in verzeichnis._methoden.get(name, ()):
                if kandidat.datei == einstieg.datei:
                    return kandidat
            return None
        return (verzeichnis.funktionen.get(name) or
                verzeichnis.klassen.get(name))

    @staticmethod
    def _entdoppeln(wege):
        u"""Zwei Routen auf dieselbe View sind EIN Workflow.

        ``/recordings/<pk>/media/`` und ``/recordings/live/<slug>/media/``
        laufen durch denselben Code. Beide zu zeigen fuellt die Liste,
        ohne etwas zu erklaeren — die zweite Adresse steht beim ersten
        Eintrag dabei.
        """
        gesehen = {}
        aus = []
        for weg in wege:
            schluessel = (weg.start.schluessel if weg.start else
                          '%s:%s' % (weg.einstieg.art, weg.einstieg.ziel))
            if schluessel in gesehen:
                gesehen[schluessel].setdefault('auch', []).append(
                    weg.einstieg.titel)
                continue
            weg.auch = []
            gesehen[schluessel] = {'auch': weg.auch}
            aus.append(weg)
        return aus

    # ── Gliederung ──────────────────────────────────────────────

    def reiter(self):
        u"""Die Wege auf die Reiter verteilt, Reihenfolge erhalten."""
        faecher = [(kuerzel, titel, []) for kuerzel, titel, _ in REITER]
        faecher.append(('rest', u'Weitere Wege', []))
        for weg in self.wege:
            faecher[self._fach(weg)][2].append(weg)
        return [f for f in faecher if f[2]]

    @staticmethod
    def _fach(weg):
        adresse = weg.einstieg.adresse.lower()
        marke = ('faden:' + adresse) if weg.einstieg.art == 'faden' \
            else adresse
        for stelle, (_kuerzel, _titel, muster) in enumerate(REITER):
            if any(m in marke for m in muster):
                return stelle
        return len(REITER)

    def als_dict(self):
        return {
            'kennzahlen': self.kennzahlen,
            'verworfen': self.verworfen,
            'reiter': [{'kuerzel': k, 'titel': t,
                        'wege': [w.als_dict() for w in wege]}
                       for k, t, wege in self.reiter()],
        }


class Workflowspeicher(Speicher):
    u"""Die ermittelten Wege — einmal gelesen, dann gemerkt.

    STEHT HIER, NICHT IN DER ANSICHT (27.08.2026)
    =============================================
    Zuerst lag diese Klasse in ``views/workflows.py``, weil nur die Seite
    sie brauchte. Dann brauchte ``skills/testdeckung.py`` dieselben Wege —
    und ein Werkzeug, das eine Ansicht importiert, steht auf dem Kopf.

    Der Ausweg wäre ein zweiter Speicher gewesen. Zwei Speicher für
    dieselbe Sache laufen auseinander, sobald einer angefasst wird; das
    hat dieses Projekt an der Live-Kachel Wochen gekostet.

    Gemessen: ``testdeckung`` fiel damit von 34 s auf unter eine Sekunde,
    sobald die Wege schon einmal gelesen waren.
    """

    bereich = 'workflows'

    #: Aendert sich einer dieser vier, ist das gespeicherte Bild ueberholt
    #: und wird beim naechsten Aufschlagen NEU gerechnet — ohne dass
    #: jemand einen Knopf druecken muss.
    quellen = (__file__,
               str(Path(__file__).with_name('wegenetz.py')),
               str(Path(__file__).with_name('einstiege.py')),
               str(Path(__file__).with_name('workflowbild.py')))

    @staticmethod
    def bauen(wurzel):
        return Workflowliste(wurzel).lesen()
