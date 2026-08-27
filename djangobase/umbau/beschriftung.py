# -*- coding: utf-8 -*-
u"""Aus einem Aufruf einen lesbaren Satz machen — ohne zu erfinden.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „mach mir die grafische Ausgabe von vorher, kein Quelltext, aber
     sowas in der Richtung des Screenshots. Ideen?"

Die Vorlage zeigt „Nächsten Datensatz holen". Mein erstes Bild zeigte
``self.service.wait(1.0)``. Der Unterschied ist nicht die FORM, sondern
der TEXT.

DREI QUELLEN, GEMESSEN
======================
Woher kann ein solcher Satz kommen, ohne ihn zu erfinden?

    1  der Docstring der gerufenen Funktion   16 % (gemessen)
    2  der Name, als Woerter gelesen         ~85 %
    3  erfunden                               VERBOTEN

Nummer 1 waere die schoenste Quelle: Prosa, vom Entwickler geschrieben.
Gemessen an den zwanzig schwersten Ablaeufen in CamTrack trifft sie aber
nur 37 von 236 Schritten — und einmal falsch, weil ein mehrdeutiger Name
(``flush``) auf die falsche Klasse zeigte.

Nummer 2 ist das Arbeitspferd: ``_install_signal_handlers`` wird zu
„install signal handlers". Das ist keine Uebersetzung, sondern DIESELBEN
Woerter, nur ohne Unterstriche — genau wie ``Testsatz`` es fuer
Pruefnamen tut. Wer den Namen gut gewaehlt hat, bekommt einen guten Satz;
wer ihn schlecht gewaehlt hat, sieht das jetzt.

WARUM NICHT UEBERSETZT WIRD
===========================
Ein Woerterbuch ``prepare -> vorbereiten`` waere schnell geschrieben und
waere eine Erfindung: Es behauptet, ``prepare`` bedeute hier
„vorbereiten", und niemand hat das geprueft. Bei ``handle``, ``run`` oder
``process`` waere die Behauptung schon fast sicher falsch.

Das Bild sagt darum lieber „was der Entwickler geschrieben hat, in
lesbar" als „was ich glaube, dass er gemeint hat".
"""
import ast
import re

#: Wortanfaenge, die im Namen keine eigene Trennung verdienen.
ZUSAMMEN = ('Js', 'Ui', 'Db', 'Api', 'Id', 'Ip', 'Url')

#: Vorsaetze, die nichts ueber die Handlung sagen.
VORSATZ = ('_', 'do_', 'get_', 'set_')

#: Hoechstlaenge eines Kastentextes.
BREIT = 46


class Beschriftung:
    u"""Der Satz zu EINEM Aufruf.

        >>> Beschriftung('_install_signal_handlers').satz()
        'install signal handlers'
    """

    def __init__(self, name, bezug=None, empfaenger='', merkmal=''):
        self.name = name or ''
        #: Die gerufene Definition — fuer den Docstring. Darf fehlen.
        self.bezug = bezug
        #: ``self.service`` -> ``service``; steht als Gegenstand davor.
        self.empfaenger = empfaenger
        #: Das erste Argument, wenn es die Handlung unterscheidet.
        self.merkmal = merkmal

    @classmethod
    def fuer(cls, knoten, verzeichnis=None):
        u"""Der Satz zu EINEM Ablauf-Knoten.

        Die Zuordnung gehoert hierher und nicht in die Ansicht: Sonst
        beschriftet jede Seite anders, und zwei Bilder desselben Ablaufs
        sagen Verschiedenes.
        """
        art = getattr(knoten, 'art', '')
        if art == 'frage':
            return u'%s?' % cls(knoten.text)._kuerzen(knoten.text)
        if art in ('schleife', 'block', 'absicherung'):
            return cls(knoten.text)._kuerzen(knoten.text)
        if art == 'ende':
            return cls(knoten.text)._kuerzen(knoten.text)
        bezug = None
        ziel = getattr(knoten, 'ziel', '')
        if ziel and verzeichnis is not None:
            klasse, _punkt, name = ziel.rpartition('.')
            bezug = (verzeichnis.in_klasse(klasse, name) if klasse
                     else verzeichnis.funktionen.get(name))
        return cls(getattr(knoten, 'aufruf', '') or knoten.text, bezug,
                   getattr(knoten, 'empfaenger', ''),
                   getattr(knoten, 'merkmal', '')).satz()

    @classmethod
    def herkunft(cls, knoten, verzeichnis=None):
        u"""Woher dieser Kasten kommt — Klasse, Methode, Modul, Zeile.

        DIE ANSAGE (Edgar, 27.08.2026)
        ==============================
            „kannst du hover und popups machen, die bei Klick auf einen
             Bereich die Klasse und die Methode anzeigt?"

        Der Satz im Kasten ist Prosa und sagt darum NICHT, wo das steht.
        Beides zugleich in den Kasten zu schreiben ginge nicht — dann
        waere er wieder Quelltext.

        Zwei Zeilen werden unterschieden:

            zeile     wo der AUFRUF steht (im gezeigten Ablauf)
            ziel_*    wo die gerufene Funktion DEFINIERT ist

        Das ist nicht dasselbe, und wer springen will, meint meist das
        zweite.
        """
        angaben = {
            'quelle': getattr(knoten, 'text', ''),
            'zeile': getattr(knoten, 'zeile', 0),
            'art': getattr(knoten, 'art', ''),
        }
        ziel = getattr(knoten, 'ziel', '')
        if not ziel or verzeichnis is None:
            return angaben
        klasse, _punkt, name = ziel.rpartition('.')
        if klasse:
            bezug = verzeichnis.in_klasse(klasse, name)
            angaben['klasse'] = klasse
            angaben['methode'] = name
        elif name in verzeichnis.klassen:
            # ERZEUGEN IST KEIN METHODENAUFRUF (27.08.2026)
            # `self.service = RecordingService(...)` stand als
            # „Methode: RecordingService" im Fenster. Hier wird eine
            # KLASSE gebaut; wer das verwechselt, sucht die Methode im
            # falschen Modul.
            bezug = verzeichnis.klassen[name]
            angaben['klasse'] = name
            angaben['erzeugt'] = 'ja'
        else:
            bezug = verzeichnis.funktionen.get(name)
            angaben['funktion'] = name
        if bezug is not None:
            angaben['modul'] = bezug.modul
            angaben['zielzeile'] = bezug.zeile
            angaben['doku'] = cls('', bezug).aus_doku()
            angaben['voll'] = cls._voll(bezug)
            rufer = cls._ruferliste(bezug, verzeichnis)
            if rufer:
                angaben['gerufenvon'] = '|'.join(rufer)
                angaben['ruferzahl'] = len(rufer)
        return angaben

    @staticmethod
    def _voll(bezug):
        u"""Die Kennung, wie man sie nennt: ``Klasse.methode``.

        OBEN STEHT, WORUM ES GEHT (27.08.2026, auf Ansage)
        =================================================
            „mach doch oben Klasse.Methode"

        Bei einer freien Funktion gibt es keine Klasse. Dann traegt der
        LETZTE Teil des Moduls den Gegenstand: ``path_resolver
        .get_trt_cache_dir``. Der ganze Modulpfad waere zu lang fuer eine
        Ueberschrift und steht ohnehin darunter.
        """
        if getattr(bezug, 'klasse', ''):
            return '%s.%s' % (bezug.klasse, bezug.name)
        letzter = str(getattr(bezug, 'modul', '')).rsplit('.', 1)[-1]
        return '%s.%s' % (letzter, bezug.name) if letzter else bezug.name

    #: So viele Rufer nennt das Fenster; darüber wird nur gezählt.
    RUFER = 6

    @classmethod
    def _ruferliste(cls, bezug, verzeichnis):
        u"""Wer ruft diese Stelle sonst noch? — als LISTE, nicht als Satz.

            „auch von wem die aufgerufen wird … darunter, ebenfalls
             Klasse.Methode" (Edgar, 27.08.2026)

        Ein Bild zeigt EINEN Weg. „Wer ruft das hier eigentlich?" ist die
        Frage, die man stellt, bevor man etwas aendert — und die das Bild
        nicht beantwortet, weil die anderen Rufer nicht darin stehen.

        ALS LISTE, NICHT ALS FLIESSTEXT: Vier Namen hintereinander
        („AdaFaceEmbedder._init_session, Command.handle, TrtWarmupRunner
        .cache_dir, trt_cache_dir") laufen ueber zwei Zeilen um und sind
        nicht mehr auseinanderzuhalten. Untereinander liest man sie.

        Gekuerzt wird trotzdem: Dreissig Namen beantworten die Frage auch
        nicht mehr, sie verdecken sie. Die GESAMTZAHL bleibt daneben
        stehen — sie sagt, wie weit eine Aenderung reicht.
        """
        try:
            rufer = verzeichnis.rufer(bezug.schluessel)
        except (AttributeError, TypeError):
            return []
        namen = sorted({r.anzeige for r in rufer})
        if len(namen) <= cls.RUFER:
            return namen
        return namen[:cls.RUFER] + [u'… und %d weitere'
                                    % (len(namen) - cls.RUFER)]

    # ── Der Satz ────────────────────────────────────────────────

    def satz(self):
        u"""Docstring, sonst der Name als Woerter."""
        aus = self.aus_doku() or self.aus_namen()
        return self._kuerzen(aus)

    def aus_doku(self):
        u"""Die erste Zeile des Docstrings — wenn es eine gibt.

        Nur die ERSTE Zeile, und nur wenn sie ein Satz ist: Ein Docstring,
        der mit ``>>>`` oder einer Ueberschrift anfaengt, beschreibt nicht
        die Handlung.
        """
        if self.bezug is None:
            return ''
        try:
            doku = ast.get_docstring(self.bezug.knoten)
        except (TypeError, AttributeError):
            return ''
        if not doku:
            return ''
        erste = doku.strip().splitlines()[0].strip()
        if not erste or erste.startswith(('>>>', '=', '-', '#')):
            return ''
        return erste.rstrip('.')

    def aus_namen(self):
        u"""``_install_signal_handlers`` -> ``install signal handlers``."""
        name = self.name
        for vor in VORSATZ:
            if name.startswith(vor) and len(name) > len(vor):
                name = name[len(vor):]
                break
        woerter = self._trennen(name)
        if not woerter:
            return self.name
        satz = ' '.join(woerter)
        if self.empfaenger and self.empfaenger not in ('self', 'cls'):
            gegenstand = self._gegenstand()
            # KEIN STOTTERN (27.08.2026, auf Ansage „zweimal signal:signal")
            # ================================================================
            # `signal.signal(signal.SIGINT, …)` und `signal.signal(
            # signal.SIGTERM, …)` standen beide als „signal: signal"
            # untereinander — zwei Kaesten, die dasselbe behaupteten und
            # den Unterschied verschwiegen.
            #
            # Heisst der Empfaenger wie der Aufruf, sagt die Wiederholung
            # nichts. Dann traegt das erste Argument die Unterscheidung.
            if gegenstand.lower() == satz.lower():
                if self.merkmal:
                    return '%s: %s' % (satz, self._klarname(self.merkmal))
                return satz
            return '%s: %s' % (gegenstand, satz)
        if self.merkmal and len(woerter) == 1:
            # Auch ohne Empfaenger kann ein Aufruf nichtssagend sein:
            # `sleep(0.5)` gegen `sleep(interval)`.
            return '%s: %s' % (satz, self._klarname(self.merkmal))
        return satz

    def _klarname(self, wert):
        u"""Das Argument lesbar, aber unveraendert: ``SIGINT`` bleibt."""
        return ' '.join(self._trennen(wert)) if '_' in str(wert) else str(wert)

    def _gegenstand(self):
        return ' '.join(self._trennen(self.empfaenger))

    # ── Kleinteile ──────────────────────────────────────────────

    @staticmethod
    def _trennen(name):
        u"""Unterstriche UND Binnengrossschreibung — beides kommt vor."""
        roh = []
        for teil in str(name).split('_'):
            if not teil:
                continue
            # `[A-Z]+(?![a-z])` haelt Abkuerzungen zusammen: Ohne das
            # wurde aus `SUCCESS` ein „S U C C E S S".
            roh.extend(re.findall(
                r'[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+', teil)
                or [teil])
        aus = []
        for wort in roh:
            if aus and aus[-1] in ZUSAMMEN:
                aus[-1] = aus[-1] + wort
            else:
                aus.append(wort)
        return aus

    @staticmethod
    def _kuerzen(text):
        text = ' '.join(str(text).split())
        if len(text) <= BREIT:
            return text
        # An einer Wortgrenze kuerzen — mitten im Wort liest sich schlechter.
        schnitt = text.rfind(' ', 0, BREIT - 1)
        return text[:schnitt if schnitt > BREIT // 2 else BREIT - 1] + u'…'
