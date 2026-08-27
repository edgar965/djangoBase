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

    def __init__(self, name, bezug=None, empfaenger=''):
        self.name = name or ''
        #: Die gerufene Definition — fuer den Docstring. Darf fehlen.
        self.bezug = bezug
        #: ``self.service`` -> ``service``; steht als Gegenstand davor.
        self.empfaenger = empfaenger

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
                   getattr(knoten, 'empfaenger', '')).satz()

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
        return angaben

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
            return '%s: %s' % (self._gegenstand(), satz)
        return satz

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
