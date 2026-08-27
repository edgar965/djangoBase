# -*- coding: utf-8 -*-
u"""Wie groß ist dieses Projekt — Dateien, Zeilen, Klassen, nach Art getrennt.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „ein Button der eine Statistik macht: Anzahl Dateien, Anzahl py
     Code-Dateien, Anzahl html, js, sonstige (mach Vorschlag). Anzahl
     Code-Zeilen gesamt, py, js, htm usw. Anzahl Klassen (py, js)"

DIE EINTEILUNG — DER VORSCHLAG
==============================
Sieben Arten statt „py / html / js / sonstige". Der Grund steht in der
Spalte „Übrige": Wer alles außer dreien dorthin schiebt, bekommt einen
Posten, der größer ist als alle anderen zusammen, und lernt nichts.

    Python           .py
    HTML-Vorlagen    .html .htm
    JavaScript       .js .mjs
    Stilblätter      .css
    Einstellungen    .json .yml .yaml .ini .cfg .toml .xml
    Dokumentation    .md .rst .txt
    Bilder & Binäres .png .jpg .svg .ico .woff … (nur gezählt, nicht gelesen)
    Übrige           alles andere

DREI ZEILENARTEN, NICHT EINE
============================
„Anzahl Code-Zeilen" ist mehrdeutig. Eine Datei mit 200 Zeilen, davon 120
Kommentar, ist etwas anderes als 200 Zeilen Anweisungen — und in DIESEM
Projekt ist der Unterschied groß, weil die Dateien ihre Vorgeschichte im
Kopf tragen. Gezählt wird deshalb getrennt: Anweisungen, Kommentar, leer.

Bei Python zählt der AST, nicht ein Muster: `#` in einer Zeichenkette ist
kein Kommentar, und ein Docstring ist keine Anweisung.
"""
import ast
import io
import re
from pathlib import Path

from .klassenmodell import AUS

#: Die Arten, in der Reihenfolge der Anzeige. Erste Übereinstimmung gilt.
ARTEN = (
    (u'Python', ('.py',)),
    (u'HTML-Vorlagen', ('.html', '.htm')),
    (u'JavaScript', ('.js', '.mjs')),
    (u'Stilblätter', ('.css',)),
    (u'Einstellungen', ('.json', '.yml', '.yaml', '.ini', '.cfg', '.toml',
                        '.xml')),
    (u'Dokumentation', ('.md', '.rst', '.txt')),
    (u'Bilder & Binäres', ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                           '.webp', '.woff', '.woff2', '.ttf', '.eot',
                           '.pdf', '.zip', '.mp4', '.pt', '.engine',
                           '.onnx', '.pyc', '.exe', '.dll')),
)

#: Was in keine Art passt. Fällt nicht weg — sonst stimmt die Summe nicht.
UEBRIGE = u'Übrige'

#: Diese Arten werden nur gezählt, nicht zeilenweise gelesen.
NICHT_LESEN = frozenset((u'Bilder & Binäres',))

#: Laufzeitdaten — gehören nicht in eine Statistik über QUELLTEXT.
#:
#: WAS DER ERSTE LAUF ZEIGTE (24.08.2026)
#: ======================================
#: „Übrige: 47 Dateien, 4.858.015 Zeilen" — mehr als das ganze übrige
#: Projekt zusammen. Es waren die `.pkl`-Zwischenspeicher des Kalenders,
#: byteweise als Text gelesen. Daneben `media/` mit 2673 Bildern und
#: Videos, darunter eines mit **1,7 GB**. Das Verzeichnis heisst nicht
#: umsonst so: Dort liegt, was die Anlage im Betrieb erzeugt.
DATEN = ('media', 'logs', 'log', '.cache', 'tmp', 'temp', 'output',
         'htmlcov', 'dist', 'build', '_build', '.pytest_cache', '.idea')

#: Über dieser Grösse ist es kein Quelltext mehr, egal wie es heisst.
#: Die längste Datei dieses Projekts hat 126 KB; das Modell daneben 174 MB.
GROESSTE_QUELLDATEI = 2 * 1024 * 1024

#: `class Name {` und `class Name extends X {` — die ES6-Schreibweise.
JS_KLASSE = re.compile(r'^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)',
                       re.MULTILINE)
#: `function name(`, `name(…) {` als Methode, und `const name = (…) =>`.
JS_FUNKTION = re.compile(
    r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)'
    r'|^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
    re.MULTILINE)


class Artzahlen:
    u"""Was von EINER Art zusammenkommt."""

    #: ``ausserhalb`` = Anweisungszeilen, die in KEINER Klasse stehen
    #: (27.08.2026, auf Ansage). Die Spalte „Klassen" sagt, wie viele es
    #: gibt - nicht, wie viel Code an gar keiner haengt. Genau das ist der
    #: Massstab aus Kriterium 1 und 18: Modulebene ist Zustand und Ablauf,
    #: der niemandem gehoert.
    #:
    #: NUR PYTHON WIRD GEZAEHLT. Dort sagt der Syntaxbaum die Klassenspanne
    #: eindeutig (``lineno`` bis ``end_lineno``, samt Dekoratoren). Bei
    #: JavaScript muesste man Klammern zaehlen und dabei Zeichenketten,
    #: Vorlagen-Literale und Kommentare auseinanderhalten - eine Zahl, die
    #: manchmal danebenliegt, ist hier schlimmer als keine. Arten ohne
    #: Klassenbegriff (HTML, CSS) tragen deshalb ``None``, nicht 0: Die
    #: Vorlage zeigt dann „-" statt einer Null, die wie ein Messergebnis
    #: aussaehe.
    __slots__ = ('name', 'dateien', 'zeilen', 'anweisungen', 'kommentar',
                 'leer', 'klassen', 'funktionen', 'bytes', 'ausserhalb')

    def __init__(self, name):
        self.name = name
        self.dateien = 0
        self.zeilen = 0
        self.anweisungen = 0
        self.kommentar = 0
        self.leer = 0
        self.klassen = 0
        self.funktionen = 0
        self.bytes = 0
        #: None = fuer diese Art nicht ermittelbar (siehe __slots__ oben).
        self.ausserhalb = None

    def als_dict(self):
        return dict((f, getattr(self, f)) for f in self.__slots__)


class Codezahlen:
    u"""Zählt ein Projektverzeichnis aus."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        #: ``{Artname: Artzahlen}``
        self.arten = {}
        #: Dateien, die sich nicht lesen liessen.
        self.unlesbar = 0
        #: Laufzeitdaten, die nicht mitgezählt wurden — samt Verzeichnis.
        self.ausgelassen = 0
        self.ausgelassen_wo = {}

    # ── einlesen ────────────────────────────────────────────────
    def lesen(self):
        for pfad in self.wurzel.rglob('*'):
            if not pfad.is_file():
                continue
            # NUR DER TEIL INNERHALB DES PROJEKTS ZAEHLT (24.08.2026).
            # Vorher stand hier `pfad.parts` — der ABSOLUTE Pfad. Ein
            # Projekt unter `C:\Users\…\Temp\…` verschwand damit
            # vollstaendig, weil `temp` in `DATEN` steht. Aufgefallen ist
            # es in den eigenen Pruefungen, die genau dort ablegen; in
            # einem Projekt unter `C:\build\…` waere es dasselbe gewesen.
            teile = self._innen(pfad)
            # LAUFZEITDATEN ZUERST - sie werden GENANNT, nicht verschwiegen
            # (27.08.2026).
            #
            # ``AUS`` und ``DATEN`` ueberschneiden sich seit ``tmp``/``temp``
            # in beiden stehen. AUS zuerst zu pruefen liess einen tmp-Ordner
            # STILL verschwinden: weder gezaehlt noch als ausgelassen
            # vermerkt. Genau das darf dieses Werkzeug nicht - „1.119 Dateien"
            # liest sich sonst wie das ganze Verzeichnis.
            #
            # Die Ergaenzung von AUS kam aus dem Wegenetz („laesst fremden
            # Code aus") und ist dort richtig; AUS ist aber eine GETEILTE
            # Konstante, und der zweite Nutzer hat eine andere Zusage. Die
            # Reihenfolge hier loest das, ohne einem der beiden etwas
            # wegzunehmen.
            daten = [t for t in teile[:-1] if t.lower() in self.DATEN]
            if daten:
                self._auslassen(daten[0])
                continue
            if any(teil in AUS for teil in teile):
                continue
            try:
                if pfad.stat().st_size > GROESSTE_QUELLDATEI:
                    self._auslassen(u'zu groß')
                    continue
            except OSError:
                pass
            self._eine(pfad)
        return self

    #: Als Attribut, damit ein Projekt die Liste erweitern kann.
    DATEN = frozenset(DATEN)

    def _innen(self, pfad):
        u"""Die Pfadteile INNERHALB des Projekts — nie die davor."""
        try:
            return pfad.relative_to(self.wurzel).parts
        except ValueError:
            return pfad.parts

    def _auslassen(self, wo):
        self.ausgelassen += 1
        self.ausgelassen_wo[wo] = self.ausgelassen_wo.get(wo, 0) + 1

    def _eine(self, pfad):
        art = self.art(pfad.name)
        zahlen = self.arten.setdefault(art, Artzahlen(art))
        zahlen.dateien += 1
        try:
            zahlen.bytes += pfad.stat().st_size
        except OSError:
            pass
        if art in NICHT_LESEN:
            return
        try:
            text = pfad.read_text(encoding='utf-8', errors='replace')
        except OSError:
            self.unlesbar += 1
            return
        if art == u'Python':
            self._python(text, zahlen)
        else:
            self._zeilenweise(text, zahlen,
                              art in (u'JavaScript', u'Stilblätter'))
            if art == u'JavaScript':
                zahlen.klassen += len(JS_KLASSE.findall(text))
                zahlen.funktionen += len(JS_FUNKTION.findall(text))

    # ── je Art ──────────────────────────────────────────────────
    @staticmethod
    def _python(text, zahlen):
        u"""Bei Python entscheidet der AST, nicht ein Muster.

        `#` in einer Zeichenkette ist kein Kommentar, und ein Docstring ist
        keine Anweisung. Wer das mit `startswith('#')` zählt, bekommt in
        einem Projekt mit langen Vorgeschichten im Kopf jeder Datei eine
        Zahl, die um Prozente danebenliegt.
        """
        zeilen = text.splitlines()
        zahlen.zeilen += len(zeilen)
        anweisungszeilen = []
        for nr, zeile in enumerate(zeilen, start=1):
            blank = zeile.strip()
            if not blank:
                zahlen.leer += 1
            elif blank.startswith('#'):
                zahlen.kommentar += 1
            else:
                zahlen.anweisungen += 1
                anweisungszeilen.append(nr)
        try:
            baum = ast.parse(text)
        except (SyntaxError, ValueError):
            # Ohne Baum ist die Klassenspanne unbekannt. Die Datei zaehlt
            # bei den Zeilen mit, aber NICHT bei „ausserhalb" - sonst
            # zaehlte eine kaputte Datei als lauter globaler Code.
            return
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                zahlen.klassen += 1
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                zahlen.funktionen += 1
        innen = Codezahlen._klassenzeilen(baum)
        if zahlen.ausserhalb is None:
            zahlen.ausserhalb = 0
        zahlen.ausserhalb += sum(1 for nr in anweisungszeilen if nr not in innen)

    @staticmethod
    def _klassenzeilen(baum):
        u"""Alle Zeilennummern, die INNERHALB einer Klasse liegen.

        Dekoratoren gehoeren dazu: ``@dataclass`` ueber ``class Punkt``
        steht vor ``lineno`` und ist trotzdem Teil der Klasse. Verschachtelte
        Klassen brauchen nichts Eigenes - ihre Spanne liegt in der aeusseren.
        """
        innen = set()
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.ClassDef):
                continue
            anfang = knoten.lineno
            for schmuck in getattr(knoten, 'decorator_list', ()):
                anfang = min(anfang, getattr(schmuck, 'lineno', anfang))
            ende = getattr(knoten, 'end_lineno', None) or anfang
            innen.update(range(anfang, ende + 1))
        return innen

    @staticmethod
    def _zeilenweise(text, zahlen, mit_schraegstrich=False):
        zeilen = text.splitlines()
        zahlen.zeilen += len(zeilen)
        for zeile in zeilen:
            blank = zeile.strip()
            if not blank:
                zahlen.leer += 1
            elif (blank.startswith('<!--')
                  or (mit_schraegstrich and (blank.startswith('//')
                                             or blank.startswith('/*')
                                             or blank.startswith('*')))):
                zahlen.kommentar += 1
            else:
                zahlen.anweisungen += 1

    # ── Auskunft ────────────────────────────────────────────────
    @staticmethod
    def art(dateiname):
        u"""Die Art einer Datei am Suffix."""
        punkt = dateiname.rfind('.')
        endung = dateiname[punkt:].lower() if punkt > 0 else ''
        for name, endungen in ARTEN:
            if endung in endungen:
                return name
        return UEBRIGE

    def liste(self):
        u"""Alle Arten in der Reihenfolge von ``ARTEN``, Übrige zuletzt.

        Auch die leeren: Dass ein Projekt KEIN JavaScript hat, ist eine
        Auskunft, und eine fehlende Zeile liest sich als Versehen.
        """
        raus = []
        for name, _e in ARTEN:
            raus.append((self.arten.get(name) or Artzahlen(name)).als_dict())
        raus.append((self.arten.get(UEBRIGE) or Artzahlen(UEBRIGE)).als_dict())
        return raus

    def gesamt(self):
        u"""Die Summe über alle Arten — dieselben Felder."""
        summe = Artzahlen(u'Gesamt')
        for zahlen in self.arten.values():
            for feld in ('dateien', 'zeilen', 'anweisungen', 'kommentar',
                         'leer', 'klassen', 'funktionen', 'bytes'):
                setattr(summe, feld,
                        getattr(summe, feld) + getattr(zahlen, feld))
            # ``ausserhalb`` getrennt: None heisst „nicht ermittelbar" und
            # darf nicht als 0 in die Summe. Bleibt KEINE Art messbar, bleibt
            # auch die Summe None - eine 0 saehe aus wie „kein globaler Code".
            if zahlen.ausserhalb is not None:
                summe.ausserhalb = (summe.ausserhalb or 0) + zahlen.ausserhalb
        return summe.als_dict()

    def kennzahlen(self):
        u"""Die wenigen Zahlen für die Karten oben."""
        gesamt = self.gesamt()
        py = (self.arten.get(u'Python') or Artzahlen(u'Python')).als_dict()
        js = (self.arten.get(u'JavaScript')
              or Artzahlen(u'JavaScript')).als_dict()
        return {
            'dateien': gesamt['dateien'],
            'zeilen': gesamt['zeilen'],
            'anweisungen': gesamt['anweisungen'],
            'klassen': gesamt['klassen'],
            'py_dateien': py['dateien'],
            'py_zeilen': py['zeilen'],
            'py_klassen': py['klassen'],
            'py_ausserhalb': py['ausserhalb'],
            'js_dateien': js['dateien'],
            'js_zeilen': js['zeilen'],
            'js_klassen': js['klassen'],
            # Wie viel vom Quelltext ist Erklärung? In diesem Projekt eine
            # aussagekräftige Zahl, weil die Vorgeschichte im Kopf steht.
            'kommentar_anteil': (
                round(100.0 * gesamt['kommentar']
                      / max(1, gesamt['zeilen'] - gesamt['leer']), 1)),
        }


__all__ = ['ARTEN', 'UEBRIGE', 'Artzahlen', 'Codezahlen']
