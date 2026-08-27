# -*- coding: utf-8 -*-
u"""Von einem Einstieg aus verfolgen, welcher Code beteiligt ist.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „das bild soll aber nach durchlesen des Codes gezeichnet werden"
    „(oder schon mal nach dem Code mal gezeichnet worden sein)"
    „ordne sie an nach Komplexität (Anzahl der beteiligten Klassen)"

Ein Workflow ist hier kein von Hand gemalter Kasten, sondern der Weg, den
der Code nimmt: Man setzt einen Finger auf einen Einstieg — eine Route,
einen Befehl, einen Faden — und liest, was von dort aus gerufen wird.

WARUM DAS AUFRUFNETZ ALLEIN NICHT REICHT
========================================
``aufrufnetz.py`` zaehlt Aufrufe beim Namen und verwirft bewusst
``objekt.methode()``, weil der Name ``malen`` nicht sagt, WELCHE Klasse
gemeint ist. Gemessen an CamTrack (27.08.2026):

    name(...)          10.877 Aufrufe
    objekt.methode(..) 24.463 Aufrufe   <- 69 Prozent

Fuer eine Aufnahme-Kette, die fast nur aus ``self.producer.start()``
besteht, waere ein Bild ohne diese 69 Prozent kein Bild.

DIE REGEL, DIE DIESE LUECKE SCHLIESST — OHNE ZU RATEN
=====================================================
Ein Methodenname wird NUR aufgeloest, wenn ihn im ganzen Projekt genau
EINE Klasse traegt. Gemessen an CamTrack ohne den Pruefcode: 1.792 von
2.111 Namen, also 85 Prozent. (Mit Pruefcode waren es 3.432 von 3.746 —
die Doppelgaenger aus den Tests hoben die Quote scheinbar auf 92 Prozent.
Die Seite zeigt die Zahl darum selbst an, statt sie hier festzuschreiben.)

    self.zwischenlager.einmal()   ->  BlockUebernahme.einmal
                                      (``einmal`` gibt es nur dort)

    self.dings.run()              ->  offen, nicht geraten
                                      (``run`` tragen sieben Klassen)

Was mehrdeutig ist, wird NICHT verbunden, sondern unter ``offen``
gezaehlt und angezeigt. Ein Bild mit einer ehrlichen Luecke ist brauchbar;
ein Bild mit einer geratenen Kante ist es nicht — es sieht genauso aus wie
ein richtiges.

WAS DABEI HERAUSKOMMT
=====================
Je Einstieg: die beteiligten Klassen, die beruehrten Module, die Schritte
mit Datei und Zeile — und die offenen Enden. Die Anzahl der Klassen ist
das Mass fuer die Komplexitaet, nach dem die Liste sortiert wird.
"""
import ast
from pathlib import Path

from .klassenmodell import AUS

#: Pruefcode gehoert nicht in einen Weg durch das laufende System.
#:
#: Gemessen am 27.08.2026 endete die Aufnahme-Kette bei sechs Methoden von
#: ``_FakeCv2`` aus ``tests/unit/test_motion_gate.py``: Der Name
#: ``GaussianBlur`` ist im Projekt eindeutig — er gehoert nur eben einem
#: Doppelgaenger, den nie ein Dienst ruft.
OHNE = ('tests', 'test', 'testdaten')

#: Namen, die zu jeder zweiten Klasse gehoeren und darum nichts ueber den
#: Weg aussagen. Ohne diese Liste fuehrt jeder Weg ueber ``__init__``.
STUMPF = {
    '__init__', '__str__', '__repr__', '__enter__', '__exit__',
    '__len__', '__iter__', '__eq__', '__hash__', '__call__',
    'setUp', 'tearDown', 'setUpClass', 'setUpTestData',
}

#: Was Python selbst mitbringt — kein Schritt des Projekts.
EINGEBAUT = {
    'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'print', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'sum',
    'min', 'max', 'abs', 'round', 'any', 'all', 'open', 'type', 'super',
    'isinstance', 'issubclass', 'getattr', 'setattr', 'hasattr', 'repr',
    'format', 'bytes', 'frozenset', 'reversed', 'iter', 'next', 'id',
}


class Bezug:
    u"""EINE Definition im Projekt — der Ort, auf den ein Kasten zeigt."""

    __slots__ = ('name', 'art', 'klasse', 'modul', 'datei', 'zeile',
                 'knoten')

    def __init__(self, name, art, klasse, modul, datei, zeile, knoten):
        self.name = name
        #: ``'klasse'``, ``'funktion'`` oder ``'methode'``
        self.art = art
        #: Bei einer Methode: die tragende Klasse. Sonst ``''``.
        self.klasse = klasse
        self.modul = modul
        self.datei = datei
        self.zeile = zeile
        self.knoten = knoten

    @property
    def schluessel(self):
        u"""Eindeutig ueber das ganze Projekt."""
        if self.klasse:
            return '%s:%s.%s' % (self.modul, self.klasse, self.name)
        return '%s:%s' % (self.modul, self.name)

    @property
    def anzeige(self):
        u"""Was im Kasten steht."""
        if self.klasse:
            return '%s.%s' % (self.klasse, self.name)
        return self.name

    def __repr__(self):
        return '<Bezug %s>' % self.schluessel


class Verzeichnis:
    u"""Alle Definitionen des Projekts, nachschlagbar nach Namen.

    Wird EINMAL gelesen und dann von jedem Weg benutzt — sonst liest jeder
    der fuenfzig Wege das Projekt erneut.
    """

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        #: Klassenname -> Bezug
        self.klassen = {}
        #: Freier Funktionsname -> Bezug
        self.funktionen = {}
        #: Methodenname -> Liste von Bezuegen (fuer die Eindeutigkeitsprobe)
        self._methoden = {}
        #: BESITZ: Klassenname -> {feldname: Klassenname}
        #:
        #: Aus ``self.service = RecordingService(...)``. Damit loest sich
        #: ``self.service.start()`` auf, obwohl sieben Klassen ein
        #: ``start`` tragen — nicht geraten, sondern nachgelesen, wo der
        #: Code selbst hinschreibt, was in dem Feld steckt.
        #:
        #: Ohne diesen Schritt fehlte die wichtigste Kette des Projekts:
        #: ``manage.py record_streams`` ist eine duenne Huelle, die alles
        #: ueber solche Felder weiterreicht — gemessen am 27.08.2026 fiel
        #: sie mit vier beteiligten Klassen unter jede Grenze.
        self.felder = {}
        self.dateien = 0
        #: ALLE Klassen, auch namensgleiche in zwei Dateien.
        self.klassen_gesamt = 0

    def lesen(self):
        for datei in sorted(self.wurzel.rglob('*.py')):
            if any(teil in AUS or teil in OHNE for teil in datei.parts):
                continue
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8'))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            self.dateien += 1
            self._datei_lesen(baum, datei)
        return self

    def _datei_lesen(self, baum, datei):
        modul = self._modul(datei)
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                self.klassen_gesamt += 1
                self.klassen.setdefault(knoten.name, Bezug(
                    knoten.name, 'klasse', '', modul, datei,
                    knoten.lineno, knoten))
                for kind in knoten.body:
                    if isinstance(kind, (ast.FunctionDef,
                                         ast.AsyncFunctionDef)):
                        self._methoden.setdefault(kind.name, []).append(
                            Bezug(kind.name, 'methode', knoten.name, modul,
                                  datei, kind.lineno, kind))
                self._besitz_lesen(knoten)
        for knoten in baum.body:
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funktionen.setdefault(knoten.name, Bezug(
                    knoten.name, 'funktion', '', modul, datei,
                    knoten.lineno, knoten))

    def _besitz_lesen(self, klasse):
        u"""``self.feld = Klasse(...)`` einsammeln — in JEDER Methode.

        Nicht nur in ``__init__``: Ein Feld wird oft erst dort gesetzt, wo
        es gebraucht wird (``_open_hi_channel``, ``prepare``). Wer nur
        ``__init__`` liest, verliert genau die spaeten Verzweigungen.
        """
        aus = self.felder.setdefault(klasse.name, {})
        for knoten in ast.walk(klasse):
            if not isinstance(knoten, ast.Assign):
                continue
            if not (isinstance(knoten.value, ast.Call)
                    and isinstance(knoten.value.func, ast.Name)):
                continue
            typ = knoten.value.func.id
            for ziel in knoten.targets:
                if (isinstance(ziel, ast.Attribute)
                        and isinstance(ziel.value, ast.Name)
                        and ziel.value.id == 'self'):
                    aus.setdefault(ziel.attr, typ)

    def _modul(self, datei):
        try:
            rel = datei.relative_to(self.wurzel)
        except ValueError:
            return datei.stem
        return rel.as_posix()[:-3].replace('/', '.')

    # ── Nachschlagen ────────────────────────────────────────────

    def in_klasse(self, klassenname, methodenname):
        u"""Die Methode EINER bestimmten Klasse — auch wenn der Name
        mehrdeutig ist. Hier ist er es nicht: Die Klasse steht fest."""
        for bezug in self._methoden.get(methodenname, ()):
            if bezug.klasse == klassenname:
                return bezug
        return None

    def feldtyp(self, klassenname, feldname):
        u"""Was in ``self.<feldname>`` steckt — laut Code, nicht geraten."""
        return self.felder.get(klassenname, {}).get(feldname)

    def methode(self, name):
        u"""Der Bezug — aber NUR wenn genau eine Klasse den Namen traegt.

        Das ist die Stelle, an der dieses Werkzeug sich weigert zu raten.
        Bei ``run`` (sieben Klassen) kommt ``None`` zurueck, und der Weg
        bekommt ein offenes Ende statt einer erfundenen Kante.
        """
        treffer = self._methoden.get(name)
        if not treffer or len(treffer) != 1:
            return None
        return treffer[0]

    def mehrdeutig(self, name):
        return len(self._methoden.get(name, ())) > 1

    def kennzahlen(self):
        u"""NAMEN und ANZAHL sind hier nicht dasselbe (27.08.2026).

        Die Kopfzeile las sich als „587 Klassen in 587 Dateien" — eine
        Zahl, die stutzig macht und es auch verdient: Es sind 646 Klassen
        mit 587 verschiedenen NAMEN. Dass die Zahl der Namen zufaellig auf
        die Zahl der Dateien fiel, machte den Fehler erst sichtbar.

        Der Unterschied ist keine Haarspalterei: Genau an ihm haengt die
        Aufloesungsregel. Ein Name, den zwei Klassen tragen, wird nicht
        verbunden.
        """
        eindeutig = sum(1 for v in self._methoden.values() if len(v) == 1)
        return {
            'dateien': self.dateien,
            'klassen': self.klassen_gesamt,
            'klassennamen': len(self.klassen),
            'funktionen': len(self.funktionen),
            'methodennamen': len(self._methoden),
            'eindeutig': eindeutig,
        }


class Schritt:
    u"""Ein Kasten im Bild: eine Definition und wie weit sie vom Einstieg
    entfernt liegt."""

    __slots__ = ('bezug', 'tiefe')

    def __init__(self, bezug, tiefe):
        self.bezug = bezug
        self.tiefe = tiefe

    def __repr__(self):
        return '<Schritt %s @%d>' % (self.bezug.schluessel, self.tiefe)


class Kante:
    u"""Eine Linie im Bild: von wo nach wo, und warum sie da ist."""

    __slots__ = ('von', 'nach', 'grund')

    def __init__(self, von, nach, grund):
        self.von = von
        self.nach = nach
        #: ``'aufruf'`` (``name()``) oder ``'methode'`` (``x.name()``)
        self.grund = grund

    def __repr__(self):
        return '<Kante %s -> %s>' % (self.von, self.nach)


class Weg:
    u"""EIN Workflow: der Weg des Codes ab einem Einstieg."""

    def __init__(self, einstieg, start=None):
        self.einstieg = einstieg
        #: Der Bezug, bei dem der Weg anfaengt.
        #:
        #: WARUM NICHT DER NAME DES ZIELS (27.08.2026)
        #: Alle 32 Management-Befehle heissen ``handle``. Wer danach
        #: entdoppelt, behaelt EINEN Befehl und wirft 31 weg — genau so
        #: verschwand die Aufnahme-Kette (35 beteiligte Klassen) hinter
        #: ``process_faces``. Der Startbezug traegt Modul UND Klasse und
        #: ist damit ueber das Projekt eindeutig.
        self.start = start
        self.schritte = []
        self.kanten = []
        #: Namen, die nicht eindeutig aufloesbar waren.
        self.offen = []
        #: Der Weg geht weiter, als hier gezeichnet ist.
        #:
        #: Ein Bild, das seine eigene Unvollstaendigkeit verschweigt, ist
        #: schlimmer als eines mit sichtbarer Luecke: Es sieht aus wie das
        #: Ganze. Darum wird vermerkt, wenn die Tiefengrenze oder der
        #: Deckel greift und dahinter noch etwas stand.
        self.abgeschnitten = False

    @property
    def klassen(self):
        u"""Die beteiligten Klassen — das Mass fuer die Komplexitaet."""
        return sorted({s.bezug.klasse for s in self.schritte if
                       s.bezug.klasse} |
                      {s.bezug.name for s in self.schritte if
                       s.bezug.art == 'klasse'})

    @property
    def module(self):
        return sorted({s.bezug.modul for s in self.schritte})

    @property
    def tiefe(self):
        return max([s.tiefe for s in self.schritte], default=0)

    def als_dict(self):
        return {
            'einstieg': self.einstieg.als_dict(),
            'klassen': self.klassen,
            'module': self.module,
            'anzahl_klassen': len(self.klassen),
            'anzahl_schritte': len(self.schritte),
            'tiefe': self.tiefe,
            'offen': sorted(set(self.offen)),
            'abgeschnitten': self.abgeschnitten,
            'schritte': [{'name': s.bezug.anzeige,
                          'modul': s.bezug.modul,
                          'datei': str(s.bezug.datei),
                          'zeile': s.bezug.zeile,
                          'tiefe': s.tiefe} for s in self.schritte],
            'kanten': [{'von': k.von, 'nach': k.nach, 'grund': k.grund}
                       for k in self.kanten],
        }


class Wegsucher:
    u"""Verfolgt einen Einstieg durch den Code.

    ``tiefe`` begrenzt, wie weit verfolgt wird. Ohne Grenze laeuft jeder
    Weg irgendwann bei den Hilfsfunktionen zusammen und jedes Bild sieht
    aus wie jedes andere — gemessen an CamTrack liegt ab Tiefe sieben
    praktisch das halbe Projekt in jedem Weg.
    """

    def __init__(self, verzeichnis, tiefe=5, hoechstens=90):
        self.verzeichnis = verzeichnis
        self.tiefe = tiefe
        #: Reissleine gegen Wege, die alles einsammeln.
        self.hoechstens = hoechstens

    def verfolgen(self, einstieg, start):
        u"""Ab ``start`` (einem Bezug) den Weg ablaufen."""
        weg = Weg(einstieg, start)
        gesehen = {start.schluessel}
        weg.schritte.append(Schritt(start, 0))
        rand = [(start, 0)]
        while rand:
            bezug, tief = rand.pop(0)
            if len(weg.schritte) >= self.hoechstens:
                weg.abgeschnitten = True
                continue
            if tief >= self.tiefe:
                # OHNE `weg`: Hier wird nur nachgesehen, ob es weiterginge.
                # Mit `weg` landeten die mehrdeutigen Namen dieser Stufe in
                # `offen`, obwohl sie gar nicht mehr betrachtet wird.
                if self._gerufene(bezug, None):
                    weg.abgeschnitten = True
                continue
            for ziel, grund in self._gerufene(bezug, weg):
                weg.kanten.append(Kante(bezug.anzeige, ziel.anzeige, grund))
                if ziel.schluessel in gesehen:
                    continue
                gesehen.add(ziel.schluessel)
                weg.schritte.append(Schritt(ziel, tief + 1))
                rand.append((ziel, tief + 1))
        return weg

    @staticmethod
    def _rumpf(bezug):
        u"""Welche Knoten gehoeren zu diesem Kasten?

        EIN KLASSENKASTEN IST DER KONSTRUKTOR, NICHT DIE GANZE KLASSE
        =============================================================
            „warum so viele Aufrufe aus dem Konstruktor des
             LiveOrchestrator?" (Edgar, 27.08.2026)

        Weil es gar nicht der Konstruktor war. Fuer eine Klasse lag hier
        der ganze ``ClassDef``, und ``ast.walk`` lief damit ueber JEDE
        Methode. Der Kasten ``LiveOrchestrator`` zeigte darum 26 Kanten —
        darunter ``stop``, ``start_async`` und ``_publish_offline``, die
        beim Erzeugen niemand ruft.

        Gemessen: der Konstruktor allein ruft **9**. Siebzehn Kanten waren
        erfunden, und sie liessen ein sauber gebautes Objekt aussehen wie
        einen Selbstbedienungsladen.

        ``Klasse()`` ruft ``__init__``. Alles andere ist nur erreichbar,
        wenn jemand die Methode ruft — und dann steht diese Methode als
        eigener Kasten im Bild, mit ihrer eigenen Kante.

        Mitgenommen wird ausserdem, was auf KLASSENEBENE steht
        (``vorgabe = Fabrik()``): Das laeuft beim Import, also erst recht
        vor jedem Gebrauch.
        """
        if bezug.art != 'klasse':
            return [bezug.knoten]
        aus = [k for k in bezug.knoten.body
               if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for k in bezug.knoten.body:
            if (isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and k.name == '__init__'):
                aus.append(k)
        return aus

    def _gerufene(self, bezug, weg):
        u"""Was in diesem Rumpf gerufen wird — aufgeloest, soweit belegbar.

        ``weg`` darf ``None`` sein: Dann wird nur geantwortet, OB etwas
        gerufen wird, ohne die offenen Enden mitzuschreiben.
        """
        aus = []
        rumpf = self._rumpf(bezug)
        oertlich = {}
        for teil in rumpf:
            oertlich.update(self._oertliche_typen(teil))
        for knoten in [k for teil in rumpf for k in ast.walk(teil)]:
            if not isinstance(knoten, ast.Call):
                continue
            ziel = grund = None
            if isinstance(knoten.func, ast.Name):
                name = knoten.func.id
                if name in EINGEBAUT:
                    continue
                ziel = (self.verzeichnis.klassen.get(name) or
                        self.verzeichnis.funktionen.get(name))
                grund = 'aufruf'
            elif isinstance(knoten.func, ast.Attribute):
                name = knoten.func.attr
                if name in STUMPF or name in EINGEBAUT:
                    continue
                ziel = self._ueber_besitz(bezug, knoten.func, oertlich)
                grund = 'besitz'
                if ziel is None:
                    ziel = self.verzeichnis.methode(name)
                    grund = 'methode'
                if (ziel is None and weg is not None
                        and self.verzeichnis.mehrdeutig(name)):
                    weg.offen.append(name)
            if ziel is not None and ziel.schluessel != bezug.schluessel:
                aus.append((ziel, grund))
        return aus

    def _ueber_besitz(self, bezug, funk, oertlich):
        u"""``self.service.start()`` und ``p = Producer(); p.start()``.

        Beides steht im Code: einmal als Feldzuweisung in der Klasse,
        einmal als Zuweisung im selben Rumpf. Kein Raten, keine
        Typermittlung ueber Bibliotheken.
        """
        traeger = None
        if (isinstance(funk.value, ast.Attribute)
                and isinstance(funk.value.value, ast.Name)
                and funk.value.value.id == 'self' and bezug.klasse):
            traeger = self.verzeichnis.feldtyp(bezug.klasse,
                                               funk.value.attr)
        elif isinstance(funk.value, ast.Name):
            traeger = oertlich.get(funk.value.id)
        if not traeger:
            return None
        return self.verzeichnis.in_klasse(traeger, funk.attr)

    @staticmethod
    def _oertliche_typen(rumpf):
        u"""``bild = Klassenbild(...)`` -> ``{'bild': 'Klassenbild'}``."""
        aus = {}
        for knoten in ast.walk(rumpf):
            if not isinstance(knoten, ast.Assign):
                continue
            if not (isinstance(knoten.value, ast.Call)
                    and isinstance(knoten.value.func, ast.Name)):
                continue
            for ziel in knoten.targets:
                if isinstance(ziel, ast.Name):
                    aus.setdefault(ziel.id, knoten.value.func.id)
        return aus
