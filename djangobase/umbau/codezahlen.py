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

from .klassenmodell import AUS, ausser

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
#:
#: WARUM AUCH „ÜBRIGE" (02.09.2026)
#: ================================
#: Edgar: „bei Statistik habe ich über 3 Millionen leere Zeilen bei Übrige?
#: was ist das". Es waren die `.eml`-Dateien des Mail-Archivs — 45.000 Stück
#: unter `Mail-Archive/`, jede byteweise als Text gelesen. Eine „leere Zeile"
#: in einer E-Mail ist die Trennung zwischen Kopf und Rumpf, keine
#: Quelltextzeile.
#:
#: „Übrige" ist per Definition das, was dieses Werkzeug NICHT kennt. Eine
#: Zeilenzahl darüber ist keine Auskunft, sondern Rauschen — und in der
#: Summenzeile verdirbt sie jede andere Zahl. Gezählt werden deshalb nur noch
#: Dateien und Bytes; WAS dort liegt, sagt `uebrige_arten()` nach Endung.
NICHT_LESEN = frozenset((u'Bilder & Binäres', UEBRIGE))

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


def ablagen(wurzel):
    u"""Verzeichnisse, die das Projekt SELBST als Ablage angemeldet hat.

    WARUM NICHT WIEDER EINE NAMENSLISTE (02.09.2026)
    ================================================
    `DATEN` oben ist geraten: `media`, `logs`, `tmp` … Namen, die man kennt.
    `Mail-Archive/` stand nicht darin, und so zählten 45.000 `.eml`-Dateien
    als Quelldateien des Projekts — über drei Millionen Zeilen. Die nächste
    Anwendung legt ihre Daten unter einem anderen Namen ab, und die Liste
    liegt wieder daneben.

    Django benennt Ablagen konventionell mit ``…_ROOT``: ``MEDIA_ROOT``,
    ``STATIC_ROOT``, hier ``MAIL_ARCHIVE_ROOT``. **Kein** Setting auf
    ``_ROOT`` bezeichnet Quelltext. Der Plural ``…_DIRS`` dagegen schon —
    ``STATICFILES_DIRS`` zeigt in `assistant` auf `templates/css`, also
    ausdrücklich auf Quelltext; er wird nicht angefasst. ``BASE_DIR`` ist das
    Projekt selbst und ebenso ausgenommen (``ROOT_URLCONF`` endet nicht auf
    ``_ROOT``, sondern beginnt damit — er trifft die Prüfung gar nicht).

    Zurück kommt ein Tupel relativer Pfadteile, kein blosser Name: Läge das
    Archiv unter ``daten/mail``, dürfte nicht ganz ``daten/`` wegfallen.
    """
    try:
        from django.conf import settings
        wurzel = Path(wurzel).resolve()
        namen = dir(settings)
    except Exception:                       # kein Django, keine Ablagen
        return ()
    raus = set()
    for name in namen:
        if not name.endswith('_ROOT') or name == 'BASE_DIR':
            continue
        try:
            wert = getattr(settings, name)
        except Exception:
            continue
        if not isinstance(wert, (str, Path)):
            continue
        try:
            teile = Path(wert).resolve().relative_to(wurzel).parts
        except (ValueError, OSError):       # ausserhalb des Projekts
            continue
        if teile:
            raus.add(teile)
    # Untergeordnete wegwerfen: `Mail-Archive/trash` sagt nichts mehr, wenn
    # `Mail-Archive` schon draussen ist — sonst zaehlt die Meldung doppelt.
    return tuple(sorted(
        t for t in raus
        if not any(a != t and t[:len(a)] == a for a in raus)))


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
        u"""Alle Felder — plus ``gelesen``.

        NULL IST KEIN MESSERGEBNIS (02.09.2026): „Bilder & Binäres" und
        „Übrige" werden nur gezählt, nicht zeilenweise gelesen. In der
        Tabelle stand dafür `0` — und `0 Zeilen` liest sich wie „diese
        Dateien sind leer", nicht wie „hier wurde nicht gezählt". Dasselbe
        Argument wie bei ``ausserhalb``, das aus diesem Grund `None` trägt.
        """
        raus = dict((f, getattr(self, f)) for f in self.__slots__)
        raus['gelesen'] = self.name not in NICHT_LESEN
        return raus


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
        #: ``{Endung: [Dateien, Bytes, Beispielpfad]}`` — was in „Übrige"
        #: steckt. Ohne diese Aufschlüsselung ist die Zeile eine Zahl ohne
        #: Auskunft, und genau danach wurde gefragt.
        self.uebrige = {}

    # ── einlesen ────────────────────────────────────────────────
    def lesen(self):
        raus = ausser()      # samt der virtuellen Umgebungen des Projekts
        anmeldungen = ablagen(self.wurzel)
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
            # Vom Projekt angemeldete Ablagen (…_ROOT) — dieselbe Behandlung
            # wie `DATEN`: ausgelassen, aber GENANNT.
            angemeldet = next((a for a in anmeldungen
                               if teile[:len(a)] == a), None)
            if angemeldet is not None:
                self._auslassen('/'.join(angemeldet))
                continue
            if any(teil in raus for teil in teile):
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

    def _uebrig(self, pfad, groesse):
        u"""Eine Datei ohne bekannte Art vermerken — nach Endung.

        Als Beispiel steht die GRÖSSTE Datei der Endung, nicht die erste:
        Bei 385 Dateien ohne Endung ist die erste zufällig (`.gitignore`),
        die grösste dagegen sagt, worum es geht.
        """
        punkt = pfad.name.rfind('.')
        endung = pfad.name[punkt:].lower() if punkt > 0 else u'(ohne Endung)'
        try:
            name = str(pfad.relative_to(self.wurzel))
        except ValueError:
            name = pfad.name
        eintrag = self.uebrige.get(endung)
        if eintrag is None:
            self.uebrige[endung] = [1, groesse, name, groesse]
            return
        eintrag[0] += 1
        eintrag[1] += groesse
        if groesse > eintrag[3]:
            eintrag[2] = name
            eintrag[3] = groesse

    def _eine(self, pfad):
        art = self.art(pfad.name)
        zahlen = self.arten.setdefault(art, Artzahlen(art))
        zahlen.dateien += 1
        groesse = 0
        try:
            groesse = pfad.stat().st_size
            zahlen.bytes += groesse
        except OSError:
            pass
        if art == UEBRIGE:
            self._uebrig(pfad, groesse)
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
        innen = Codezahlen._klassenzeilen(baum)
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                zahlen.klassen += 1
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # NUR FUNKTIONEN AUSSERHALB VON KLASSEN (02.09.2026, auf
                # Ansage: „Spalte Funktionen — wenn die innerhalb von
                # Klassen sind dann lass die weg").
                #
                # Vorher zählte hier jedes `def`: Methoden, freie und
                # verschachtelte zusammen. Die Zahl war damit
                # bedeutungslos — sie sagte ungefähr „wie viel Code",
                # nicht „wie viel hängt an keiner Klasse". Genau das ist
                # aber die Frage, um die es auf dieser Seite geht.
                if knoten.lineno not in innen:
                    zahlen.funktionen += 1
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

    def uebrige_arten(self, hoechstens=25):
        u"""Woraus die Zeile „Übrige" besteht — nach Endung, grösste zuerst.

        Die Zeile nennt eine Zahl und lässt offen, wofür sie steht. Am
        02.09.2026 waren es 45.000 `.eml`-Dateien, und die Frage „was ist
        das?" liess sich nur mit einem eigenen Skript beantworten. Diese
        Auskunft steht seither auf der Seite selbst.
        """
        # ``schluessel`` ist der Wert, den der Löschen-Knopf zurückschickt:
        # die Endung selbst, oder ``(ohne)`` für die ohne. Ein LEERER Wert
        # ginge nicht — im Formular wäre er von „fehlt" nicht zu
        # unterscheiden, und das Löschen träfe dann alles oder nichts.
        from .uebrigesuche import geschuetzt      # spät: Kreis vermeiden
        raus = [{'endung': endung, 'dateien': n, 'bytes': b,
                 'mb': round(b / 1048576.0, 2), 'beispiel': beispiel,
                 'groesste': gross,
                 'groesste_mb': round(gross / 1048576.0, 2),
                 'schluessel': ('(ohne)' if endung == u'(ohne Endung)'
                                else endung),
                 # Geschützte Arten bekommen keinen Löschen-Knopf. Sie
                 # bleiben SICHTBAR — dass 10 `.xlsm` im Projektbaum
                 # liegen, ist eine Auskunft; sie von hier aus löschen zu
                 # können war der Fehler (02.09.2026).
                 'loeschbar': not geschuetzt(endung)}
                for endung, (n, b, beispiel, gross) in self.uebrige.items()]
        raus.sort(key=lambda e: (-e['dateien'], e['endung']))
        return raus[:hoechstens]

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


__all__ = ['ARTEN', 'UEBRIGE', 'ablagen', 'Artzahlen', 'Codezahlen']
