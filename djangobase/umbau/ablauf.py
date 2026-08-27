# -*- coding: utf-8 -*-
u"""Der Ablauf EINER Funktion: Reihenfolge, Verzweigungen, Ausgaenge.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „das ist auch nicht verständlich, ich brauche einen klaren Workflow,
     was in welcher Reihenfolge gemacht wird. Kannst du nicht sowas wie
     ein Ablaufdiagramm machen mit Entscheidungsbäumen?"

Berechtigt. ``wegenetz.py`` beantwortet die Frage „was ist von hier aus
erreichbar" und ordnet nach ENTFERNUNG. Das ist eine Landkarte, kein
Ablauf: Zwei Kaesten nebeneinander sagen nicht, welcher zuerst kommt,
und eine Bedingung sieht darin aus wie ein Aufruf.

WAS HIER ANDERS IST
===================
Gelesen wird der Rumpf in seiner REIHENFOLGE, mit den Verzweigungen, die
darin stehen::

    def run(self):
        cap = cv2.VideoCapture(self.recording_path)
        if not cap.isOpened():                 -> Frage
            return {'error': ...}              ->   ja: Ende
        started = time.monotonic()             -> Schritt
        try:                                   -> Absicherung
            self._read_all(cap)                ->   Schritt
        finally:
            cap.release()                      ->   danach immer
        self._flush_all()                      -> Schritt
        return self._result(duration)          -> Ende

Damit beantwortet das Bild die Frage, die man vor fremdem Code
tatsaechlich hat: Was passiert zuerst, wo entscheidet sich etwas, und wie
kann das hier ausgehen?

WAS ES NICHT KANN — UND WARUM DAS SO BLEIBT
===========================================
Es folgt nicht in jede gerufene Funktion hinein. Ein Ablauf, der alles
einsetzt, ist nach drei Ebenen wieder die Tapete, aus der er entstanden
ist. Ein Schritt, der etwas Eigenes ruft, traegt darum ein Ziel — man
klickt es an und sieht DESSEN Ablauf.
"""
import ast

#: Aufrufe, die nichts ueber den Ablauf sagen.
#:
#: AUSGABE IST KEINE HANDLUNG (27.08.2026)
#: ======================================
#: Im ersten Aktivitaetsbild von `backfill_soft_biometrics` stand
#: neunmal „stdout: write". Das ist richtig gelesen und trotzdem falsch:
#: Wer wissen will, was der Befehl TUT, interessiert sich nicht dafuer,
#: dass er dabei etwas auf die Konsole schreibt.
#:
#: Dasselbe gilt fuer das Protokoll und fuer Rechnerei wie `max`/`min`.
STUMM = ('len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set',
         'print', 'isinstance', 'getattr', 'hasattr', 'sorted', 'enumerate',
         'range', 'append', 'get', 'format', 'join', 'strip', 'split',
         'write', 'flush', 'info', 'debug', 'warning', 'error', 'exception',
         'max', 'min', 'abs', 'round', 'sum', 'any', 'all', 'items',
         'keys', 'values', 'add', 'update', 'pop', 'setdefault')

#: Hoechstlaenge einer Beschriftung.
BREIT = 58


class Knoten:
    u"""Gemeinsame Grundform aller Ablauf-Teile."""

    art = 'knoten'

    def __init__(self, text, zeile, ziel='', aufruf='', empfaenger='',
                 merkmal=''):
        self.text = text
        self.zeile = zeile
        #: ``Klasse.methode`` — wenn dieser Schritt etwas Eigenes ruft.
        self.ziel = ziel
        #: Der gerufene Name (``prepare``) — Grundlage der Beschriftung.
        self.aufruf = aufruf
        #: Worauf gerufen wurde (``service``), ohne ``self``.
        self.empfaenger = empfaenger
        #: Das erste Argument, wenn es ein einfacher Name ist.
        #:
        #: WAS ZWEI GLEICHE KAESTEN UNTERSCHEIDET (27.08.2026)
        #: ==================================================
        #: ``signal.signal(signal.SIGINT, …)`` und ``signal.signal(
        #: signal.SIGTERM, …)`` standen beide als „signal: signal"
        #: untereinander — zwei Kaesten, die dasselbe behaupteten.
        #:
        #: Was sie unterscheidet, steht im ERSTEN Argument. Es wird nur
        #: mitgenommen, wenn es ein Name oder eine Zeichenkette ist:
        #: Ein ganzer Ausdruck waere wieder Quelltext im Kasten.
        self.merkmal = merkmal

    def als_dict(self):
        return {'art': self.art, 'text': self.text, 'zeile': self.zeile,
                'ziel': self.ziel, 'aufruf': self.aufruf,
                'empfaenger': self.empfaenger, 'merkmal': self.merkmal}

    def __repr__(self):
        return '<%s %s>' % (self.art, self.text[:30])


class Schritt(Knoten):
    u"""Etwas wird getan."""
    art = 'schritt'


class Ende(Knoten):
    u"""Hier ist der Ablauf zu Ende — ``return``, ``raise``, ``break``."""
    art = 'ende'


class Frage(Knoten):
    u"""Eine Entscheidung mit zwei Wegen."""

    art = 'frage'

    def __init__(self, text, zeile):
        Knoten.__init__(self, text, zeile)
        self.ja = []
        self.nein = []

    def als_dict(self):
        d = Knoten.als_dict(self)
        d['ja'] = [k.als_dict() for k in self.ja]
        d['nein'] = [k.als_dict() for k in self.nein]
        return d


class Wiederholung(Knoten):
    u"""``for`` oder ``while`` — der Rumpf laeuft mehrfach."""

    art = 'schleife'

    def __init__(self, text, zeile):
        Knoten.__init__(self, text, zeile)
        self.rumpf = []

    def als_dict(self):
        d = Knoten.als_dict(self)
        d['rumpf'] = [k.als_dict() for k in self.rumpf]
        return d


class Absicherung(Knoten):
    u"""``try`` mit ``except``/``finally`` — was schiefgehen darf."""

    art = 'absicherung'

    def __init__(self, text, zeile):
        Knoten.__init__(self, text, zeile)
        self.rumpf = []
        self.sonst = []      # except-Zweige
        self.immer = []      # finally

    def als_dict(self):
        d = Knoten.als_dict(self)
        d['rumpf'] = [k.als_dict() for k in self.rumpf]
        d['sonst'] = [k.als_dict() for k in self.sonst]
        d['immer'] = [k.als_dict() for k in self.immer]
        return d


class Ablauf:
    u"""Liest EINEN Funktionsrumpf als Folge von Knoten.

        >>> Ablauf(bezug).lesen().knoten      # doctest: +SKIP
        [<schritt ...>, <frage ...>, <ende ...>]
    """

    def __init__(self, bezug, verzeichnis=None):
        self.bezug = bezug
        #: Nur zum Aufloesen der Ziele — darf fehlen.
        self.verzeichnis = verzeichnis
        self.knoten = []

    #: Fuer die Anzeige — die Vorlage darf nicht in den Bezug greifen.
    @property
    def name(self):
        return self.bezug.anzeige

    @property
    def modul(self):
        return self.bezug.modul

    @property
    def zeile(self):
        return self.bezug.zeile

    def lesen(self):
        rumpf = getattr(self.bezug.knoten, 'body', [])
        self.knoten = self._folge(rumpf)
        return self

    # ── Der Rumpf, Anweisung fuer Anweisung ─────────────────────

    def _folge(self, anweisungen):
        aus = []
        for a in anweisungen:
            knoten = self._eine(a)
            if knoten is not None:
                aus.append(knoten)
        return aus

    def _eine(self, a):
        if isinstance(a, ast.If):
            frage = Frage(self._text(a.test), a.lineno)
            frage.ja = self._folge(a.body)
            frage.nein = self._folge(a.orelse)
            return frage
        if isinstance(a, (ast.For, ast.AsyncFor)):
            schleife = Wiederholung(
                u'für jedes %s in %s' % (self._text(a.target),
                                         self._text(a.iter)), a.lineno)
            schleife.rumpf = self._folge(a.body)
            return schleife
        if isinstance(a, ast.While):
            schleife = Wiederholung(u'solange %s' % self._text(a.test),
                                    a.lineno)
            schleife.rumpf = self._folge(a.body)
            return schleife
        if isinstance(a, ast.Try):
            sicher = Absicherung(u'versuchen', a.lineno)
            sicher.rumpf = self._folge(a.body)
            for h in a.handlers:
                sicher.sonst.extend(self._folge(h.body))
            sicher.immer = self._folge(a.finalbody)
            return sicher
        if isinstance(a, ast.Return):
            return Ende(u'zurück: %s' % self._text(a.value) if a.value
                        else u'zurück', a.lineno)
        if isinstance(a, ast.Raise):
            return Ende(u'Fehler: %s' % self._text(a.exc) if a.exc
                        else u'Fehler weiterreichen', a.lineno)
        if isinstance(a, ast.Break):
            return Ende(u'Schleife verlassen', a.lineno)
        if isinstance(a, ast.Continue):
            return Ende(u'nächster Durchgang', a.lineno)
        if isinstance(a, (ast.With, ast.AsyncWith)):
            # Ein `with` ist kein Ablaufschritt, sein Rumpf schon.
            aus = self._folge(a.body)
            return aus[0] if len(aus) == 1 else (
                self._buendeln(aus, a.lineno) if aus else None)
        return self._anweisung(a)

    @staticmethod
    def _buendeln(knoten, zeile):
        u"""Mehrere Knoten aus einem ``with`` als Schleifenrumpf halten —
        damit die Reihenfolge nicht verlorengeht."""
        traeger = Wiederholung(u'im Block', zeile)
        traeger.art = 'block'
        traeger.rumpf = knoten
        return traeger

    def _anweisung(self, a):
        u"""Eine gewoehnliche Zeile — nur zeigen, wenn sie etwas TUT.

        DER AEUSSERSTE AUFRUF ENTSCHEIDET (27.08.2026)
        ==============================================
        Erst nahm hier der erste NICHT-stumme Aufruf irgendwo in der Zeile
        das Ruder. Bei ``self.stdout.write(self.style.SUCCESS('...'))``
        war ``write`` stumm, ``SUCCESS`` nicht — und im Bild stand
        „style: SUCCESS". Das ist eine Ausgabe, keine Handlung, und der
        Kasten war reines Rauschen.

        Was die Zeile TUT, sagt ihr aeusserster Aufruf. Ist der stumm, ist
        es die ganze Zeile.
        """
        aeusserst = self._aeusserster(a)
        if aeusserst is None or not self._sagt_etwas(aeusserst):
            return None
        wichtig = [aeusserst]
        erster = wichtig[0]
        return Schritt(self._text(a), a.lineno, self._ziel(erster),
                       self._aufrufname(erster), self._empfaenger(erster),
                       self._merkmal(erster))

    @staticmethod
    def _aeusserster(a):
        u"""Der Aufruf, der diese Anweisung ausmacht — oder ``None``."""
        wert = getattr(a, 'value', None)
        if isinstance(wert, ast.Call):
            return wert
        for knoten in ast.iter_child_nodes(a):
            if isinstance(knoten, ast.Call):
                return knoten
        treffer = [k for k in ast.walk(a) if isinstance(k, ast.Call)]
        return treffer[0] if treffer else None

    @staticmethod
    def _aufrufname(aufruf):
        return (getattr(aufruf.func, 'attr', None)
                or getattr(aufruf.func, 'id', ''))

    @staticmethod
    def _merkmal(aufruf):
        u"""Das erste Argument — aber nur, wenn es ein einfacher Name ist.

        ``signal.SIGINT`` -> ``SIGINT``; ``'copy'`` -> ``copy``. Ein
        Ausdruck wie ``options['poll'] or 5`` wird NICHT genommen: Er
        macht den Kasten wieder zu Quelltext, und genau davon soll das
        Bild wegkommen.
        """
        for wert in list(aufruf.args)[:1]:
            if isinstance(wert, ast.Attribute):
                return wert.attr
            if isinstance(wert, ast.Name):
                return wert.id
            if isinstance(wert, ast.Constant) and isinstance(wert.value, str):
                return wert.value[:24]
        return ''

    @staticmethod
    def _empfaenger(aufruf):
        u"""``self.service.prepare()`` -> ``service``; ``self.tun()`` -> ''.

        ``self`` faellt weg: Es sagt nur „dieses Objekt" und steht in
        jedem zweiten Kasten — als Gegenstand waere es Rauschen.
        """
        wert = getattr(aufruf.func, 'value', None)
        if isinstance(wert, ast.Attribute):
            return wert.attr
        if isinstance(wert, ast.Name) and wert.id not in ('self', 'cls'):
            return wert.id
        return ''

    @staticmethod
    def _sagt_etwas(aufruf):
        name = (getattr(aufruf.func, 'attr', None)
                or getattr(aufruf.func, 'id', ''))
        return name not in STUMM

    def _ziel(self, aufruf):
        u"""``Klasse.methode`` im Projekt — oder leer."""
        if self.verzeichnis is None:
            return ''
        name = (getattr(aufruf.func, 'attr', None)
                or getattr(aufruf.func, 'id', ''))
        # NICHT RATEN: `self.log.start(...)` traf sonst irgendeine freie
        # Funktion namens `start`, weil `methode('start')` wegen
        # Mehrdeutigkeit None liefert und der naechste Versuch zugriff.
        if self.verzeichnis.mehrdeutig(name):
            return ''
        bezug = (self.verzeichnis.methode(name)
                 or self.verzeichnis.funktionen.get(name)
                 or self.verzeichnis.klassen.get(name))
        return bezug.anzeige if bezug is not None else ''

    # ── Beschriftung ────────────────────────────────────────────

    @staticmethod
    def _text(knoten):
        u"""Die Zeile, wie sie dasteht — gekuerzt.

        ``ast.unparse`` statt eigener Formatierung: Was dort herauskommt,
        ist gueltiges Python und damit dasselbe, was im Editor steht.
        """
        if knoten is None:
            return ''
        try:
            roh = ast.unparse(knoten)
        except Exception:
            return ''
        roh = ' '.join(roh.split())
        return roh if len(roh) <= BREIT else roh[:BREIT - 1] + u'…'

    def als_dict(self):
        return {'name': self.bezug.anzeige, 'modul': self.bezug.modul,
                'zeile': self.bezug.zeile,
                'knoten': [k.als_dict() for k in self.knoten]}
